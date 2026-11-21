from __future__ import annotations

import shutil
from pathlib import Path

import check_extractable
import pytest
from _layout import Layout

LAYOUT: Layout = {
    "contracts": {"kind": "contracts", "dir": "modules/contracts", "deps": []},
    "feat-a": {"kind": "feature", "dir": "features/a", "deps": ["contracts"]},
    "feat-b": {"kind": "feature", "dir": "features/b", "deps": []},  # imports contracts without declaring it
    "feat-c": {"kind": "feature", "dir": "features/c", "deps": ["svc-later"]},
    "svc-later": {"kind": "service", "dir": "services/later", "deps": []},  # no folder
}

pytestmark = pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not installed")


def make(root: Path, key: str, body: str, test: str) -> None:
    name = "token_economics_" + key.replace("-", "_")
    deps = ", ".join(f'"token-economics-{d}"' for d in LAYOUT[key]["deps"] if d != "svc-later")
    pkg = root / LAYOUT[key]["dir"]
    (pkg / "src" / name).mkdir(parents=True)
    (pkg / "tests").mkdir()
    (pkg / "pyproject.toml").write_text(
        f'[project]\nname = "token-economics-{key}"\nversion = "0.0.0"\nrequires-python = ">=3.12"\n'
        f"dependencies = [{deps}]\n"
        '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n'
        f'[tool.hatch.build.targets.wheel]\npackages = ["src/{name}"]\n'
    )
    (pkg / "src" / name / "__init__.py").write_text(body)
    (pkg / "tests" / "test_it.py").write_text(test)


def build(root: Path) -> None:
    make(root, "contracts", "VALUE = 1\n", "def test_ok() -> None:\n    assert True\n")
    make(
        root,
        "feat-a",
        "from token_economics_contracts import VALUE\n",
        "import token_economics_feat_a\n\ndef test_ok() -> None:\n    assert token_economics_feat_a.VALUE == 1\n",
    )
    make(root, "feat-b", "from token_economics_contracts import VALUE\n", "def test_ok() -> None:\n    assert True\n")
    make(root, "feat-c", "x = 1\n", "def test_ok() -> None:\n    assert True\n")
    shutil.rmtree(root / "services", ignore_errors=True)


def test_declared_deps_pass_and_undeclared_fail(tmp_path: Path) -> None:
    build(tmp_path)
    assert check_extractable.check_package(LAYOUT, "feat-a", tmp_path).ok
    undeclared = check_extractable.check_package(LAYOUT, "feat-b", tmp_path)
    assert not undeclared.ok and "import" in undeclared.detail


def test_failing_tests_fail(tmp_path: Path) -> None:
    build(tmp_path)
    (tmp_path / "features/a/tests/test_it.py").write_text("def test_bad() -> None:\n    assert False\n")
    result = check_extractable.check_package(LAYOUT, "feat-a", tmp_path)
    assert not result.ok and "tests failed" in result.detail


def test_declared_dep_without_folder_fails(tmp_path: Path) -> None:
    build(tmp_path)
    result = check_extractable.check_package(LAYOUT, "feat-c", tmp_path)
    assert not result.ok and "svc-later" in result.detail
