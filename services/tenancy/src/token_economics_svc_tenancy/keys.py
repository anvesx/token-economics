"""Virtual keys hashed at rest. The plaintext is shown once at issue and never stored or logged."""

from __future__ import annotations

import builtins
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from token_economics_contracts import KeyInfo, ResolvedKey

from ._db import Database
from .audit import AuditLog, append, now_text

_NOTE = "These keys moved to tenancy.sqlite, hashed. This file no longer holds any key.\n"
_REFRESH_S = 0.5  # a key revoked by another process (the CLI) takes effect within about this long


class KeyRecord(BaseModel):
    """One stored key as `list()` shows it: never the plaintext, never the hash."""

    model_config = ConfigDict(frozen=True)

    key_id: str
    info: KeyInfo
    created_at: datetime
    revoked_at: datetime | None = None


def _digest(plaintext: str) -> bytes:
    return hashlib.sha256(plaintext.encode()).digest()


def _key_id(digest: bytes) -> str:
    return digest.hex()[:16]


class KeyStore:
    """The `KeyResolver` port on SQLite. One connection behind a lock; safe to share between threads."""

    def __init__(self, state_dir: Path | str, *, refresh_s: float = _REFRESH_S) -> None:
        path = Path(state_dir)
        path.mkdir(parents=True, exist_ok=True)
        self._init(Database(path / "tenancy.sqlite"), refresh_s)

    @classmethod
    def in_memory(cls) -> KeyStore:
        self = cls.__new__(cls)
        self._init(Database(":memory:"), _REFRESH_S)
        return self

    def _init(self, db: Database, refresh_s: float) -> None:
        self._db = db
        self._refresh_s = refresh_s
        self.audit = AuditLog(db)
        self._cache_lock = threading.Lock()
        self._cache: dict[bytes, tuple[str, KeyInfo, bool]] = {}
        self._loaded_at = float("-inf")

    def issue(self, info: KeyInfo, *, actor: str = "cli") -> tuple[str, str]:
        """A new key: `(plaintext, key_id)`. The plaintext is returned once and not kept."""
        plaintext = "vk-" + secrets.token_urlsafe(24)
        return plaintext, self._insert(plaintext, info, actor, "key_issued")

    def _insert(self, plaintext: str, info: KeyInfo, actor: str, action: str) -> str:
        digest = _digest(plaintext)
        key_id = _key_id(digest)
        with self._db.lock:
            conn = self._db.conn
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT INTO keys (key_id, key_hash, tenant, team, caller, agent, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (key_id, digest, info.tenant, info.team, info.caller, info.agent, now_text()),
                )
                append(conn, action, key_id, {"tenant": info.tenant, "caller": info.caller}, actor)
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        self._invalidate()
        return key_id

    def revoke(self, key_id: str, *, actor: str = "cli") -> bool:
        """Revoke a key. False when there is no such key or it is already revoked."""
        with self._db.lock:
            conn = self._db.conn
            conn.execute("BEGIN IMMEDIATE")
            try:
                known = conn.execute("SELECT 1 FROM keys WHERE key_id = ?", (key_id,)).fetchone()
                done = conn.execute("SELECT 1 FROM revocations WHERE key_id = ?", (key_id,)).fetchone()
                ok = known is not None and done is None
                if ok:
                    conn.execute(
                        "INSERT INTO revocations (key_id, revoked_at, actor) VALUES (?, ?, ?)",
                        (key_id, now_text(), actor),
                    )
                    append(conn, "key_revoked", key_id, {}, actor)
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        self._invalidate()
        return ok

    def resolve(self, presented: str) -> ResolvedKey:
        if not presented:
            return ResolvedKey(info=KeyInfo(tenant="unknown"), status="none")
        digest = _digest(presented)
        found = None
        for stored, value in self._snapshot().items():
            if hmac.compare_digest(stored, digest):
                found = value
        if found is None:
            return ResolvedKey(info=KeyInfo(tenant="unknown"), status="unknown")
        key_id, info, revoked = found
        return ResolvedKey(key_id=key_id, info=info, status="revoked" if revoked else "active")

    def _invalidate(self) -> None:
        with self._cache_lock:
            self._loaded_at = float("-inf")

    def _snapshot(self) -> dict[bytes, tuple[str, KeyInfo, bool]]:
        with self._cache_lock:
            if time.monotonic() - self._loaded_at < self._refresh_s:
                return self._cache
            with self._db.lock:
                records = self._db.conn.execute(
                    "SELECT k.key_hash, k.key_id, k.tenant, k.team, k.caller, k.agent, r.key_id IS NOT NULL "
                    "FROM keys k LEFT JOIN revocations r ON r.key_id = k.key_id"
                ).fetchall()
            self._cache = {
                bytes(h): (kid, KeyInfo(tenant=t, team=tm, caller=c, agent=a), bool(rev))
                for h, kid, t, tm, c, a, rev in records
            }
            self._loaded_at = time.monotonic()
            return self._cache

    def list(self) -> builtins.list[KeyRecord]:
        with self._db.lock:
            records = self._db.conn.execute(
                "SELECT k.key_id, k.tenant, k.team, k.caller, k.agent, k.created_at, r.revoked_at "
                "FROM keys k LEFT JOIN revocations r ON r.key_id = k.key_id ORDER BY k.created_at, k.rowid"
            ).fetchall()
        return [
            KeyRecord(
                key_id=kid,
                info=KeyInfo(tenant=t, team=tm, caller=c, agent=a),
                created_at=datetime.fromisoformat(created),
                revoked_at=None if revoked is None else datetime.fromisoformat(revoked),
            )
            for kid, t, tm, c, a, created, revoked in records
        ]

    def import_legacy(self, path: Path) -> int:
        """Import a P0 plaintext `keys.json` (the same plaintext keeps working), then scrub and rename it.

        Returns the number of keys newly added. Safe to repeat: keys already stored are skipped.
        """
        path = Path(path)
        if not path.exists():
            return 0
        raw = json.loads(path.read_text())
        if not isinstance(raw, dict):
            raise ValueError(f"{path} is not a JSON object of key to identity")
        added = 0
        for plaintext, fields in raw.items():
            info = KeyInfo(**fields)
            with self._db.lock:
                exists = self._db.conn.execute(
                    "SELECT 1 FROM keys WHERE key_hash = ?", (_digest(plaintext),)
                ).fetchone()
            if exists is None:
                self._insert(plaintext, info, "legacy-import", "key_imported")
                added += 1
        path.write_text(_NOTE)
        os.replace(path, path.with_name(path.name + ".imported"))
        return added

    def close(self) -> None:
        self._db.close()
