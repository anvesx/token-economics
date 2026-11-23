"""Mask old tool results in steps, so the cached prefix only changes when the boundary moves."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from token_economics_contracts.types import Decision, FeatureEnv, LedgerRow, RequestContext, Rewrite

DEFAULT_MIN_EVENTS = 10  # plan/06: negative at 7 or fewer events, so start above about 10
DEFAULT_KEEP = 5
DEFAULT_STEP = 10
DEFAULT_PROTECT_TOOLS: tuple[str, ...] = ("Read", "Edit", "MultiEdit", "Write", "NotebookEdit", "NotebookRead")


def _marker(chars: int) -> str:
    return f"[token-economics: tool result masked, {chars} characters]"


def _text_length(content: Any) -> int:
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return sum(
            len(b["text"])
            for b in content
            if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str)
        )
    return 0


class ObservationMasking:
    name = "observation_masking"
    fail_closed = False

    def __init__(
        self,
        min_events: int = DEFAULT_MIN_EVENTS,
        keep: int = DEFAULT_KEEP,
        step: int = DEFAULT_STEP,
        protect_tools: Sequence[str] = DEFAULT_PROTECT_TOOLS,
    ) -> None:
        self.min_events = min_events
        self.keep = keep
        self.step = step
        self.protect_tools = frozenset(protect_tools)

    def before(self, ctx: RequestContext) -> Decision | None:
        return None

    def rewrite(self, ctx: RequestContext, body: dict[str, Any]) -> Rewrite | None:
        if ctx.provider != "anthropic":
            return None
        messages = body.get("messages")
        if not isinstance(messages, list):
            return None
        tools: dict[str, str] = {}
        events = 0
        for msg in messages:
            content = msg.get("content") if isinstance(msg, dict) else None
            if not isinstance(content, list):
                continue
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    events += 1
        if events <= self.min_events:
            return None
        # The boundary moves only every `step` events, so between moves the masked prefix is byte-identical.
        boundary = ((events - self.keep) // self.step) * self.step
        if boundary <= 0:
            return None

        out: list[Any] = []
        index = masked = chars_total = 0
        for msg in messages:
            content = msg.get("content") if isinstance(msg, dict) else None
            if not isinstance(content, list):
                out.append(msg)
                continue
            if msg.get("role") == "assistant":
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        tools[str(b.get("id"))] = str(b.get("name"))
                out.append(msg)
                continue
            new_content: list[Any] = []
            changed = False
            for b in content:
                if not (isinstance(b, dict) and b.get("type") == "tool_result"):
                    new_content.append(b)
                    continue
                position, index = index, index + 1
                chars = _text_length(b.get("content"))
                if (
                    position >= boundary
                    or b.get("is_error") is True
                    or tools.get(str(b.get("tool_use_id")), "") in self.protect_tools
                    or chars <= len(_marker(chars))  # masking must not add tokens
                ):
                    new_content.append(b)
                    continue
                new_content.append({**b, "content": _marker(chars)})
                changed = True
                masked += 1
                chars_total += chars
            out.append({**msg, "content": new_content} if changed else msg)
        if not masked:
            return None
        return Rewrite(
            body={**body, "messages": out},
            changes=(f"masked {masked} of {events} tool results, {chars_total} chars",),
        )

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        return None


def _int(value: Any, default: int, low: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= low else default


def create(env: FeatureEnv) -> ObservationMasking:
    cfg = env.config
    tools = cfg.get("protect_tools")
    return ObservationMasking(
        min_events=_int(cfg.get("min_events"), DEFAULT_MIN_EVENTS, 0),
        keep=_int(cfg.get("keep"), DEFAULT_KEEP, 0),
        step=_int(cfg.get("step"), DEFAULT_STEP, 1),
        protect_tools=tools
        if isinstance(tools, list) and all(isinstance(t, str) for t in tools)
        else DEFAULT_PROTECT_TOOLS,
    )
