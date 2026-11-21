from __future__ import annotations

import pytest
from check_pr_title import check, scopes

ALLOWED = {"ledger", "tools"}


@pytest.mark.parametrize("title", ["feat(ledger): append-only rows", "fix(tools)!: break it", "gate(ledger): P0 exit"])
def test_good_titles(title: str) -> None:
    assert check(title, ALLOWED) is None


BAD = ["add ledger", "feat: no scope", "feature(ledger): x", "feat(Ledger): x", "feat(nowhere): x", "feat(ledger):x"]


@pytest.mark.parametrize("title", BAD)
def test_bad_titles(title: str) -> None:
    assert check(title, ALLOWED) is not None


def test_scopes_come_from_the_layout() -> None:
    assert {"ledger", "upstream", "tools"} <= scopes()
