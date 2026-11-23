"""Cap oversized tool results before they are sent, keeping head and tail, never cutting errors or edit anchors."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from token_economics_contracts.types import Decision, FeatureEnv, LedgerRow, RequestContext, Rewrite

DEFAULT_LIMIT_TOKENS = 25_000
DEFAULT_CHARS_PER_TOKEN = 4.0
DEFAULT_HEAD_SHARE = 0.7
DEFAULT_PROTECT_TOOLS: tuple[str, ...] = ("Read", "Edit", "MultiEdit", "Write", "NotebookEdit", "NotebookRead")
DEFAULT_PROTECT_PATTERNS: tuple[str, ...] = (
    r"Traceback \(most recent call last\)",  # Python
    r'^\s+File ".*", line \d+',  # Python frame
    r"^\s+at .+\(.+:\d+(?::\d+)?\)",  # JS / Java frame
    r"^\s+at [\w.$<>]+\(.*\.java:\d+\)",  # Java frame
    r"^Exception in thread ",  # Java
    r"^goroutine \d+ \[",  # Go
    r"\bpanic:",  # Go
    r"thread '.*' panicked at",  # Rust
    r"^error\[E\d+\]",  # Rust compiler
    r"\bFAILED\b",  # pytest and friends
    r"AssertionError",
    r"^=+ .*\b(?:FAILURES|failed)\b.* =+$",  # test-failure summary
)


def _marker(removed: int) -> str:
    return f"[token-economics: {removed} characters removed from this tool result]"


def _cap_text(text: str, allowed: int, head_share: float) -> tuple[str, int]:
    """Return (text, removed). Deterministic: depends only on the text and the numbers."""
    if len(text) <= allowed:
        return text, 0
    removed = len(text) - allowed
    head = int(allowed * head_share)
    tail = allowed - head
    tail_part = text[len(text) - tail :] if tail > 0 else ""
    return f"{text[:head]}\n{_marker(removed)}\n{tail_part}", removed


class OutputCap:
    name = "output_cap"
    fail_closed = False

    def __init__(
        self,
        limit_tokens: int = DEFAULT_LIMIT_TOKENS,
        chars_per_token: float = DEFAULT_CHARS_PER_TOKEN,
        head_share: float = DEFAULT_HEAD_SHARE,
        protect_tools: Sequence[str] = DEFAULT_PROTECT_TOOLS,
        protect_patterns: Sequence[str] = DEFAULT_PROTECT_PATTERNS,
    ) -> None:
        self.allowed = max(1, int(limit_tokens * chars_per_token))
        self.head_share = head_share
        self.protect_tools = frozenset(protect_tools)
        self.patterns = [re.compile(p, re.MULTILINE) for p in protect_patterns]

    def before(self, ctx: RequestContext) -> Decision | None:
        return None

    def _protected_text(self, text: str) -> bool:
        return any(p.search(text) for p in self.patterns)

    def _cap_result(self, block: dict[str, Any], tools: dict[str, str]) -> tuple[dict[str, Any], int] | None:
        if block.get("is_error") is True or tools.get(str(block.get("tool_use_id")), "") in self.protect_tools:
            return None
        content = block.get("content")
        if isinstance(content, str):
            if len(content) <= self.allowed or self._protected_text(content):
                return None
            text, removed = _cap_text(content, self.allowed, self.head_share)
            return {**block, "content": text}, removed
        if not isinstance(content, list):
            return None
        texts = [
            b["text"]
            for b in content
            if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str)
        ]
        if not any(len(t) > self.allowed for t in texts) or any(self._protected_text(t) for t in texts):
            return None
        total = 0
        parts: list[Any] = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str):
                text, removed = _cap_text(b["text"], self.allowed, self.head_share)
                if removed:
                    b = {**b, "text": text}
                    total += removed
            parts.append(b)
        return {**block, "content": parts}, total

    def rewrite(self, ctx: RequestContext, body: dict[str, Any]) -> Rewrite | None:
        if ctx.provider != "anthropic":
            return None
        messages = body.get("messages")
        if not isinstance(messages, list):
            return None
        tools: dict[str, str] = {}
        out: list[Any] = []
        capped = removed_total = 0
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
                result = self._cap_result(b, tools) if isinstance(b, dict) and b.get("type") == "tool_result" else None
                if result is None:
                    new_content.append(b)
                    continue
                new_content.append(result[0])
                changed = True
                capped += 1
                removed_total += result[1]
            out.append({**msg, "content": new_content} if changed else msg)
        if not capped:
            return None
        return Rewrite(
            body={**body, "messages": out},
            changes=(f"capped {capped} tool results, {removed_total} chars removed",),
        )

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        return None


def _num(value: Any, default: float, low: float, high: float | None = None, *, integer: bool = False) -> float:
    ok = isinstance(value, int | float) and not isinstance(value, bool) and value > low
    if ok and integer:
        ok = isinstance(value, int)
    if ok and high is not None:
        ok = value <= high
    return value if ok else default


def _strings(value: Any, default: Sequence[str]) -> Sequence[str]:
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return value
    return default


def create(env: FeatureEnv) -> OutputCap:
    cfg = env.config
    patterns: list[str] = []
    for p in _strings(cfg.get("protect_patterns"), DEFAULT_PROTECT_PATTERNS):
        try:
            re.compile(p)
        except re.error:
            continue  # a bad regex is dropped, not fatal
        patterns.append(p)
    return OutputCap(
        limit_tokens=int(_num(cfg.get("limit_tokens"), DEFAULT_LIMIT_TOKENS, 0, integer=True)),
        chars_per_token=float(_num(cfg.get("chars_per_token"), DEFAULT_CHARS_PER_TOKEN, 0)),
        head_share=float(_num(cfg.get("head_share"), DEFAULT_HEAD_SHARE, 0, 1)),
        protect_tools=_strings(cfg.get("protect_tools"), DEFAULT_PROTECT_TOOLS),
        protect_patterns=patterns,
    )
