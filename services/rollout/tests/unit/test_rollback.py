import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from token_economics_contracts import (
    SERVICES,
    Buckets,
    CostSource,
    KillFile,
    LedgerRow,
    RollbackChecker,
    canary_slot,
    load,
)
from token_economics_svc_rollout import Rollback, open_rollback

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)
FEATURE, SHARE = "output_cap", 0.5


def split(n_canary: int, n_control: int, feature: str = FEATURE) -> tuple[list[str], list[str]]:
    """Session ids that fall inside and outside the canary."""
    canary: list[str] = []
    control: list[str] = []
    i = 0
    while len(canary) < n_canary or len(control) < n_control:
        sid = f"s{i}"
        i += 1
        (canary if canary_slot(sid, feature) < SHARE else control).append(sid)
    return canary[:n_canary], control[:n_control]


class MemoryLedger:
    """Just enough of the Ledger port, so these tests run with only this package's declared dependencies."""

    def __init__(self) -> None:
        self._rows: list[LedgerRow] = []

    def write(self, row: LedgerRow) -> bool:
        self._rows.append(row)
        return True

    def rows(self, since: datetime | None = None, until: datetime | None = None) -> list[LedgerRow]:
        return [r for r in self._rows if (since is None or r.ts >= since) and (until is None or r.ts < until)]


class World:
    def __init__(self, tmp: Path, policy: dict[str, Any] | None = None) -> None:
        self.tmp = tmp
        self.n = 0
        section = {"mode": "enforced", "canary": {"share": SHARE}}
        (tmp / "policy.json").write_text(json.dumps({"features": {FEATURE: section}} if policy is None else policy))
        self.ledger = MemoryLedger()

    def add(
        self, session: str, cost: str = "1.00", status: int = 200, cache_read: int = 0, tenant: str = "acme"
    ) -> None:
        self.n += 1
        self.ledger.write(
            LedgerRow(
                provider="anthropic",
                response_id=f"resp-{self.n}",
                ts=NOW - timedelta(hours=1),
                tenant=tenant,
                session_id=session,
                model="m1",
                buckets=Buckets(fresh_input=1000 - cache_read, cache_read=cache_read, output=10),
                cost_estimate_usd=Decimal(cost),
                cost_source=CostSource.GATEWAY,
                price_row_id="p1",
                http_status=status,
            )
        )

    def fill(self, n: int = 40, **canary: Any) -> None:
        """n canary and n control sessions; `canary` overrides the canary rows' fields."""
        can, ctl = split(n, n)
        for s in ctl:
            self.add(s)
        for s in can:
            self.add(s, **canary)

    def check(self) -> list[dict[str, Any]]:
        return list(Rollback(self.tmp, ledger=self.ledger).check(NOW))

    def killed(self) -> KillFile:
        try:
            return KillFile.model_validate_json((self.tmp / "kill.json").read_text())
        except FileNotFoundError:
            return KillFile()

    def lines(self, name: str) -> list[dict[str, Any]]:
        try:
            return [json.loads(x) for x in (self.tmp / name).read_text().splitlines()]
        except FileNotFoundError:
            return []


def test_registered_as_rollback_service(tmp_path: Path) -> None:
    # Given the entry point, when loaded, then it is a RollbackChecker
    try:
        factory = load(SERVICES, "rollback")
    except LookupError:
        pytest.skip("entry point not installed yet: run uv sync")
    assert isinstance(factory(str(tmp_path)), RollbackChecker)


def test_a_canary_that_costs_more_than_the_control_interval_is_killed(tmp_path: Path) -> None:
    # Given 40 canary and 40 control sessions, the canary costing three times as much
    w = World(tmp_path)
    w.fill(cost="3.00")
    # When the check runs
    (result,) = w.check()
    # Then the feature is killed for every tenant, with the numbers as the reason, and an alert and a log line exist
    assert result["feature"] == FEATURE and result["action"] == "killed"
    assert result["triggers"]["cost"]["status"] == "breach"
    assert w.killed().killed(FEATURE, "any") and "cost" in w.killed().kills[0].reason
    assert w.killed().kills[0].by == "rollback:cost"
    assert w.lines("rollbacks.jsonl")[0]["trigger"] == "cost"
    assert [a["kind"] for a in w.lines("alerts.jsonl")] == ["rollback"]
    assert "latency" in result["latency"].lower() and "not measurable" in result["latency"]


def test_a_canary_that_costs_the_same_is_left_running(tmp_path: Path) -> None:
    # Given equal canary and control
    w = World(tmp_path)
    w.fill()
    # When the check runs, then nothing is killed
    (result,) = w.check()
    assert result["action"] == "none" and not w.killed().kills and not w.lines("alerts.jsonl")


def test_too_few_sessions_is_insufficient_data_and_no_action(tmp_path: Path) -> None:
    # Given 5 sessions per side with a terrible canary
    w = World(tmp_path)
    w.fill(n=5, cost="9.00", status=500)
    # When the check runs, then it says so and does nothing
    (result,) = w.check()
    assert result["action"] == "none" and result["status"] == "insufficient data"
    assert not w.killed().kills


def test_a_canary_with_more_errors_than_the_margin_is_killed(tmp_path: Path) -> None:
    # Given a canary whose rows all fail with 500
    w = World(tmp_path)
    w.fill(status=500)
    # When the check runs
    (result,) = w.check()
    # Then the errors trigger fires (cost is equal, so only this one)
    assert result["triggers"]["errors"]["status"] == "breach" and result["triggers"]["cost"]["status"] == "ok"
    assert w.killed().kills[0].by == "rollback:errors"


def test_a_success_rate_below_the_floor_is_killed_only_when_outcomes_exist(tmp_path: Path) -> None:
    # Given no outcomes file, the success trigger is not applicable
    w = World(tmp_path)
    w.fill()
    assert w.check()[0]["triggers"]["success"]["status"] == "n/a"
    # When outcomes say the canary succeeds 50% against 100% for control
    can, ctl = split(40, 40)
    lines = [{"session_id": s, "success": True} for s in ctl]
    lines += [{"session_id": s, "success": i % 2 == 0} for i, s in enumerate(can)]
    (tmp_path / "outcomes.jsonl").write_text("\n".join(json.dumps(x) for x in lines) + "\nnot json\n")
    (result,) = w.check()
    # Then it is killed
    assert result["triggers"]["success"]["status"] == "breach" and result["action"] == "killed"
    assert w.killed().kills[0].by == "rollback:success"


def test_a_cache_hit_rate_drop_is_killed(tmp_path: Path) -> None:
    # Given a control that reads 80% from cache and a canary at 20%
    w = World(tmp_path)
    can, ctl = split(40, 40)
    for s in ctl:
        w.add(s, cache_read=800)
    for s in can:
        w.add(s, cache_read=200)
    # When the check runs, then the hit trigger fires
    (result,) = w.check()
    assert result["triggers"]["cache_hit"]["status"] == "breach"
    assert w.killed().kills[0].by == "rollback:cache_hit"


def test_billed_far_from_estimated_kills_every_canaried_feature(tmp_path: Path) -> None:
    # Given two canaried features and one without a canary, healthy traffic, and a reconciliation 20% off
    policy = {
        "features": {
            "a": {"mode": "enforced", "canary": {"share": SHARE}},
            "b": {"mode": "advisory", "canary": {"share": SHARE}},
            "c": {"mode": "enforced"},
        }
    }
    w = World(tmp_path, policy)
    (tmp_path / "reconciliation.jsonl").write_text(
        json.dumps({"date": "2026-11-21", "provider": "anthropic", "billed_usd": "100", "estimated_usd": "100"})
        + "\n"
        + json.dumps({"date": "2026-11-22", "provider": "anthropic", "billed_usd": "120", "estimated_usd": "100"})
        + "\n"
    )
    # When the check runs
    results = w.check()
    # Then a and b are killed by the billing trigger; c is not canaried so it is not touched
    assert {r["feature"] for r in results} == {"a", "b"} and all(r["action"] == "killed" for r in results)
    assert {k.feature for k in w.killed().kills} == {"a", "b"}
    assert all(k.by == "rollback:billing" for k in w.killed().kills)


def test_billing_within_tolerance_does_nothing(tmp_path: Path) -> None:
    w = World(tmp_path)
    (tmp_path / "reconciliation.jsonl").write_text(
        json.dumps({"date": "2026-11-22", "provider": "anthropic", "billed_usd": "102", "estimated_usd": "100"}) + "\n"
    )
    assert w.check()[0]["triggers"]["billing"]["status"] == "ok" and not w.killed().kills


def test_a_second_check_does_not_kill_again_or_alert_twice(tmp_path: Path) -> None:
    # Given a breach that was already handled
    w = World(tmp_path)
    w.fill(cost="3.00")
    w.check()
    # When the check runs again
    (result,) = w.check()
    # Then the feature is reported as already killed and nothing new is written
    assert result["action"] == "already_killed" and len(w.killed().kills) == 1
    assert len(w.lines("rollbacks.jsonl")) == 1 and len(w.lines("alerts.jsonl")) == 1


def test_thresholds_come_from_rollout_json(tmp_path: Path) -> None:
    # Given a canary with 10% errors and a margin of 0.02 (breach) versus 0.5 in rollout.json (fine)
    w = World(tmp_path)
    can, ctl = split(40, 40)
    for s in ctl:
        w.add(s)
    for i, s in enumerate(can):
        w.add(s, status=500 if i < 4 else 200)
    (tmp_path / "rollout.json").write_text(json.dumps({"error_margin": 0.5}))
    assert w.check()[0]["triggers"]["errors"]["status"] == "ok"


def test_the_canary_and_control_are_limited_to_the_listed_tenants_with_mode_on(tmp_path: Path) -> None:
    # Given a canary for acme only, and a bad "other" tenant that is not in it
    policy = {"features": {FEATURE: {"mode": "enforced", "canary": {"share": SHARE, "tenants": ["acme"]}}}}
    w = World(tmp_path, policy)
    can, ctl = split(40, 40)
    for s in ctl:
        w.add(s)
    for s in can:
        w.add(s)
    other_can, _ = split(60, 0)
    for s in other_can:
        w.add(s, cost="50.00", tenant="other")
    # When the check runs, then the other tenant's rows are ignored
    (result,) = w.check()
    assert result["action"] == "none" and result["sessions"] == {"canary": 40, "control": 40}


def test_a_tenant_with_the_feature_off_is_left_out(tmp_path: Path) -> None:
    # Given acme has the feature off, so its canary-slot sessions did not get it
    policy = {"features": {FEATURE: {"mode": "enforced", "tenants": {"acme": "off"}, "canary": {"share": SHARE}}}}
    w = World(tmp_path, policy)
    w.fill(cost="9.00")
    (result,) = w.check()
    assert result["status"] == "insufficient data" and result["action"] == "none"


def test_broken_files_are_reported_and_never_raise(tmp_path: Path) -> None:
    # Given unreadable config, outcomes, reconciliation and kill files, and a good bad-canary ledger
    w = World(tmp_path)
    w.fill(cost="3.00")
    (tmp_path / "rollout.json").write_text("{broken")
    (tmp_path / "reconciliation.jsonl").write_text("garbage\n")
    (tmp_path / "kill.json").write_text("{broken")
    # When the check runs
    (result,) = w.check()
    # Then it reports the problems, does not touch the broken kill file, and does not raise
    assert result["action"] == "error" and result["problems"]
    assert (tmp_path / "kill.json").read_text() == "{broken"


def test_no_ledger_and_no_policy_is_an_empty_report(tmp_path: Path) -> None:
    assert list(open_rollback(str(tmp_path)).check(NOW)) == []


def test_healthy_small_canaries_are_rarely_killed_by_noise(tmp_path: Path) -> None:
    # Given 40 days where a 5% canary and the control draw session costs from the SAME distribution
    import random

    from token_economics_stats import mean_diff_interval

    rng = random.Random(7)
    fired = 0
    for day in range(40):
        canary = [rng.lognormvariate(0, 1) for _ in range(30)]
        control = [rng.lognormvariate(0, 1) for _ in range(570)]
        ci = mean_diff_interval(canary, control, 0.95, 500, day)
        fired += ci is not None and ci[0] > 0
    # Then the cost trigger fires on at most a few of them (about 2.5% expected), not a third
    assert fired <= 4
