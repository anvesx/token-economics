"""Header and URL rules shared by every provider file. Header values are never stored or logged."""
from __future__ import annotations

from collections.abc import Mapping

HOP_BY_HOP = frozenset(
    {
        "host",
        "content-length",
        "connection",
        "keep-alive",
        "transfer-encoding",
        "te",
        "upgrade",
        "proxy-authorization",
        "proxy-connection",
    }
)
VIRTUAL_KEY_HEADER = "x-token-economics-key"
DROPPED = HOP_BY_HOP | {VIRTUAL_KEY_HEADER}


def forward(headers: Mapping[str, str]) -> dict[str, str]:
    """Every header unchanged (original name casing) except hop-by-hop headers and the virtual key."""
    return {name: value for name, value in headers.items() if name.lower() not in DROPPED}


def join_url(base_url: str, path: str, query: str) -> str:
    url = base_url.rstrip("/") + "/" + path.lstrip("/")
    return f"{url}?{query.lstrip('?')}" if query else url
