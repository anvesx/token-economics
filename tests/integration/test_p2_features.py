"""Every P2 feature, loaded through its entry point, switched on together and sent through the real gateway."""

from __future__ import annotations

import json
from typing import Any

import httpx

HEADERS = {
    "user-agent": "claude-cli/2.1.330",
    "x-api-key": "sk-ant-api-test",
    "content-type": "application/json",
    "x-token-economics-key": "vk-dev-1",
}
ALL = [
    "rules_router",
    "sticky_model",
    "max_tokens",
    "output_cap",
    "observation_masking",
    "context_clearing",
    "schema_deferral",
    "compaction_guard",
    "cache_planner",
    "cache_hit_monitor",
]


def policy(mode: str) -> dict[str, Any]:
    sections: dict[str, Any] = {n: {"mode": mode} for n in ALL}
    sections["max_tokens"]["default"] = 8192
    sections["output_cap"]["limit_tokens"] = 1000
    sections["rules_router"]["rules"] = [{"when": {"caller": "dhruv"}, "model": "claude-sonnet-5-5"}]
    return {"order": ALL, "features": sections}


def heavy_body(message_id: str, turns: int = 16) -> bytes:
    names = ["Bash", "Read"] + [f"mcp__srv__t{i}" for i in range(30)]  # core tools stay loaded
    tools = [{"name": n, "description": "d", "input_schema": {"type": "object"}} for n in names]
    messages: list[dict[str, Any]] = [{"role": "user", "content": "start"}]
    for i in range(turns):
        messages.append(
            {"role": "assistant", "content": [{"type": "tool_use", "id": f"tu{i}", "name": "Bash", "input": {}}]}
        )
        messages.append(
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": f"tu{i}", "content": "x" * 9000}]}
        )
    return json.dumps(
        {
            "model": "claude-opus-5-5",
            "max_tokens": 64000,
            "stream": True,
            "message_id": message_id,
            "metadata": {"user_id": "user_x_account__session_11111111-2222-3333-4444-555555555555"},
            "tools": tools,
            "messages": messages,
        }
    ).encode()


def test_all_p2_features_enforced_together_rewrite_one_request_and_it_still_succeeds(rig_factory: Any) -> None:
    # Given every P2 feature enforced, loaded by entry point
    rig = rig_factory(policy("enforced"))
    # When a Claude Code conversation starts, then sends a heavy turn 16
    url = f"{rig.gateway_url}/v1/messages"
    assert httpx.post(url, content=heavy_body("msg_p2_start", turns=0), headers=HEADERS, timeout=30).status_code == 200
    resp = httpx.post(url, content=heavy_body("msg_p2_all"), headers=HEADERS, timeout=30)
    rig.wait_idle("rows")
    # Then it succeeds, every rewriter changed the body (the turn-0 route is kept) and the policy shows no problem
    assert resp.status_code == 200
    sent = json.loads(rig.provider.requests[1]["body"])
    assert sent["model"] == "claude-sonnet-5-5" and sent["max_tokens"] == 8192
    assert "context_management" in sent and any(t.get("defer_loading") for t in sent["tools"])
    results = [
        b
        for m in sent["messages"]
        if isinstance(m["content"], list)
        for b in m["content"]
        if b["type"] == "tool_result"
    ]
    assert any("masked" in str(b["content"]) for b in results)
    assert any("removed" in str(b["content"]) for b in results)
    health = httpx.get(f"{rig.gateway_url}/_te/health").json()
    assert health["policy_problems"] == []
    log = [json.loads(x) for x in (rig.settings.state_dir / "decisions.jsonl").read_text().splitlines()]
    assert {r["feature"] for r in log if r["action"] == "rewritten"} >= {
        "rules_router", "max_tokens", "output_cap", "observation_masking", "context_clearing", "schema_deferral",
    }  # fmt: skip
    assert "x" * 100 not in json.dumps(log)  # no tool text in the log


def test_all_p2_features_advisory_send_the_original_bytes(rig_factory: Any) -> None:
    rig = rig_factory(policy("advisory"))
    original = heavy_body("msg_p2_adv")
    resp = httpx.post(f"{rig.gateway_url}/v1/messages", content=original, headers=HEADERS, timeout=30)
    assert resp.status_code == 200 and rig.provider.requests[0]["body"] == original
