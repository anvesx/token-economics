"""P3 security: nothing secret or from a prompt reaches disk (plan/08 log redaction), and admin tokens are hashed."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx
from token_economics_contracts import Decision, LedgerRow, RequestContext, Rewrite
from token_economics_redaction import scan_for_content
from token_economics_svc_policy import PolicyService
from token_economics_svc_rollout import Shadow
from token_economics_svc_tenancy import AdminAuth, open_admin_auth

PROMPT = "prompt-text-SECRET-that-must-never-be-stored"
SYSTEM_TEXT = "system-prompt-SECRET-text-never-stored"
API_KEY = "sk-ant-api-SECRET-provider-key-0123456789"
OAUTH = "oat-SECRET-subscription-token-0123456789"
VIRTUAL_KEY = "vk-dev-1"  # the rig's key; it is imported into the hashed store at start-up
UNISSUED_KEY = "vk-never-issued-SECRET-0123456789"


class Cap:
    """A rewriter, so the decision log and the shadow pair log both get lines."""

    name, fail_closed = "max_tokens", False

    def before(self, ctx: RequestContext) -> Decision | None:
        return None

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        return None

    def rewrite(self, ctx: RequestContext, body: dict[str, Any]) -> Rewrite | None:
        return Rewrite(body={**body, "max_tokens": 1024}, changes=("max_tokens 4096->1024",))


def request_body(message_id: str, scenario: str = "stream") -> bytes:
    return json.dumps(
        {
            "model": "claude-opus-5-5",
            "max_tokens": 4096,
            "stream": True,
            "scenario": scenario,
            "message_id": message_id,
            "system": SYSTEM_TEXT,
            "metadata": {"user_id": "user_x_account__session_11111111-2222-3333-4444-555555555555"},
            "messages": [{"role": "user", "content": PROMPT}],
        }
    ).encode()


def headers(**extra: str) -> dict[str, str]:
    return {
        "user-agent": "claude-cli/2.1.330",
        "content-type": "application/json",
        "x-token-economics-key": VIRTUAL_KEY,
        "x-api-key": API_KEY,
        "authorization": f"Bearer {OAUTH}",
        **extra,
    }


def state_files(state: Path) -> list[Path]:
    return sorted(p for p in state.rglob("*") if p.is_file())


def test_no_secret_or_prompt_text_is_in_any_file_the_gateway_wrote(rig_factory: Any) -> None:
    # Given a gateway with an enforced rewriting feature and a shadow run at 100% sampling
    holder: dict[str, Any] = {}

    def shadow_parts(state: Path) -> dict[str, Any]:
        if not holder:
            folder = state / "shadow"
            folder.mkdir()
            (folder / "shadow.json").write_text(json.dumps({"enabled": True, "share": 1.0}))
            (folder / "policy.json").write_text(json.dumps({"features": {"max_tokens": {"mode": "enforced"}}}))
            holder["shadow"] = Shadow(state)
            holder["shadow_policy"] = PolicyService(folder, factories={"max_tokens": lambda env: Cap()})
        return holder

    rig = rig_factory(
        {"features": {"max_tokens": {"mode": "enforced"}}},
        features={"max_tokens": Cap()},
        app_kw={
            "shadow": lambda s: shadow_parts(s)["shadow"],
            "shadow_policy": lambda s: shadow_parts(s)["shadow_policy"],
        },
    )
    state = rig.settings.state_dir
    # When requests carry a provider key, an OAuth token, the virtual key and prompt text: a good one, one the
    # normaliser rejects (rejects.jsonl), and one with a virtual key that was never issued
    ok = httpx.post(f"{rig.gateway_url}/v1/messages", content=request_body("msg_sec_1"), headers=headers(), timeout=30)
    httpx.post(
        f"{rig.gateway_url}/v1/messages",
        content=request_body("msg_sec_2", "unknown_key"),
        headers=headers(),
        timeout=30,
    )
    httpx.post(
        f"{rig.gateway_url}/v1/messages",
        content=request_body("msg_sec_3"),
        headers=headers(**{"x-token-economics-key": UNISSUED_KEY}),
        timeout=30,
    )
    rig.wait_idle("unknown_usage_key")
    deadline = time.time() + 10
    while time.time() < deadline and not (state / "shadow" / "pairs.jsonl").exists():
        time.sleep(0.05)
    time.sleep(0.3)  # let the mirrored run finish writing
    assert ok.status_code == 200
    # Then the log files exist (so the scan is not vacuous) ...
    names = {p.name for p in state_files(state)}
    assert {"ledger.sqlite", "tenancy.sqlite", "decisions.jsonl", "rejects.jsonl", "pairs.jsonl"} <= names
    # ... and none of them, the ledger, the key store, the audit log or the shadow files included, holds a secret
    needles = [PROMPT, SYSTEM_TEXT, API_KEY, OAUTH, VIRTUAL_KEY, UNISSUED_KEY, "SECRET"]
    assert scan_for_content([state], needles) == []


def test_admin_tokens_are_stored_hashed_and_a_revoked_token_is_refused(tmp_path: Path) -> None:
    # Given an admin token
    auth: AdminAuth = open_admin_auth(str(tmp_path))
    plaintext, token_id = auth.issue("ann", "admin", actor="cli")
    # Then the database holds only the digest, not the token or the hex of its digest
    import hashlib

    assert scan_for_content([tmp_path], [plaintext, hashlib.sha256(plaintext.encode()).hexdigest()]) == []
    assert auth.resolve(plaintext) is not None
    # When it is revoked Then it is refused at once, by this handle and by a new one
    assert auth.revoke(token_id, actor="cli") is True
    assert auth.resolve(plaintext) is None
    assert open_admin_auth(str(tmp_path)).resolve(plaintext) is None
    # And the audit log records who issued and revoked it, never the token
    assert scan_for_content([tmp_path], [plaintext]) == []
