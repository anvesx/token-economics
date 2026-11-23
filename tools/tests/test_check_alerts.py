from __future__ import annotations

import json
from pathlib import Path

import check_alerts


def entry(kind: str, owner: str = "UNASSIGNED", runbook: str | None = None) -> dict[str, str]:
    return {
        "kind": kind,
        "source": "somewhere",
        "severity": "page",
        "owner": owner,
        "runbook": runbook or f"docs/runbooks/{kind}.md",
    }


def build(root: Path, entries: list[dict[str, str]], source: str = "", runbooks: tuple[str, ...] = ()) -> None:
    (root / "ops").mkdir()
    (root / "ops/alerts.json").write_text(json.dumps(entries))
    (root / "docs/runbooks").mkdir(parents=True)
    for name in runbooks:
        (root / f"docs/runbooks/{name}.md").write_text("# x\n")
    pkg = root / "features/thing/src/pkg"
    pkg.mkdir(parents=True)
    (pkg / "mod.py").write_text(source)


def test_complete_alerts_pass(tmp_path: Path) -> None:
    # Given an entry with a runbook, and a refusal and an alert kind in source that both have entries
    src = 'Decision(code="budget_exhausted")\nALERTS = "alerts.jsonl"\nrec = {"kind": "cache_hit_rate"}\n'
    build(
        tmp_path,
        [entry("budget_exhausted"), entry("cache_hit_rate")],
        src,
        ("budget_exhausted", "cache_hit_rate"),
    )
    # Then nothing is reported
    assert check_alerts.check(tmp_path) == []


def test_entry_without_a_runbook_file_fails(tmp_path: Path) -> None:
    # Given an entry whose runbook file is missing
    build(tmp_path, [entry("gateway_down")])
    # Then it is named
    (problem,) = check_alerts.check(tmp_path)
    assert "gateway_down" in problem and "does not exist" in problem


def test_decision_code_in_source_without_an_entry_fails(tmp_path: Path) -> None:
    # Given a refusal code in a feature that no entry covers
    build(tmp_path, [], 'return Decision(allow=False, code="brand_new_refusal")\n')
    # Then the code and its file are named
    (problem,) = check_alerts.check(tmp_path)
    assert "brand_new_refusal" in problem and "features/thing/src/pkg/mod.py" in problem


def test_alert_kind_without_an_entry_fails_only_in_files_that_write_alerts(tmp_path: Path) -> None:
    # Given a "kind" literal in a file that writes alerts, and another in a file that does not
    build(tmp_path, [], 'path = "alerts.jsonl"\nrec = {"kind": "new_alert"}\n')
    other = tmp_path / "services/svc/src/pkg"
    other.mkdir(parents=True)
    (other / "job.py").write_text('job = {"kind": "label"}\n')
    # Then only the alert one is reported
    (problem,) = check_alerts.check(tmp_path)
    assert "new_alert" in problem


def test_vendored_and_test_code_are_not_scanned(tmp_path: Path) -> None:
    # Given literals under hermes/ and tests/
    build(tmp_path, [])
    for sub in ("services/insight/src/pkg/hermes", "features/thing/src/pkg/tests"):
        d = tmp_path / sub
        d.mkdir(parents=True)
        (d / "x.py").write_text('alerts = 1\nDecision(code="ignored_code")\n')
    # Then nothing is reported
    assert check_alerts.check(tmp_path) == []


def test_unassigned_owner_fails_only_when_owners_are_required(tmp_path: Path) -> None:
    # Given one unassigned and one named owner
    build(tmp_path, [entry("a_alert"), entry("b_alert", owner="Asha")], runbooks=("a_alert", "b_alert"))
    # When owners are not required, then it passes; when required, the unassigned one is named
    assert check_alerts.check(tmp_path) == []
    (problem,) = check_alerts.check(tmp_path, require_owners=True)
    assert "a_alert" in problem and "UNASSIGNED" in problem


def test_missing_field_and_bad_severity_fail(tmp_path: Path) -> None:
    # Given an entry with no source and an unknown severity
    bad = entry("x_alert")
    del bad["source"]
    bad["severity"] = "loud"
    build(tmp_path, [bad], runbooks=("x_alert",))
    # Then both are named
    problems = check_alerts.check(tmp_path)
    assert any("missing source" in p for p in problems) and any("severity" in p for p in problems)


def test_the_real_repository_alerts_file_is_consistent() -> None:
    # Given the checked-in ops/alerts.json, when it is checked against the real source, then it passes
    assert check_alerts.check() == []
