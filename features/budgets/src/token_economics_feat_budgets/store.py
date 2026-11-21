"""Budget store: spend, reservations and sent alerts in SQLite. Money is whole micro-dollars.

This is working state, not the ledger: rows here are updated. The ledger stays the record of what was spent.
Reserve-then-true-up runs in one `BEGIN IMMEDIATE` transaction, so parallel requests (and other processes) cannot
both pass a check that only one of them fits under.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

_SCHEMA = """
CREATE TABLE IF NOT EXISTS spend (
    scope TEXT NOT NULL, win TEXT NOT NULL, period TEXT NOT NULL, micro INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (scope, win, period)
);
CREATE TABLE IF NOT EXISTS reservations (
    request_id TEXT NOT NULL, scope TEXT NOT NULL, win TEXT NOT NULL, period TEXT NOT NULL,
    micro INTEGER NOT NULL, expires_at REAL NOT NULL,
    PRIMARY KEY (request_id, scope, win)
);
CREATE TABLE IF NOT EXISTS alerts_sent (
    scope TEXT NOT NULL, win TEXT NOT NULL, period TEXT NOT NULL, threshold TEXT NOT NULL,
    PRIMARY KEY (scope, win, period, threshold)
);
CREATE TABLE IF NOT EXISTS limits (
    kind TEXT NOT NULL, match TEXT NOT NULL, win TEXT NOT NULL, micro INTEGER NOT NULL,
    PRIMARY KEY (kind, match, win)
);
"""


@dataclass(frozen=True)
class Slot:
    """One budget a request counts against: a scope ("caller:dhruv"), a window and its current period."""

    scope: str
    win: str
    period: str
    limit_micro: int


@dataclass(frozen=True)
class Refusal:
    slot: Slot
    spent_micro: int
    reserved_micro: int


class BudgetStore:
    def __init__(self, path: str | Path) -> None:
        self._lock = Lock()
        self._db = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None, timeout=10.0)
        if str(path) != ":memory:":
            self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(_SCHEMA)

    def reserve(self, request_id: str, slots: Sequence[Slot], micro: int, now: float, ttl_s: float) -> Refusal | None:
        """Hold `micro` against every slot, or hold nothing and say which slot has no room."""
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                self._db.execute("DELETE FROM reservations WHERE expires_at <= ?", (now,))  # leaked reservations expire
                for slot in slots:
                    spent, reserved = self._used(slot)
                    if spent + reserved + micro > slot.limit_micro:
                        self._db.execute("ROLLBACK")
                        return Refusal(slot, spent, reserved)
                for slot in slots:
                    self._db.execute(
                        "INSERT OR REPLACE INTO reservations VALUES (?, ?, ?, ?, ?, ?)",
                        (request_id, slot.scope, slot.win, slot.period, micro, now + ttl_s),
                    )
                self._db.execute("COMMIT")
                return None
            except BaseException:
                self._db.execute("ROLLBACK")
                raise

    def settle(self, request_id: str, slots: Sequence[Slot], micro: int) -> list[tuple[Slot, int, int]]:
        """Replace the reservation with the true cost. Returns (slot, spent before, spent after) per slot."""
        out = []
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                self._db.execute("DELETE FROM reservations WHERE request_id = ?", (request_id,))
                for slot in slots:
                    before, _ = self._used(slot)
                    if micro:
                        self._db.execute(
                            "INSERT INTO spend (scope, win, period, micro) VALUES (?, ?, ?, ?) "
                            "ON CONFLICT (scope, win, period) DO UPDATE SET micro = micro + excluded.micro",
                            (slot.scope, slot.win, slot.period, micro),
                        )
                    out.append((slot, before, before + micro))
                self._db.execute("COMMIT")
            except BaseException:
                self._db.execute("ROLLBACK")
                raise
        return out

    def mark_alert(self, slot: Slot, threshold: str) -> bool:
        """True the first time this threshold is crossed for the slot's period."""
        with self._lock:
            cur = self._db.execute(
                "INSERT OR IGNORE INTO alerts_sent VALUES (?, ?, ?, ?)", (slot.scope, slot.win, slot.period, threshold)
            )
            return cur.rowcount == 1

    def used(self, slot: Slot) -> tuple[int, int]:
        with self._lock:
            return self._used(slot)

    def _used(self, slot: Slot) -> tuple[int, int]:
        key = (slot.scope, slot.win, slot.period)
        spent = self._db.execute("SELECT micro FROM spend WHERE scope = ? AND win = ? AND period = ?", key).fetchone()
        reserved = self._db.execute(
            "SELECT COALESCE(SUM(micro), 0) FROM reservations WHERE scope = ? AND win = ? AND period = ?", key
        ).fetchone()
        return (int(spent[0]) if spent else 0, int(reserved[0]))

    def save_limits(self, limits: Iterable[tuple[str, str, str, int]]) -> None:
        """Record the configured limits so read-only reports can show them."""
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            self._db.execute("DELETE FROM limits")
            self._db.executemany("INSERT OR REPLACE INTO limits VALUES (?, ?, ?, ?)", list(limits))
            self._db.execute("COMMIT")

    def limits(self) -> list[tuple[str, str, str, int]]:
        with self._lock:
            return [tuple(r) for r in self._db.execute("SELECT kind, match, win, micro FROM limits ORDER BY 1, 2, 3")]

    def scopes(self, kind: str, win: str, period: str) -> list[str]:
        """Scopes of one kind with spend or reservations in a period."""
        with self._lock:
            rows = self._db.execute(
                "SELECT scope FROM spend WHERE win = ? AND period = ? AND scope LIKE ? "
                "UNION SELECT scope FROM reservations WHERE win = ? AND period = ? AND scope LIKE ?",
                (win, period, kind + ":%", win, period, kind + ":%"),
            )
            return sorted(r[0] for r in rows)

    def close(self) -> None:
        self._db.close()
