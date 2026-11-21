"""Claude Code: base URL, OAuth passthrough, blocking hooks, OTel, budget flags, transcripts."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any

from token_economics_contracts.types import Capabilities, Identity, Observation, QuerySource, RequestFacts

from .. import _anthropic_wire
from .._sse import header

__all__ = ["ADAPTER", "ClaudeCodeAdapter"]


class ClaudeCodeAdapter:
    name = "claude_code"
    provider = "anthropic"
    capabilities = Capabilities(
        base_url=True,
        oauth_passthrough=True,
        hooks_blocking=True,
        otel=True,
        budget_flag=True,
        headless=True,
        model_rewrite=False,
        transcript_path=True,
    )

    def route(self, gateway_url: str, key: str) -> dict[str, str]:
        # The user's own Anthropic credential still goes upstream untouched.
        return {"ANTHROPIC_BASE_URL": gateway_url, "ANTHROPIC_CUSTOM_HEADERS": f"x-token-economics-key: {key}"}

    def matches(self, method: str, path: str, headers: Mapping[str, str]) -> bool:
        return (
            method.upper() == "POST"
            and path.split("?", 1)[0].rstrip("/").endswith("/v1/messages")
            and header(headers, "user-agent").lower().startswith("claude-cli")
        )

    def identify(self, headers: Mapping[str, str], body: bytes) -> Identity:
        try:
            session = header(headers, "x-claude-code-session-id") or _anthropic_wire.session_from_metadata(body)
            authz, api_key = header(headers, "authorization"), header(headers, "x-api-key")
            if authz.startswith("Bearer sk-ant-oat"):
                auth_mode = "oauth"
            elif api_key or authz.lower().startswith("bearer "):
                auth_mode = "api_key"
            else:
                auth_mode = "unknown"
            sub = bool(header(headers, "x-claude-code-agent-id") or header(headers, "x-claude-code-parent-session-id"))
            return Identity(
                session_id=session,
                query_source=QuerySource.SUBAGENT if sub else QuerySource.MAIN,
                auth_mode=auth_mode,
            )
        except Exception:  # noqa: BLE001
            return Identity()

    def facts(self, headers: Mapping[str, str], body: bytes) -> RequestFacts:
        return _anthropic_wire.facts(body)

    def observe(self, status: int, headers: Mapping[str, str], body: bytes) -> Observation | None:
        return _anthropic_wire.observe(status, headers, body)

    def cap(self, policy: Mapping[str, Any]) -> dict[str, str]:
        flags: dict[str, str] = {}
        if policy.get("budget_usd") is not None:
            flags["--max-budget-usd"] = str(policy["budget_usd"])
        if policy.get("max_turns") is not None:
            flags["--max-turns"] = str(policy["max_turns"])
        return flags

    def replay(self, transcript: Path) -> Iterable[Observation]:
        return list(_replay(transcript))


def _replay(transcript: Path) -> Iterator[Observation]:
    """One observation per message id, in first-seen order, with the last usage seen for that id."""
    latest: dict[str, tuple[str, dict[str, Any]]] = {}
    try:
        lines = transcript.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    for line in lines:
        try:
            entry = json.loads(line)
            if not isinstance(entry, dict) or entry.get("type") != "assistant":
                continue
            message = entry.get("message")
            if not isinstance(message, dict):
                continue
            mid, model, usage = message.get("id"), message.get("model"), message.get("usage")
            if not isinstance(mid, str) or not isinstance(usage, dict) or not usage or model == "<synthetic>":
                continue
            latest[mid] = (model if isinstance(model, str) else "", usage)  # re-assigning keeps first-seen order
        except ValueError:
            continue
    for mid, (model, usage) in latest.items():
        tier, speed, geo = usage.get("service_tier"), usage.get("speed"), usage.get("inference_geo")
        yield Observation(
            provider="anthropic",
            response_id=mid,
            model=model,
            usage=dict(usage),
            service_tier=tier if isinstance(tier, str) and tier else "standard",
            speed=speed if isinstance(speed, str) else "",
            inference_geo=geo if isinstance(geo, str) else "",
        )


ADAPTER = ClaudeCodeAdapter()
