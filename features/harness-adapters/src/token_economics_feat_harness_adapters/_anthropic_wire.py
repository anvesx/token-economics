"""Anthropic Messages wire format: observe a response, read the session id from a request."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from token_economics_contracts.types import Observation, RequestFacts

from ._sse import events, header, is_sse, loads_object

_SESSION_RE = re.compile(r"session_([0-9a-fA-F-]{8,})")


def _observation(headers: Mapping[str, str], rid: Any, model: Any, usage: Any) -> Observation | None:
    if not isinstance(usage, dict) or not usage or not isinstance(rid, str):
        return None
    tier, speed, geo = usage.get("service_tier"), usage.get("speed"), usage.get("inference_geo")
    return Observation(
        provider="anthropic",
        response_id=rid,
        model=model if isinstance(model, str) else "",
        usage=dict(usage),
        request_id=header(headers, "request-id"),
        service_tier=tier if isinstance(tier, str) and tier else "standard",
        speed=speed if isinstance(speed, str) else "",
        inference_geo=geo if isinstance(geo, str) else "",
    )


def observe(status: int, headers: Mapping[str, str], body: bytes) -> Observation | None:
    """Never raises. None for non-2xx, empty, unparseable or usage-less bodies."""
    try:
        if not 200 <= status < 300 or not body.strip():
            return None
        text = body.decode("utf-8", errors="replace")
        if not is_sse(headers, text):
            msg = loads_object(body)
            if msg is None:
                return None
            return _observation(headers, msg.get("id"), msg.get("model"), msg.get("usage"))
        rid: Any = None
        model: Any = None
        usage: dict[str, Any] = {}
        for name, data in events(text):
            if not isinstance(data, dict):
                continue
            if name == "message_start" and isinstance(data.get("message"), dict):
                message = data["message"]
                rid, model = message.get("id"), message.get("model")
                if isinstance(message.get("usage"), dict):
                    usage = dict(message["usage"])
            elif name == "message_delta" and isinstance(data.get("usage"), dict):
                usage.update(data["usage"])  # cumulative final counts replace the message_start placeholders
        return _observation(headers, rid, model, usage)
    except Exception:  # noqa: BLE001  (observation must never break the request path)
        return None


def session_from_metadata(body: bytes) -> str:
    """Session id from the JSON body's `metadata.user_id`: a plain string or a JSON string with `session_id`."""
    try:
        parsed = loads_object(body)
        meta = parsed.get("metadata") if parsed else None
        user_id = meta.get("user_id") if isinstance(meta, dict) else None
        if not isinstance(user_id, str) or not user_id:
            return ""
        try:
            inner = json.loads(user_id)
        except ValueError:
            inner = None
        if isinstance(inner, dict):
            sid = inner.get("session_id")
            if isinstance(sid, str):
                return sid
        found = _SESSION_RE.search(user_id)
        return found.group(1) if found else ""
    except Exception:  # noqa: BLE001
        return ""


def _signature(name: Any, tool_input: Any) -> str:
    """First 16 hex chars of sha256 over the tool name and its canonical JSON input: a hash, never text."""
    raw = f"{name}\0{json.dumps(tool_input, sort_keys=True, separators=(',', ':'))}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _blocks(message: Any) -> list[dict[str, Any]]:
    """The content blocks of a message; a plain string content has none."""
    content = message.get("content") if isinstance(message, dict) else None
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


def _tool_results(messages: list[Any]) -> list[tuple[str, bool]]:
    """(signature, failed) for every tool result, in conversation order."""
    calls: dict[str, str] = {}
    results: list[tuple[str, bool]] = []
    for message in messages:
        role = message.get("role") if isinstance(message, dict) else None
        for block in _blocks(message):
            if role == "assistant" and block.get("type") == "tool_use" and isinstance(block.get("id"), str):
                calls[block["id"]] = _signature(block.get("name"), block.get("input"))
            elif role == "user" and block.get("type") == "tool_result":
                signature = calls.get(str(block.get("tool_use_id")))
                if signature is not None:  # a result with no matching call in the body cannot be compared
                    results.append((signature, block.get("is_error") is True))
    return results


def facts(body: bytes) -> RequestFacts:
    """Never raises; RequestFacts() for anything unparseable. Numbers and hashes only, never text.

    `est_input_tokens` is len(body) // 3: a rough upper estimate from the body size, not a token count.
    """
    try:
        parsed = loads_object(body)
        if parsed is None:
            return RequestFacts()
        messages = parsed.get("messages")
        messages = messages if isinstance(messages, list) else []
        turns = sum(1 for m in messages if isinstance(m, dict) and m.get("role") == "assistant")
        results = _tool_results(messages)
        last_failure = next((sig for sig, failed in reversed(results) if failed), "")
        repeats = 0
        for sig, failed in reversed(results):
            if not failed or sig != last_failure:
                break
            repeats += 1
        model, max_tokens = parsed.get("model"), parsed.get("max_tokens")
        return RequestFacts(
            model=model if isinstance(model, str) else "",
            max_tokens=max_tokens if isinstance(max_tokens, int) and not isinstance(max_tokens, bool) else None,
            stream=parsed.get("stream") is True,
            turns=turns,
            est_input_tokens=len(body) // 3,
            last_failure_signature=last_failure,
            trailing_repeat_failures=repeats,
        )
    except Exception:  # noqa: BLE001  (facts must never break the request path)
        return RequestFacts()
