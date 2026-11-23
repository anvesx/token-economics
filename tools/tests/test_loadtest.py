from __future__ import annotations

from pathlib import Path

import loadtest


def test_percentile_uses_nearest_rank() -> None:
    # Given 1..100
    values = [float(i) for i in range(1, 101)]
    # Then nearest-rank percentiles are the values themselves
    assert loadtest.percentile(values, 50) == 50
    assert loadtest.percentile(values, 95) == 95
    assert loadtest.percentile(values, 99) == 99
    assert loadtest.percentile([], 95) == 0.0


def test_verdict_fails_when_added_p95_is_over_the_budget() -> None:
    # Given a report with 7 ms added p95 TTFB and a consistent ledger
    report = {
        "gateway": {"errors": 0},
        "ledger": {"consistent": True},
        "added": {"ttfb_ms": {"p95": 7.0}},
    }
    # When the budget is 5 ms, then the run fails; at 10 ms it passes; with no budget it passes
    assert loadtest.verdict(report, 5.0)
    assert loadtest.verdict(report, 10.0) == []
    assert loadtest.verdict(report, None) == []


def test_small_load_writes_exactly_one_ledger_row_per_successful_request(tmp_path: Path) -> None:
    # Given the gateway and a fake provider on local ports
    # When a small load runs through both, non-streamed and then streamed
    for stream in (False, True):
        report = loadtest.run_load(
            requests=30,
            concurrency=5,
            stream=stream,
            delay_ms=1,
            chunks=2,
            chunk_delay_ms=0,
            state_dir=tmp_path / str(stream),
        )
        # Then nothing failed and the ledger has no lost or double rows
        assert report["gateway"]["errors"] == 0 and report["direct"]["errors"] == 0
        assert report["ledger"]["consistent"], report["ledger"]
        assert report["ledger"]["rows"] == report["gateway"]["ok"] + 30
        assert set(report["added"]["ttfb_ms"]) == {"p50", "p95", "p99"}
