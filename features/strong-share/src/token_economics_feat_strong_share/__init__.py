"""Cap each tenant's share of strong-model calls and alert on drift."""

from .strong_share import StrongShare, create

__all__ = ["StrongShare", "create"]
