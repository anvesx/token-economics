"""Back up and restore a Token Economics state dir.

    uv run python tools/backup.py backup <state_dir> <out_dir>
    uv run python tools/backup.py verify <backup_dir>
    uv run python tools/backup.py restore <backup_dir> <state_dir>

`backup` is safe while the gateway runs: each `*.sqlite` is copied with the sqlite3 online backup API (a consistent
snapshot, taken page by page without blocking writers for long), so the `-wal` and `-shm` files are not needed.
JSON and JSONL files and `shadow/` are plain copies (an append in flight can leave a half line at the end of a
JSONL file; readers already skip those). `manifest.json` lists every file with its sha256 and, for SQLite, the row
count of each table. `restore` only writes into an empty or missing directory and verifies the sha256s before and
after. Exits 1 on any problem, one line each.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MANIFEST = "manifest.json"
SUFFIXES = {".json", ".jsonl"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def table_counts(db: Path) -> dict[str, int]:
    """Row count per table of a SQLite file, opened read-only."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        names = [
            r[0]
            for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
        ]
        return {n: int(con.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0]) for n in sorted(names)}
    finally:
        con.close()


def _sources(state: Path) -> list[Path]:
    """Files to back up, relative to the state dir: SQLite and JSON(L) files, and everything under shadow/."""
    found: list[Path] = []
    for p in sorted(state.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(state)
        if p.suffix == ".sqlite" or rel.parts[0] == "shadow" or (len(rel.parts) == 1 and p.suffix in SUFFIXES):
            found.append(rel)
    return found


def _snapshot(src: Path, dst: Path) -> None:
    """Consistent copy of a live SQLite database with the online backup API."""
    source = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    target = sqlite3.connect(dst)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


def backup(state: Path, out: Path) -> dict[str, Any]:
    """Write the backup and return its manifest. `out` must be empty or missing."""
    if not state.is_dir():
        raise ValueError(f"{state} is not a directory")
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"{out} is not empty: backups are never merged")
    out.mkdir(parents=True, exist_ok=True)
    files: dict[str, Any] = {}
    for rel in _sources(state):
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if rel.suffix == ".sqlite":
            _snapshot(state / rel, dst)
        else:
            shutil.copy2(state / rel, dst)
        entry: dict[str, Any] = {"sha256": sha256(dst), "bytes": dst.stat().st_size}
        if rel.suffix == ".sqlite":
            entry["rows"] = table_counts(dst)
        files[rel.as_posix()] = entry
    manifest = {"created": datetime.now(UTC).isoformat(), "source": str(state), "files": files}
    (out / MANIFEST).write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def verify(backup_dir: Path) -> list[str]:
    """Problems found in a backup: missing manifest or files, hash or row count differences."""
    try:
        manifest = json.loads((backup_dir / MANIFEST).read_text())
    except (OSError, ValueError) as e:
        return [f"{MANIFEST}: cannot read ({type(e).__name__})"]
    problems = []
    for name, entry in sorted(manifest.get("files", {}).items()):
        path = backup_dir / name
        if not path.is_file():
            problems.append(f"{name}: missing")
        elif sha256(path) != entry["sha256"]:
            problems.append(f"{name}: sha256 does not match the manifest")
        elif "rows" in entry:
            try:
                counts = table_counts(path)
            except sqlite3.Error as e:
                problems.append(f"{name}: not a readable SQLite file ({e})")
                continue
            if counts != entry["rows"]:
                problems.append(f"{name}: row counts {counts} differ from the manifest {entry['rows']}")
    return problems


def restore(backup_dir: Path, state: Path) -> list[str]:
    """Copy a verified backup into an empty or missing state dir. Returns problems; nothing is written if any
    are found before copying."""
    problems = verify(backup_dir)
    if problems:
        return problems
    if state.exists() and (not state.is_dir() or any(state.iterdir())):
        return [f"{state} is not empty: restore never overwrites a state dir"]
    manifest = json.loads((backup_dir / MANIFEST).read_text())
    state.mkdir(parents=True, exist_ok=True)
    for name, entry in manifest["files"].items():
        dst = state / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_dir / name, dst)
        if sha256(dst) != entry["sha256"]:
            problems.append(f"{name}: sha256 differs after copy")
    return problems


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Back up and restore a Token Economics state dir")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backup", help="consistent copy of a state dir, safe while the gateway runs")
    b.add_argument("state_dir", type=Path)
    b.add_argument("out_dir", type=Path)
    v = sub.add_parser("verify", help="check a backup against its manifest")
    v.add_argument("backup_dir", type=Path)
    r = sub.add_parser("restore", help="restore a backup into an empty state dir")
    r.add_argument("backup_dir", type=Path)
    r.add_argument("state_dir", type=Path)
    a = p.parse_args(argv)
    problems: list[str] = []
    if a.cmd == "backup":
        try:
            manifest = backup(a.state_dir.expanduser(), a.out_dir.expanduser())
        except (ValueError, OSError, sqlite3.Error) as e:
            problems = [str(e)]
        else:
            for name, entry in manifest["files"].items():
                rows = f"  rows {entry['rows']}" if "rows" in entry else ""
                print(f"{name}  {entry['sha256'][:12]}{rows}")
            print(f"backed up {len(manifest['files'])} files to {a.out_dir}")
    elif a.cmd == "verify":
        problems = verify(a.backup_dir.expanduser())
        if not problems:
            print("backup ok")
    else:
        problems = restore(a.backup_dir.expanduser(), a.state_dir.expanduser())
        if not problems:
            print(f"restored into {a.state_dir}")
    for line in problems:
        print(line, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
