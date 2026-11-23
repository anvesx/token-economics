import copy
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from importlib.metadata import entry_points

from token_economics_contracts.types import (
    Buckets,
    CostSource,
    FeatureEnv,
    Identity,
    KeyInfo,
    LedgerRow,
    RequestContext,
    RequestFacts,
)
from token_economics_feat_strong_share import create

OPUS, SONNET = "claude-opus-5-5", "claude-sonnet-5-5"
T0 = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


def ctx(model=OPUS, turns=0, ts=T0, tenant="acme"):
    return RequestContext(
        request_id="r",
        ts=ts,
        key=KeyInfo(tenant=tenant),
        provider="anthropic",
        identity=Identity(session_id="s"),
        facts=RequestFacts(model=model, turns=turns),
    )


def row(model=OPUS, ts=T0, cost="1", tenant="acme"):
    return LedgerRow(
        provider="anthropic", response_id="x", ts=ts, tenant=tenant, model=model, buckets=Buckets(),
        cost_estimate_usd=Decimal(cost), cost_source=CostSource.GATEWAY, price_row_id="p",
    )  # fmt: skip


def feature(tmp_path, **cfg):
    base = {"strong_models": [OPUS], "min_calls": 10}
    return create(FeatureEnv(state_dir=tmp_path, config={**base, **cfg}))


def feed(f, strong, weak, ts=T0, cost="1"):
    for _ in range(strong):
        f.after(ctx(), row(OPUS, ts, cost), 200)
    for _ in range(weak):
        f.after(ctx(SONNET), row(SONNET, ts, cost), 200)


def test_entry_point_is_registered():
    assert any(e.name == "strong_share" for e in entry_points(group="token_economics.features"))


def test_strong_request_over_the_share_is_refused_with_429(tmp_path):
    # Given 8 of 10 calls were strong (0.8 > 0.5) / When a strong request arrives / Then 429 strong_share_exceeded
    f = feature(tmp_path)
    feed(f, 8, 2)
    d = f.before(ctx())
    assert d is not None and not d.allow and d.status == 429 and d.code == "strong_share_exceeded"
    assert "0.80" in d.message


def test_weak_request_is_never_refused(tmp_path):
    f = feature(tmp_path)
    feed(f, 8, 2)
    assert f.before(ctx(SONNET)) is None


def test_nothing_acts_before_min_calls(tmp_path):
    # Given 5 strong calls (share 1.0 but under min_calls 10) / Then no refusal
    f = feature(tmp_path)
    feed(f, 5, 0)
    assert f.before(ctx()) is None


def test_under_the_share_is_allowed(tmp_path):
    f = feature(tmp_path)
    feed(f, 4, 6)
    assert f.before(ctx()) is None


def test_old_calls_leave_the_window(tmp_path):
    # Given strong-heavy calls 25 h ago / When a request arrives now / Then they no longer count
    f = feature(tmp_path)
    feed(f, 10, 0, ts=T0 - timedelta(hours=25))
    assert f.before(ctx()) is None
    feed(f, 0, 10)
    assert f.before(ctx()) is None


def test_inert_without_strong_models(tmp_path):
    f = create(FeatureEnv(state_dir=tmp_path, config={"strong_models": [], "min_calls": 0}))
    f.after(ctx(), row(), 200)
    assert f.before(ctx()) is None and f.rewrite(ctx(), {}) is None


def test_tenants_are_counted_separately(tmp_path):
    f = feature(tmp_path)
    feed(f, 8, 2)
    assert f.before(ctx(tenant="other")) is None


def test_cost_measure_uses_spend_not_calls(tmp_path):
    # Given 1 strong call costing $9 and 9 weak calls costing $1 each: calls 0.1, cost 0.5
    f = feature(tmp_path, measure="cost", max_share=0.4)
    f.after(ctx(), row(OPUS, cost="9"), 200)
    for _ in range(9):
        f.after(ctx(SONNET), row(SONNET, cost="1"), 200)
    assert f.before(ctx()) is not None
    assert feature(tmp_path / "calls", max_share=0.4).before(ctx()) is None


def test_downgrade_rewrites_at_conversation_start_with_a_note(tmp_path):
    # Given a downgrade target and an over-share tenant / When a conversation starts / Then the model is swapped
    f = feature(tmp_path, downgrade_to=SONNET)
    feed(f, 62, 38)
    body = {"model": OPUS, "messages": []}
    original = copy.deepcopy(body)
    out = f.rewrite(ctx(), body)
    assert out is not None and out.body["model"] == SONNET
    assert out.changes == (f"model {OPUS}->{SONNET} (strong share 0.62 > 0.50)",)
    assert body == original
    assert f.before(ctx()) is None  # downgrade replaces the refusal


def test_downgrade_leaves_mid_session_requests_alone(tmp_path):
    f = feature(tmp_path, downgrade_to=SONNET)
    feed(f, 8, 2)
    assert f.rewrite(ctx(turns=3), {"model": OPUS}) is None


def test_downgrade_skips_weak_models_and_under_share(tmp_path):
    f = feature(tmp_path, downgrade_to=SONNET)
    feed(f, 8, 2)
    assert f.rewrite(ctx(SONNET), {}) is None
    g = feature(tmp_path / "g", downgrade_to=SONNET)
    feed(g, 2, 8)
    assert g.rewrite(ctx(), {}) is None


def test_one_alert_per_tenant_per_utc_day(tmp_path):
    # Given the share crosses alert_at (0.45) / When more calls arrive / Then one alert that day, another next day
    f = feature(tmp_path)
    feed(f, 8, 2)
    feed(f, 1, 0)
    lines = [json.loads(x) for x in (tmp_path / "alerts.jsonl").read_text().splitlines()]
    assert len(lines) == 1
    assert lines[0]["kind"] == "strong_share" and lines[0]["tenant"] == "acme" and lines[0]["max_share"] == 0.5
    f.after(ctx(), row(OPUS, ts=T0 + timedelta(hours=13)), 200)
    assert len((tmp_path / "alerts.jsonl").read_text().splitlines()) == 2


def test_no_alert_below_alert_at(tmp_path):
    f = feature(tmp_path)
    feed(f, 2, 8)
    assert not (tmp_path / "alerts.jsonl").exists()


def test_counts_survive_a_restart_and_hold_only_numbers(tmp_path):
    f = feature(tmp_path)
    feed(f, 8, 2)  # the alert forces a write
    g = feature(tmp_path)
    assert g.before(ctx()) is not None
    text = (tmp_path / "strong_share.json").read_text()
    assert OPUS not in text and "acme" in text


def test_corrupt_state_file_reads_as_empty(tmp_path):
    (tmp_path / "strong_share.json").write_text("{not json")
    f = feature(tmp_path)
    assert f.before(ctx()) is None
    (tmp_path / "strong_share.json").write_text(json.dumps({"tenants": {"acme": {"x": [1]}}}))
    assert feature(tmp_path).before(ctx()) is None


def test_row_none_and_odd_config_do_not_raise(tmp_path):
    f = create(
        FeatureEnv(state_dir=tmp_path, config={"strong_models": [OPUS, 3], "max_share": "x", "window_hours": -1})
    )
    f.after(ctx(), None, 500)
    assert f.before(ctx()) is None
