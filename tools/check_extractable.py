"""Extractability check: a package works with only its declared dependencies (plan/13-monorepo-layout.md, rule 4).

    uv run python tools/check_extractable.py                  # every existing package
    uv run python tools/check_extractable.py svc-ledger app-cli

For each package: a fresh virtual environment in a temp dir (`uv venv`), `uv pip install` of ONLY that package and
its declared workspace deps (transitively, from layout.json, as local paths) plus pytest, hypothesis and
pytest-asyncio, then import the package and run its tests there with `--import-mode=importlib`. Prints a summary
table and one line per failure. Exits 1 if any package fails. `uv` caches wheels, so repeat runs are quick.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from _layout import ROOT, Layout, dependency_closure, existing, load_layout, module_name

TEST_TOOLS = ["pytest", "hypothesis", "pytest-asyncio"]


@dataclass
class Result:
    key: str
    ok: bool
    seconds: float
    detail: str


def _run(cmd: list[str], cwd: Path, env: dict[str, str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, check=False)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def _last_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    summary = [line for line in lines if " passed" in line or " failed" in line or " error" in line]
    return (summary or lines or [""])[-1]


def check_package(layout: Layout, key: str, root: Path = ROOT, python: str = "3.12") -> Result:
    start = time.monotonic()
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("VIRTUAL_ENV", None)
    members = sorted(dependency_closure(layout, [key]))
    missing = [m for m in members if not (root / layout[m]["dir"]).is_dir()]
    if missing:
        detail = f"declared dependency has no folder yet: {', '.join(missing)}"
        return Result(key, False, time.monotonic() - start, detail)
    pkg_dir = root / layout[key]["dir"]
    with tempfile.TemporaryDirectory(prefix=f"extractable-{key}-") as tmp:
        tmp_path = Path(tmp)
        venv = tmp_path / "venv"
        py = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        steps: list[tuple[str, list[str]]] = [
            ("create venv", ["uv", "venv", "--quiet", "--python", python, str(venv)]),
            (
                "install",
                ["uv", "pip", "install", "--quiet", "--python", str(py)]
                + [str(root / layout[m]["dir"]) for m in members]
                + TEST_TOOLS,
            ),
            ("import", [str(py), "-c", f"import {module_name(key)}"]),
        ]
        for name, cmd in steps:
            code, out = _run(cmd, tmp_path, env)
            if code != 0:
                return Result(key, False, time.monotonic() - start, f"{name} failed: {_last_line(out)}")
        tests = pkg_dir / "tests"
        if not tests.is_dir():
            return Result(key, False, time.monotonic() - start, "no tests/ folder")
        cmd = [
            str(py),
            "-m",
            "pytest",
            str(tests),
            "--import-mode=importlib",
            "-q",
            "-p",
            "no:cacheprovider",
            "-o",
            "asyncio_mode=auto",
        ]
        code, out = _run(cmd, tmp_path, env)
        if code == 5:
            return Result(key, False, time.monotonic() - start, "no tests collected")
        if code != 0:
            return Result(key, False, time.monotonic() - start, f"tests failed: {_last_line(out)}")
        return Result(key, True, time.monotonic() - start, _last_line(out))


def main(argv: list[str]) -> int:
    layout = load_layout()
    present = existing(layout)
    keys = argv or present
    unknown = [k for k in keys if k not in present]
    if unknown:
        print(f"unknown or missing package: {', '.join(unknown)}", file=sys.stderr)
        return 2
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda k: check_package(layout, k), keys))
    width = max(len(r.key) for r in results) if results else 0
    print(f"{'package'.ljust(width)}  status  seconds  detail")
    for r in results:
        print(f"{r.key.ljust(width)}  {'ok' if r.ok else 'FAIL':<6}  {r.seconds:7.1f}  {r.detail}")
    failed = [r for r in results if not r.ok]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
