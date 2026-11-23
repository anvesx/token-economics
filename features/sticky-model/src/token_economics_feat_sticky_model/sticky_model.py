"""Pin the first model seen in a conversation and put it back when a later request names another (plan/05, stickiness).

Only MAIN and SUBAGENT conversations are pinned; AUXILIARY requests (title generation on a small model) are ignored.
Put "rules_router" before "sticky_model" in the policy `order` so the pin is the routed model. Do not enable it
together with switch_pricer: both answer "may the model change mid-session"; switch_pricer prices the answer.
"""

from __future__ import annotations

from threading import Lock
from typing import Any

from token_economics_contracts.types import FeatureEnv, LedgerRow, RequestContext, Rewrite

from ._state import ConversationState, conversation_key, is_auxiliary
from .providers import anthropic

STATE_FILE = "sticky_model.json"


class StickyModel:
    name = "sticky_model"
    fail_closed = False

    def __init__(self, state: ConversationState) -> None:
        self._state = state
        self._lock = Lock()

    def before(self, ctx: RequestContext) -> None:
        return None

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        with self._lock:
            self._state.flush_if_due()

    def rewrite(self, ctx: RequestContext, body: dict[str, Any]) -> Rewrite | None:
        key = conversation_key(ctx)
        if ctx.provider != anthropic.PROVIDER or key is None or is_auxiliary(ctx):
            return None
        model = anthropic.model_of(body)
        if model is None:
            return None
        with self._lock:
            entry = self._state.get(key) if ctx.facts.turns > 0 else None  # turn 0 starts a new conversation
            pinned = entry.get("model") if entry else None
            if not isinstance(pinned, str) or not pinned:
                self._state.put(key, {"model": model})
                return None
        if model == pinned:
            return None
        return Rewrite(
            body=anthropic.with_model(body, pinned),
            changes=(f"model {model}->{pinned} (pinned for session)",),
        )


def create(env: FeatureEnv) -> StickyModel:
    return StickyModel(ConversationState(env.state_dir / STATE_FILE))
