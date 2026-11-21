"""Seed price rows for OpenAI models: none yet.

plan/04 records conflicting figures for the GPT-6 cache-write charge (1.25x on a third-party sheet, 2.5x in a changelog
snippet) and says to read OpenAI's own page before use. No row is seeded from an unresolved conflict, so OpenAI
responses are stored with `cost_estimate_usd` empty until rows are added from the vendor page.
"""

from __future__ import annotations

from token_economics_contracts import PriceRow

PROVIDER = "openai"


def rows() -> list[PriceRow]:
    return []
