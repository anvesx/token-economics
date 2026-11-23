"""Every alert has an owner, a runbook and an entry in `ops/alerts.json`.

    uv run python tools/check_alerts.py [--require-owners]

Fails (exit 1, one line per problem) when:
- an entry in `ops/alerts.json` lacks a field, or its runbook file does not exist;
- a `Decision(... code="...")` literal, or an alert record `"kind": "..."` literal (in a file that writes alerts),
  in `features/*/src`, `services/*/src` or `apps/*/src` has no entry in `ops/alerts.json`;
- with `--require-owners`, an entry still has the owner `UNASSIGNED`.

Entries with no literal in the source are allowed: some alerts are computed (budget thresholds, gateway down) or
come from a package that is not built yet. Uses `re` only, nothing needs to be installed. The vendored
`hermes/` folder and test folders are not scanned.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path

from _layout import ROOT

ALERTS_FILE = "ops/alerts.json"
FIELDS = ("kind", "source", "severity", "owner", "runbook")
SEVERITIES = {"page", "ticket", "info"}
UNASSIGNED = "UNASSIGNED"
SCAN = ("features", "services", "apps")
CODE = re.compile(r"""\bcode\s*=\s*["']([A-Za-z0-9_]+)["']""")
KIND = re.compile(r"""["']kind["']\s*:\s*["']([A-Za-z0-9_]+)["']""")


def source_literals(root: Path) -> dict[str, str]:
    """Alert names found in source, each with the first file that holds it."""
    found: dict[str, str] = {}
    for top in SCAN:
        for path in sorted((root / top).glob("*/src/**/*.py")):
            rel = path.relative_to(root)
            if "hermes" in rel.parts or "tests" in rel.parts:
                continue
            text = path.read_text()
            names = CODE.findall(text)
            if "alert" in text.lower():
                names += KIND.findall(text)
            for name in names:
                found.setdefault(name, rel.as_posix())
    return found


def check(root: Path = ROOT, require_owners: bool = False) -> list[str]:
    path = root / ALERTS_FILE
    try:
        entries = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        return [f"{ALERTS_FILE}: cannot read ({type(e).__name__})"]
    if not isinstance(entries, list):
        return [f"{ALERTS_FILE}: must be a list of entries"]
    problems: list[str] = []
    kinds: set[str] = set()
    for i, entry in enumerate(entries):
        label = f"{ALERTS_FILE}[{i}]"
        if not isinstance(entry, dict):
            problems.append(f"{label}: not an object")
            continue
        label = f"{ALERTS_FILE}: {entry.get('kind', i)}"
        for f in FIELDS:
            if not isinstance(entry.get(f), str) or not entry[f]:
                problems.append(f"{label}: missing {f}")
        if entry.get("severity") not in SEVERITIES:
            problems.append(f"{label}: severity must be one of {sorted(SEVERITIES)}")
        kind = entry.get("kind")
        if isinstance(kind, str):
            if kind in kinds:
                problems.append(f"{label}: listed twice")
            kinds.add(kind)
        runbook = entry.get("runbook")
        if isinstance(runbook, str) and runbook and not (root / runbook).is_file():
            problems.append(f"{label}: runbook {runbook} does not exist")
        if require_owners and entry.get("owner") == UNASSIGNED:
            problems.append(f"{label}: owner is {UNASSIGNED}")
    for name, where in sorted(source_literals(root).items()):
        if name not in kinds:
            problems.append(f"{where}: {name!r} is emitted but has no entry in {ALERTS_FILE}")
    return problems


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Every alert has an owner, a runbook and an entry")
    p.add_argument("--require-owners", action="store_true", help="fail while any owner is UNASSIGNED")
    a = p.parse_args(argv)
    problems = check(ROOT, a.require_owners)
    for line in problems:
        print(line)
    if not problems:
        print("alerts ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
