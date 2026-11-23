import json
from datetime import UTC, datetime, timedelta
from importlib.metadata import entry_points
from pathlib import Path

from token_economics_contracts.types import (
    Buckets,
    CostSource,
    FeatureEnv,
    Identity,
    KeyInfo,
    LedgerRow,
    RequestContext,
)
from token_economics_feat_cache_hit_monitor import CacheHitMonitor, create

T0 = datetime(2026, 1, 1, tzinfo=UTC)
M = "claude-test-1"


def ctx(caller: str = "dev") -> RequestContext:
    return RequestContext(request_id="r", ts=T0, key=KeyInfo(tenant="t", caller=caller), identity=Identity())


def row(at: float, read=0, w5=0, w1h=0, fresh=0, model=M, session="s1", caller="dev") -> LedgerRow:
    return LedgerRow(
        provider="anthropic",
        response_id=f"resp-{at}-{session}",
        ts=T0 + timedelta(seconds=at),
        caller=caller,
        session_id=session,
        model=model,
        buckets=Buckets(fresh_input=fresh, cache_read=read, cache_write_5m=w5, cache_write_1h=w1h, output=10),
        cost_estimate_usd=None,
        cost_source=CostSource.GATEWAY,
        price_row_id="",
    )


def monitor(tmp_path: Path, **config) -> CacheHitMonitor:
    return create(FeatureEnv(state_dir=tmp_path, config=config))  # type: ignore[return-value]


def misses(tmp_path: Path) -> list[dict]:
    p = tmp_path / "cache_misses.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


def test_before_never_decides(tmp_path):
    # Given a monitor / When a request arrives / Then it passes untouched
    assert monitor(tmp_path).before(ctx()) is None


def test_hit_rate_is_read_over_read_write_and_fresh_per_caller_and_model(tmp_path):
    # Given two callers on one model / When calls are recorded / Then each has its own rate
    m = monitor(tmp_path)
    m.after(ctx(), row(0, read=800, w5=100, w1h=50, fresh=50), 200)
    m.after(ctx("cron"), row(0, read=0, w5=900, fresh=100, caller="cron", session="c"), 200)
    snap = m.snapshot()["callers"]
    assert snap["dev"][M]["hit_rate"] == 0.8 and snap["dev"][M]["write"] == 150
    assert snap["cron"][M]["hit_rate"] == 0.0 and snap["cron"][M]["calls"] == 1


def test_a_missing_row_is_ignored(tmp_path):
    # Given a failed call with no ledger row / When after runs / Then nothing is recorded
    m = monitor(tmp_path)
    m.after(ctx(), None, 500)
    assert m.snapshot()["callers"] == {}


def test_the_first_call_in_a_session_is_never_a_miss(tmp_path):
    # Given a big cold first call / When recorded / Then no miss event
    monitor(tmp_path).after(ctx(), row(0, w5=50_000), 200)
    assert misses(tmp_path) == []


def test_a_large_reprocess_after_a_long_gap_is_a_ttl_miss(tmp_path):
    # Given a 5-minute write then a call 10 minutes later that rewrites 50k tokens
    m = monitor(tmp_path)
    m.after(ctx(), row(0, w5=50_000), 200)
    m.after(ctx(), row(600, w5=50_000), 200)
    (ev,) = misses(tmp_path)
    assert (ev["reason"], ev["reprocessed"], ev["prompt_tokens"], ev["gap_s"]) == ("ttl_expired", 50_000, 50_000, 600.0)
    assert ev["caller"] == "dev" and ev["session_id"] == "s1"


def test_a_one_hour_write_keeps_the_ttl_open_for_an_hour(tmp_path):
    # Given a 1h write / When the next miss comes after 20 minutes / Then it is a prefix change, not expiry
    m = monitor(tmp_path)
    m.after(ctx(), row(0, w1h=50_000), 200)
    m.after(ctx(), row(1200, w1h=50_000), 200)
    assert misses(tmp_path)[0]["reason"] == "prefix_changed"


def test_a_prompt_that_changed_within_the_ttl_is_a_prefix_miss(tmp_path):
    m = monitor(tmp_path)
    m.after(ctx(), row(0, w5=50_000), 200)
    m.after(ctx(), row(30, read=10_000, w5=40_000), 200)
    assert misses(tmp_path)[0]["reason"] == "prefix_changed"


def test_a_model_switch_is_reported_as_such(tmp_path):
    m = monitor(tmp_path)
    m.after(ctx(), row(0, w5=50_000), 200)
    m.after(ctx(), row(30, w5=50_000, model="claude-test-2"), 200)
    assert misses(tmp_path)[0]["reason"] == "model_changed"


def test_small_or_proportionally_tiny_reprocessing_is_not_a_miss(tmp_path):
    # Given 1,999 tokens reprocessed, and 5,000 of 200,000 (2.5%) / Then neither counts
    m = monitor(tmp_path)
    m.after(ctx(), row(0, read=1000), 200)
    m.after(ctx(), row(10, read=3000, fresh=1999), 200)
    m.after(ctx(), row(20, read=195_000, fresh=5000), 200)
    assert misses(tmp_path) == []


def test_a_growing_conversation_that_writes_its_new_turn_is_not_a_miss(tmp_path):
    # Given a 50k prompt cached on turn 1
    m = monitor(tmp_path)
    m.after(ctx(), row(0, w5=50_000), 200)
    # When turn 2 reads all of it back and writes a 20k tool result that is new
    m.after(ctx(), row(20, read=50_000, w5=20_000), 200)
    # Then nothing was reprocessed: the write is growth, not a miss
    assert misses(tmp_path) == []


def test_miss_counts_reach_the_snapshot_file(tmp_path):
    # Given a miss / When the snapshot is flushed / Then the file has per caller and model numbers and no text
    m = monitor(tmp_path)
    m.after(ctx(), row(0, w5=50_000), 200)
    m.after(ctx(), row(600, w5=50_000), 200)
    m.flush()
    data = json.loads((tmp_path / "cache_monitor.json").read_text())
    assert data["callers"]["dev"][M]["misses"] == 1
    assert not list(tmp_path.glob("*.tmp"))


def test_snapshot_writes_are_throttled(tmp_path):
    # Given a fake clock / When calls land inside 30 s / Then the file is not rewritten
    now = [0.0]
    m = CacheHitMonitor(tmp_path, clock=lambda: now[0])
    m.after(ctx(), row(0, read=10), 200)
    first = (tmp_path / "cache_monitor.json").read_text()
    m.after(ctx(), row(1, read=10, session="b"), 200)
    assert (tmp_path / "cache_monitor.json").read_text() == first
    now[0] = 31.0
    m.after(ctx(), row(2, read=10, session="c"), 200)
    assert json.loads((tmp_path / "cache_monitor.json").read_text())["callers"]["dev"][M]["calls"] == 3


def alerts(tmp_path: Path) -> list[dict]:
    p = tmp_path / "alerts.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


def test_no_alert_unless_configured(tmp_path):
    m = monitor(tmp_path)
    for i in range(100):
        m.after(ctx(), row(i, fresh=1000, session=f"s{i}"), 200)
    assert alerts(tmp_path) == []


def test_a_hit_rate_drop_alerts_once_per_caller_per_day(tmp_path):
    # Given alert_below 0.5 and min_calls 5 / When a caller has 0% hits over 8 calls
    m = monitor(tmp_path, alert_below=0.5, min_calls=5)
    for i in range(8):
        m.after(ctx(), row(i, fresh=1000, session=f"s{i}"), 200)
    # Then one alert; a second day gives one more
    assert len(alerts(tmp_path)) == 1 and alerts(tmp_path)[0]["scope"] == "caller:dev"
    m.after(ctx(), row(86_400 + 1, fresh=1000, session="x"), 200)
    assert len(alerts(tmp_path)) == 2


def test_a_healthy_caller_does_not_alert_and_min_calls_is_respected(tmp_path):
    m = monitor(tmp_path, alert_below=0.5, min_calls=5)
    for i in range(10):
        m.after(ctx(), row(i, read=900, fresh=100, session=f"s{i}"), 200)
    for i in range(4):
        m.after(ctx("new"), row(i, fresh=1000, session=f"n{i}", caller="new"), 200)
    assert alerts(tmp_path) == []


def test_session_memory_is_bounded(tmp_path):
    m = monitor(tmp_path, max_sessions=3)
    for i in range(10):
        m.after(ctx(), row(i, read=10, session=f"s{i}"), 200)
    assert len(m._sessions) == 3


def test_entry_point_is_registered():
    eps = entry_points(group="token_economics.features")
    assert eps["cache_hit_monitor"].load() is create
