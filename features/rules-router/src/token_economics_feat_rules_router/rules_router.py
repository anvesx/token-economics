"""Route a conversation to a model by rules when it starts, then keep it there (plan/05, routing ladder, rung 1).

The first rule whose `when` matches wins. The target is remembered per conversation and applied on every later turn,
because the client keeps sending its own model and a flip back would break the prompt cache. If the client itself
sends a third model mid-conversation (the user's /model), routing stops for that conversation.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from threading import Lock
from typing import Any

from token_economics_contracts.types import FeatureEnv, LedgerRow, RequestContext, Rewrite

from ._state import ConversationState, conversation_key

STATE_FILE = "rules_router.json"
WHEN_KEYS = frozenset(
    {"harness", "tenant", "team", "caller", "query_source", "model", "min_est_input_tokens", "max_est_input_tokens"}
)
_STR_KEYS = ("harness", "tenant", "team", "caller", "query_source", "model")


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


@dataclass(frozen=True)
class Rule:
    when: Mapping[str, Any]
    model: str
    reason: str = ""

    def matches(self, ctx: RequestContext, model: str) -> bool:
        actual = {
            "harness": ctx.harness,
            "tenant": ctx.key.tenant,
            "team": ctx.key.team,
            "caller": ctx.key.caller,
            "query_source": ctx.identity.query_source.value,
            "model": model,
        }
        if any(actual[k] != self.when[k] for k in _STR_KEYS if k in self.when):
            return False
        est = ctx.facts.est_input_tokens
        if "min_est_input_tokens" in self.when and est < self.when["min_est_input_tokens"]:
            return False
        return not ("max_est_input_tokens" in self.when and est > self.when["max_est_input_tokens"])


def parse_rules(raw: Any) -> tuple[list[Rule | None], list[str]]:
    """Rules in order (a malformed one becomes None so rule numbers stay true) and a list of what was skipped."""
    if not isinstance(raw, list):
        return [], []
    rules: list[Rule | None] = []
    skipped: list[str] = []
    for i, item in enumerate(raw, 1):
        when = item.get("when", {}) if isinstance(item, dict) else None
        ok = (
            isinstance(item, dict)
            and isinstance(item.get("model"), str)
            and item["model"]
            and isinstance(when, dict)
            and set(when) <= WHEN_KEYS
            and all(isinstance(when[k], str) for k in _STR_KEYS if k in when)
            and all(_is_int(when[k]) for k in when if k.endswith("_est_input_tokens"))
        )
        if not ok:
            rules.append(None)
            skipped.append(f"rule {i}")
            continue
        rules.append(Rule(dict(when), item["model"], str(item.get("reason", ""))))  # type: ignore[arg-type]
    return rules, skipped


class RulesRouter:
    name = "rules_router"
    fail_closed = False

    def __init__(
        self,
        rules: list[Rule | None],
        state: ConversationState,
        pricebook: Any = None,
        skipped: list[str] | None = None,
    ) -> None:
        self.rules, self.skipped = rules, skipped or []
        self._state, self._pricebook = state, pricebook
        self._lock = Lock()

    def before(self, ctx: RequestContext) -> None:
        return None

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        with self._lock:
            self._state.flush_if_due()

    def rewrite(self, ctx: RequestContext, body: dict[str, Any]) -> Rewrite | None:
        key, model = conversation_key(ctx), body.get("model")
        if ctx.provider != "anthropic" or key is None or not isinstance(model, str) or not model:
            return None
        with self._lock:
            if ctx.facts.turns == 0:
                return self._start(ctx, body, key, model)
            entry = self._state.get(key)
            if entry is None or entry.get("stopped"):
                return None
            routed = str(entry["routed"])
            if model == routed:
                return None
            if model != entry.get("orig"):
                # The client sent a model that is neither its starting one nor ours: the user chose it. Stop routing.
                self._state.put(key, {**entry, "stopped": True, "user_model": model})
                return None
            return _switch(body, model, routed, str(entry.get("rule", "")))

    def _start(self, ctx: RequestContext, body: dict[str, Any], key: str, model: str) -> Rewrite | None:
        for n, rule in enumerate(self.rules, 1):
            if rule is None or not rule.matches(ctx, model):
                continue
            if rule.model == model or not self._priced(ctx, rule.model):
                return None
            self._state.put(key, {"orig": model, "routed": rule.model, "rule": n, "stopped": False})
            return _switch(body, model, rule.model, str(n))
        if self._state.get(key) is not None:  # a new conversation under an old key: forget the old route
            self._state.put(key, {"orig": model, "routed": model, "rule": "", "stopped": True})
        return None

    def _priced(self, ctx: RequestContext, model: str) -> bool:
        """An unpriced model escapes budgets, so it is never a target. With no price book there is nothing to check."""
        if self._pricebook is None:
            return True
        try:
            self._pricebook.lookup("anthropic", model, ctx.ts, ctx.facts.est_input_tokens)
        except Exception:  # NoPriceRow, or an odd price book: either way the target is unchecked
            return False
        return True


def _switch(body: dict[str, Any], old: str, new: str, rule: str) -> Rewrite:
    return Rewrite(body={**body, "model": new}, changes=(f"model {old}->{new} (rule {rule})",))


def create(env: FeatureEnv) -> RulesRouter:
    rules, skipped = parse_rules(env.config.get("rules"))
    return RulesRouter(rules, ConversationState(env.state_dir / STATE_FILE), env.pricebook, skipped)
