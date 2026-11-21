"""Sync the vendored hermes-engine leak detectors, or check they are untouched.

    python sync_hermes.py /path/to/hermes-engine          copy the five files, rewrite VENDORED.md
    python sync_hermes.py --check                         exit 1 if a vendored file differs from its recorded sha256

Standard library only; the --check form needs no other repository.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

FILES = ("leak_report.py", "leak_extra.py", "leak_categories.py", "leak_config.py", "prompt_check.py")
SOURCE_SUBDIR = Path("plugins/token-metrics/scripts")
SOURCE_REPO = "hermes-engine"
HERE = Path(__file__).resolve().parent
VENDOR_DIR = HERE.parent / "src" / "token_economics_svc_insight" / "hermes"
MANIFEST = VENDOR_DIR / "VENDORED.md"

# One manifest row per file: "| `name.py` | <64 hex> |".
_ROW = re.compile(r"^\| `(?P<name>[\w.]+)` \| (?P<sha>[0-9a-f]{64}) \|$", re.MULTILINE)
_COMMIT = re.compile(r"^- Commit: `(?P<commit>[0-9a-f]{40})`$", re.MULTILINE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recorded() -> dict[str, str]:
    """File name -> sha256 recorded in VENDORED.md."""
    return {m["name"]: m["sha"] for m in _ROW.finditer(MANIFEST.read_text())}


def check(vendor_dir: Path | None = None) -> list[str]:
    """Problems found: a file missing, changed, or not in the manifest. Empty when untouched."""
    vendor_dir = vendor_dir or VENDOR_DIR
    want = recorded()
    problems = []
    for name in FILES:
        path = vendor_dir / name
        if name not in want:
            problems.append(f"{name}: not recorded in VENDORED.md")
        elif not path.is_file():
            problems.append(f"{name}: missing")
        elif sha256(path) != want[name]:
            problems.append(f"{name}: sha256 differs from VENDORED.md (edited by hand?)")
    return problems


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def sync(repo: Path) -> None:
    source = repo / SOURCE_SUBDIR
    missing = [n for n in FILES if not (source / n).is_file()]
    if missing:
        raise SystemExit(f"not a hermes-engine checkout (missing in {source}): {', '.join(missing)}")
    if _git(repo, "status", "--porcelain", "--", str(SOURCE_SUBDIR)):
        raise SystemExit("the checkout has uncommitted changes under plugins/token-metrics/scripts: commit them first")
    commit = _git(repo, "rev-parse", "HEAD")
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    committed = _git(repo, "show", "-s", "--format=%cI", "HEAD")
    for name in FILES:
        shutil.copyfile(source / name, VENDOR_DIR / name)
    rows = "\n".join(f"| `{n}` | {sha256(VENDOR_DIR / n)} |" for n in FILES)
    MANIFEST.write_text(
        f"""# Vendored from hermes-engine

Do not edit these files here. Change hermes-engine and re-run the sync:

    python services/insight/tools/sync_hermes.py /path/to/hermes-engine

- Source repo: `{SOURCE_REPO}` (folder `{SOURCE_SUBDIR}`)
- Branch: `{branch}`
- Commit: `{commit}`
- Commit date: {committed}
- Synced: {date.today().isoformat()}

The files are copied byte for byte. Tamper check, usable in CI without the other repo:

    python services/insight/tools/sync_hermes.py --check

| File | sha256 |
|---|---|
{rows}
"""
    )
    print(f"synced {len(FILES)} files from {repo} at {commit[:12]}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", nargs="?", type=Path, help="path to a hermes-engine checkout")
    ap.add_argument("--check", action="store_true", help="verify the vendored files against VENDORED.md and exit")
    args = ap.parse_args(argv)
    if args.check:
        problems = check()
        for p in problems:
            print(p, file=sys.stderr)
        if not problems:
            print("vendored hermes files match VENDORED.md")
        return 1 if problems else 0
    if args.repo is None:
        ap.error("give the hermes-engine checkout, or --check")
    sync(args.repo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
