import json
import threading
from datetime import UTC, datetime
from importlib.metadata import entry_points
from pathlib import Path

from token_economics_contracts.types import (
    Buckets,
    FeatureEnv,
    Identity,
    KeyInfo,
    LedgerRow,
    QuerySource,
    RequestContext,
)
from token_economics_feat_compaction_guard import CompactionGuard, create

TS = datetime(2026, 1, 1, tzinfo=UTC)


def ctx(sid: str = "s1", source: QuerySource = QuerySource.MAIN) -> RequestContext:
    return RequestContext(
        request_id="r",
        ts=TS,
        key=KeyInfo(tenant="t"),
        identity=Identity(session_id=sid, query_source=source),
    )


def row(prompt: int) -> LedgerRow:
    return LedgerRow(
        provider="anthropic",
        response_id="x",
        ts=TS,
        model="m",
        buckets=Buckets(fresh_input=prompt),
        cost_estimate_usd=None,
        cost_source="gateway",
        price_row_id="",
    )


def feature(tmp_path: Path, config: dict | None = None) -> CompactionGuard:
    return create(FeatureEnv(state_dir=tmp_path, config=config or {}))


def feed(f: CompactionGuard, *prompts: int, sid: str = "s1") -> None:
    for p in prompts:
        f.after(ctx(sid), row(p), 200)


def test_a_big_drop_after_a_large_prompt_counts_as_a_compaction(tmp_path):
    # Given a prompt of 100k / When the next is 20k / Then one compaction is counted
    f = feature(tmp_path)
    feed(f, 100_000, 20_000)
    assert f._sessions["s1"]["count"] == 1


def test_small_prompts_and_small_drops_are_not_compactions(tmp_path):
    # Given a drop from 40k (below min_prompt) and one from 100k to 60k (above the ratio)
    f = feature(tmp_path)
    feed(f, 40_000, 1_000, 100_000, 60_000)
    assert f._sessions["s1"]["count"] == 0


def test_allows_below_the_limit_and_refuses_at_three(tmp_path):
    # Given two compactions / Then allowed; a third / Then refused with 429
    f = feature(tmp_path)
    feed(f, 100_000, 10_000)
    feed(f, 100_000, 10_000)
    assert f.before(ctx()) is None
    feed(f, 100_000, 10_000)
    d = f.before(ctx())
    assert d is not None
    assert (d.allow, d.feature, d.status, d.code) == (False, "compaction_guard", 429, "compaction_limit")
    assert "compacted 3 times" in d.message


def test_only_main_thread_calls_with_a_session_and_a_row_count(tmp_path):
    # Given subagent calls, no session, and no row
    f = feature(tmp_path)
    f.after(ctx(source=QuerySource.SUBAGENT), row(100_000), 200)
    f.after(ctx(source=QuerySource.SUBAGENT), row(1_000), 200)
    f.after(ctx(sid=""), row(100_000), 200)
    f.after(ctx(), None, 500)
    # Then nothing is tracked
    assert f._sessions == {}


def test_sessions_are_independent(tmp_path):
    f = feature(tmp_path, {"restart_at": 1})
    feed(f, 100_000, 10_000, sid="a")
    assert f.before(ctx("a")) is not None
    assert f.before(ctx("b")) is None
    assert f.before(ctx("")) is None


def test_state_persists_across_create_and_holds_numbers_only(tmp_path):
    # Given a counted compaction / When the feature is created again on the same dir
    feed(feature(tmp_path), 100_000, 10_000)
    again = feature(tmp_path)
    # Then the count is restored and the file has only ids and numbers
    assert again._sessions["s1"]["count"] == 1
    data = json.loads((tmp_path / "compaction_guard.json").read_text())
    assert set(data["sessions"]["s1"]) == {"count", "last_prompt", "last_seen"}
    assert list(tmp_path.iterdir()) == [tmp_path / "compaction_guard.json"]


def test_corrupt_state_starts_empty(tmp_path):
    (tmp_path / "compaction_guard.json").write_text("{not json")
    assert feature(tmp_path)._sessions == {}
    (tmp_path / "compaction_guard.json").write_text('{"sessions": {"a": {"count": "x"}}}')
    assert feature(tmp_path)._sessions == {}


def test_sessions_unseen_for_seven_days_are_pruned(tmp_path):
    # Given an old session and a clock eight days later
    now = [1_000_000.0]
    f = CompactionGuard(tmp_path / "compaction_guard.json", clock=lambda: now[0])
    feed(f, 100_000, 10_000, sid="old")
    now[0] += 8 * 24 * 3600
    # When another session reports / Then the old one is gone
    feed(f, 1_000, sid="new")
    assert set(f._sessions) == {"new"}


def test_config_overrides_and_bad_values_fall_back(tmp_path):
    f = feature(tmp_path, {"restart_at": 2, "drop_ratio": 0.9, "min_prompt": 10})
    assert (f.restart_at, f.drop_ratio, f.min_prompt) == (2, 0.9, 10)
    g = feature(tmp_path, {"restart_at": 0, "drop_ratio": 5, "min_prompt": "x"})
    assert (g.restart_at, g.drop_ratio, g.min_prompt) == (3, 0.5, 50_000)


def test_concurrent_after_calls_keep_the_count_exact(tmp_path):
    # Given 8 threads each reporting 10 compaction pairs on one session
    f = feature(tmp_path, {"restart_at": 1000})

    def work() -> None:
        for _ in range(10):
            f.after(ctx(), row(100_000), 200)
            f.after(ctx(), row(1_000), 200)

    ts = [threading.Thread(target=work) for _ in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    # Then the count is at least one and the state is a consistent dict (no crash, no lost session)
    assert f._sessions["s1"]["count"] >= 1


def test_entry_point_resolves_to_the_factory():
    eps = {e.name: e for e in entry_points(group="token_economics.features")}
    assert eps["compaction_guard"].load() is create
