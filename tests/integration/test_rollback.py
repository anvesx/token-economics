"""P3 drill: a bad optimisation is reverted without a deploy. Bad canary rows reach the ledger, auto-rollback runs, and
the next request goes to the provider byte for byte as the client sent it."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
from token_economics_contracts import (
    SERVICES,
    Buckets,
    CostSource,
    Decision,
    LedgerRow,
    RequestContext,
    Rewrite,
    canary_slot,
    load,
)
from token_economics_svc_rollout import open_rollback

HEADERS = {"user-agent": "claude-cli/2.1.330", "x-api-key": "sk-ant-api-test", "content-type": "application/json"}
ORIGINAL = (
    b'{"model": "claude-opus-5-5",  "max_tokens": 64000, "stream": true, "message_id": "msg_rb_%d",'
    b' "messages": [{"role": "user", "content": "hello"}]}'
)


class Cap:
    name, fail_closed = "max_tokens", False

    def before(self, ctx: RequestContext) -> Decision | None:
        return None

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        return None

    def rewrite(self, ctx: RequestContext, body: dict[str, Any]) -> Rewrite | None:
        return Rewrite(body={**body, "max_tokens": 8192}, changes=("max_tokens 64000->8192",))


def bad_traffic(rig: Any, n: int = 35) -> None:
    """Synthetic ledger rows: the canary sessions are expensive and failing, the control sessions are healthy."""
    ledger = load(SERVICES, "ledger")(str(rig.settings.state_dir / "ledger.sqlite"))
    inside = [s for s in (f"s{i}" for i in range(400)) if canary_slot(s, "max_tokens") < 0.5][:n]
    outside = [s for s in (f"s{i}" for i in range(400)) if canary_slot(s, "max_tokens") >= 0.5][:n]
    for i, (sid, bad) in enumerate([(s, True) for s in inside] + [(s, False) for s in outside]):
        ledger.write(
            LedgerRow(
                provider="anthropic",
                response_id=f"drill-{i}",
                ts=datetime.now(UTC) - timedelta(hours=1),
                tenant="devx",
                session_id=sid,
                model="claude-opus-5-5",
                buckets=Buckets(fresh_input=1000, output=10),
                cost_estimate_usd=Decimal("5.00" if bad else "1.00"),
                cost_source=CostSource.GATEWAY,
                price_row_id="p1",
                http_status=500 if bad else 200,
            )
        )


def test_a_rollback_drill_reverts_a_bad_optimisation_without_a_deploy(rig_factory: Any) -> None:
    # Given a rewriting feature in a canary on a running gateway, and a session inside the canary
    rig = rig_factory(
        {"features": {"max_tokens": {"mode": "enforced", "canary": {"share": 0.5}}}}, features={"max_tokens": Cap()}
    )
    url = f"{rig.gateway_url}/v1/messages"
    inside = next(f"c{i}" for i in range(50) if canary_slot(f"c{i}", "max_tokens") < 0.5)
    headers = {**HEADERS, "x-claude-code-session-id": inside}
    httpx.post(url, content=ORIGINAL % 1, headers=headers, timeout=30)
    assert json.loads(rig.provider.requests[0]["body"])["max_tokens"] == 8192
    # When bad canary rows reach the ledger and the rollback check runs
    bad_traffic(rig)
    (result,) = open_rollback(str(rig.settings.state_dir)).check()
    # Then the feature is killed, and the next request reaches the provider byte for byte as sent
    assert result["action"] == "killed"
    httpx.post(url, content=ORIGINAL % 2, headers=headers, timeout=30)
    assert rig.provider.requests[1]["body"] == ORIGINAL % 2
