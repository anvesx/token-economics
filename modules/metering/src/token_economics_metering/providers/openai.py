"""OpenAI usage to five buckets.

`input_tokens` / `prompt_tokens` INCLUDE cached tokens (plan/03): fresh = input - cached.

Handles the Responses shape (input_tokens, output_tokens) and the Chat Completions shape (prompt_tokens,
completion_tokens). No cache-write field is known; a response that carries one is rejected as an unknown key, which is
how a new write charge shows up instead of being priced wrongly.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from token_economics_contracts import Buckets

from ._keys import reject_unknown, tokens

PROVIDER = "openai"
RESPONSES_KEYS = ("input_tokens", "output_tokens", "total_tokens", "input_tokens_details", "output_tokens_details")
CHAT_KEYS = ("prompt_tokens", "completion_tokens", "total_tokens", "prompt_tokens_details", "completion_tokens_details")
INPUT_DETAIL_KEYS = ("cached_tokens", "audio_tokens")
OUTPUT_DETAIL_KEYS = ("reasoning_tokens", "audio_tokens", "accepted_prediction_tokens", "rejected_prediction_tokens")


class OpenAINormaliser:
    provider = PROVIDER

    def normalise(self, usage: Mapping[str, Any]) -> Buckets:
        chat = "prompt_tokens" in usage or "completion_tokens" in usage
        reject_unknown(PROVIDER, usage, CHAT_KEYS if chat else RESPONSES_KEYS)
        in_key, out_key, in_detail, out_detail = (
            ("prompt_tokens", "completion_tokens", "prompt_tokens_details", "completion_tokens_details")
            if chat
            else ("input_tokens", "output_tokens", "input_tokens_details", "output_tokens_details")
        )
        details = usage.get(in_detail) or {}
        if not isinstance(details, Mapping):
            raise ValueError(f"usage.{in_detail} is not an object: {details!r}")
        reject_unknown(PROVIDER, details, INPUT_DETAIL_KEYS, prefix=f"{in_detail}.")
        out_details = usage.get(out_detail) or {}
        if isinstance(out_details, Mapping):  # reasoning is already inside the output count: checked, never added
            reject_unknown(PROVIDER, out_details, OUTPUT_DETAIL_KEYS, prefix=f"{out_detail}.")
        total_in, cached, out = tokens(usage, in_key), tokens(details, "cached_tokens"), tokens(usage, out_key)
        if cached > total_in:
            raise ValueError(f"cached_tokens {cached} exceeds {in_key} {total_in}")
        if usage.get("total_tokens") is not None and tokens(usage, "total_tokens") != total_in + out:
            raise ValueError(f"total_tokens {usage['total_tokens']} is not {in_key} + {out_key} ({total_in + out})")
        return Buckets(fresh_input=total_in - cached, cache_read=cached, output=out)


NORMALISER = OpenAINormaliser()
