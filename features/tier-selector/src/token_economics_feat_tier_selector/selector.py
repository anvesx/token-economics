"""Pick the service tier per workload by rule (plan/05, "Tier and cache selection").

Config: {"rules": [{"when": {"harness": "...", "tenant": "...", "team": "...", "caller": "...", "query_source": "...",
"model": "..."}, "service_tier": "flex"}], "override": false}
The first rule whose `when` matches (exact match on every key given) decides. A rule with an empty `when` matches
everything; a `when` key that is not known never matches. If the winning rule's tier is not allowed for the request's
provider, nothing is rewritten (later rules are not tried). A request that already sets `service_tier` is left alone
unless `override` is true.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from token_economics_contracts.types import FeatureEnv, LedgerRow, RequestContext, Rewrite

from .providers import ALLOWED_BY_PROVIDER

WHEN_KEYS = ("harness", "tenant", "team", "caller", "query_source", "model")


@dataclass(frozen=True)
class Rule:
    when: Mapping[str, str]
    service_tier: str

    def matches(self, ctx: RequestContext) -> bool:
        actual = {
            "harness": ctx.harness,
            "tenant": ctx.key.tenant,
            "team": ctx.key.team,
            "caller": ctx.key.caller,
            "query_source": ctx.identity.query_source.value,
            "model": ctx.facts.model,
        }
        return all(k in actual and actual[k] == v for k, v in self.when.items())


def parse_rules(raw: Any) -> list[Rule]:
    """Valid rules in order; a malformed one is kept as a never-matching rule so rule numbers stay stable."""
    rules: list[Rule] = []
    for item in raw if isinstance(raw, list) else []:
        when = item.get("when") if isinstance(item, dict) else None
        tier = item.get("service_tier") if isinstance(item, dict) else None
        if isinstance(when, dict) and isinstance(tier, str) and tier and all(
            isinstance(k, str) and isinstance(v, str) for k, v in when.items()
        ):  # fmt: skip
            rules.append(Rule(dict(when), tier))
        else:
            rules.append(Rule({"": ""}, ""))  # never matches: the context has no "" key
    return rules


class TierSelector:
    name = "tier_selector"
    fail_closed = False

    def __init__(self, rules: list[Rule], override: bool = False) -> None:
        self._rules, self._override = rules, override

    def before(self, ctx: RequestContext) -> None:
        return None

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        return None

    def rewrite(self, ctx: RequestContext, body: dict[str, Any]) -> Rewrite | None:
        try:
            current = body.get("service_tier")
            if current is not None and not self._override:
                return None
            for number, rule in enumerate(self._rules, start=1):
                if not rule.matches(ctx):
                    continue
                if rule.service_tier not in ALLOWED_BY_PROVIDER.get(ctx.provider, frozenset()):
                    return None
                if current == rule.service_tier:
                    return None
                return Rewrite(
                    body={**body, "service_tier": rule.service_tier},
                    changes=(f"service_tier -> {rule.service_tier} (rule {number})",),
                )
        except (AttributeError, TypeError):
            return None
        return None


def create(env: FeatureEnv) -> TierSelector:
    return TierSelector(parse_rules(env.config.get("rules")), env.config.get("override") is True)
