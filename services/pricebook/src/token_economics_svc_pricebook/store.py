"""The price store: price rows in SQLite, append-only, served through the PriceBook port."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Sequence
from datetime import datetime
from pathlib import Path
from threading import Lock

from token_economics_contracts import PriceRow
from token_economics_pricebook_core import PriceBookCore, seed_rows

_SCHEMA = """
CREATE TABLE IF NOT EXISTS price_rows (
    price_row_id TEXT PRIMARY KEY CHECK (price_row_id <> ''),
    added_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    row_json     TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS price_rows_no_update BEFORE UPDATE ON price_rows
BEGIN SELECT RAISE(ABORT, 'the price book is append-only'); END;
CREATE TRIGGER IF NOT EXISTS price_rows_no_delete BEFORE DELETE ON price_rows
BEGIN SELECT RAISE(ABORT, 'the price book is append-only'); END;
"""


class SqlitePriceBook:
    """Price rows on disk, with the lookup rules of pricebook-core. A stored row is never changed or removed."""

    def __init__(self, path: str | Path, *, seed: bool = True) -> None:
        self._lock = Lock()
        self._db = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        if str(path) != ":memory:":
            self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(_SCHEMA)
        stored = [
            PriceRow.model_validate_json(j)
            for (j,) in self._db.execute("SELECT row_json FROM price_rows ORDER BY rowid")
        ]
        self._core = PriceBookCore(stored)
        if seed:
            self.add_all(seed_rows())

    def add(self, row: PriceRow) -> bool:
        """Append one row. False when the identical row is already stored. Raises PriceBookViolation on a conflict."""
        with self._lock:
            if not self._core.add(row):  # validates before anything is written
                return False
            self._db.execute(
                "INSERT INTO price_rows (price_row_id, row_json) VALUES (?, ?)",
                (row.price_row_id, row.model_dump_json()),
            )
            return True

    def add_all(self, rows: Iterable[PriceRow]) -> int:
        return sum(self.add(r) for r in rows)

    def rows(self) -> Sequence[PriceRow]:
        return self._core.rows()

    def get(self, price_row_id: str) -> PriceRow:
        return self._core.get(price_row_id)

    def lookup(
        self,
        provider: str,
        model: str,
        at: datetime,
        prompt_tokens: int,
        service_tier: str = "standard",
        region: str = "",
    ) -> PriceRow:
        return self._core.lookup(provider, model, at, prompt_tokens, service_tier, region)

    def stale(self, now: datetime) -> Sequence[PriceRow]:
        return self._core.stale(now)

    def close(self) -> None:
        self._db.close()


def open_pricebook(path: str, seed: bool = True) -> SqlitePriceBook:
    return SqlitePriceBook(path, seed=seed)
