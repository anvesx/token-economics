"""Refuse a request once the conversation has as many turns as the model's cap."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from token_economics_contracts.types import Decision, FeatureEnv, LedgerRow, RequestContext

MIN_SAMPLES = 20


def p75_caps(turns_by_model: Mapping[str, Sequence[int]]) -> dict[str, int]:
    """Nearest-rank 75th percentile of each model's baseline turns (rank = ceil(0.75 n)).

    Models with fewer than 20 samples are left out: no cap is better than a cap from noise.
    """
    caps: dict[str, int] = {}
    for model, turns in turns_by_model.items():
        if len(turns) < MIN_SAMPLES:
            continue
        caps[model] = sorted(turns)[math.ceil(0.75 * len(turns)) - 1]
    return caps


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


class TurnCap:
    name = "turn_cap"
    fail_closed = False

    def __init__(self, caps: Mapping[str, int] | None = None, default: int | None = None) -> None:
        self.caps = dict(caps or {})
        self.default = default

    def before(self, ctx: RequestContext) -> Decision | None:
        model, turns = ctx.facts.model, ctx.facts.turns
        cap = self.caps.get(model, self.default)  # exact model id only
        if cap is None or turns < cap:
            return None
        return Decision(
            allow=False,
            feature=self.name,
            status=429,
            code="turn_cap_reached",
            message=(
                f"Turn cap reached: this conversation has {turns} turns and the cap for {model} is {cap}. "
                "Start a new session or ask an admin to raise the cap."
            ),
        )

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        return None


def create(env: FeatureEnv) -> TurnCap:
    raw = env.config.get("caps")
    caps = (
        {m: c for m, c in raw.items() if isinstance(m, str) and _int_or_none(c) is not None}
        if isinstance(raw, dict)
        else {}
    )
    return TurnCap(caps, _int_or_none(env.config.get("default")))
