import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from token_economics_contracts import Decision, FeatureEnv, KeyInfo, LedgerRow, PolicyEngine, RequestContext
from token_economics_svc_policy import PolicyService

CTX = RequestContext(request_id="r1", ts=datetime(2026, 11, 21, tzinfo=UTC), key=KeyInfo(tenant="devx", caller="dhruv"))
BLOCK = Decision(allow=False, status=429, code="nope", message="no")


class Fake:
    def __init__(
        self, name: str, decision: Decision | None = None, fail_closed: bool = False, boom: bool = False
    ) -> None:
        self.name, self.fail_closed, self._decision, self._boom = name, fail_closed, decision, boom
        self.before_calls, self.after_calls = 0, []

    def before(self, ctx: RequestContext) -> Decision | None:
        self.before_calls += 1
        if self._boom:
            raise OSError("store down")
        return self._decision

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        self.after_calls.append(status)


def service(tmp_path: Path, features: dict[str, Fake], policy: dict[str, Any] | None) -> PolicyService:
    if policy is not None:
        (tmp_path / "policy.json").write_text(json.dumps(policy))
    return PolicyService(tmp_path, factories={n: (lambda env, f=f: f) for n, f in features.items()})


def decisions(tmp_path: Path) -> list[dict[str, Any]]:
    p = tmp_path / "decisions.jsonl"
    return [json.loads(line) for line in p.read_text().splitlines()] if p.exists() else []


def test_every_feature_is_off_without_a_policy_file(tmp_path: Path) -> None:
    f = Fake("budgets", BLOCK)
    svc = service(tmp_path, {"budgets": f}, None)
    assert isinstance(svc, PolicyEngine)
    assert svc.before(CTX).allow and f.before_calls == 0 and svc.modes() == {}


def test_an_enforced_feature_blocks_and_earlier_features_are_released(tmp_path: Path) -> None:
    # Given budgets passes (holding a reservation) and the turn cap refuses
    budgets, cap = Fake("budgets"), Fake("turn_cap", BLOCK)
    svc = service(
        tmp_path,
        {"budgets": budgets, "turn_cap": cap},
        {"features": {"budgets": {"mode": "enforced"}, "turn_cap": {"mode": "enforced"}}},
    )
    d = svc.before(CTX)
    # Then the request is blocked, budgets was told to release, and the decision is logged without any text
    assert not d.allow and d.feature == "turn_cap" and d.status == 429
    assert budgets.after_calls == [429] and cap.after_calls == []
    (rec,) = decisions(tmp_path)
    assert (rec["action"], rec["feature"], rec["code"], rec["caller"]) == ("blocked", "turn_cap", "nope", "dhruv")


def test_an_advisory_feature_records_and_lets_the_request_through(tmp_path: Path) -> None:
    f = Fake("loop_guard", BLOCK)
    svc = service(tmp_path, {"loop_guard": f}, {"features": {"loop_guard": {"mode": "advisory"}}})
    assert svc.before(CTX).allow
    assert decisions(tmp_path)[0]["action"] == "would_block"
    svc.after(CTX, None, 200)
    assert f.after_calls == [200]


def test_a_failing_feature_fails_open_unless_it_is_an_enforced_fail_closed_one(tmp_path: Path) -> None:
    # Given a broken loop guard (fail open) and a broken budget store (fail closed)
    guard, budgets = Fake("loop_guard", boom=True), Fake("budgets", boom=True, fail_closed=True)
    open_svc = service(tmp_path / "a", {"loop_guard": guard}, None)
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "policy.json").write_text(json.dumps({"features": {"loop_guard": {"mode": "enforced"}}}))
    assert open_svc.before(CTX).allow
    (tmp_path / "b").mkdir()
    closed = service(tmp_path / "b", {"budgets": budgets}, {"features": {"budgets": {"mode": "enforced"}}})
    d = closed.before(CTX)
    assert not d.allow and d.status == 503 and d.code == "policy_unavailable"
    # And the same broken budget in advisory mode does not block
    (tmp_path / "c").mkdir()
    advisory = service(tmp_path / "c", {"budgets": budgets}, {"features": {"budgets": {"mode": "advisory"}}})
    assert advisory.before(CTX).allow


def test_an_enforced_feature_that_cannot_start_refuses_instead_of_passing_silently(tmp_path: Path) -> None:
    def bad_factory(env: FeatureEnv) -> Any:
        raise ValueError("bad budget limit")

    (tmp_path / "policy.json").write_text(
        json.dumps({"features": {"budgets": {"mode": "enforced"}, "ghost": {"mode": "enforced"}}})
    )
    svc = PolicyService(tmp_path, factories={"budgets": bad_factory})
    assert not svc.before(CTX).allow
    assert len(svc.problems) == 2 and "bad budget limit" in svc.problems[0] and "ghost" in svc.problems[1]


def test_policy_file_changes_apply_without_a_restart(tmp_path: Path) -> None:
    f = Fake("turn_cap", BLOCK)
    svc = service(tmp_path, {"turn_cap": f}, {"features": {"turn_cap": {"mode": "off"}}})
    assert svc.before(CTX).allow
    path = tmp_path / "policy.json"
    path.write_text(json.dumps({"features": {"turn_cap": {"mode": "enforced", "default": 5}}}))
    os.utime(path, ns=(1, 1))  # make sure the stamp differs even on a coarse clock
    assert not svc.before(CTX).allow


def test_features_run_in_the_configured_order(tmp_path: Path) -> None:
    a, b = Fake("budgets", BLOCK), Fake("turn_cap", BLOCK.model_copy(update={"code": "cap"}))
    svc = service(
        tmp_path,
        {"budgets": a, "turn_cap": b},
        {
            "order": ["turn_cap", "budgets"],
            "features": {"budgets": {"mode": "enforced"}, "turn_cap": {"mode": "enforced"}},
        },
    )
    assert svc.before(CTX).code == "cap" and a.before_calls == 0
