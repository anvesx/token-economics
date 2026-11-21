"""P1 gates end to end: budget-overshoot, fault, failure-posture, capability-matrix (PHASES.md "P1 done")."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from typing import Any

import httpx
from token_economics_contracts import ADAPTERS, SERVICES, load, load_all
from token_economics_contracts.testing import check_adapter
from token_economics_svc_ledger import SqliteLedger

OVERSHOOT_BOUND = Decimal("0")  # measured: the worst-case reservation covers every fixture response (see test below)
COST_PER_RESPONSE = Decimal("0.039448")  # the streamed fixture on claude-opus-5-5 at seed prices


def budget_policy(usd: str, mode: str = "enforced", **extra: Any) -> dict[str, Any]:
    limits = [{"scope": "caller", "match": "*", "window": "day", "usd": usd}]
    return {"features": {"budgets": {"mode": mode, "limits": limits, **extra}}}


def body(message_id: str, scenario: str = "stream", **extra: Any) -> bytes:
    spec = {
        "model": "claude-opus-5-5",
        "max_tokens": 4096,
        "stream": True,
        "scenario": scenario,
        "message_id": message_id,
        "messages": [{"role": "user", "content": "hello"}],
        **extra,
    }
    return json.dumps(spec).encode()


def post(rig: Any, content: bytes, key: str = "vk-dev-1") -> httpx.Response:
    headers = {
        "user-agent": "claude-cli/2.1.330",
        "x-api-key": "sk-ant-api-test",
        "content-type": "application/json",
        "x-token-economics-key": key,
    }
    try:
        return httpx.post(f"{rig.gateway_url}/v1/messages", content=content, headers=headers, timeout=30)
    except httpx.HTTPError as exc:  # a cut stream surfaces as a client-side protocol error
        return httpx.Response(599, text=type(exc).__name__)


def settled(rig: Any, requests: int, timeout: float = 15.0) -> list[Any]:
    """Wait until every reservation is released, then return the ledger rows."""
    reader = load(SERVICES, "budget_status")(str(rig.settings.state_dir))
    deadline = time.time() + timeout
    while time.time() < deadline:
        if rig.app.state.observer.stats.get("requests", 0) >= requests and all(
            s.reserved_usd == 0 for s in reader.status()
        ):
            break
        time.sleep(0.05)
    return list(SqliteLedger(rig.settings.ledger_path).rows())


def decisions(rig: Any) -> list[dict[str, Any]]:
    path = rig.settings.state_dir / "decisions.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def test_request_over_budget_is_refused_at_the_gateway_and_never_reaches_the_provider(rig_factory: Any) -> None:
    # Given a caller budget too small for one request
    rig = rig_factory(budget_policy("0.01"))
    # When a request arrives
    resp = post(rig, body("msg_b1"))
    # Then the gateway answers 402 in the provider's error shape, naming the budget, and nothing went upstream
    assert resp.status_code == 402 and resp.headers["x-token-economics-blocked"] == "budget_exhausted"
    err = resp.json()
    assert err["type"] == "error" and err["error"]["type"] == "billing_error"
    assert "caller:dhruv" in err["error"]["message"] and "$0.01" in err["error"]["message"]
    assert rig.provider.requests == []
    assert decisions(rig)[0]["action"] == "blocked" and decisions(rig)[0]["code"] == "budget_exhausted"


def test_key_never_exceeds_budget_by_more_than_measured_overshoot(rig_factory: Any) -> None:
    # Given a key with a 1 dollar budget and the overshoot bound measured for this build
    rig = rig_factory(budget_policy("1"))
    # When 50 parallel requests arrive
    with ThreadPoolExecutor(25) as pool:
        codes = list(pool.map(lambda i: post(rig, body(f"msg_par_{i}")).status_code, range(50)))
    rows = settled(rig, 50)
    billed = sum((r.cost_estimate_usd or Decimal(0)) for r in rows)
    # Then total billed cost stays within budget plus the bound, and every passed request has exactly one row
    assert billed <= Decimal(1) + OVERSHOOT_BOUND
    assert codes.count(200) == len(rows) and codes.count(402) == 50 - len(rows) and 0 < len(rows) < 50
    assert billed == COST_PER_RESPONSE * len(rows)
    # And another caller's budget is untouched
    assert post(rig, body("msg_other"), key="vk-dev-2").status_code == 200


def test_spend_is_trued_up_to_the_real_cost_after_the_response(rig_factory: Any) -> None:
    rig = rig_factory(budget_policy("5"))
    assert post(rig, body("msg_t1")).status_code == 200
    settled(rig, 1)
    (status,) = load(SERVICES, "budget_status")(str(rig.settings.state_dir)).status()
    assert (status.scope, status.spent_usd, status.reserved_usd) == ("caller:dhruv", COST_PER_RESPONSE, Decimal(0))


def test_advisory_budget_blocks_nothing_and_records_what_it_would_have_done(rig_factory: Any) -> None:
    rig = rig_factory(budget_policy("0.01", mode="advisory"))
    assert post(rig, body("msg_a1")).status_code == 200
    assert [d["action"] for d in decisions(rig)] == ["would_block"]


def test_fault_injection_never_double_counts_or_loses_a_ledger_row(rig_factory: Any) -> None:
    # Given budgets on, and a provider that answers 429, 500, cuts a stream, then works twice with the same id
    rig = rig_factory(budget_policy("5"))
    assert post(rig, body("msg_f1", "rate_limited")).status_code == 429
    assert post(rig, body("msg_f2", "server_error")).status_code == 500
    post(rig, body("msg_f3", "cut"))
    assert post(rig, body("msg_f4")).status_code == 200
    assert post(rig, body("msg_f4")).status_code == 200  # a retry the provider answered with the same response id
    rows = settled(rig, 5)
    # Then there is exactly one row per billable response: the cut stream (billed for what it started) and msg_f4
    assert sorted(r.response_id for r in rows) == ["msg_f3", "msg_f4"]
    # And no reservation is left behind by any of the five requests
    (status,) = load(SERVICES, "budget_status")(str(rig.settings.state_dir)).status()
    assert status.reserved_usd == 0 and status.spent_usd == sum(r.cost_estimate_usd for r in rows)


def test_provider_timeout_returns_a_gateway_error_and_releases_the_reservation(rig_factory: Any) -> None:
    rig = rig_factory(budget_policy("5"), upstream_timeout_s=0.5)
    assert post(rig, body("msg_slow", "slow")).status_code == 502
    assert settled(rig, 1) == []
    assert all(s.reserved_usd == 0 for s in load(SERVICES, "budget_status")(str(rig.settings.state_dir)).status())


def test_budgets_fail_closed_and_observation_fails_open(rig_factory: Any) -> None:
    # Given an enforced budget whose configuration cannot be loaded (the budget check is unavailable)
    broken = {
        "features": {"budgets": {"mode": "enforced", "limits": [{"scope": "caller", "window": "day", "usd": "-1"}]}}
    }
    closed = rig_factory(broken)
    # Then budgeted calls are refused
    resp = post(closed, body("msg_fc"))
    assert resp.status_code == 503 and resp.headers["x-token-economics-blocked"] == "policy_unavailable"
    assert closed.provider.requests == []
    health = httpx.get(f"{closed.gateway_url}/_te/health").json()
    assert health["policy"] == {"budgets": "enforced"} and "budgets" in health["policy_problems"][0]
    # And with the same broken budget only advisory, traffic flows and is still observed
    broken["features"]["budgets"]["mode"] = "advisory"
    opened = rig_factory(broken)
    assert post(opened, body("msg_fo")).status_code == 200
    assert opened.wait_idle("rows").get("rows") == 1


def test_key_revoked_mid_session_gets_401_on_the_next_call_and_is_audited(rig_factory: Any) -> None:
    rig = rig_factory()
    assert post(rig, body("msg_k1")).status_code == 200
    # When the key is revoked from another process (the CLI)
    store = load(SERVICES, "keys")(str(rig.settings.state_dir))
    key_id = next(k.key_id for k in store.list() if k.info.caller == "dhruv")
    assert store.revoke(key_id, actor="test")
    time.sleep(1.2)
    # Then the next call is refused and the audit log has both the revocation and the refused use
    resp = post(rig, body("msg_k2"))
    assert resp.status_code == 401 and resp.json()["error"]["type"] == "authentication_error"
    actions = [e.action for e in load(SERVICES, "audit")(str(rig.settings.state_dir)).entries()]
    assert "key_revoked" in actions and "revoked_key_refused" in actions
    assert len(rig.provider.requests) == 1


def test_loop_guard_stops_at_the_first_repeated_failure(rig_factory: Any) -> None:
    rig = rig_factory({"features": {"loop_guard": {"mode": "enforced"}}})
    call = {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "make test"}}
    fail = {"type": "tool_result", "tool_use_id": "t1", "is_error": True, "content": "exit 2"}
    once = [
        {"role": "user", "content": "go"},
        {"role": "assistant", "content": [call]},
        {"role": "user", "content": [fail]},
    ]
    twice = [
        *once,
        {"role": "assistant", "content": [{**call, "id": "t2"}]},
        {"role": "user", "content": [{**fail, "tool_use_id": "t2"}]},
    ]
    assert post(rig, body("msg_l1", messages=once)).status_code == 200
    resp = post(rig, body("msg_l2", messages=twice))
    assert resp.status_code == 429 and resp.headers["x-token-economics-blocked"] == "repeated_failure"


def test_turn_cap_refuses_a_conversation_past_its_cap(rig_factory: Any) -> None:
    rig = rig_factory({"features": {"turn_cap": {"mode": "enforced", "default": 2}}})
    turns = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}, {"role": "user", "content": "c"}]
    assert post(rig, body("msg_c1", messages=turns)).status_code == 200
    longer = [*turns, {"role": "assistant", "content": "d"}, {"role": "user", "content": "e"}]
    resp = post(rig, body("msg_c2", messages=longer))
    assert resp.status_code == 429 and resp.headers["x-token-economics-blocked"] == "turn_cap_reached"


def test_backend_rate_limit_shows_in_gateway_health(rig_factory: Any) -> None:
    rig = rig_factory()
    post(rig, body("msg_h1", "rate_limited"))
    backend = httpx.get(f"{rig.gateway_url}/_te/health").json()["backends"]["anthropic"]
    assert backend["state"] == "rate_limited" and backend["retry_until"]


def test_no_harness_with_base_url_false_is_marked_enforced() -> None:
    # Capability matrix: every registered adapter passes the shared contract, which includes this rule
    adapters = load_all(ADAPTERS)
    assert {"claude_code", "codex", "sdk"} <= set(adapters)
    for adapter in adapters.values():
        check_adapter(adapter)
        if not adapter.capabilities.base_url:
            assert adapter.cap({"budget_usd": 1}) == {}
