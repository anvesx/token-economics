"""Every provider's seed rows. All unverified: see each provider file."""

from __future__ import annotations

from token_economics_contracts import PriceRow

from .providers import anthropic, openai


def seed_rows() -> list[PriceRow]:
    return [*anthropic.rows(), *openai.rows()]
