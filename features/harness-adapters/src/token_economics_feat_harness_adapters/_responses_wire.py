"""OpenAI Responses wire format (Codex): observe a response."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from token_economics_contracts.types import Observation

from ._sse import events, header, is_sse, loads_object


def _observation(headers: Mapping[str, str], response: Any) -> Observation | None:
    if not isinstance(response, dict):
        return None
    usage, rid, model = response.get("usage"), response.get("id"), response.get("model")
    if not isinstance(usage, dict) or not usage or not isinstance(rid, str):
        return None
    tier = response.get("service_tier")
    return Observation(
        provider="openai",
        response_id=rid,
        model=model if isinstance(model, str) else "",
        usage=dict(usage),
        request_id=header(headers, "x-request-id"),
        service_tier=tier if isinstance(tier, str) and tier else "standard",
    )


def observe(status: int, headers: Mapping[str, str], body: bytes) -> Observation | None:
    """Never raises. None for non-2xx, empty, unparseable or usage-less bodies."""
    try:
        if not 200 <= status < 300 or not body.strip():
            return None
        text = body.decode("utf-8", errors="replace")
        if not is_sse(headers, text):
            return _observation(headers, loads_object(body))
        for name, data in events(text):
            if name == "response.completed" and isinstance(data, dict):
                return _observation(headers, data.get("response"))
        return None
    except Exception:  # noqa: BLE001  (observation must never break the request path)
        return None
