"""Anthropic Messages wire format: observe a response, read the session id from a request."""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from token_economics_contracts.types import Observation

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
