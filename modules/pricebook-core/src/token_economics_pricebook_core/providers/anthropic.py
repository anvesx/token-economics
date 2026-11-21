"""Seed price rows for Anthropic models. USD per 1M tokens.

EVERY ROW HERE IS UNVERIFIED. The numbers were copied on 2026-11-21 from two secondary sources, not from Anthropic's
pricing page:
  - plan/04-cost-formula.md and plan/16-research-update-2026-11.md (cache multipliers, Haiku 5.5 length cliff, region);
  - hermes-engine `PRICES` (input and output rates per model version).
`effective_from` is a placeholder (2026-01-01), not the real date each price took effect. Verify each row on the vendor
page, then append a new row with `confidence="verified"`, the real `effective_from` and `last_verified_at`; never edit
a row in place. Until then the price book reports all of these as stale, which is the intended signal.

Cache writes: 5-minute 1.25x input, 1-hour 2x input. Cache reads: 0.1x input, except 0.05x on Opus 5.5 and Sonnet 5.5
and 0.025x on Fable 5.1 and 5.2. `inference_geo: "us"` multiplies every bucket by 1.1.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from token_economics_contracts import Multiplier, PriceRow

PROVIDER = "anthropic"
PLACEHOLDER_FROM = datetime(2026, 1, 1, tzinfo=UTC)
SNAPSHOT = datetime(2026, 11, 21, tzinfo=UTC)
US_REGION = Multiplier(name="region:us", factor=Decimal("1.1"), applies_to="all")

# model id: (input, output, cache-read multiple of input, source)
_MODELS: dict[str, tuple[str, str, str, str]] = {
    "claude-fable-5-2": ("10", "50", "0.025", "hermes-engine PRICES; plan/16 cache-read multiple"),
    "claude-fable-5-1": ("10", "50", "0.025", "hermes-engine PRICES; plan/16 cache-read multiple"),
    "claude-opus-5-5": ("4", "20", "0.05", "hermes-engine PRICES; plan/16 cache-read multiple"),
    "claude-sonnet-5-5": ("2", "10", "0.05", "hermes-engine PRICES; plan/16 cache-read multiple"),
    "claude-sonnet-5": ("2", "10", "0.1", "plan/16: held at $2 and $10"),
    "claude-opus-4-8": ("5", "25", "0.1", "hermes-engine PRICES"),
    "claude-opus-4-7": ("5", "25", "0.1", "hermes-engine PRICES"),
    "claude-sonnet-4-6": ("3", "15", "0.1", "hermes-engine PRICES"),
    "claude-sonnet-4-5": ("3", "15", "0.1", "hermes-engine PRICES"),
    "claude-haiku-4-5": ("1", "5", "0.1", "hermes-engine PRICES"),
}
# Haiku 5.5 prices a request by its length: above 100K prompt tokens every bucket is repriced (plan/16).
_HAIKU_5_5_BANDS = ((0, "0.10", "0.50"), (100_001, "0.50", "2.50"))


def _row(model: str, band: int, rate_in: str, rate_out: str, read_x: str, source: str) -> PriceRow:
    i = Decimal(rate_in)
    return PriceRow(
        price_row_id=f"anthropic:{model}:standard:{band}:2026-01-01:seed1",
        provider=PROVIDER,
        model=model,
        context_band_min=band,
        effective_from=PLACEHOLDER_FROM,
        input=i,
        output=Decimal(rate_out),
        cache_read=i * Decimal(read_x),
        cache_write_5m=i * Decimal("1.25"),
        cache_write_1h=i * Decimal("2"),
        multipliers=(US_REGION,),
        source_id=source,
        snapshot_date=SNAPSHOT,
        last_verified_at=None,
        confidence="unverified",
    )


def rows() -> list[PriceRow]:
    out = [_row(model, 0, i, o, x, src) for model, (i, o, x, src) in _MODELS.items()]
    out += [
        _row("claude-haiku-5-5", band, i, o, "0.1", "plan/16: length cliff at 100K tokens")
        for band, i, o in _HAIKU_5_5_BANDS
    ]
    return out
