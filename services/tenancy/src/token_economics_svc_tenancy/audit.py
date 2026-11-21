"""Append-only audit log. Secrets cannot be logged: a value holding a key or provider token is refused."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from ._db import Database

_FORBIDDEN = ("vk-", "sk-ant")


class AuditEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    ts: datetime
    actor: str
    action: str
    subject: str
    detail: dict[str, Any]


def now_text() -> str:
    """Fixed-width UTC text, so text order is time order."""
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _checked_detail(action: str, subject: str, actor: str, detail: Mapping[str, Any]) -> str:
    text = json.dumps(dict(detail), default=str, sort_keys=True)
    for part in (action, subject, actor, text):
        for bad in _FORBIDDEN:
            if bad in part:
                raise ValueError(f"audit entry refused: it contains {bad!r}, which looks like a secret")
    return text


def append(conn: sqlite3.Connection, action: str, subject: str, detail: Mapping[str, Any], actor: str) -> None:
    """Insert one entry on an existing connection (the caller holds the lock and any transaction)."""
    text = _checked_detail(action, subject, actor, detail)
    conn.execute(
        "INSERT INTO audit (ts, actor, action, subject, detail) VALUES (?, ?, ?, ?, ?)",
        (now_text(), actor, action, subject, text),
    )


class AuditLog:
    """Who did what to which key, in the same database as the keys. Insert and select only."""

    def __init__(self, db: Database) -> None:
        self._db = db

    @classmethod
    def open(cls, state_dir: Path | str) -> AuditLog:
        path = Path(state_dir)
        path.mkdir(parents=True, exist_ok=True)
        return cls(Database(path / "tenancy.sqlite"))

    def record(self, action: str, subject: str, detail: Mapping[str, Any], actor: str = "system") -> None:
        with self._db.lock:
            append(self._db.conn, action, subject, detail, actor)

    def entries(self, since: datetime | None = None) -> list[AuditEntry]:
        """Entries with `ts >= since`, oldest first."""
        sql = "SELECT ts, actor, action, subject, detail FROM audit"
        args: list[str] = []
        if since is not None:
            if since.tzinfo is None:
                raise ValueError("since must be timezone-aware")
            sql += " WHERE ts >= ?"
            args.append(since.astimezone(UTC).isoformat(timespec="microseconds"))
        with self._db.lock:
            records = self._db.conn.execute(sql + " ORDER BY ts, rowid", args).fetchall()
        return [
            AuditEntry(ts=datetime.fromisoformat(ts), actor=a, action=ac, subject=s, detail=json.loads(d))
            for ts, a, ac, s, d in records
        ]

    def close(self) -> None:
        self._db.close()
