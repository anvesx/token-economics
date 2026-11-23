"""Add Anthropic context management so the provider clears old tool results server-side."""

from __future__ import annotations

from typing import Any

from token_economics_contracts.types import FeatureEnv, LedgerRow, RequestContext, Rewrite

DEFAULT_TRIGGER = 35_000
DEFAULT_KEEP = 5
DEFAULT_CLEAR_AT_LEAST = 4_000
DEFAULT_EDIT_TYPE = "clear_tool_uses_20250919"  # unverified
DEFAULT_BETA = "context-management-2025-06-27"  # unverified


def _pos_int(value: Any, default: int) -> int:
    ok = isinstance(value, int) and not isinstance(value, bool) and value >= 1
    return value if ok else default


def _str(value: Any, default: str) -> str:
    return value if isinstance(value, str) and value else default


def _str_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(v for v in value if isinstance(v, str) and v)


class ContextClearing:
    name = "context_clearing"
    fail_closed = False

    def __init__(
        self,
        trigger: int = DEFAULT_TRIGGER,
        keep: int = DEFAULT_KEEP,
        clear_at_least: int = DEFAULT_CLEAR_AT_LEAST,
        exclude_tools: tuple[str, ...] = (),
        edit_type: str = DEFAULT_EDIT_TYPE,
        beta: str = DEFAULT_BETA,
        models: tuple[str, ...] = (),
    ) -> None:
        self.trigger = trigger
        self.keep = keep
        self.clear_at_least = clear_at_least
        self.exclude_tools = exclude_tools
        self.edit_type = edit_type
        self.beta = beta
        self.models = models

    def before(self, ctx: RequestContext) -> None:
        return None

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        return None

    def rewrite(self, ctx: RequestContext, body: dict[str, Any]) -> Rewrite | None:
        if ctx.provider != "anthropic" or "context_management" in body:
            return None
        if self.models and ctx.facts.model not in self.models:
            return None
        edit: dict[str, Any] = {
            "type": self.edit_type,
            "trigger": {"type": "input_tokens", "value": self.trigger},
            "keep": {"type": "tool_uses", "value": self.keep},
            "clear_at_least": {"type": "input_tokens", "value": self.clear_at_least},
        }
        if self.exclude_tools:
            edit["exclude_tools"] = list(self.exclude_tools)
        new_body = {**body, "context_management": {"edits": [edit]}}
        note = f"context_management trigger={self.trigger} keep={self.keep} clear_at_least={self.clear_at_least}"
        return Rewrite(body=new_body, changes=(note,), add_headers=(("anthropic-beta", self.beta),))


def create(env: FeatureEnv) -> ContextClearing:
    c = env.config
    return ContextClearing(
        trigger=_pos_int(c.get("trigger"), DEFAULT_TRIGGER),
        keep=_pos_int(c.get("keep"), DEFAULT_KEEP),
        clear_at_least=_pos_int(c.get("clear_at_least"), DEFAULT_CLEAR_AT_LEAST),
        exclude_tools=_str_list(c.get("exclude_tools")),
        edit_type=_str(c.get("edit_type"), DEFAULT_EDIT_TYPE),
        beta=_str(c.get("beta"), DEFAULT_BETA),
        models=_str_list(c.get("models")),
    )
