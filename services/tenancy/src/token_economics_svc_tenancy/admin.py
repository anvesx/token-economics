"""Admin tokens for the admin API: role-based, hashed at rest, shown once at issue. Revoked, never deleted."""

from __future__ import annotations

import builtins
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from ._db import Database
from .audit import append, now_text

Role = Literal["viewer", "operator", "admin"]
ROLES: tuple[Role, ...] = ("viewer", "operator", "admin")  # lowest first


def role_at_least(have: str, need: str) -> bool:
    """True when role `have` ranks at or above `need`. An unknown role never passes."""
    return have in ROLES and need in ROLES and ROLES.index(have) >= ROLES.index(need)


class AdminIdentity(BaseModel):
    model_config = ConfigDict(frozen=True)

    token_id: str
    name: str
    role: Role


class AdminTokenRecord(BaseModel):
    """One stored token as `list()` shows it: never the plaintext, never the hash."""

    model_config = ConfigDict(frozen=True)

    token_id: str
    name: str
    role: Role
    created_at: datetime
    revoked_at: datetime | None = None


def _digest(plaintext: str) -> bytes:
    return hashlib.sha256(plaintext.encode()).digest()


class AdminAuth:
    """Issue, resolve and revoke admin tokens in `tenancy.sqlite`. Every change is audited. No cache: a revoked token
    is refused on its next use."""

    def __init__(self, db: Database) -> None:
        self._db = db

    @classmethod
    def open(cls, state_dir: Path | str) -> AdminAuth:
        path = Path(state_dir)
        path.mkdir(parents=True, exist_ok=True)
        return cls(Database(path / "tenancy.sqlite"))

    def issue(self, name: str, role: Role, *, actor: str = "cli") -> tuple[str, str]:
        """A new token: `(plaintext, token_id)`. The plaintext is returned once and not kept. Names are unique."""
        if role not in ROLES:
            raise ValueError(f"role must be one of {ROLES}")
        if not name.strip():
            raise ValueError("name must not be empty")
        plaintext = "adm-" + secrets.token_urlsafe(24)
        digest = _digest(plaintext)
        token_id = digest.hex()[:16]
        with self._db.lock:
            conn = self._db.conn
            conn.execute("BEGIN IMMEDIATE")
            try:
                if conn.execute("SELECT 1 FROM admin_tokens WHERE name = ?", (name,)).fetchone():
                    raise ValueError(f"an admin token for {name!r} already exists")
                conn.execute(
                    "INSERT INTO admin_tokens (token_id, token_hash, name, role, created_at) VALUES (?, ?, ?, ?, ?)",
                    (token_id, digest, name, role, now_text()),
                )
                append(conn, "admin_token_issued", token_id, {"name": name, "role": role}, actor)
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return plaintext, token_id

    def resolve(self, presented: str) -> AdminIdentity | None:
        """The identity for a live token, or None for an empty, unknown or revoked one."""
        if not presented:
            return None
        with self._db.lock:
            found = self._db.conn.execute(
                "SELECT t.token_id, t.name, t.role, r.token_id IS NOT NULL FROM admin_tokens t "
                "LEFT JOIN admin_revocations r ON r.token_id = t.token_id WHERE t.token_hash = ?",
                (_digest(presented),),
            ).fetchone()
        if found is None or found[3]:
            return None
        return AdminIdentity(token_id=found[0], name=found[1], role=found[2])

    def revoke(self, token_id: str, *, actor: str = "cli") -> bool:
        """False when there is no such token or it is already revoked."""
        with self._db.lock:
            conn = self._db.conn
            conn.execute("BEGIN IMMEDIATE")
            try:
                known = conn.execute("SELECT 1 FROM admin_tokens WHERE token_id = ?", (token_id,)).fetchone()
                done = conn.execute("SELECT 1 FROM admin_revocations WHERE token_id = ?", (token_id,)).fetchone()
                ok = known is not None and done is None
                if ok:
                    conn.execute(
                        "INSERT INTO admin_revocations (token_id, revoked_at, actor) VALUES (?, ?, ?)",
                        (token_id, now_text(), actor),
                    )
                    append(conn, "admin_token_revoked", token_id, {}, actor)
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return ok

    def has_tokens(self) -> bool:
        """True once any token was ever issued, revoked or not, so revoking the last one never reopens the API."""
        with self._db.lock:
            return self._db.conn.execute("SELECT 1 FROM admin_tokens LIMIT 1").fetchone() is not None

    def list(self) -> builtins.list[AdminTokenRecord]:
        with self._db.lock:
            records = self._db.conn.execute(
                "SELECT t.token_id, t.name, t.role, t.created_at, r.revoked_at FROM admin_tokens t "
                "LEFT JOIN admin_revocations r ON r.token_id = t.token_id ORDER BY t.created_at, t.rowid"
            ).fetchall()
        return [
            AdminTokenRecord(
                token_id=i,
                name=n,
                role=r,
                created_at=datetime.fromisoformat(c),
                revoked_at=None if v is None else datetime.fromisoformat(v),
            )
            for i, n, r, c, v in records
        ]

    def close(self) -> None:
        self._db.close()
