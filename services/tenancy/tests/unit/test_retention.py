import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from token_economics_svc_tenancy import FileRetention

NOW = datetime(2026, 11, 23, tzinfo=UTC)


def line(days_ago: float | None, **fields: object) -> str:
    out: dict[str, object] = dict(fields)
    if days_ago is not None:
        out["ts"] = (NOW - timedelta(days=days_ago)).isoformat()
    return json.dumps(out) + "\n"


def test_no_config_does_nothing(tmp_path: Path):
    (tmp_path / "decisions.jsonl").write_text(line(500))
    assert FileRetention(tmp_path).apply(NOW) == {"dropped": 0, "files": {}}
    assert (tmp_path / "decisions.jsonl").read_text() == line(500)


def test_old_lines_go_by_tenant_days_and_odd_lines_stay(tmp_path: Path):
    # Given 90 days default, 30 for acme, and a log with every kind of line
    (tmp_path / "retention.json").write_text(json.dumps({"default_days": 90, "tenants": {"acme": 30}}))
    (tmp_path / "decisions.jsonl").write_text(
        line(100, n=1)  # default tenant, older than 90: dropped
        + line(60, n=2)  # default, within 90: kept
        + line(60, n=3, tenant="acme")  # acme, older than 30: dropped
        + line(10, n=4, tenant="acme")  # kept
        + line(60, n=5, tenant="other")  # unlisted tenant uses the default: kept
        + line(None, n=6)  # no ts: kept
        + "not json\n"  # kept
        + json.dumps({"n": 7, "ts": "garbage"})
        + "\n"  # unparsable ts: kept
    )
    (tmp_path / "shadow").mkdir()
    (tmp_path / "shadow" / "pairs.jsonl").write_text(line(200, n=8))
    # And files retention must never touch
    for name in ("ledger.sqlite", "tenancy.sqlite", "prices.sqlite"):
        (tmp_path / name).write_bytes(b"x" * 10)
    # When retention applies
    result = FileRetention(tmp_path).apply(NOW)
    # Then the expired lines are gone, the rest stay in order, and counts are returned
    kept = [
        json.loads(x).get("n") for x in (tmp_path / "decisions.jsonl").read_text().splitlines() if x.startswith("{")
    ]
    assert kept == [2, 4, 5, 6, 7]
    assert "not json" in (tmp_path / "decisions.jsonl").read_text()
    assert (tmp_path / "shadow" / "pairs.jsonl").read_text() == ""
    assert result["dropped"] == 3 and result["files"]["decisions.jsonl"] == {"kept": 6, "dropped": 2}
    assert all((tmp_path / n).read_bytes() == b"x" * 10 for n in ("ledger.sqlite", "tenancy.sqlite", "prices.sqlite"))
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".retention-")]


def test_bad_config_is_an_error_not_a_silent_skip(tmp_path: Path):
    (tmp_path / "retention.json").write_text(json.dumps({"default_days": 0}))
    with pytest.raises(ValueError):
        FileRetention(tmp_path).apply(NOW)
