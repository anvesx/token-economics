"""Shared helpers for the repo checks: read plan/model/layout.json, map keys to names and folders.

Every check works on "the packages whose folder exists" and ignores layout entries with no folder yet.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
Layout = dict[str, dict[str, Any]]

# Imports may only point to the left of this list (rule 1 of plan/13-monorepo-layout.md).
KIND_ORDER = ["contracts", "module", "feature", "service", "app"]


def load_layout(root: Path = ROOT) -> Layout:
    data: Layout = json.loads((root / "plan/model/layout.json").read_text())
    return data


def dist_name(key: str) -> str:
    return f"token-economics-{key}"


def module_name(key: str) -> str:
    return dist_name(key).replace("-", "_")


def existing(layout: Layout, root: Path = ROOT) -> list[str]:
    """Layout keys whose folder exists, in layout order."""
    return [k for k, spec in layout.items() if (root / spec["dir"]).is_dir()]


def src_dir(layout: Layout, key: str, root: Path = ROOT) -> Path:
    return Path(root / layout[key]["dir"]) / "src" / module_name(key)


def dependency_closure(layout: Layout, keys: list[str]) -> set[str]:
    """The keys plus everything they depend on, transitively."""
    seen: set[str] = set()
    todo = list(keys)
    while todo:
        key = todo.pop()
        if key in seen or key not in layout:
            continue
        seen.add(key)
        todo.extend(layout[key]["deps"])
    return seen


def dependents_closure(layout: Layout, keys: set[str]) -> set[str]:
    """The keys plus everything that depends on them, transitively."""
    seen = set(keys)
    grew = True
    while grew:
        grew = False
        for key, spec in layout.items():
            if key not in seen and any(d in seen for d in spec["deps"]):
                seen.add(key)
                grew = True
    return seen
