"""Lower max_tokens to a per-model cap before dispatch."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from token_economics_contracts.types import Decision, FeatureEnv, LedgerRow, RequestContext, Rewrite


def _positive_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


class MaxTokens:
    name = "max_tokens"
    fail_closed = False

    def __init__(self, caps: Mapping[str, int] | None = None, default: int | None = None) -> None:
        self.caps = dict(caps or {})
        self.default = default

    def before(self, ctx: RequestContext) -> Decision | None:
        return None

    def rewrite(self, ctx: RequestContext, body: dict[str, Any]) -> Rewrite | None:
        if ctx.provider != "anthropic":
            return None
        current = _positive_int(body.get("max_tokens"))
        model = body.get("model")
        if current is None or not isinstance(model, str):
            return None
        cap = self.caps.get(model, self.default)  # exact model id only
        if cap is None or cap >= current:
            return None
        thinking = body.get("thinking")
        if isinstance(thinking, dict) and thinking.get("type") == "enabled":
            budget = thinking.get("budget_tokens")
            # The API requires max_tokens > budget_tokens; an unreadable budget is treated as unsafe.
            if not isinstance(budget, int) or isinstance(budget, bool) or cap <= budget:
                return None
        return Rewrite(body={**body, "max_tokens": cap}, changes=(f"max_tokens {current}->{cap}",))

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        return None


def create(env: FeatureEnv) -> MaxTokens:
    raw = env.config.get("caps")
    caps = (
        {m: c for m, c in raw.items() if isinstance(m, str) and _positive_int(c) is not None}
        if isinstance(raw, dict)
        else {}
    )
    return MaxTokens(caps, _positive_int(env.config.get("default")))
