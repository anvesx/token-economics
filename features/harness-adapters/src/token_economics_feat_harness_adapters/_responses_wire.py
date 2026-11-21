"""OpenAI Responses wire format (Codex): observe a response."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from token_economics_contracts.types import Observation, RequestFacts

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


def facts(body: bytes) -> RequestFacts:
    """Never raises; RequestFacts() for anything unparseable. Numbers only, never text.

    `est_input_tokens` is len(body) // 3: a rough upper estimate from the body size. Turn counting and the
    failure signature are not built for the Responses wire: `turns` stays 0 and the failure fields stay empty.
    """
    try:
        parsed = loads_object(body)
        if parsed is None:
            return RequestFacts()
        model, max_tokens = parsed.get("model"), parsed.get("max_output_tokens")
        return RequestFacts(
            model=model if isinstance(model, str) else "",
            max_tokens=max_tokens if isinstance(max_tokens, int) and not isinstance(max_tokens, bool) else None,
            stream=parsed.get("stream") is True,
            est_input_tokens=len(body) // 3,
        )
    except Exception:  # noqa: BLE001
        return RequestFacts()
