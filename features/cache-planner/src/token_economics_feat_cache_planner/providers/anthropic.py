"""Anthropic Messages bodies: the prefix key and the `cache_control` TTLs the client already placed."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Iterator
from typing import Any

DEFAULT_TTL = "5m"  # a cache_control block without `ttl` is a 5-minute breakpoint


def prefix_hash(body: dict[str, Any], scope: str, harness: str) -> str | None:
    """Hash of (model, tools, system) and the caller scope. Numbers and hashes only ever leave this function."""
    model = body.get("model")
    if not isinstance(model, str) or not model:
        return None
    try:
        canon = json.dumps(
            [model, body.get("tools"), body.get("system"), scope, harness],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    except (TypeError, ValueError):
        return None
    return hashlib.sha256(canon.encode()).hexdigest()


def _blocks(body: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Every block the client could have put a `cache_control` on: tools, system blocks, message content blocks."""
    for key in ("tools", "system"):
        value = body.get(key)
        if isinstance(value, list):
            yield from (b for b in value if isinstance(b, dict))
    messages = body.get("messages")
    if isinstance(messages, list):
        for message in messages:
            content = message.get("content") if isinstance(message, dict) else None
            if isinstance(content, list):
                yield from (b for b in content if isinstance(b, dict))


def _controls(body: dict[str, Any]) -> Iterator[dict[str, Any]]:
    for block in _blocks(body):
        cc = block.get("cache_control")
        if isinstance(cc, dict):
            yield cc


def ttls_in(body: dict[str, Any]) -> set[str]:
    """The TTLs of the breakpoints the client placed (empty when it placed none)."""
    return {str(cc.get("ttl", DEFAULT_TTL)) for cc in _controls(body)}


def with_ttl(body: dict[str, Any], ttl: str) -> dict[str, Any]:
    """A copy of `body` with every existing breakpoint at `ttl`: "1h" sets it, "5m" drops the key. Adds none."""
    out = copy.deepcopy(body)
    for cc in _controls(out):
        if ttl == DEFAULT_TTL:
            cc.pop("ttl", None)
        else:
            cc["ttl"] = ttl
    return out
