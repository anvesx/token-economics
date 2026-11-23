"""Mark rarely needed tool schemas as deferred and add the provider's tool search tool."""

from __future__ import annotations

import json
import threading
from collections import OrderedDict
from typing import Any

from token_economics_contracts.types import FeatureEnv, LedgerRow, RequestContext, Rewrite

DEFAULT_MIN_TOOLS = 20
DEFAULT_MIN_SHARE = 0.10
DEFAULT_KEEP = (
    "Bash",
    "Read",
    "Edit",
    "MultiEdit",
    "Write",
    "Glob",
    "Grep",
    "Task",
    "Agent",
    "TodoWrite",
    "WebFetch",
    "WebSearch",
    "NotebookEdit",
    "Skill",
)
DEFAULT_SEARCH_TOOL: dict[str, Any] = {  # unverified
    "type": "tool_search_tool_regex_20251119",
    "name": "tool_search_tool_regex",
}
DEFAULT_BETA = "advanced-tool-use-2025-11-20"  # unverified
MAX_SESSIONS = 10_000


def _pos_int(value: Any, default: int) -> int:
    ok = isinstance(value, int) and not isinstance(value, bool) and value >= 0
    return value if ok else default


def _share(value: Any, default: float) -> float:
    ok = isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1
    return float(value) if ok else default


def _is_custom(tool: dict[str, Any]) -> bool:
    return bool(tool.get("type", "custom") == "custom")


class SchemaDeferral:
    name = "schema_deferral"
    fail_closed = False

    def __init__(
        self,
        min_tools: int = DEFAULT_MIN_TOOLS,
        min_share: float = DEFAULT_MIN_SHARE,
        keep: tuple[str, ...] = DEFAULT_KEEP,
        search_tool: dict[str, Any] | None = None,
        beta: str = DEFAULT_BETA,
    ) -> None:
        self.min_tools = min_tools
        self.min_share = min_share
        self.keep = frozenset(keep)
        self.search_tool = dict(search_tool or DEFAULT_SEARCH_TOOL)
        self.beta = beta
        # Sessions where deferral fired. The share rule shrinks as a conversation grows; without this a session could
        # stop deferring mid-way, change its tool list and lose the cached prefix.
        self._fired: OrderedDict[str, None] = OrderedDict()
        self._lock = threading.Lock()

    def _remember(self, session_id: str) -> None:
        with self._lock:
            self._fired[session_id] = None
            self._fired.move_to_end(session_id)
            while len(self._fired) > MAX_SESSIONS:
                self._fired.popitem(last=False)

    def before(self, ctx: RequestContext) -> None:
        return None

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        return None

    def rewrite(self, ctx: RequestContext, body: dict[str, Any]) -> Rewrite | None:
        if ctx.provider != "anthropic":
            return None
        tools = body.get("tools")
        if not isinstance(tools, list) or not tools or not all(isinstance(t, dict) for t in tools):
            return None
        for t in tools:
            if "defer_loading" in t or str(t.get("type", "")).startswith("tool_search_tool"):
                return None  # the harness manages tool search itself
        try:
            schema_tokens = len(json.dumps(tools, sort_keys=True)) / 4
        except (TypeError, ValueError):
            return None
        est = ctx.facts.est_input_tokens
        share_hit = est > 0 and schema_tokens / est > self.min_share
        sid = ctx.identity.session_id
        with self._lock:
            fired_before = bool(sid) and sid in self._fired
        if not (len(tools) > self.min_tools or share_hit or fired_before):
            return None
        defer = [i for i, t in enumerate(tools) if _is_custom(t) and t.get("name") not in self.keep]
        if not defer or len(defer) == len(tools):
            return None
        if sid:
            self._remember(sid)
        marked = set(defer)
        new_tools = [{**t, "defer_loading": True} if i in marked else t for i, t in enumerate(tools)]
        new_tools.append(dict(self.search_tool))
        return Rewrite(
            body={**body, "tools": new_tools},
            changes=(f"deferred {len(defer)} of {len(tools)} tools",),
            add_headers=(("anthropic-beta", self.beta),),
        )


def create(env: FeatureEnv) -> SchemaDeferral:
    c = env.config
    keep = c.get("keep")
    search = c.get("search_tool")
    beta = c.get("beta")
    return SchemaDeferral(
        min_tools=_pos_int(c.get("min_tools"), DEFAULT_MIN_TOOLS),
        min_share=_share(c.get("min_share"), DEFAULT_MIN_SHARE),
        keep=tuple(k for k in keep if isinstance(k, str)) if isinstance(keep, list) else DEFAULT_KEEP,
        search_tool=search if isinstance(search, dict) and search else None,
        beta=beta if isinstance(beta, str) and beta else DEFAULT_BETA,
    )
