"""Codex CLI: model_providers base URL, Responses wire."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from token_economics_contracts.types import Capabilities, Identity, Observation

from .. import _responses_wire
from .._sse import header

__all__ = ["ADAPTER", "CodexAdapter"]


class CodexAdapter:
    name = "codex"
    provider = "openai"
    capabilities = Capabilities(base_url=True, otel=True, headless=True, transcript_path=True)

    def route(self, gateway_url: str, key: str) -> dict[str, str]:
        # Config keys for ~/.codex/config.toml (Codex ignores project-local config for these). `key` is
        # not placed in config: the user's own OpenAI credential goes upstream untouched.
        return {
            "model_providers.token-economics.base_url": gateway_url.rstrip("/") + "/v1",
            "model_providers.token-economics.wire_api": "responses",
            "model_provider": "token-economics",
        }

    def matches(self, method: str, path: str, headers: Mapping[str, str]) -> bool:
        return method.upper() == "POST" and path.split("?", 1)[0].rstrip("/").endswith("/responses")

    def identify(self, headers: Mapping[str, str], body: bytes) -> Identity:
        try:
            return Identity(session_id=header(headers, "session_id") or header(headers, "conversation_id"))
        except Exception:  # noqa: BLE001
            return Identity()

    def observe(self, status: int, headers: Mapping[str, str], body: bytes) -> Observation | None:
        return _responses_wire.observe(status, headers, body)

    def cap(self, policy: Mapping[str, Any]) -> dict[str, str]:
        return {}

    def replay(self, transcript: Path) -> Iterable[Observation]:
        return ()  # not built: the history.jsonl shape is not in the corpus


ADAPTER = CodexAdapter()
