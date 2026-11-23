"""Price a mid-conversation model switch and undo it when the cache rewrite costs more than it saves (plan/05).

A new model starts with a cold cache, so the whole prompt is written again at its cache-write rate. The switch is
allowed only when the saving per turn over the expected remaining turns exceeds that one-off cost. Every decision is
appended to `switch_pricer.jsonl` (metadata only), which is the logged reason.

`est_input_tokens` is an upper estimate from the body size, so the cost side is pessimistic: some switches that would
pay off are reverted. A switch with no price row on either side is left alone and logged as "unpriced".
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from threading import Lock
from typing import Any

from token_economics_contracts.types import FeatureEnv, LedgerRow, PriceRow, RequestContext, Rewrite

from ._state import ConversationState, conversation_key

STATE_FILE, LOG_FILE = "switch_pricer.json", "switch_pricer.jsonl"
DEFAULT_OUTPUT_TOKENS, DEFAULT_REMAINING_TURNS = 2000, 10
_MILLION, _CENT4 = Decimal(1_000_000), Decimal("0.0001")


def _usd(value: Decimal) -> str:
    return str(value.quantize(_CENT4, rounding=ROUND_HALF_UP))


def _positive_int(value: Any, default: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else default


class SwitchPricer:
    name = "switch_pricer"
    fail_closed = False

    def __init__(
        self,
        state: ConversationState,
        log_path: Any,
        pricebook: Any = None,
        expected_output_tokens: int = DEFAULT_OUTPUT_TOKENS,
        expected_remaining_turns: int = DEFAULT_REMAINING_TURNS,
    ) -> None:
        self._state, self._log, self._pricebook = state, log_path, pricebook
        self.expected_output_tokens = expected_output_tokens
        self.expected_remaining_turns = expected_remaining_turns
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
            entry = self._state.get(key) if ctx.facts.turns > 0 else None  # turn 0 starts a new conversation
            prev = entry.get("model") if entry else None
            if not isinstance(prev, str) or not prev:
                self._state.put(key, {"model": model})
                return None
            if prev == model:
                return None
            return self._decide(ctx, body, key, prev, model)

    def _decide(self, ctx: RequestContext, body: dict[str, Any], key: str, prev: str, new: str) -> Rewrite | None:
        est = ctx.facts.est_input_tokens
        rows = self._rows(ctx, prev, new)
        if rows is None:
            self._record(ctx, prev, new, None, None, "unpriced")
            self._state.put(key, {"model": new})
            return None
        old_row, new_row = rows
        # The extra cost of the switch turn over staying: the prompt is written to the new model's cache instead of
        # read from the old one's. Later turns are covered by the per-turn saving.
        cost = max(Decimal(0), Decimal(est) * (new_row.cache_write_5m - old_row.cache_read) / _MILLION)
        per_turn = (
            Decimal(est) * (old_row.cache_read - new_row.cache_read) / _MILLION
            + Decimal(self.expected_output_tokens) * (old_row.output - new_row.output) / _MILLION
        )
        saving = per_turn * self.expected_remaining_turns
        if saving > cost:
            self._record(ctx, prev, new, saving, cost, "allowed", per_turn)
            self._state.put(key, {"model": new})
            return None
        self._record(ctx, prev, new, saving, cost, "reverted", per_turn)
        note = (
            f"model {new}->{prev} (switch reverted: saving ${_usd(saving)} over "
            f"{self.expected_remaining_turns} turns <= cache rewrite ${_usd(cost)})"
        )
        return Rewrite(body={**body, "model": prev}, changes=(note,))

    def _rows(self, ctx: RequestContext, prev: str, new: str) -> tuple[PriceRow, PriceRow] | None:
        if self._pricebook is None:
            return None
        try:
            at, est = ctx.ts, ctx.facts.est_input_tokens
            return (
                self._pricebook.lookup("anthropic", prev, at, est),
                self._pricebook.lookup("anthropic", new, at, est),
            )
        except Exception:  # NoPriceRow, or an odd price book: either way leave the switch alone
            return None

    def _record(
        self,
        ctx: RequestContext,
        prev: str,
        new: str,
        saving: Decimal | None,
        cost: Decimal | None,
        verdict: str,
        per_turn: Decimal | None = None,
    ) -> None:
        record = {
            "ts": datetime.now(UTC).isoformat(),
            "session_id": ctx.identity.session_id,
            "agent": ctx.identity.agent,
            "query_source": ctx.identity.query_source.value,
            "from": prev,
            "to": new,
            "est_input_tokens": ctx.facts.est_input_tokens,
            "saving_per_turn_usd": _usd(per_turn) if per_turn is not None else None,
            "saving_usd": _usd(saving) if saving is not None else None,
            "cost_usd": _usd(cost) if cost is not None else None,
            "remaining_turns": self.expected_remaining_turns,
            "verdict": verdict,
        }
        try:
            with self._log.open("a") as f:
                f.write(json.dumps(record) + "\n")
        except OSError:
            pass  # the log is best effort: a failed write must never fail a request


def create(env: FeatureEnv) -> SwitchPricer:
    return SwitchPricer(
        ConversationState(env.state_dir / STATE_FILE),
        env.state_dir / LOG_FILE,
        env.pricebook,
        _positive_int(env.config.get("expected_output_tokens"), DEFAULT_OUTPUT_TOKENS),
        _positive_int(env.config.get("expected_remaining_turns"), DEFAULT_REMAINING_TURNS),
    )
