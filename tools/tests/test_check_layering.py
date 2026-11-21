from __future__ import annotations

from pathlib import Path

import check_layering
from _layout import Layout

LAYOUT: Layout = {
    "contracts": {"kind": "contracts", "dir": "modules/contracts", "deps": []},
    "metering": {"kind": "module", "dir": "modules/metering", "deps": ["contracts"]},
    "redaction": {"kind": "module", "dir": "modules/redaction", "deps": ["contracts"]},
    "feat-a": {"kind": "feature", "dir": "features/a", "deps": ["contracts"]},
    "feat-b": {"kind": "feature", "dir": "features/b", "deps": ["contracts"]},
    "svc-ledger": {"kind": "service", "dir": "services/ledger", "deps": ["contracts", "metering"]},
    "app-cli": {"kind": "app", "dir": "apps/cli", "deps": ["contracts"]},
    "svc-later": {"kind": "service", "dir": "services/later", "deps": ["contracts"]},  # no folder
}


def write(root: Path, key: str, text: str, sub: str = "src", name: str = "mod.py") -> None:
    mod = "token_economics_" + key.replace("-", "_")
    folder = root / LAYOUT[key]["dir"] / sub
    if sub == "src":
        folder = folder / mod
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(text)


def build(root: Path) -> None:
    for key in LAYOUT:
        if key != "svc-later":
            write(root, key, "x = 1\n", name="__init__.py")


def test_allowed_imports_pass(tmp_path: Path) -> None:
    build(tmp_path)
    write(
        tmp_path,
        "svc-ledger",
        "import os\nimport pydantic\nimport token_economics_contracts\n"
        "from token_economics_metering import Meter\nfrom . import sibling\n",
    )
    assert check_layering.check(LAYOUT, tmp_path) == []


def test_feature_importing_feature_fails(tmp_path: Path) -> None:
    build(tmp_path)
    write(tmp_path, "feat-a", "from token_economics_feat_b import thing\n")
    problems = check_layering.check(LAYOUT, tmp_path)
    assert len(problems) == 1 and "sibling or higher kind" in problems[0]


def test_module_importing_service_fails(tmp_path: Path) -> None:
    build(tmp_path)
    write(tmp_path, "metering", "import token_economics_svc_ledger\n")
    problems = check_layering.check(LAYOUT, tmp_path)
    assert len(problems) == 1 and "higher kind" in problems[0]


def test_undeclared_lower_dep_fails(tmp_path: Path) -> None:
    build(tmp_path)
    write(tmp_path, "app-cli", "from token_economics_metering import Meter\n")
    problems = check_layering.check(LAYOUT, tmp_path)
    assert len(problems) == 1 and "not declared in deps" in problems[0]


def test_private_modules_fail(tmp_path: Path) -> None:
    build(tmp_path)
    write(
        tmp_path,
        "svc-ledger",
        "from token_economics_metering._internal import x\n"
        "import token_economics_metering._cache\nfrom token_economics_metering import _helper\n",
    )
    assert len(check_layering.check(LAYOUT, tmp_path)) == 3


def test_own_private_modules_are_fine(tmp_path: Path) -> None:
    build(tmp_path)
    write(tmp_path, "metering", "from token_economics_metering._internal import x\n")
    assert check_layering.check(LAYOUT, tmp_path) == []


def test_tests_may_import_own_package_and_contracts_testing(tmp_path: Path) -> None:
    build(tmp_path)
    layout = {**LAYOUT, "feat-a": {**LAYOUT["feat-a"], "deps": []}}
    code = "from token_economics_feat_a import x\nfrom token_economics_contracts.testing import suite\n"
    write(tmp_path, "feat-a", code, sub="tests", name="test_x.py")
    assert check_layering.check(layout, tmp_path) == []
    write(tmp_path, "feat-a", "import token_economics_contracts\n", sub="tests", name="test_y.py")
    problems = check_layering.check(layout, tmp_path)
    assert len(problems) == 1 and "test_y.py" in problems[0]


def test_tests_cannot_import_siblings(tmp_path: Path) -> None:
    build(tmp_path)
    write(tmp_path, "feat-a", "import token_economics_feat_b\n", sub="tests", name="test_x.py")
    assert len(check_layering.check(LAYOUT, tmp_path)) == 1


def test_missing_folders_are_ignored(tmp_path: Path) -> None:
    build(tmp_path)  # svc-later has no folder
    assert check_layering.check(LAYOUT, tmp_path) == []


def test_importlinter_config(tmp_path: Path) -> None:
    build(tmp_path)
    write(tmp_path, "metering", "x = 1\n", name="_internal.py")
    text = check_layering.importlinter_config(LAYOUT, tmp_path)
    assert "token_economics_svc_later" not in text
    assert "    token_economics_feat_a | token_economics_feat_b" in text
    assert "[importlinter:contract:deps-feat-a]" in text
    assert "token_economics_metering._internal" in text
    assert "[importlinter:contract:private-feat-a]" not in text
