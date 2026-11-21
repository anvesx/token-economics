"""Packages meet at runtime: each registers its implementations under one of these entry-point groups."""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any

ADAPTERS = "token_economics.adapters"
NORMALISERS = "token_economics.normalisers"
UPSTREAMS = "token_economics.upstreams"
FEATURES = "token_economics.features"  # values are factories: (env: FeatureEnv) -> Feature
SERVICES = "token_economics.services"  # names: "ledger", "pricebook", "cost", "detectors"; values are factories


def load_all(group: str) -> dict[str, Any]:
    """Every object registered under `group`, by entry-point name."""
    return {ep.name: ep.load() for ep in entry_points(group=group)}


def load(group: str, name: str) -> Any:
    """One registered object. Raises LookupError with the names that do exist."""
    found = entry_points(group=group)
    for ep in found:
        if ep.name == name:
            return ep.load()
    raise LookupError(f"nothing registered as {name!r} in {group}; found {sorted(e.name for e in found)}")
