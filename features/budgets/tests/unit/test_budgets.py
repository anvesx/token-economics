import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from token_economics_contracts import (
    Buckets,
    BudgetReader,
    CostSource,
    Feature,
    FeatureEnv,
    KeyInfo,
    LedgerRow,
    NoPriceRow,
    PriceRow,
    RequestContext,
    RequestFacts,
)
from token_economics_feat_budgets import BudgetConfigError, create, open_status

NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)
PRICE = PriceRow(
    price_row_id="p",
    provider="anthropic",
    model="m",
    effective_from=datetime(2026, 1, 1, tzinfo=UTC),
    input=Decimal("2"),
    output=Decimal("10"),
    cache_read=Decimal("0.1"),
    cache_write_5m=Decimal("2.5"),
    cache_write_1h=Decimal("4"),
)


class Book:
    def lookup(
        self,
        provider: str,
        model: str,
        at: datetime,
        prompt_tokens: int,
        service_tier: str = "standard",
        region: str = "",
    ) -> PriceRow:
        if model != "m":
            raise NoPriceRow(model)
        return PRICE


def feature(tmp_path: Path, **cfg: Any) -> Any:
    cfg.setdefault("limits", [{"scope": "caller", "match": "*", "window": "day", "usd": "1"}])
    return create(FeatureEnv(state_dir=tmp_path, config=cfg, pricebook=Book()))


def ctx(
    rid: str, caller: str = "dhruv", model: str = "m", est: int = 10_000, max_tokens: int = 1_000, ts: datetime = NOW
) -> RequestContext:
    return RequestContext(
        request_id=rid,
        ts=ts,
        key_id="k1",
        key=KeyInfo(tenant="devx", caller=caller),
        provider="anthropic",
        facts=RequestFacts(model=model, est_input_tokens=est, max_tokens=max_tokens),
    )


def row(cost: str) -> LedgerRow:
    return LedgerRow(
        provider="anthropic",
        response_id="r",
        ts=NOW,
        model="m",
        buckets=Buckets(),
        cost_estimate_usd=Decimal(cost),
        cost_source=CostSource.GATEWAY,
        price_row_id="p",
    )


def test_feature_and_reader_satisfy_their_ports(tmp_path: Path) -> None:
    f = feature(tmp_path)
    assert isinstance(f, Feature) and f.fail_closed is True
    assert isinstance(open_status(str(tmp_path)), BudgetReader)


def test_worst_case_reserves_the_dearest_input_rate_and_every_output_token(tmp_path: Path) -> None:
    # Given 10,000 estimated input tokens (x1.5 safety) at the $4 one-hour write rate and 1,000 output at $10
    f = feature(tmp_path)
    assert f.worst_case_micro(ctx("a")) == 15_000 * 4 + 1_000 * 10  # micro-dollars


def test_request_is_refused_when_spend_plus_reservation_would_pass_the_limit(tmp_path: Path) -> None:
    f = feature(tmp_path)
    # Given $0.95 already spent of a $1 day budget
    assert f.before(ctx("a")) is None
    f.after(ctx("a"), row("0.95"), 200)
    # When a request that could cost $0.07 arrives  # Then it is refused with the budget named
    d = f.before(ctx("b"))
    assert d is not None and not d.allow and d.status == 429 and d.code == "budget_exhausted"
    assert "caller:dhruv" in d.message and "$0.95" in d.message and "$1.00" in d.message
    assert d.retry_after_s == 12 * 3600
    # And another caller still has their own budget
    assert f.before(ctx("c", caller="asha")) is None


def test_true_up_replaces_the_reservation_with_the_real_cost(tmp_path: Path) -> None:
    f = feature(tmp_path)
    f.before(ctx("a"))
    (s,) = open_status(str(tmp_path)).status(NOW)
    assert (s.spent_usd, s.reserved_usd) == (Decimal("0"), Decimal("0.07"))
    f.after(ctx("a"), row("0.002"), 200)
    (s,) = open_status(str(tmp_path)).status(NOW)
    assert (s.scope, s.spent_usd, s.reserved_usd, s.limit_usd) == (
        "caller:dhruv",
        Decimal("0.002"),
        Decimal("0"),
        Decimal("1"),
    )


def test_a_request_with_no_usage_releases_its_reservation(tmp_path: Path) -> None:
    f = feature(tmp_path)
    f.before(ctx("a"))
    f.after(ctx("a"), None, 529)
    assert open_status(str(tmp_path)).status(NOW) == [] or open_status(str(tmp_path)).status(NOW)[0].reserved_usd == 0


def test_a_leaked_reservation_expires(tmp_path: Path) -> None:
    f = feature(
        tmp_path, reservation_ttl_s=60, limits=[{"scope": "caller", "match": "*", "window": "day", "usd": "0.1"}]
    )
    assert f.before(ctx("a")) is None  # holds $0.07 and never settles
    assert f.before(ctx("b")) is not None
    later = NOW.replace(minute=2)
    assert f.before(ctx("c", ts=later)) is None


def test_parallel_requests_never_reserve_past_the_limit(tmp_path: Path) -> None:
    # Given a $1 budget and requests that each reserve $0.07
    f = feature(tmp_path)
    with ThreadPoolExecutor(25) as pool:
        decisions = list(pool.map(lambda i: f.before(ctx(f"r{i}")), range(50)))
    # Then exactly 14 fit (14 x 0.07 = 0.98) and the rest are refused
    assert sum(d is None for d in decisions) == 14
    (s,) = open_status(str(tmp_path)).status(NOW)
    assert s.reserved_usd == Decimal("0.98") and s.used_share <= 1


def test_every_matching_limit_counts_and_windows_stack(tmp_path: Path) -> None:
    f = feature(
        tmp_path,
        limits=[
            {"scope": "caller", "match": "dhruv", "window": "day", "usd": "10"},
            {"scope": "tenant", "match": "*", "window": "month", "usd": "0.05"},
        ],
    )
    d = f.before(ctx("a"))
    assert d is not None and "tenant:devx" in d.message and "this month" in d.message


def test_a_new_day_starts_a_new_budget(tmp_path: Path) -> None:
    f = feature(tmp_path)
    f.before(ctx("a"))
    f.after(ctx("a"), row("0.99"), 200)
    assert f.before(ctx("b")) is not None
    assert f.before(ctx("c", ts=NOW.replace(day=22))) is None


def test_alerts_fire_once_each_at_75_90_and_100_percent(tmp_path: Path) -> None:
    f = feature(tmp_path, limits=[{"scope": "caller", "match": "*", "window": "day", "usd": "10"}])
    for n, cost in enumerate(["7.6", "0.1", "1.4", "1.0"]):
        f.before(ctx(f"r{n}", est=10, max_tokens=10))
        f.after(ctx(f"r{n}", est=10, max_tokens=10), row(cost), 200)
    alerts = [json.loads(line) for line in (tmp_path / "alerts.jsonl").read_text().splitlines()]
    assert [a["threshold"] for a in alerts] == ["0.75", "0.9", "1"]
    assert alerts[0]["scope"] == "caller:dhruv" and alerts[0]["limit_usd"] == "10"


def test_an_unpriced_model_is_refused_unless_configured_to_pass(tmp_path: Path) -> None:
    d = feature(tmp_path / "a").before(ctx("a", model="unknown-model"))
    assert d is not None and d.code == "unpriced_model"
    assert feature(tmp_path / "b", unpriced="allow").before(ctx("a", model="unknown-model")) is None


def test_a_request_without_a_key_matches_no_wildcard_budget(tmp_path: Path) -> None:
    f = feature(tmp_path, limits=[{"scope": "key", "match": "*", "window": "day", "usd": "0.01"}])
    anon = RequestContext(
        request_id="x",
        ts=NOW,
        key=KeyInfo(tenant="unknown"),
        provider="anthropic",
        facts=RequestFacts(model="m", est_input_tokens=10_000, max_tokens=1000),
    )
    assert f.before(anon) is None


def test_a_bad_limit_is_a_config_error(tmp_path: Path) -> None:
    for bad in (
        {"scope": "planet", "window": "day", "usd": "1"},
        {"scope": "caller", "window": "week", "usd": "1"},
        {"scope": "caller", "window": "day", "usd": "-1"},
        {"scope": "caller", "window": "day"},
    ):
        with pytest.raises(BudgetConfigError):
            feature(tmp_path, limits=[bad])
