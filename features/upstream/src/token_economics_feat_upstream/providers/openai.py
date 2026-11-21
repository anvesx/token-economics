"""OpenAI upstream: where requests go and which headers pass through."""

from __future__ import annotations

import os
from collections.abc import Mapping

from .._http import forward, join_url

__all__ = ["DEFAULT_BASE_URL", "ENV_VAR", "SECRET_HEADERS", "UPSTREAM", "OpenAIUpstream"]

DEFAULT_BASE_URL = "https://api.openai.com"
ENV_VAR = "TOKEN_ECONOMICS_UPSTREAM_OPENAI"

# Header names whose values must never be written to disk.
SECRET_HEADERS = frozenset({"authorization", "x-api-key", "x-token-economics-key", "cookie", "proxy-authorization"})


class OpenAIUpstream:
    provider = "openai"

    def __init__(self, base_url: str | None = None) -> None:
        # Argument first, then the environment (read now, at construction), then the default.
        self.base_url = (base_url or os.environ.get(ENV_VAR) or DEFAULT_BASE_URL).rstrip("/")

    def url(self, path: str, query: str) -> str:
        return join_url(self.base_url, path, query)

    def forward_headers(self, headers: Mapping[str, str]) -> dict[str, str]:
        return forward(headers)


UPSTREAM = OpenAIUpstream()
