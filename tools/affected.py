"""Which packages does a change touch?

    uv run python tools/affected.py origin/main            # layout keys, one per line
    uv run python tools/affected.py origin/main --dirs     # package folders instead of keys
    uv run python tools/affected.py --all                  # every existing package

Prints the packages touched by `git diff --name-only <base-ref>...HEAD`, plus everything that depends on them
(transitively, from plan/model/layout.json). A change under tools/, .github/, the root pyproject.toml or uv.lock means
all packages. Only packages whose folder exists are printed.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from _layout import ROOT, Layout, dependents_closure, existing, load_layout

ALL_PREFIXES = ("tools/", ".github/")
ALL_FILES = {"pyproject.toml", "uv.lock", ".python-version", "ruff.toml"}


def affected(layout: Layout, changed: list[str], present: list[str] | None = None) -> list[str]:
    """Layout keys touched by the changed paths plus their dependents. `present` limits the answer (default: all)."""
    keys = present if present is not None else list(layout)
    if any(f in ALL_FILES or f.startswith(ALL_PREFIXES) for f in changed):
        return sorted(keys)
    touched = {key for key, spec in layout.items() if any(f.startswith(spec["dir"] + "/") for f in changed)}
    return sorted(k for k in dependents_closure(layout, touched) if k in keys)


def changed_files(base: str, root: Path = ROOT) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"], cwd=root, capture_output=True, text=True, check=False
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or f"git diff failed for {base}")
    return [line for line in out.stdout.splitlines() if line]


def main(argv: list[str]) -> int:
    flags = [a for a in argv if a.startswith("--")]
    args = [a for a in argv if not a.startswith("--")]
    layout = load_layout()
    present = existing(layout)
    if "--all" in flags:
        keys = sorted(present)
    elif len(args) == 1:
        try:
            keys = affected(layout, changed_files(args[0]), present)
        except RuntimeError as exc:
            print(f"affected.py: {exc}", file=sys.stderr)
            return 2
    else:
        print("usage: affected.py <base-ref> [--dirs] | --all [--dirs]", file=sys.stderr)
        return 2
    for key in keys:
        print(layout[key]["dir"] if "--dirs" in flags else key)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
