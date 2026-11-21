from __future__ import annotations

import os
from pathlib import Path

import pytest
from token_economics_contracts import SERVICES, load
from token_economics_svc_insight import HermesDetectors, baseline, open_detectors


def test_detectors_and_baseline_resolve_under_the_services_group() -> None:
    # Given the installed package, When resolved through contracts' registry, Then they are the package's own objects
    assert load(SERVICES, "detectors") is open_detectors
    assert load(SERVICES, "baseline") is baseline


def test_open_detectors_builds_a_hermes_detector_with_prompt_check_off(tmp_path: Path) -> None:
    # Given plain string arguments, as a config file would hold them
    d = load(SERVICES, "detectors")(str(tmp_path / "t"), str(tmp_path / "s"))
    # Then
    assert isinstance(d, HermesDetectors) and d.prompt_check is False
    assert load(SERVICES, "detectors")(str(tmp_path), str(tmp_path), prompt_check=True).prompt_check is True


@pytest.mark.skipif(
    os.environ.get("TOKEN_ECONOMICS_REAL_TRANSCRIPTS") != "1", reason="set TOKEN_ECONOMICS_REAL_TRANSCRIPTS=1"
)
def test_real_transcripts_smoke(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Given the developer's own transcripts and a scratch state dir
    d = HermesDetectors(Path.home() / ".claude" / "projects", tmp_path / "state")
    # When
    findings, coverage = d.run()
    # Then 50 lines; the summary is printed with -s
    assert [c.row for c in coverage] == list(range(1, 51))
    counts = {s: sum(1 for c in coverage if c.status == s) for s in ("fired", "not_fired", "unmeasurable", "retired")}
    top = sorted((c for c in coverage if c.status == "fired"), key=lambda c: -c.cost_estimate_usd)[:5]
    with capsys.disabled():
        print(f"\nSMOKE counts={counts} findings={len(findings)} total_usd={d.last_total_usd}")
        for c in top:
            print(f"SMOKE row {c.row} {c.name}: fired={c.fired} ${c.cost_estimate_usd:,.2f}")
