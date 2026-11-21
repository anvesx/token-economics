from __future__ import annotations

import os
import subprocess
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from token_economics_contracts import CostSource, Detector
from token_economics_svc_insight import HermesDetectors, coverage_markdown
from token_economics_svc_insight._hermes_loader import load_hermes

RETIRED = {2, 3, 11, 14, 15, 19, 31}


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """HOME pointed at an empty directory, so any write to ~/.claude/metrics would show up."""
    h = tmp_path / "home"
    h.mkdir()
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.delenv("CC_METRICS_DIR", raising=False)
    return h


def run(transcripts: Path, tmp_path: Path, **kw: Any) -> HermesDetectors:
    return HermesDetectors(transcripts, tmp_path / "state", **kw)


def test_hermes_detectors_satisfies_the_detector_port(transcripts: Path, tmp_path: Path) -> None:
    # Given / When / Then
    assert isinstance(run(transcripts, tmp_path), Detector)
    assert run(transcripts, tmp_path).name == "hermes"


def test_coverage_has_one_line_per_row_1_to_50_with_retired_rows_marked(
    transcripts: Path, tmp_path: Path, home: Path
) -> None:
    # Given a small transcript tree
    # When the detectors run
    _, coverage = run(transcripts, tmp_path).run()
    # Then
    assert [c.row for c in coverage] == list(range(1, 51))
    assert {c.row for c in coverage if c.status == "retired"} == RETIRED
    assert all(c.name and c.note for c in coverage if c.status == "retired")
    assert next(c for c in coverage if c.row == 2).name == "Cache-write premium"
    assert all(c.status != "retired" and c.group for c in coverage if c.row not in RETIRED)


def test_cache_rewrite_after_a_long_gap_fires_row_4_with_decimal_cost(
    transcripts: Path, tmp_path: Path, home: Path
) -> None:
    # Given a session whose cache was fully rewritten after a 3-hour gap
    # When the detectors run
    findings, coverage = run(transcripts, tmp_path).run()
    # Then row 4 fired, priced from the transcript's own usage
    row4 = [f for f in findings if f.row == 4]
    assert len(row4) == 1
    assert row4[0].name == "Cache expired after a break"
    assert isinstance(row4[0].cost_estimate_usd, Decimal) and row4[0].cost_estimate_usd > 0
    assert row4[0].cost_source is CostSource.CLIENT
    assert row4[0].scope == "-work-demo/s-break"
    assert "break" in row4[0].detail
    line = next(c for c in coverage if c.row == 4)
    assert line.status == "fired" and line.fired == 1 and line.cost_estimate_usd == row4[0].cost_estimate_usd


def test_fired_counts_and_costs_match_the_findings(transcripts: Path, tmp_path: Path, home: Path) -> None:
    # Given / When
    findings, coverage = run(transcripts, tmp_path).run()
    # Then every coverage line agrees with the findings of its row
    assert len(findings) > 0
    for c in coverage:
        mine = [f for f in findings if f.row == c.row]
        assert c.fired == len(mine)
        assert isinstance(c.cost_estimate_usd, Decimal)
        assert c.cost_estimate_usd == sum((f.cost_estimate_usd for f in mine), Decimal(0))
        if c.status == "fired":
            assert c.fired > 0
        if c.status in ("not_fired", "unmeasurable", "retired"):
            assert c.fired == 0
    assert all(f.cost_estimate_usd.as_tuple().exponent == -6 for f in findings)


def test_details_and_notes_do_not_contain_prompt_text(
    transcripts: Path, tmp_path: Path, home: Path, synth: Any
) -> None:
    # Given transcripts whose prompts carry a sentinel
    # When the detectors run
    findings, coverage = run(transcripts, tmp_path).run()
    # Then the sentinel appears in no finding, coverage line or rendered table
    everything = "".join(f.model_dump_json() for f in findings) + "".join(c.model_dump_json() for c in coverage)
    assert synth.SENTINEL not in everything
    assert synth.SENTINEL not in coverage_markdown(coverage)


def test_nothing_is_written_outside_the_state_dir(transcripts: Path, tmp_path: Path, home: Path) -> None:
    # Given HOME is an empty directory
    before = sorted(transcripts.rglob("*"))
    # When the detectors run
    run(transcripts, tmp_path).run()
    # Then ~/.claude/metrics was neither created nor read into, and the transcripts are untouched
    assert list(home.rglob("*")) == []
    assert not (home / ".claude" / "metrics").exists()
    assert sorted(transcripts.rglob("*")) == before


def test_prompt_check_off_never_starts_a_subprocess(
    transcripts: Path, tmp_path: Path, home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given a claude binary that looks installed and subprocess calls that fail the test
    def boom(*a: Any, **k: Any) -> Any:
        raise AssertionError("a subprocess was started")

    monkeypatch.setattr("shutil.which", lambda name, *a, **k: "/usr/local/bin/claude")
    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(subprocess, "Popen", boom)
    monkeypatch.delenv("CC_METRICS_PROMPT_CHECK", raising=False)
    # When the detectors run with the default prompt_check=False
    _, coverage = run(transcripts, tmp_path).run()
    # Then nothing was started, and the process environment was not left changed
    assert len(coverage) == 50
    assert "CC_METRICS_PROMPT_CHECK" not in os.environ and "CC_METRICS_DIR" not in os.environ


def test_prompt_check_on_is_the_only_way_to_reach_the_model(
    tmp_path: Path, home: Path, monkeypatch: pytest.MonkeyPatch, synth: Any
) -> None:
    # Given a session with several typed prompts, so the check has something to label
    call, prompt, write_session = synth.call, synth.prompt, synth.write_session
    root = tmp_path / "projects"
    write_session(root, "-work-demo", "s-talk", [
        prompt("s-talk", 0, "first synthetic prompt"),
        call("s-talk", 1, 1, cache_read=0, cache_write=20_000),
        prompt("s-talk", 5, "second synthetic prompt"),
        call("s-talk", 6, 2, cache_read=20_000, cache_write=100),
    ])
    calls: list[list[str]] = []

    def fake(cmd: list[str], **k: Any) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 1, "", "")

    monkeypatch.setattr("shutil.which", lambda name, *a, **k: "/usr/local/bin/claude")
    monkeypatch.setattr(subprocess, "run", fake)
    # When prompt_check is requested
    HermesDetectors(root, tmp_path / "state_on", prompt_check=True).run()
    # Then the vendored check tried the model; and a later default run on the same state dir does not
    assert calls
    calls.clear()
    HermesDetectors(root, tmp_path / "state_on").run()
    assert calls == []


def test_empty_root_gives_fifty_lines_and_nothing_fired(tmp_path: Path, home: Path) -> None:
    # Given a transcripts root with no sessions
    empty = tmp_path / "empty"
    empty.mkdir()
    # When
    d = HermesDetectors(empty, tmp_path / "state")
    findings, coverage = d.run()
    # Then
    assert findings == []
    assert [c.row for c in coverage] == list(range(1, 51))
    assert all(c.fired == 0 for c in coverage)
    assert {c.row for c in coverage if c.status == "retired"} == RETIRED
    assert {c.status for c in coverage if c.row not in RETIRED} == {"not_fired"}
    assert d.last_total_usd is None


def test_a_missing_root_is_treated_as_empty(tmp_path: Path, home: Path) -> None:
    # Given a root that does not exist, When run, Then no findings and 50 lines
    findings, coverage = HermesDetectors(tmp_path / "nope", tmp_path / "state").run()
    assert findings == [] and len(coverage) == 50


def test_since_drops_sessions_before_the_window(transcripts: Path, tmp_path: Path, home: Path) -> None:
    # Given a window that starts after every transcript entry
    from datetime import UTC, datetime

    # When
    findings, coverage = run(transcripts, tmp_path).run(since=datetime(2026, 12, 1, tzinfo=UTC))
    # Then
    assert findings == [] and len(coverage) == 50


def test_coverage_markdown_lists_leaks_review_rows_and_retired_numbers(
    transcripts: Path, tmp_path: Path, home: Path
) -> None:
    # Given
    d = run(transcripts, tmp_path)
    _, coverage = d.run()
    # When
    md = coverage_markdown(coverage, d.last_total_usd)
    # Then
    assert "| # | name | group | status | fired | est. cost | note |" in md
    assert "## Spend to review" in md and "## Retired" in md
    assert md.index("Cache expired after a break") < md.index("## Spend to review")
    assert md.index("## Spend to review") < md.index("Old replies replayed")
    assert "- 2 Cache-write premium:" in md
    assert "Spend read: $" in md
    assert sum(1 for line in md.splitlines() if line.startswith("| ") and line[2].isdigit()) == 43


def test_vendored_modules_are_isolated_per_state_dir_and_leave_no_global_imports(tmp_path: Path, home: Path) -> None:
    # Given two loads with different state dirs
    import sys

    a, b = load_hermes(tmp_path / "a"), load_hermes(tmp_path / "b")
    # Then each is bound to its own dir, cached, and nothing is importable by its bare name afterwards
    assert Path(a.leak_config.METRICS_DIR) == (tmp_path / "a").resolve()
    assert Path(b.leak_config.METRICS_DIR) == (tmp_path / "b").resolve()
    assert load_hermes(tmp_path / "a") is a
    assert not {"leak_report", "leak_extra", "leak_categories", "leak_config", "prompt_check"} & set(sys.modules)
    assert not any(str(p).endswith("hermes") for p in sys.path)


def test_cache_ttl_must_be_5m_or_1h(tmp_path: Path) -> None:
    # Given / When / Then
    with pytest.raises(ValueError, match="cache_ttl"):
        HermesDetectors(tmp_path, tmp_path, cache_ttl="10m")
