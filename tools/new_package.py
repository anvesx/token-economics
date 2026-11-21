"""Scaffold one package from plan/model/layout.json: `python tools/new_package.py svc-ledger "what it does"`.

Creates the folder shape every package has (13-monorepo-layout.md): own pyproject, README, CHANGELOG, src/, tests/.
Existing files are never overwritten.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LAYOUT: dict[str, dict[str, Any]] = json.loads((ROOT / "plan/model/layout.json").read_text())


def names(key: str) -> tuple[str, str]:
    """(distribution name, import name) for a layout key."""
    dist = f"token-economics-{key}"
    return dist, dist.replace("-", "_")


def scaffold(key: str, summary: str) -> Path:
    spec = LAYOUT[key]
    dist, mod = names(key)
    root: Path = ROOT / spec["dir"]
    deps = [names(d)[0] for d in spec["deps"]]
    files = {
        "pyproject.toml": f'''[project]
name = "{dist}"
version = "0.1.0"
description = "{summary}"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [{", ".join(f'"{d}"' for d in deps)}]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{mod}"]

[tool.pytest.ini_options]
addopts = "--import-mode=importlib"
testpaths = ["tests"]
''',
        "README.md": f"# {dist}\n\n{summary}\n\nKind: {spec['kind']}. Phase: {spec['phase']}. "
        f"May import: {', '.join(deps) or 'nothing'}.\n\n"
        f"Run alone: `uv run --package {dist} pytest {spec['dir']}`\n",
        "CHANGELOG.md": f"# Changelog: {dist}\n\n## 0.1.0\n\n- First version (P0).\n",
        f"src/{mod}/__init__.py": f'"""{summary}"""\n\n__all__: list[str] = []\n',
        f"src/{mod}/py.typed": "",
        "tests/unit/.gitkeep": "",
    }
    for rel, text in files.items():
        path = root / rel
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    return root


if __name__ == "__main__":
    print(scaffold(sys.argv[1], sys.argv[2]))
