import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from importlib.metadata import entry_points
from pathlib import Path

import pytest
from token_economics_contracts import PriceBook, PriceBookViolation, PriceRow
from token_economics_svc_pricebook import SqlitePriceBook, open_pricebook

AT = datetime(2026, 11, 1, tzinfo=UTC)


def new_row(rid: str = "x1", read: str = "0.1") -> PriceRow:
    return PriceRow(
        price_row_id=rid,
        provider="anthropic",
        model="test-model",
        effective_from=datetime(2026, 2, 1, tzinfo=UTC),
        input=Decimal("1"),
        output=Decimal("5"),
        cache_read=Decimal(read),
        cache_write_5m=Decimal("1.25"),
        cache_write_1h=Decimal("2"),
    )


def test_store_serves_the_price_book_port_and_is_registered() -> None:
    assert isinstance(SqlitePriceBook(":memory:"), PriceBook)
    eps = entry_points(group="token_economics.services")
    assert eps["pricebook"].load() is open_pricebook


def test_seed_rows_load_once_and_survive_a_reopen(tmp_path: Path) -> None:
    # Given a new price store  # When it is opened twice
    first = SqlitePriceBook(tmp_path / "prices.sqlite")
    n = len(first.rows())
    first.close()
    second = SqlitePriceBook(tmp_path / "prices.sqlite")
    # Then the seed rows are there once, and a lookup works
    assert n > 0 and len(second.rows()) == n
    assert second.lookup("anthropic", "claude-opus-5-5", AT, 1_000).input == Decimal("4")


def test_added_row_round_trips_exactly(tmp_path: Path) -> None:
    book = SqlitePriceBook(tmp_path / "p.sqlite", seed=False)
    assert book.add(new_row()) is True and book.add(new_row()) is False
    book.close()
    assert SqlitePriceBook(tmp_path / "p.sqlite", seed=False).get("x1") == new_row()


def test_a_stored_price_cannot_be_rewritten(tmp_path: Path) -> None:
    # Given a stored row
    path = tmp_path / "p.sqlite"
    book = SqlitePriceBook(path, seed=False)
    book.add(new_row())
    # When a different price is offered under the same id  # Then it is refused and nothing was written
    with pytest.raises(PriceBookViolation):
        book.add(new_row(read="0.05"))
    assert book.get("x1").cache_read == Decimal("0.1")
    # And even a direct connection cannot update or delete it
    raw = sqlite3.connect(path)
    with pytest.raises(sqlite3.DatabaseError):
        raw.execute("UPDATE price_rows SET row_json = '{}'")
    with pytest.raises(sqlite3.DatabaseError):
        raw.execute("DELETE FROM price_rows")
