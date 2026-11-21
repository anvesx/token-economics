"""One SQLite connection behind a lock. Every table is append-only: triggers abort UPDATE and DELETE."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS keys (
    key_id TEXT PRIMARY KEY,
    key_hash BLOB NOT NULL UNIQUE,
    tenant TEXT NOT NULL,
    team TEXT NOT NULL,
    caller TEXT NOT NULL,
    agent TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS revocations (
    key_id TEXT PRIMARY KEY,
    revoked_at TEXT NOT NULL,
    actor TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
    ts TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    subject TEXT NOT NULL,
    detail TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS audit_ts ON audit (ts);
"""
_TABLES = ("keys", "revocations", "audit")


def _triggers() -> str:
    return "".join(
        f"CREATE TRIGGER IF NOT EXISTS {t}_no_update BEFORE UPDATE ON {t} "
        f"BEGIN SELECT RAISE(ABORT, '{t} is append-only: UPDATE is not allowed'); END;\n"
        f"CREATE TRIGGER IF NOT EXISTS {t}_no_delete BEFORE DELETE ON {t} "
        f"BEGIN SELECT RAISE(ABORT, '{t} is append-only: DELETE is not allowed'); END;\n"
        for t in _TABLES
    )


class Database:
    """Connection plus lock. Callers take `lock` around every use of `conn`."""

    def __init__(self, path: Path | str) -> None:
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None, timeout=5.0)
        with self.lock:
            if str(path) != ":memory:":
                self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.executescript(_SCHEMA + _triggers())

    def close(self) -> None:
        with self.lock:
            self.conn.close()
