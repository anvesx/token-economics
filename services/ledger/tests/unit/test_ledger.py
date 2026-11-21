import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from token_economics_contracts.ports import Ledger
from token_economics_contracts.registry import SERVICES, load
from token_economics_contracts.types import Buckets, CostSource, LedgerRow
from token_economics_svc_ledger import SqliteLedger, open_ledger

T0 = datetime(2026, 1, 1, 12, tzinfo=UTC)


def make_row(response_id: str = "r1", provider: str = "anthropic", ts: datetime = T0, **kw: object) -> LedgerRow:
    base: dict[str, object] = dict(
        provider=provider, response_id=response_id, ts=ts, model="m",
        buckets=Buckets(fresh_input=10, output=5), cost_estimate_usd=Decimal("0.0123"),
        cost_source=CostSource.GATEWAY, price_row_id="p1",
    )  # fmt: skip
    return LedgerRow(**(base | kw))  # type: ignore[arg-type]  # test helper merges plain kwargs


def test_ledger_satisfies_port_and_registers_as_entry_point():
    # Given the installed package
    # When the services entry point named ledger is loaded and called
    factory = load(SERVICES, "ledger")
    # Then it yields an object that implements the Ledger port
    assert factory is open_ledger
    assert isinstance(factory(":memory:"), Ledger)


def test_duplicate_response_id_writes_one_row_and_keeps_first_values():
    # Given a ledger that already holds a row for a response id
    ledger = SqliteLedger(":memory:")
    assert ledger.write(make_row(model="first")) is True
    # When the same response id arrives again with different values
    second = ledger.write(make_row(model="second", buckets=Buckets(output=99)))
    # Then write returns False and the first row is unchanged
    assert second is False
    assert ledger.count("r1") == 1
    (row,) = ledger.rows()
    assert row.model == "first" and row.buckets.output == 5


def test_same_response_id_under_two_providers_is_two_rows():
    # Given one response id
    ledger = SqliteLedger(":memory:")
    # When two providers each write it
    a = ledger.write(make_row(provider="anthropic"))
    b = ledger.write(make_row(provider="openai"))
    # Then both are kept
    assert a and b
    assert ledger.count("r1") == 2


def test_empty_response_id_is_rejected():
    # Given a row with no response id
    ledger = SqliteLedger(":memory:")
    # When it is written
    # Then it is refused, since it cannot be deduped
    with pytest.raises(ValueError, match="response_id"):
        ledger.write(make_row(response_id=""))
    assert ledger.rows() == []


def test_naive_timestamp_is_rejected():
    # Given a row with a timezone-naive ts
    ledger = SqliteLedger(":memory:")
    # When it is written
    # Then it is refused, since its order against other rows is ambiguous
    with pytest.raises(ValueError, match="timezone"):
        ledger.write(make_row(ts=datetime(2026, 1, 1)))


def test_raw_update_and_delete_are_refused(tmp_path: Path):
    # Given a ledger file with one row
    path = tmp_path / "l.db"
    SqliteLedger(path).write(make_row())
    # When a raw connection tries to rewrite or remove history
    raw = sqlite3.connect(path)
    # Then both fail and the row is intact
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        raw.execute("UPDATE ledger SET model = 'x'")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        raw.execute("DELETE FROM ledger")
    assert raw.execute("SELECT model FROM ledger").fetchall() == [("m",)]


def test_rows_filters_by_since_inclusive_and_until_exclusive():
    # Given rows an hour apart, written out of order
    ledger = SqliteLedger(":memory:")
    for i in (2, 0, 1):
        ledger.write(make_row(response_id=f"r{i}", ts=T0 + timedelta(hours=i)))
    # When filtering by since and until
    # Then the window is [since, until) and ordered by ts
    assert [r.response_id for r in ledger.rows()] == ["r0", "r1", "r2"]
    assert [r.response_id for r in ledger.rows(since=T0 + timedelta(hours=1))] == ["r1", "r2"]
    assert [r.response_id for r in ledger.rows(until=T0 + timedelta(hours=1))] == ["r0"]
    assert [r.response_id for r in ledger.rows(T0 + timedelta(hours=1), T0 + timedelta(hours=2))] == ["r1"]


def test_equal_timestamps_keep_insertion_order():
    # Given rows with the same ts
    ledger = SqliteLedger(":memory:")
    for i in ("b", "a", "c"):
        ledger.write(make_row(response_id=i))
    # When read back
    # Then insertion order breaks the tie
    assert [r.response_id for r in ledger.rows()] == ["b", "a", "c"]


def test_fifty_threads_writing_same_response_id_leave_one_row():
    # Given one shared ledger
    ledger = SqliteLedger(":memory:")
    results: list[bool] = []
    barrier = threading.Barrier(50)

    def work() -> None:
        barrier.wait()
        results.append(ledger.write(make_row()))

    # When 50 threads write the same response id at once
    threads = [threading.Thread(target=work) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # Then exactly one write won and one row exists
    assert results.count(True) == 1 and results.count(False) == 49
    assert ledger.count("r1") == 1


def test_file_database_reopened_still_has_its_rows(tmp_path: Path):
    # Given rows written to a file database that is then closed
    path = tmp_path / "l.db"
    first = SqliteLedger(path)
    first.write(make_row("a"))
    first.write(make_row("b"))
    first.close()
    # When it is opened again
    again = SqliteLedger(str(path))
    # Then the rows are there, duplicates are still refused, and WAL is on
    assert [r.response_id for r in again.rows()] == ["a", "b"]
    assert again.write(make_row("a")) is False
    assert sqlite3.connect(path).execute("PRAGMA journal_mode").fetchone() == ("wal",)
