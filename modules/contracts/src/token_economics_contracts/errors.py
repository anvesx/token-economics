"""Errors every package may raise or catch."""

from __future__ import annotations


class TokenEconomicsError(Exception):
    """Base class."""


class UnknownUsageKey(TokenEconomicsError):
    """A usage object carried a key the normaliser does not know. Rejected, never guessed (03, rule 1)."""

    def __init__(self, provider: str, keys: list[str]) -> None:
        super().__init__(f"{provider}: unknown usage keys {sorted(keys)}")
        self.provider, self.keys = provider, sorted(keys)


class NoPriceRow(TokenEconomicsError):
    """No price row is in force for this provider, exact model id, tier and date."""


class PriceBookViolation(TokenEconomicsError):
    """An attempt to change or contradict an existing price row. The price book is append-only."""
