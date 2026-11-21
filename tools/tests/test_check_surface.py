from __future__ import annotations

from pathlib import Path

import check_surface
from _layout import Layout

LAYOUT: Layout = {
    "contracts": {"kind": "contracts", "dir": "modules/contracts", "deps": []},
    "later": {"kind": "module", "dir": "modules/later", "deps": []},
}


def init(root: Path, text: str) -> None:
    folder = root / "modules/contracts/src/token_economics_contracts"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "__init__.py").write_text(text)
    (folder / "errors.py").write_text("class E(Exception): ...\n")


def run(tmp_path: Path, text: str) -> list[str]:
    init(tmp_path, text)
    return check_surface.check(LAYOUT, tmp_path)


def test_complete_surface_passes(tmp_path: Path) -> None:
    text = '''"""Doc."""
from __future__ import annotations

from .errors import E
import json as _json
from typing import Any as Any

VERSION = "1"
_private = 1


def make() -> None: ...


class Thing: ...


__all__ = ["E", "Any", "VERSION", "make", "Thing", "errors"]
'''
    assert run(tmp_path, text) == []


def test_missing_all(tmp_path: Path) -> None:
    assert "no __all__" in run(tmp_path, "x = 1\n")[0]


def test_unlisted_public_name(tmp_path: Path) -> None:
    problems = run(tmp_path, "from .errors import E\ndef f() -> None: ...\n__all__ = ['E']\n")
    assert problems == ["modules/contracts/src/token_economics_contracts/__init__.py: public name f is not in __all__"]


def test_all_names_that_do_not_exist(tmp_path: Path) -> None:
    problems = run(tmp_path, "from .errors import E\n__all__ = ['E', 'Ghost']\n")
    assert len(problems) == 1 and "Ghost" in problems[0]


def test_conditional_binding_and_augmented_all(tmp_path: Path) -> None:
    text = "try:\n    from .errors import E\nexcept ImportError:\n    E = None\n__all__ = []\n__all__ += ['E']\n"
    assert run(tmp_path, text) == []


def test_non_literal_all_and_star_import(tmp_path: Path) -> None:
    assert "literal" in run(tmp_path, "from .errors import E\n__all__ = list(['E'])\n")[0]
    assert "star import" in run(tmp_path, "from .errors import *\n__all__ = []\n")[0]


def test_missing_init(tmp_path: Path) -> None:
    (tmp_path / "modules/contracts/src/token_economics_contracts").mkdir(parents=True)
    assert "missing" in check_surface.check(LAYOUT, tmp_path)[0]
