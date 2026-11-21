"""Agent SDK and plain Messages API clients: base URL only."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from token_economics_contracts.types import Capabilities, Identity, Observation

from .. import _anthropic_wire

__all__ = ["ADAPTER", "SdkAdapter"]


class SdkAdapter:
    name = "sdk"
    provider = "anthropic"
    capabilities = Capabilities(base_url=True)

    def route(self, gateway_url: str, key: str) -> dict[str, str]:
        # The client must also send `key` as the default header `x-token-economics-key`.
        return {"ANTHROPIC_BASE_URL": gateway_url, "TOKEN_ECONOMICS_KEY": key}

    def matches(self, method: str, path: str, headers: Mapping[str, str]) -> bool:
        # Fallback for the Messages API: the gateway asks Claude Code first.
        return method.upper() == "POST" and path.split("?", 1)[0].rstrip("/").endswith("/v1/messages")

    def identify(self, headers: Mapping[str, str], body: bytes) -> Identity:
        try:
            return Identity(session_id=_anthropic_wire.session_from_metadata(body))
        except Exception:  # noqa: BLE001
            return Identity()

    def observe(self, status: int, headers: Mapping[str, str], body: bytes) -> Observation | None:
        return _anthropic_wire.observe(status, headers, body)

    def cap(self, policy: Mapping[str, Any]) -> dict[str, str]:
        return {}

    def replay(self, transcript: Path) -> Iterable[Observation]:
        return ()  # not built: SDK clients have no transcript format


ADAPTER = SdkAdapter()
