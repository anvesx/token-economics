"""Shared checks for usage objects."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from token_economics_contracts import UnknownUsageKey


def reject_unknown(provider: str, usage: Mapping[str, Any], known: Iterable[str], prefix: str = "") -> None:
    """Raise UnknownUsageKey when `usage` carries a key outside `known` (plan/03, normalisation rule 1)."""
    extra = [f"{prefix}{k}" for k in usage if k not in set(known)]
    if extra:
        raise UnknownUsageKey(provider, extra)


def tokens(usage: Mapping[str, Any], key: str) -> int:
    """A token count: missing or null is 0; anything but a non-negative whole number is an error."""
    value = usage.get(key)
    if value is None:
        return 0
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"usage.{key} is not a token count: {value!r}")
    return value
