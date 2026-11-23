import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from token_economics_app_worker import main, tick

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)


class Rollback:
    def __init__(self, state: str) -> None:
        self.state = state

    def check(self, now: datetime | None = None) -> list[dict[str, Any]]:
        return [{"feature": "output_cap", "action": "killed"}]


class Retention:
    def __init__(self, state: str) -> None:
        self.state = state

    def apply(self, now: datetime | None = None) -> dict[str, Any]:
        return {"dropped": 3}


def registry(**services: Any) -> Callable[[str], Any]:
    def lookup(name: str) -> Any:
        if name not in services:
            raise LookupError(f"nothing registered as {name!r}")
        return services[name]

    return lookup


def test_a_tick_runs_rollback_and_retention_and_reports_both(tmp_path: Path) -> None:
    # Given both services are installed
    lookup = registry(rollback=Rollback, retention=Retention)
    # When one tick runs
    record = tick(tmp_path, lookup, NOW)
    # Then each job's result is in the record
    assert record["jobs"]["rollback"] == {"ok": True, "result": [{"feature": "output_cap", "action": "killed"}]}
    assert record["jobs"]["retention"] == {"ok": True, "result": {"dropped": 3}}


def test_a_failing_job_is_reported_and_does_not_stop_the_others(tmp_path: Path) -> None:
    # Given a rollback checker that raises
    class Broken(Rollback):
        def check(self, now: datetime | None = None) -> list[dict[str, Any]]:
            raise RuntimeError("ledger locked")

    # When a tick runs
    record = tick(tmp_path, registry(rollback=Broken, retention=Retention), NOW)
    # Then the failure is reported and retention still ran
    assert record["jobs"]["rollback"] == {"ok": False, "error": "RuntimeError: ledger locked"}
    assert record["jobs"]["retention"]["ok"] is True


def test_retention_is_optional_but_a_missing_rollback_is_an_error(tmp_path: Path) -> None:
    # Given only retention is missing, then it is skipped
    record = tick(tmp_path, registry(rollback=Rollback), NOW)
    assert record["jobs"]["retention"] == {"ok": True, "skipped": "not installed"}
    # And given rollback is missing, it is reported as failed
    record = tick(tmp_path, registry(), NOW)
    assert record["jobs"]["rollback"]["ok"] is False


def test_once_logs_one_json_line_and_exits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given a failing job, so the exit code shows it
    monkeypatch.setattr("token_economics_app_worker.worker._lookup", registry())
    # When the worker runs once
    code = main(["--once", "--state-dir", str(tmp_path)])
    # Then one JSON line is on stdout and the exit code is 1
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["jobs"]["rollback"]["ok"] is False and code == 1
