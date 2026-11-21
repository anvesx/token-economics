from datetime import UTC, datetime
from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st
from token_economics_contracts import Buckets, PriceRow
from token_economics_metering import OrderedCostCalculator
from token_economics_metering.providers.anthropic import NORMALISER as anthropic
from token_economics_metering.providers.openai import NORMALISER as openai

count = st.integers(min_value=0, max_value=5_000_000)
rate = st.decimals(min_value=0, max_value=500, places=4, allow_nan=False, allow_infinity=False)


@given(count, count, count, count, count)
def test_anthropic_buckets_always_sum_to_the_provider_total(i: int, r: int, w5: int, w1h: int, o: int) -> None:
    usage = {
        "input_tokens": i,
        "cache_read_input_tokens": r,
        "cache_creation_input_tokens": w5 + w1h,
        "cache_creation": {"ephemeral_5m_input_tokens": w5, "ephemeral_1h_input_tokens": w1h},
        "output_tokens": o,
    }
    b = anthropic.normalise(usage)
    assert b.prompt_tokens == i + r + w5 + w1h and b.total == i + r + w5 + w1h + o


@given(count, count, count)
def test_openai_buckets_always_sum_to_total_tokens(fresh: int, cached: int, o: int) -> None:
    usage = {
        "input_tokens": fresh + cached,
        "input_tokens_details": {"cached_tokens": cached},
        "output_tokens": o,
        "total_tokens": fresh + cached + o,
    }
    assert openai.normalise(usage).total == usage["total_tokens"]


@given(count, count, count, count, count, rate, rate, rate, rate, rate)
def test_cost_is_never_negative_and_is_linear_in_tokens(
    i: int, r: int, w5: int, w1h: int, o: int, pi: Decimal, po: Decimal, pr: Decimal, p5: Decimal, p1: Decimal
) -> None:
    row = PriceRow(
        price_row_id="p",
        provider="x",
        model="m",
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
        input=pi,
        output=po,
        cache_read=pr,
        cache_write_5m=p5,
        cache_write_1h=p1,
    )
    b = Buckets(fresh_input=i, cache_read=r, cache_write_5m=w5, cache_write_1h=w1h, output=o)
    twice = Buckets(fresh_input=2 * i, cache_read=2 * r, cache_write_5m=2 * w5, cache_write_1h=2 * w1h, output=2 * o)
    calc = OrderedCostCalculator()
    assert calc.cost(b, row) >= 0
    assert calc.cost(twice, row) == 2 * calc.cost(b, row)
