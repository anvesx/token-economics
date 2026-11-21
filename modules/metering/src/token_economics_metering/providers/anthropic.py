"""Anthropic Messages usage to five buckets. `input_tokens` excludes cache reads and writes (plan/03)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from token_economics_contracts import Buckets

from ._keys import reject_unknown, tokens

PROVIDER = "anthropic"
TOKEN_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
    "cache_creation",
)
# Present in real responses, carry no extra billable tokens: routing labels, reasoning already inside output_tokens,
# per-iteration breakdowns of the same totals. server_tool_use counts requests billed as fees, not tokens
# (fees are not priced yet).
INFO_KEYS = (
    "service_tier",
    "inference_geo",
    "speed",
    "output_tokens_details",
    "server_tool_use",
    "iterations",
    "fallback_credit",
)
SPLIT_KEYS = ("ephemeral_5m_input_tokens", "ephemeral_1h_input_tokens")


class AnthropicNormaliser:
    provider = PROVIDER

    def normalise(self, usage: Mapping[str, Any]) -> Buckets:
        reject_unknown(PROVIDER, usage, TOKEN_KEYS + INFO_KEYS)
        written = tokens(usage, "cache_creation_input_tokens")
        split = usage.get("cache_creation")
        w5 = w1h = 0
        if isinstance(split, Mapping):
            reject_unknown(PROVIDER, split, SPLIT_KEYS, prefix="cache_creation.")
            w5, w1h = tokens(split, SPLIT_KEYS[0]), tokens(split, SPLIT_KEYS[1])
            if w5 + w1h > written and "cache_creation_input_tokens" in usage:
                raise ValueError(f"cache_creation split {w5 + w1h} exceeds cache_creation_input_tokens {written}")
            written = max(written, w5 + w1h)
        elif split is not None:
            raise ValueError(f"usage.cache_creation is not an object: {split!r}")
        # Writes with no recorded lifetime are 5-minute writes: the API's default cache lifetime.
        w5 += written - w5 - w1h
        return Buckets(
            fresh_input=tokens(usage, "input_tokens"),
            cache_read=tokens(usage, "cache_read_input_tokens"),
            cache_write_5m=w5,
            cache_write_1h=w1h,
            output=tokens(usage, "output_tokens"),
        )


NORMALISER = AnthropicNormaliser()
