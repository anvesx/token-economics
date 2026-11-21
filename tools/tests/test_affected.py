from __future__ import annotations

from _layout import Layout, dependency_closure
from affected import affected

LAYOUT: Layout = {
    "contracts": {"kind": "contracts", "dir": "modules/contracts", "deps": []},
    "metering": {"kind": "module", "dir": "modules/metering", "deps": ["contracts"]},
    "feat-a": {"kind": "feature", "dir": "features/a", "deps": ["contracts"]},
    "svc-ledger": {"kind": "service", "dir": "services/ledger", "deps": ["contracts", "metering"]},
    "app-gw": {"kind": "app", "dir": "apps/gw", "deps": ["svc-ledger"]},
}


def test_leaf_change_touches_only_itself() -> None:
    assert affected(LAYOUT, ["features/a/src/x.py"]) == ["feat-a"]


def test_dependents_are_transitive() -> None:
    assert affected(LAYOUT, ["modules/metering/README.md"]) == ["app-gw", "metering", "svc-ledger"]


def test_contracts_change_touches_everything() -> None:
    assert affected(LAYOUT, ["modules/contracts/src/t.py"]) == sorted(LAYOUT)


def test_global_files_mean_all_packages() -> None:
    for path in ("tools/check_layering.py", ".github/workflows/ci.yml", "pyproject.toml", "uv.lock"):
        assert affected(LAYOUT, [path]) == sorted(LAYOUT)


def test_unrelated_files_and_prefix_lookalikes() -> None:
    assert affected(LAYOUT, ["docs/x.md", "features/abc/x.py", "modules/metering-extra/x.py"]) == []


def test_only_existing_packages_are_returned() -> None:
    assert affected(LAYOUT, ["modules/metering/x.py"], present=["metering", "feat-a"]) == ["metering"]


def test_dependency_closure() -> None:
    assert dependency_closure(LAYOUT, ["app-gw"]) == {"app-gw", "svc-ledger", "metering", "contracts"}
