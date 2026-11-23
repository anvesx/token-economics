"""P2 shadow runs end to end: a sampled request is mirrored through the candidate policy with write isolation."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx
from token_economics_contracts import Decision, LedgerRow, RequestContext, Rewrite
from token_economics_svc_ledger import SqliteLedger
from token_economics_svc_policy import PolicyService
from token_economics_svc_rollout import Shadow

HEADERS = {
    "user-agent": "claude-cli/2.1.330",
    "x-api-key": "sk-ant-api-test",
    "content-type": "application/json",
    "x-token-economics-key": "vk-dev-1",
}


class Cap:
    name, fail_closed = "max_tokens", False

    def before(self, ctx: RequestContext) -> Decision | None:
        return None

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        return None

    def rewrite(self, ctx: RequestContext, body: dict[str, Any]) -> Rewrite | None:
        return Rewrite(body={**body, "max_tokens": 1024}, changes=("max_tokens 4096->1024",))


def shadow_parts(state: Path) -> dict[str, Any]:
    folder = state / "shadow"
    folder.mkdir()
    (folder / "shadow.json").write_text(json.dumps({"enabled": True, "share": 1.0}))
    (folder / "policy.json").write_text(json.dumps({"features": {"max_tokens": {"mode": "enforced"}}}))
    return {
        "shadow": Shadow(state),
        "shadow_policy": PolicyService(folder, factories={"max_tokens": lambda env: Cap()}),
    }


def body(message_id: str) -> bytes:
    return json.dumps(
        {
            "model": "claude-opus-5-5",
            "max_tokens": 4096,
            "stream": True,
            "message_id": message_id,
            "metadata": {"user_id": "user_x_account__session_11111111-2222-3333-4444-555555555555"},
            "messages": [{"role": "user", "content": "hello"}],
        }
    ).encode()


def pairs(state: Path, n: int, timeout: float = 10.0) -> list[dict[str, Any]]:
    path = state / "shadow" / "pairs.jsonl"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.exists() and len(path.read_text().splitlines()) >= n:
            break
        time.sleep(0.05)
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def test_a_sampled_request_is_mirrored_through_the_candidate_with_write_isolation(rig_factory: Any) -> None:
    # Given shadow sampling at 100% with a candidate policy that caps max_tokens, and no policy on the primary
    parts: dict[str, Any] = {}

    def part(name: str) -> Any:
        def make(state: Path) -> Any:
            if not parts:
                parts.update(shadow_parts(state))
            return parts[name]

        return make

    rig = rig_factory({"features": {}}, app_kw={"shadow": part("shadow"), "shadow_policy": part("shadow_policy")})
    state = rig.settings.state_dir
    # When a client sends one request
    resp = httpx.post(f"{rig.gateway_url}/v1/messages", content=body("msg_shadow_1"), headers=HEADERS, timeout=30)
    recs = pairs(state, 2)
    # Then the client got the primary answer, the provider saw the original and the capped mirror
    assert resp.status_code == 200
    got = sorted(json.loads(r["body"])["max_tokens"] for r in rig.provider.requests)
    assert got == [1024, 4096]
    # And the primary ledger has one row, the shadow ledger has its own, and both sides are reported as a pair
    assert len(list(SqliteLedger(rig.settings.ledger_path).rows())) == 1
    assert len(list(SqliteLedger(state / "shadow" / "ledger.sqlite").rows())) == 1
    assert sorted(r["side"] for r in recs) == ["primary", "shadow"]
    report = parts["shadow"].report()
    assert report["pairs"] == 1 and report["status_mismatches"] == 0
