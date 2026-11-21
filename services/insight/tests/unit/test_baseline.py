from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from itertools import count
from typing import Any

from token_economics_contracts import Buckets, CostSource, LedgerRow
from token_economics_svc_insight import baseline, baseline_markdown

_ids = count(1)


def row(
    day: int,
    cost: str | None,
    *,
    caller: str = "ann",
    agent: str = "",
    model: str = "m1",
    source: CostSource = CostSource.GATEWAY,
    success: bool | None = None,
    hour: int = 10,
    **buckets: int,
) -> LedgerRow:
    return LedgerRow(
        provider="anthropic",
        response_id=f"r{next(_ids)}",
        ts=datetime(2026, 11, day, hour, tzinfo=UTC),
        caller=caller,
        agent=agent,
        model=model,
        buckets=Buckets(**buckets),
        cost_estimate_usd=None if cost is None else Decimal(cost),
        cost_source=source,
        price_row_id="" if cost is None else "p1",
        success=success,
    )


def dev(report: Any, name: str) -> Any:
    return next(d for d in report.developers if d.developer == name)


def test_daily_mean_median_and_p95_are_exact_for_a_known_series() -> None:
    # Given ann spent 1, 2, 3, 4 and 10 dollars on five days (the first day over two requests)
    rows = [row(1, "0.40"), row(1, "0.60"), row(2, "2"), row(3, "3"), row(4, "4"), row(5, "10")]
    # When
    d = dev(baseline(rows), "ann")
    # Then mean 4, median 3, nearest-rank P95 is the 5th of 5 values
    assert (d.requests, d.active_days, d.total_spend_usd) == (6, 5, Decimal("20.00"))
    assert d.mean_daily_usd == Decimal("4")
    assert d.median_daily_usd == Decimal("3")
    assert d.p95_daily_usd == Decimal("10")


def test_median_of_an_even_number_of_days_is_the_mean_of_the_middle_two() -> None:
    # Given four days: 1, 2, 3, 4
    d = dev(baseline([row(i, str(i)) for i in (1, 2, 3, 4)]), "ann")
    # Then
    assert d.median_daily_usd == Decimal("2.5") and d.p95_daily_usd == Decimal("4")


def test_p95_picks_the_20th_of_20_days() -> None:
    # Given 20 days costing 1..20 dollars
    d = dev(baseline([row(i, str(i)) for i in range(1, 21)]), "ann")
    # Then ceil(0.95 * 20) = 19th value
    assert d.p95_daily_usd == Decimal("19")


def test_unpriced_rows_are_counted_but_left_out_of_spend() -> None:
    # Given one priced and two unpriced rows
    report = baseline([row(1, "5"), row(1, None), row(2, None)])
    d = dev(report, "ann")
    # Then
    assert (d.requests, d.unpriced_requests, d.active_days, d.total_spend_usd) == (3, 2, 1, Decimal("5"))
    assert report.unpriced_requests == 2 and report.total_spend_usd == Decimal("5")


def test_developer_without_any_priced_row_has_no_daily_statistics() -> None:
    # Given only unpriced rows, Then daily stats are None rather than zero
    d = dev(baseline([row(1, None)]), "ann")
    assert d.mean_daily_usd is None and d.median_daily_usd is None and d.p95_daily_usd is None


def test_developer_falls_back_from_caller_to_agent_to_unknown() -> None:
    # Given rows with caller, only agent, and neither
    report = baseline([row(1, "1", caller="ann"), row(1, "1", caller="", agent="reviewer"), row(1, "1", caller="")])
    # Then
    assert [d.developer for d in report.developers] == ["ann", "reviewer", "unknown"]


def test_cache_hit_is_cache_read_over_all_prompt_buckets_per_caller() -> None:
    # Given ann: read 600 of (100 fresh + 600 read + 200 write 5m + 100 write 1h) = 1000; bob has no prompt tokens
    rows = [
        row(1, "1", fresh_input=100, cache_read=600, cache_write_5m=200, cache_write_1h=100, output=999),
        row(1, "1", caller="bob", output=50),
    ]
    report = baseline(rows)
    # Then
    assert dev(report, "ann").cache_hit_rate == Decimal("0.6000")
    assert dev(report, "bob").cache_hit_rate is None


def test_failed_run_share_counts_only_rows_with_a_known_outcome() -> None:
    # Given 1 failed (cost 3), 3 succeeded (cost 1 each) and 2 rows with no outcome
    rows = [
        row(1, "3", success=False),
        row(1, "1", success=True),
        row(1, "1", success=True),
        row(1, "1", success=True),
        row(1, "100"),
        row(1, "100"),
    ]
    report = baseline(rows)
    # Then 1/4 by count and 3/6 by spend
    assert report.known_outcome_requests == 4
    assert report.failed_share_by_count == Decimal("0.2500")
    assert report.failed_share_by_spend == Decimal("0.5000")


def test_failed_run_share_is_none_when_no_row_has_an_outcome_and_the_text_says_so() -> None:
    # Given rows where nothing set `success` (the P0 situation)
    report = baseline([row(1, "1"), row(2, "2")])
    # Then
    assert report.failed_share_by_count is None and report.failed_share_by_spend is None
    assert "no row has a recorded outcome" in baseline_markdown(report)


def test_period_total_model_and_cost_source_shares() -> None:
    # Given three rows across two models and two cost sources
    rows = [
        row(1, "1", model="a", hour=8),
        row(3, "2", model="b", source=CostSource.CLIENT, hour=20),
        row(3, "4", model="a"),
    ]
    report = baseline(rows)
    # Then
    assert report.period_start == datetime(2026, 11, 1, 8, tzinfo=UTC)
    assert report.period_end == datetime(2026, 11, 3, 20, tzinfo=UTC)
    assert report.total_spend_usd == Decimal("7")
    assert report.spend_by_model == {"a": Decimal("5"), "b": Decimal("2")}
    assert report.cost_source_share == {"client": Decimal("0.3333"), "gateway": Decimal("0.6667")}


def test_no_rows_gives_an_empty_report() -> None:
    # Given nothing, When baselined, Then an empty period and a readable text
    report = baseline([])
    assert report.requests == 0 and report.period_start is None and report.developers == ()
    assert "No ledger rows" in baseline_markdown(report)


def test_baseline_markdown_renders_developer_table() -> None:
    # Given
    text = baseline_markdown(baseline([row(1, "2", fresh_input=1, cache_read=1), row(2, "4")]))
    # Then
    assert "| ann | 2 | 0 | $6.00 | 2 | $3.00 | $3.00 | $4.00 | 50.0% |" in text
