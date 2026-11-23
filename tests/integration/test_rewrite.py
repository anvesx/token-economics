"""P2 request rewrites end to end: an enforced feature changes the body the provider receives; off sends bytes as-is."""

from __future__ import annotations

import json
from typing import Any

import httpx
from token_economics_contracts import Decision, LedgerRow, RequestContext, Rewrite

HEADERS = {"user-agent": "claude-cli/2.1.330", "x-api-key": "sk-ant-api-test", "content-type": "application/json"}
# Odd spacing on purpose: a body re-serialised by the gateway would not match these bytes.
ORIGINAL = (
    b'{"model": "claude-opus-5-5",  "max_tokens": 64000, "stream": true, "message_id": "msg_rw_%d",'
    b' "messages": [{"role": "user", "content": "hello"}]}'
)


class Cap:
    name, fail_closed = "max_tokens", False

    def before(self, ctx: RequestContext) -> Decision | None:
        return None

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        return None

    def rewrite(self, ctx: RequestContext, body: dict[str, Any]) -> Rewrite | None:
        return Rewrite(
            body={**body, "max_tokens": 8192},
            changes=("max_tokens 64000->8192",),
            add_headers=(("anthropic-beta", "context-management-2025-06-27"),),
        )


def run(rig_factory: Any, mode: str, n: int) -> tuple[Any, httpx.Response]:
    rig = rig_factory({"features": {"max_tokens": {"mode": mode}}}, features={"max_tokens": Cap()})
    resp = httpx.post(f"{rig.gateway_url}/v1/messages", content=ORIGINAL % n, headers=HEADERS, timeout=30)
    rig.wait_idle("rows")
    return rig.provider, resp


def test_an_enforced_rewrite_reaches_the_provider_with_a_correct_length(rig_factory: Any) -> None:
    # Given an enforced feature that caps max_tokens
    provider, resp = run(rig_factory, "enforced", 1)
    # Then the provider got the capped body with a content-length that matches it, and the reply streamed back
    (got,) = provider.requests
    assert resp.status_code == 200 and json.loads(got["body"])["max_tokens"] == 8192
    lengths = [v for k, v in got["headers"] if k.lower() == "content-length"]
    assert lengths == [str(len(got["body"]))]
    # And the header the rewrite asked for was added to the client's own
    assert ("anthropic-beta", "context-management-2025-06-27") in got["headers"]


def test_with_the_feature_advisory_or_off_the_provider_gets_the_original_bytes(rig_factory: Any) -> None:
    for i, mode in enumerate(("advisory", "off")):
        provider, resp = run(rig_factory, mode, 10 + i)
        assert resp.status_code == 200 and provider.requests[0]["body"] == ORIGINAL % (10 + i)


def test_a_killed_feature_sends_the_original_bytes_without_a_restart(rig_factory: Any) -> None:
    # Given an enforced rewrite on a running gateway
    rig = rig_factory({"features": {"max_tokens": {"mode": "enforced"}}}, features={"max_tokens": Cap()})
    url = f"{rig.gateway_url}/v1/messages"
    httpx.post(url, content=ORIGINAL % 20, headers=HEADERS, timeout=30)
    # When the kill switch is written (as the CLI or auto-rollback would)
    (rig.settings.state_dir / "kill.json").write_text(json.dumps({"kills": [{"feature": "max_tokens"}]}))
    httpx.post(url, content=ORIGINAL % 21, headers=HEADERS, timeout=30)
    # Then the next request reaches the provider byte for byte as the client sent it
    first, second = rig.provider.requests
    assert json.loads(first["body"])["max_tokens"] == 8192 and second["body"] == ORIGINAL % 21
