import json
import threading
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from token_economics_contracts import (
    SERVICES,
    Buckets,
    CostSource,
    Identity,
    KeyInfo,
    LedgerRow,
    RequestContext,
    ShadowSampler,
    load,
)
from token_economics_svc_rollout import Shadow, open_shadow

T0 = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.now = T0

    def __call__(self) -> datetime:
        return self.now


def ctx(rid: str = "r1", session: str = "s1", tenant: str = "acme", harness: str = "claude-code") -> RequestContext:
    return RequestContext(
        request_id=rid,
        ts=T0,
        key=KeyInfo(tenant=tenant, caller="dev"),
        harness=harness,
        identity=Identity(session_id=session),
    )


def row(rid: str, cost: str | None, model: str = "m1") -> LedgerRow:
    return LedgerRow(
        provider="anthropic",
        response_id="resp-" + rid,
        request_id=rid,
        ts=T0,
        model=model,
        buckets=Buckets(fresh_input=10, output=5),
        cost_estimate_usd=Decimal(cost) if cost is not None else None,
        cost_source=CostSource.GATEWAY,
        price_row_id="p1" if cost is not None else "",
    )


def config(tmp: Path, **kw: Any) -> None:
    d = tmp / "shadow"
    d.mkdir(exist_ok=True)
    (d / "shadow.json").write_text(json.dumps({"enabled": True, "share": 1.0, **kw}))


def make(tmp: Path) -> tuple[Shadow, Clock]:
    clock = Clock()
    return Shadow(tmp, clock=clock), clock


def test_disabled_by_default_when_no_config(tmp_path):
    # Given no config file
    s, _ = make(tmp_path)
    # When asked to sample
    # Then nothing is mirrored
    assert s.sample(ctx()) is False


def test_registered_as_shadow_service_and_satisfies_protocol(tmp_path):
    # Given the entry point
    # When loaded
    s = load(SERVICES, "shadow")(str(tmp_path))
    # Then it is a ShadowSampler
    assert isinstance(s, ShadowSampler)
    assert isinstance(open_shadow(str(tmp_path)), Shadow)


def test_enabled_with_zero_share_samples_nothing(tmp_path):
    # Given enabled but share 0
    config(tmp_path, share=0.0)
    s, _ = make(tmp_path)
    # Then nothing is sampled
    assert s.sample(ctx()) is False


def test_sampling_is_deterministic_per_session(tmp_path):
    # Given a 50% share
    config(tmp_path, share=0.5)
    s, _ = make(tmp_path)
    # When many requests of each session are asked about
    for n in range(40):
        session = f"sess-{n}"
        answers = {s.sample(ctx(rid=f"{session}-{i}", session=session)) for i in range(5)}
        # Then a session is wholly in or wholly out
        assert len(answers) == 1


def test_sampled_share_approximates_configured_share(tmp_path):
    # Given a 20% share
    config(tmp_path, share=0.2)
    s, _ = make(tmp_path)
    # When 2000 sessions are asked about
    hits = sum(s.sample(ctx(session=f"s{n}")) for n in range(2000))
    # Then about 20% are sampled
    assert 300 < hits < 500


def test_requests_without_session_are_hashed_by_request_id(tmp_path):
    # Given sessionless requests
    config(tmp_path, share=0.5)
    s, _ = make(tmp_path)
    # When many distinct request ids are asked about
    hits = sum(s.sample(ctx(rid=f"r{n}", session="")) for n in range(400))
    # Then some are in and some out
    assert 100 < hits < 300


def test_tenant_and_harness_filters(tmp_path):
    # Given filters on tenant and harness
    config(tmp_path, tenants=["acme"], harnesses=["claude-code"])
    s, _ = make(tmp_path)
    # Then only matching requests are sampled
    assert s.sample(ctx()) is True
    assert s.sample(ctx(tenant="other")) is False
    assert s.sample(ctx(harness="codex")) is False


def test_daily_cap_stops_sampling_and_resets_next_day(tmp_path):
    # Given a 1.00 cap
    config(tmp_path, max_usd_per_day="1.00")
    s, clock = make(tmp_path)
    assert s.sample(ctx()) is True
    # When shadow spend reaches the cap
    s.record(ctx("a"), "shadow", row("a", "1.00"), 200)
    # Then sampling stops
    assert s.sample(ctx("b")) is False
    # And resumes the next UTC day
    clock.now += timedelta(days=1)
    assert s.sample(ctx("c")) is True


def test_primary_spend_does_not_count_against_the_cap(tmp_path):
    # Given a small cap
    config(tmp_path, max_usd_per_day="1.00")
    s, _ = make(tmp_path)
    # When only the primary side spends
    s.record(ctx("a"), "primary", row("a", "9.00"), 200)
    # Then sampling continues
    assert s.sample(ctx("b")) is True


def test_spend_is_rebuilt_from_the_file_on_start(tmp_path):
    # Given a shadow row already recorded today
    config(tmp_path, max_usd_per_day="1.00")
    first, clock = make(tmp_path)
    first.record(ctx("a"), "shadow", row("a", "1.50"), 200)
    # When a new instance starts
    second = Shadow(tmp_path, clock=clock)
    # Then the cap is already reached
    assert second.sample(ctx("b")) is False


def test_config_is_hot_reloaded(tmp_path):
    # Given a disabled config
    config(tmp_path, share=1.0, enabled=False)
    s, _ = make(tmp_path)
    assert s.sample(ctx()) is False
    # When the file is rewritten with a different size
    config(tmp_path, share=1.0, tenants=["acme"])
    # Then the change applies without a restart
    assert s.sample(ctx()) is True


def test_broken_config_means_disabled_and_never_raises(tmp_path):
    # Given garbage in the config file
    (tmp_path / "shadow").mkdir()
    cfg = tmp_path / "shadow" / "shadow.json"
    s, _ = make(tmp_path)
    for text in ("{not json", "[]", '{"enabled": true, "share": "x"}', '{"enabled": true, "share": 1, "tenants": 5}'):
        cfg.write_text(text)
        # Then sampling is False, not an exception
        assert s.sample(ctx()) is False


def test_record_never_raises_when_directory_is_unwritable(tmp_path):
    # Given a state dir whose shadow path is a file
    (tmp_path / "shadow").write_text("x")
    s, _ = make(tmp_path)
    # When recording
    s.record(ctx(), "shadow", row("r1", "1.00"), 200)
    # Then nothing is raised and report degrades
    assert isinstance(s.report(), dict)
    assert s.sample(ctx()) is False


def test_pairs_file_holds_metadata_only(tmp_path):
    # Given a recorded pair
    s, _ = make(tmp_path)
    s.record(ctx("a"), "primary", row("a", "0.10"), 200)
    # When the file is read
    rec = json.loads((tmp_path / "shadow" / "pairs.jsonl").read_text())
    # Then it has ids, cost and bucket totals
    assert rec["request_id"] == "a" and rec["side"] == "primary" and rec["cost_usd"] == "0.10"
    assert rec["buckets"] == {"fresh_input": 10, "cache_read": 0, "cache_write": 0, "output": 5}
    assert rec["tenant"] == "acme" and rec["caller"] == "dev" and rec["status"] == 200


def test_report_joins_sides_in_either_order_and_counts_unmatched(tmp_path):
    # Given rows arriving out of order, plus unmatched ones on each side
    s, _ = make(tmp_path)
    s.record(ctx("a"), "shadow", row("a", "0.05"), 200)
    s.record(ctx("a"), "primary", row("a", "0.10"), 200)
    s.record(ctx("b"), "primary", row("b", "0.20"), 200)
    s.record(ctx("b"), "shadow", row("b", "0.10"), 200)
    s.record(ctx("c"), "primary", row("c", "1.00"), 200)
    s.record(ctx("d"), "shadow", row("d", "2.00"), 200)
    # When reported
    r = s.report()
    # Then the pairs are joined and the ratio uses matched pairs only
    assert r["pairs"] == 2
    assert r["unmatched"] == {"primary": 1, "shadow": 1}
    assert r["cost_ratio_shadow_over_primary"] is not None
    assert Decimal(r["cost_ratio_shadow_over_primary"]) == Decimal("0.5")
    assert r["primary"]["total_cost_usd"] == "1.30"
    assert r["shadow"]["total_cost_usd"] == "2.15"
    assert r["primary"]["cost_by_model"] == {"m1": "1.30"}
    assert r["spend_today_usd"] == "2.15" and r["max_usd_per_day"] == "5.00"
    json.dumps(r)


def test_report_median_and_p95(tmp_path):
    # Given 20 primary rows costing 1..20
    s, _ = make(tmp_path)
    for n in range(1, 21):
        s.record(ctx(f"r{n}"), "primary", row(f"r{n}", str(n)), 200)
    # When reported
    r = s.report()["primary"]
    # Then median and P95 are nearest-rank
    assert Decimal(r["median_cost_usd"]) == Decimal("10.5")
    assert Decimal(r["p95_cost_usd"]) == Decimal(19)


def test_report_flags_shadow_errors_where_primary_succeeded(tmp_path):
    # Given one pair where only the shadow fails, one where both fail
    s, _ = make(tmp_path)
    s.record(ctx("a"), "primary", row("a", "0.1"), 200)
    s.record(ctx("a"), "shadow", None, 500)
    s.record(ctx("b"), "primary", None, 429)
    s.record(ctx("b"), "shadow", None, 429)
    # When reported
    r = s.report()
    # Then only the first is a mismatch
    assert r["status_mismatches"] == 1 and r["status_mismatch_request_ids"] == ["a"]
    assert r["cost_ratio_shadow_over_primary"] is None


def test_report_on_empty_state(tmp_path):
    # Given nothing recorded
    r = make(tmp_path)[0].report()
    # Then it is a zeroed report
    assert r["pairs"] == 0 and r["primary"]["median_cost_usd"] is None


def test_concurrent_records_lose_nothing(tmp_path):
    # Given many threads recording both sides
    s, _ = make(tmp_path)

    def work(k: int) -> None:
        for n in range(25):
            rid = f"{k}-{n}"
            s.record(ctx(rid), "primary", row(rid, "0.10"), 200)
            s.record(ctx(rid), "shadow", row(rid, "0.05"), 200)

    threads = [threading.Thread(target=work, args=(k,)) for k in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # Then every line is intact and every pair is matched
    lines = (tmp_path / "shadow" / "pairs.jsonl").read_text().splitlines()
    assert len(lines) == 400 and all(json.loads(x) for x in lines)
    r = s.report()
    assert r["pairs"] == 200 and r["spend_today_usd"] == "10.00"
