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
)
from token_economics_feat_anomaly import create

TODAY = datetime(2026, 3, 20, 12, 0, tzinfo=UTC)
STEADY = [10, 11, 9, 10, 12, 10, 9, 11, 10, 10]  # median 10, MAD 0.5 -> threshold 10 + 5 * 1.4826 * 0.5 = 13.7


def ctx(caller="dev", ts=TODAY):
    return RequestContext(request_id="r", ts=ts, key=KeyInfo(tenant="acme", caller=caller), identity=Identity())


def row(cost, caller="dev", ts=TODAY, session="s1"):
    return LedgerRow(
        provider="anthropic", response_id="x", ts=ts, tenant="acme", caller=caller, session_id=session, model="m",
        buckets=Buckets(), cost_estimate_usd=None if cost is None else Decimal(str(cost)),
        cost_source=CostSource.GATEWAY, price_row_id="p",
    )  # fmt: skip


def feature(tmp_path, **cfg):
    return create(FeatureEnv(state_dir=tmp_path, config=cfg))


def history(f, spends=STEADY, caller="dev"):
    for back, usd in enumerate(spends, start=1):
        f.after(ctx(), row(usd, caller, TODAY - timedelta(days=back), session=f"old{back}"), 200)


def alerts(tmp_path):
    p = tmp_path / "alerts.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


def test_entry_point_is_registered():
    assert any(e.name == "anomaly" for e in entry_points(group="token_economics.features"))


def test_spend_far_above_the_baseline_alerts_once_per_day(tmp_path):
    # Given 10 days around $10 / When today passes median + 5 x 1.4826 x MAD (13.7) / Then one daily alert
    f = feature(tmp_path)
    history(f)
    f.after(ctx(), row(14), 200)
    f.after(ctx(), row(3), 200)
    (a,) = alerts(tmp_path)
    assert a["kind"] == "spend_anomaly" and a["trigger"] == "daily" and a["caller"] == "dev"
    assert a["median_usd"] == "10" and a["history_days"] == 10 and a["today_usd"] == "14"
    assert Decimal(a["threshold_usd"]) == Decimal("13.7065")


def test_spend_inside_the_baseline_does_not_alert(tmp_path):
    f = feature(tmp_path)
    history(f)
    f.after(ctx(), row(13), 200)
    assert alerts(tmp_path) == []


def test_a_new_day_can_alert_again(tmp_path):
    f = feature(tmp_path)
    history(f)
    f.after(ctx(), row(14), 200)
    f.after(ctx(), row(25, ts=TODAY + timedelta(days=1)), 200)
    assert len(alerts(tmp_path)) == 2


def test_not_enough_history_means_no_alert(tmp_path):
    # Given only 6 days of history (min_days 7) / When spend is huge / Then no alert
    f = feature(tmp_path)
    history(f, STEADY[:6])
    f.after(ctx(), row(500), 200)
    assert alerts(tmp_path) == []


def test_small_absolute_spend_is_ignored_even_when_relatively_huge(tmp_path):
    # Given a $0.10 a day caller / When it spends $4 (under min_usd 5) / Then no alert
    f = feature(tmp_path)
    history(f, [Decimal("0.1")] * 10)
    f.after(ctx(), row(4), 200)
    assert alerts(tmp_path) == []
    f.after(ctx(), row(2), 200)
    assert len(alerts(tmp_path)) == 1


def test_one_outlier_day_does_not_hide_the_next_anomaly(tmp_path):
    # Given a baseline that includes one $200 day / Then median and MAD barely move and $30 still alerts
    f = feature(tmp_path)
    history(f, [*STEADY[:9], 200])
    f.after(ctx(), row(30), 200)
    assert len(alerts(tmp_path)) == 1


def test_callers_are_independent(tmp_path):
    f = feature(tmp_path)
    history(f)
    f.after(ctx("other"), row(14, "other"), 200)
    assert alerts(tmp_path) == []


def test_session_spike_alerts_independently_of_the_baseline(tmp_path):
    # Given session_usd 20 and no history / When one session spends $25 / Then a session alert
    f = feature(tmp_path, session_usd=20)
    f.after(ctx(), row(12, session="big"), 200)
    f.after(ctx(), row(13, session="big"), 200)
    f.after(ctx(), row(1, session="big"), 200)
    (a,) = alerts(tmp_path)
    assert a["trigger"] == "session" and a["session_usd"] == "25" and a["limit_usd"] == "20"


def test_session_spend_is_summed_per_session(tmp_path):
    f = feature(tmp_path, session_usd=20)
    f.after(ctx(), row(15, session="a"), 200)
    f.after(ctx(), row(15, session="b"), 200)
    assert alerts(tmp_path) == []


def test_alert_only_by_default_never_blocks(tmp_path):
    f = feature(tmp_path)
    history(f)
    f.after(ctx(), row(14), 200)
    assert f.before(ctx()) is None


def test_block_refuses_the_caller_for_the_rest_of_the_utc_day(tmp_path):
    # Given block is on and an anomaly fired / Then the caller gets 429 until midnight UTC, others are fine
    f = feature(tmp_path, block=True)
    history(f)
    f.after(ctx(), row(14), 200)
    d = f.before(ctx())
    assert d is not None and not d.allow and d.status == 429 and d.code == "spend_anomaly"
    assert f.before(ctx("other")) is None
    assert f.before(ctx(ts=TODAY + timedelta(hours=13))) is None


def test_state_survives_a_restart_and_is_numbers_only(tmp_path):
    f = feature(tmp_path, block=True)
    history(f)
    f.after(ctx(), row(14), 200)
    g = feature(tmp_path, block=True)
    assert g.before(ctx()) is not None
    g.after(ctx(), row(20), 200)
    assert len(alerts(tmp_path)) == 1  # already alerted today
    assert "dev" in (tmp_path / "anomaly.json").read_text()


def test_history_is_bounded(tmp_path):
    f = feature(tmp_path, baseline_days=5)
    history(f, [1] * 100)
    f.after(ctx(), row(1), 200)
    f.flush()
    days = json.loads((tmp_path / "anomaly.json").read_text())["callers"]["dev"]
    assert len(days) <= 31


def test_corrupt_state_and_odd_rows_do_not_raise(tmp_path):
    (tmp_path / "anomaly.json").write_text("{nope")
    f = feature(tmp_path, k="x", min_usd=-1, baseline_days=0)
    f.after(ctx(), None, 500)
    f.after(ctx(), row(None), 200)
    f.after(ctx(caller=""), row(5, caller=""), 200)
    assert f.before(ctx()) is None
    (tmp_path / "anomaly.json").write_text(json.dumps({"callers": {"dev": {"2026-03-01": "oops"}}}))
    assert feature(tmp_path).before(ctx()) is None


def test_perfectly_steady_spend_does_not_alert_on_a_few_cents(tmp_path):
    # Given ten days of exactly $10 (MAD 0)
    f = feature(tmp_path)
    history(f, spends=[10] * 10)
    # When today is $10.50, then $13
    f.after(ctx(), row(10.5), 200)
    assert alerts(tmp_path) == []
    f.after(ctx(), row(2.5), 200)
    # Then only crossing 1.25 x the median ($12.50) alerts
    assert [a["today_usd"] for a in alerts(tmp_path)] == ["13.0"]
