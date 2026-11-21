"""SQLite ledger. Insert and select only: history is frozen (plan/03, rule 7)."""
from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from token_economics_contracts.types import Buckets, CostSource, LedgerRow, QuerySource

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ledger (
    provider TEXT NOT NULL,
    response_id TEXT NOT NULL CHECK (response_id <> ''),
    request_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    tenant TEXT NOT NULL,
    team TEXT NOT NULL,
    caller TEXT NOT NULL,
    agent TEXT NOT NULL,
    harness TEXT NOT NULL,
    session_id TEXT NOT NULL,
    prompt_id TEXT NOT NULL,
    query_source TEXT NOT NULL,
    model TEXT NOT NULL,
    service_tier TEXT NOT NULL,
    speed TEXT NOT NULL,
    effort TEXT NOT NULL,
    inference_geo TEXT NOT NULL,
    ttl_class TEXT NOT NULL,
    fresh_input INTEGER NOT NULL,
    cache_read INTEGER NOT NULL,
    cache_write_5m INTEGER NOT NULL,
    cache_write_1h INTEGER NOT NULL,
    output INTEGER NOT NULL,
    cost_estimate_usd TEXT,
    cost_source TEXT NOT NULL,
    price_row_id TEXT NOT NULL,
    auth_mode TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    task_id TEXT NOT NULL,
    success INTEGER,
    http_status INTEGER NOT NULL,
    UNIQUE (provider, response_id)
);
CREATE INDEX IF NOT EXISTS ledger_ts ON ledger (ts);
CREATE TRIGGER IF NOT EXISTS ledger_no_update BEFORE UPDATE ON ledger
BEGIN SELECT RAISE(ABORT, 'ledger is append-only: UPDATE is not allowed'); END;
CREATE TRIGGER IF NOT EXISTS ledger_no_delete BEFORE DELETE ON ledger
BEGIN SELECT RAISE(ABORT, 'ledger is append-only: DELETE is not allowed'); END;
"""

_BUCKET_COLUMNS = ("fresh_input", "cache_read", "cache_write_5m", "cache_write_1h", "output")
_COLUMNS = (
    "provider", "response_id", "request_id", "ts", "tenant", "team", "caller", "agent", "harness",
    "session_id", "prompt_id", "query_source", "model", "service_tier", "speed", "effort", "inference_geo",
    "ttl_class", *_BUCKET_COLUMNS, "cost_estimate_usd", "cost_source", "price_row_id", "auth_mode",
    "attempt", "task_id", "success", "http_status",
)  # fmt: skip
_INSERT = (
    f"INSERT INTO ledger ({', '.join(_COLUMNS)}) VALUES ({', '.join('?' * len(_COLUMNS))}) "
    "ON CONFLICT (provider, response_id) DO NOTHING"
)
_SELECT = f"SELECT {', '.join(_COLUMNS)} FROM ledger"


def _ts_text(ts: datetime) -> str:
    """Fixed-width UTC text, so that text order is time order."""
    if ts.tzinfo is None:
        raise ValueError("ts must be timezone-aware")
    return ts.astimezone(UTC).isoformat(timespec="microseconds")


def _to_params(row: LedgerRow) -> tuple[Any, ...]:
    if not row.response_id:
        raise ValueError("a ledger row needs a response_id: without one it cannot be deduped")
    b = row.buckets
    return (
        row.provider, row.response_id, row.request_id, _ts_text(row.ts), row.tenant, row.team, row.caller,
        row.agent, row.harness, row.session_id, row.prompt_id, row.query_source.value, row.model,
        row.service_tier, row.speed, row.effort, row.inference_geo, row.ttl_class, b.fresh_input, b.cache_read,
        b.cache_write_5m, b.cache_write_1h, b.output,
        None if row.cost_estimate_usd is None else str(row.cost_estimate_usd), row.cost_source.value,
        row.price_row_id, row.auth_mode, row.attempt, row.task_id,
        None if row.success is None else int(row.success), row.http_status,
    )  # fmt: skip


def _from_record(rec: tuple[Any, ...]) -> LedgerRow:
    d = dict(zip(_COLUMNS, rec, strict=True))
    buckets = Buckets(**{k: d.pop(k) for k in _BUCKET_COLUMNS})
    cost = d.pop("cost_estimate_usd")
    success = d.pop("success")
    return _build(d, buckets, cost, success)


def _build(d: dict[str, Any], buckets: Buckets, cost: str | None, success: int | None) -> LedgerRow:
    d["ts"] = datetime.fromisoformat(d["ts"])
    d["query_source"] = QuerySource(d["query_source"])
    d["cost_source"] = CostSource(d["cost_source"])
    return LedgerRow(
        **d,
        buckets=buckets,
        cost_estimate_usd=None if cost is None else Decimal(cost),
        success=None if success is None else bool(success),
    )


class SqliteLedger:
    """The `Ledger` port on SQLite. One connection behind a lock; safe to share between threads."""

    def __init__(self, path: str | Path) -> None:
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        with self._lock:
            if str(path) != ":memory:":
                self._db.execute("PRAGMA journal_mode=WAL")
            self._db.executescript(_SCHEMA)

    def write(self, row: LedgerRow) -> bool:
        """Append a row. False when (provider, response_id) is already there; the stored row is not changed."""
        params = _to_params(row)
        with self._lock:
            return self._db.execute(_INSERT, params).rowcount == 1

    def rows(self, since: datetime | None = None, until: datetime | None = None) -> list[LedgerRow]:
        """Rows with `since <= ts < until`, ordered by ts then insertion."""
        where, args = [], []
        if since is not None:
            where.append("ts >= ?")
            args.append(_ts_text(since))
        if until is not None:
            where.append("ts < ?")
            args.append(_ts_text(until))
        sql = _SELECT + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY ts, rowid"
        with self._lock:
            records = self._db.execute(sql, args).fetchall()
        return [_from_record(r) for r in records]

    def count(self, response_id: str) -> int:
        """Rows holding this response id, across providers."""
        with self._lock:
            row: Iterable[int] = self._db.execute(
                "SELECT COUNT(*) FROM ledger WHERE response_id = ?", (response_id,)
            ).fetchone()
        return next(iter(row))

    def close(self) -> None:
        with self._lock:
            self._db.close()


def open_ledger(path: str) -> SqliteLedger:
    """Factory registered under the `token_economics.services` entry point as `ledger`."""
    return SqliteLedger(path)
