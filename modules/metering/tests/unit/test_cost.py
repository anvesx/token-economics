from datetime import UTC, datetime
from decimal import Decimal

from token_economics_contracts import Buckets, Multiplier, PriceRow
from token_economics_metering import DedupeGuard, OrderedCostCalculator, active_multipliers

ROW = PriceRow(
    price_row_id="t1",
    provider="anthropic",
    model="m",
    effective_from=datetime(2026, 1, 1, tzinfo=UTC),
    input=Decimal("4"),
    output=Decimal("20"),
    cache_read=Decimal("0.20"),
    cache_write_5m=Decimal("5"),
    cache_write_1h=Decimal("8"),
    multipliers=(
        Multiplier(name="region:us", factor=Decimal("1.1")),
        Multiplier(name="fast", factor=Decimal("6"), applies_to="output"),
    ),
)
CALC = OrderedCostCalculator()


def test_base_cost_prices_each_bucket_at_its_own_rate() -> None:
    b = Buckets(
        fresh_input=1_000_000,
        cache_read=1_000_000,
        cache_write_5m=1_000_000,
        cache_write_1h=1_000_000,
        output=1_000_000,
    )
    assert CALC.cost(b, ROW) == Decimal("37.20")


def test_region_multiplier_applies_to_every_bucket() -> None:
    b = Buckets(fresh_input=1_000_000, cache_read=1_000_000, output=1_000_000)
    assert CALC.cost(b, ROW, active_multipliers(inference_geo="us")) == Decimal("24.2") * Decimal("1.1")


def test_multiplier_scoped_to_output_leaves_input_alone() -> None:
    b = Buckets(fresh_input=1_000_000, output=1_000_000)
    assert CALC.cost(b, ROW, {"fast"}) == Decimal("4") + Decimal("120")


def test_global_inference_and_standard_tier_activate_nothing() -> None:
    assert active_multipliers("standard", "standard", "global") == frozenset()
    assert active_multipliers("batch", "fast", "us") == {"batch", "fast", "region:us"}


def test_response_seen_twice_is_new_only_once() -> None:
    guard = DedupeGuard(capacity=2)
    assert guard.first_time("anthropic", "msg_1") is True
    assert guard.first_time("anthropic", "msg_1") is False
    assert guard.first_time("openai", "msg_1") is True  # ids are per provider
    assert guard.first_time("anthropic", "") is True and guard.first_time("anthropic", "") is True
