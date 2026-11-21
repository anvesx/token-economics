from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from itertools import count
from typing import Any

from token_economics_contracts import SERVICES, Buckets, CostSource, LedgerRow, load
from token_economics_svc_insight import dashboard_summary

_ids = count(1)
NOW = datetime(2026, 11, 10, 12, tzinfo=UTC)


def row(
    day: int,
    cost: str | None,
    *,
    hour: int = 10,
    caller: str = "ann",
    agent: str = "",
    tenant: str = "acme",
    harness: str = "claude-code",
    model: str = "m1",
    session: str = "",
    status: int = 200,
    month: int = 11,
    **buckets: int,
) -> LedgerRow:
    return LedgerRow(
        provider="anthropic",
        response_id=f"r{next(_ids)}",
        ts=datetime(2026, month, day, hour, tzinfo=UTC),
        tenant=tenant,
        caller=caller,
        agent=agent,
        harness=harness,
        session_id=session,
        model=model,
        buckets=Buckets(**buckets),
        cost_estimate_usd=None if cost is None else Decimal(cost),
        cost_source=CostSource.GATEWAY,
        price_row_id="" if cost is None else "p1",
        http_status=status,
    )


def group(groups: Any, name: str) -> Any:
    return next(g for g in groups if g.name == name)


def test_totals_hit_rate_and_period_for_a_known_window() -> None:
    # Given three rows in a 7-day window, one of them unpriced
    rows = [
        row(10, "1.50", fresh_input=100, cache_read=300, cache_write_5m=50, cache_write_1h=50, output=20),
        row(9, "0.50", fresh_input=100, cache_read=100, output=10),
        row(9, None, fresh_input=10, output=5),
    ]
    # When
    s = dashboard_summary(rows, now=NOW, days=7)
    # Then spend leaves out the unpriced row and the hit rate is 400 / (210 + 400 + 50 + 50)
    assert (s.requests, s.unpriced_requests, s.spend_usd) == (3, 1, Decimal("2.00"))
    assert s.tokens.model_dump() == {
        "fresh_input": 210,
        "cache_read": 400,
        "cache_write_5m": 50,
        "cache_write_1h": 50,
        "output": 35,
    }
    assert s.cache_hit_rate == Decimal("0.5634")
    assert s.period_start == datetime(2026, 11, 4, tzinfo=UTC) and s.period_end == NOW and s.days == 7


def test_by_day_has_one_entry_per_utc_day_with_zero_fill() -> None:
    # Given rows on 8 and 10 November only, and a row before the window
    rows = [row(8, "1", output=5), row(8, "2", output=7), row(10, "4", output=1), row(2, "9", output=9)]
    # When a 5-day window ends on the 10th
    s = dashboard_summary(rows, now=NOW, days=5)
    # Then the days are 6..10, empty ones are zero, and the old row is left out
    assert [d.day.day for d in s.by_day] == [6, 7, 8, 9, 10]
    assert [d.spend_usd for d in s.by_day] == [Decimal(0), Decimal(0), Decimal(3), Decimal(0), Decimal(4)]
    assert [d.requests for d in s.by_day] == [0, 0, 2, 0, 1]
    assert [d.tokens.output for d in s.by_day] == [0, 0, 12, 0, 1]
    assert s.requests == 3 and s.spend_usd == Decimal(7)


def test_window_starts_at_midnight_and_ignores_rows_after_now() -> None:
    # Given a row at 00:00 on the first day, one the minute before, and one after now
    rows = [row(6, "1", hour=0), row(5, "5", hour=23), row(10, "7", hour=13)]
    # When
    s = dashboard_summary(rows, now=NOW, days=5)
    # Then only the first counts
    assert (s.requests, s.spend_usd) == (1, Decimal(1))


def test_empty_input_gives_zeros_and_a_filled_calendar() -> None:
    # When
    s = dashboard_summary([], now=NOW, days=3)
    # Then
    assert (s.requests, s.unpriced_requests, s.spend_usd, s.cache_hit_rate) == (0, 0, Decimal(0), None)
    assert len(s.by_day) == 3 and all(d.requests == 0 for d in s.by_day)
    assert s.by_caller == s.by_model == s.by_tenant == s.by_harness == s.by_session == s.recent == ()
    assert s.model_dump(mode="json")["spend_usd"] == "0"


def test_group_median_p95_share_and_order_use_baseline_conventions() -> None:
    # Given ann spent 1, 2, 3, 4, 10 on five days (day one over two rows); bob spent 5 on one day
    rows = [
        row(1, "0.40"),
        row(1, "0.60"),
        row(2, "2"),
        row(3, "3"),
        row(4, "4"),
        row(5, "10"),
        row(5, "5", caller="bob"),
    ]
    # When
    s = dashboard_summary(rows, now=NOW, days=10)
    ann, bob = group(s.by_caller, "ann"), group(s.by_caller, "bob")
    # Then ann leads, median 3, nearest-rank P95 is the 5th of 5; shares add up to one
    assert [g.name for g in s.by_caller] == ["ann", "bob"]
    assert (ann.requests, ann.active_days, ann.spend_usd) == (6, 5, Decimal("20.00"))
    assert (ann.median_daily_usd, ann.p95_daily_usd) == (Decimal(3), Decimal(10))
    assert (bob.median_daily_usd, bob.p95_daily_usd) == (Decimal(5), Decimal(5))
    assert (ann.share_of_spend, bob.share_of_spend) == (Decimal("0.8000"), Decimal("0.2000"))


def test_caller_falls_back_to_agent_then_unknown_and_other_groupings_work() -> None:
    # Given
    rows = [
        row(1, "3", caller="", agent="planner", model="big", harness="claude-code", tenant="acme"),
        row(1, "1", caller="", agent="", model="small", harness="", tenant=""),
        row(1, "2", caller="ann", model="big", harness="codex", tenant="acme"),
    ]
    # When
    s = dashboard_summary(rows, now=NOW, days=10)
    # Then
    assert [g.name for g in s.by_caller] == ["planner", "ann", "unknown"]
    assert [(g.name, g.spend_usd) for g in s.by_model] == [("big", Decimal(5)), ("small", Decimal(1))]
    assert [g.name for g in s.by_harness] == ["claude-code", "codex", "unknown"]
    assert [(g.name, g.requests) for g in s.by_tenant] == [("acme", 2), ("unknown", 1)]


def test_unpriced_rows_count_as_requests_but_not_as_spend_or_active_days() -> None:
    # Given a group whose only row is unpriced, next to one priced group
    rows = [row(1, None, caller="ghost", cache_read=5, fresh_input=5), row(1, "2")]
    # When
    s = dashboard_summary(rows, now=NOW, days=10)
    ghost = group(s.by_caller, "ghost")
    # Then
    assert (ghost.requests, ghost.unpriced_requests, ghost.spend_usd, ghost.active_days) == (1, 1, Decimal(0), 0)
    assert ghost.median_daily_usd is None and ghost.p95_daily_usd is None
    assert ghost.cache_hit_rate == Decimal("0.5000") and ghost.share_of_spend == Decimal("0.0000")
    assert group(s.by_caller, "ann").share_of_spend == Decimal("1.0000")


def test_shares_are_none_when_nothing_is_priced() -> None:
    # When
    s = dashboard_summary([row(1, None)], now=NOW, days=10)
    # Then
    assert s.by_caller[0].share_of_spend is None and s.cache_hit_rate is None


def test_sessions_are_the_top_20_by_spend_with_models_and_span() -> None:
    # Given session a (two models, two rows) and 25 cheap single-row sessions, plus a row without a session id
    rows = [row(1, "1", session="a", model="m1", hour=9), row(2, "2", session="a", model="m2", hour=8)]
    rows += [row(3, "0.01", session=f"s{i:02d}") for i in range(25)] + [row(3, "50")]
    # When
    s = dashboard_summary(rows, now=NOW, days=10)
    top = s.by_session[0]
    # Then
    assert len(s.by_session) == 20 and top.session_id == "a"
    assert (top.requests, top.spend_usd, top.models, top.caller) == (2, Decimal(3), ("m1", "m2"), "ann")
    assert top.first_ts == datetime(2026, 11, 1, 9, tzinfo=UTC) and top.last_ts == datetime(2026, 11, 2, 8, tzinfo=UTC)
    assert [x.session_id for x in s.by_session[1:3]] == ["s00", "s01"]  # ties keep id order


def test_recent_is_the_50_newest_rows_with_only_ledger_fields() -> None:
    # Given 60 rows on consecutive hours of the 9th
    rows = [row(9, "0.10", hour=h, output=h) for h in range(24)] + [row(8, "0.10", hour=h, output=h) for h in range(24)]
    rows += [row(7, "0.10", hour=h) for h in range(12)]
    # When
    s = dashboard_summary(rows, now=NOW, days=5)
    # Then newest first, 50 of them, with the documented fields
    assert len(s.recent) == 50 and s.requests == 60
    assert s.recent[0].ts == datetime(2026, 11, 9, 23, tzinfo=UTC) and s.recent[0].tokens.output == 23
    assert s.recent[-1].ts == datetime(2026, 11, 7, 10, tzinfo=UTC)
    assert set(s.model_dump()["recent"][0]) == {
        "ts",
        "caller",
        "harness",
        "model",
        "tokens",
        "cost_usd",
        "cost_source",
        "http_status",
    }
    assert s.recent[0].cost_source == "gateway" and s.recent[0].http_status == 200


def test_summary_is_json_serialisable_with_money_as_strings() -> None:
    # When
    j = dashboard_summary([row(9, "1.25", output=3, status=429)], now=NOW, days=2).model_dump(mode="json")
    # Then
    assert j["spend_usd"] == "1.25" and j["by_day"][1]["day"] == "2026-11-10"
    assert j["recent"][0]["http_status"] == 429 and j["recent"][0]["cost_usd"] == "1.25"
    assert j["period_start"] == "2026-11-09T00:00:00Z"


def test_dashboard_summary_resolves_under_the_services_group() -> None:
    assert load(SERVICES, "dashboard_summary") is dashboard_summary
