"""The per-request cost formula, in the order of plan/04-cost-formula.md.

Step 1 (normalise) is done by the provider normaliser; step 2 (context band) by the price book lookup, which returns the
row for the request's total prompt tokens. This module does step 3 (base cost) and step 4 (multipliers).
Not built yet: step 5 (per-call tool fees, storage) and step 6 (plan billing).
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from token_economics_contracts import Buckets, PriceRow

MILLION = Decimal(1_000_000)


def active_multipliers(service_tier: str = "", speed: str = "", inference_geo: str = "") -> frozenset[str]:
    """Names of the multipliers in force on a request, as price rows spell them."""
    names = set()
    if service_tier and service_tier != "standard":
        names.add(service_tier)  # batch, flex, priority
    if speed and speed != "standard":
        names.add(speed)  # fast
    if inference_geo and inference_geo not in ("global", "not_available"):
        names.add(f"region:{inference_geo}")
    return frozenset(names)


class OrderedCostCalculator:
    """Prices five buckets with one price row. Exact decimal arithmetic; no rounding."""

    def cost(self, buckets: Buckets, price: PriceRow, active: Iterable[str] = ()) -> Decimal:
        if price.band_scope != "all_tokens":
            raise NotImplementedError("marginal context bands are not priced in P0")
        fresh = buckets.fresh_input * price.input
        cached = (
            buckets.cache_read * price.cache_read
            + buckets.cache_write_5m * price.cache_write_5m
            + buckets.cache_write_1h * price.cache_write_1h
        )
        output = buckets.output * price.output  # reasoning tokens are inside output: counted once
        on = set(active)
        for m in price.multipliers:
            if m.name not in on:
                continue
            if m.applies_to in ("input", "all"):
                fresh *= m.factor
            if m.applies_to in ("cached", "all"):
                cached *= m.factor
            if m.applies_to in ("output", "all"):
                output *= m.factor
        return (fresh + cached + output) / MILLION

    def active_for(self, service_tier: str = "", speed: str = "", inference_geo: str = "") -> frozenset[str]:
        return active_multipliers(service_tier, speed, inference_geo)


def open_cost_calculator() -> OrderedCostCalculator:
    return OrderedCostCalculator()
