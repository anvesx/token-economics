"""Pull request title check: Conventional Commits with a folder scope.

    python3 tools/check_pr_title.py "feat(ledger): append-only rows"

`type(scope): summary`. Types: feat, fix, test, docs, chore, spike, gate. The scope is a package folder name
(from plan/model/layout.json, e.g. `ledger`, `upstream`) or a top-level folder (e.g. `tools`, `docs`). Prints one line
and exits 1 when the title does not match. Stdlib only, so CI runs it without installing anything.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _layout import load_layout

TYPES = ("feat", "fix", "test", "docs", "chore", "spike", "gate")
TOP_LEVEL = ("tools", "docs", "plan", "ops", "evals", "papers", "spikes", "research", "github", "deps")
PATTERN = re.compile(r"^(?P<type>[a-z]+)\((?P<scope>[a-z0-9-]+)\)(?P<bang>!)?: (?P<summary>\S.*)$")


def scopes() -> set[str]:
    return {Path(spec["dir"]).name for spec in load_layout().values()} | set(TOP_LEVEL)


def check(title: str, allowed: set[str]) -> str | None:
    """None when the title is fine, else what is wrong."""
    match = PATTERN.match(title.strip())
    if match is None:
        return f"PR title must look like `type(scope): summary`, got: {title!r}"
    if match["type"] not in TYPES:
        return f"PR title type {match['type']!r} is not one of {', '.join(TYPES)}"
    if match["scope"] not in allowed:
        return f"PR title scope {match['scope']!r} is not a folder name (try one of: {', '.join(sorted(allowed))})"
    return None


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: check_pr_title.py <title>", file=sys.stderr)
        return 2
    problem = check(argv[0], scopes())
    if problem:
        print(problem)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
