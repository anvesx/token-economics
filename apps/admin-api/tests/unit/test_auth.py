from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("httpx", reason="Starlette's TestClient needs httpx (the `test` extra)")
tenancy = pytest.importorskip("token_economics_svc_tenancy", reason="the tenancy service is not installed")

from starlette.testclient import TestClient  # noqa: E402
from token_economics_app_admin_api import create_app  # noqa: E402
from token_economics_contracts import load  # noqa: E402

DIRECT = {
    "admin_auth": tenancy.open_admin_auth,
    "changes": tenancy.open_changes,
    "audit": tenancy.open_audit,
    "keys": tenancy.open_keys,
}
POLICY = {"features": {"max_tokens": {"mode": "advisory"}}}


def loader(group: str, name: str) -> Any:
    if name in DIRECT:  # direct, so the tests do not depend on the entry points having been synced
        return DIRECT[name]
    return load(group, name)


def make(state: Path, *, require_auth: bool = False) -> TestClient:
    return TestClient(create_app(state, loader, require_auth=require_auth))


def tokens(state: Path) -> dict[str, str]:
    auth = tenancy.open_admin_auth(str(state))
    out = {role: auth.issue(f"{role}-user", role, actor="test")[0] for role in ("viewer", "operator", "admin")}
    out["admin2"] = auth.issue("second-admin", "admin", actor="test")[0]
    auth.close()
    return out


def bearer(token: str | None) -> dict[str, str]:
    return {} if token is None else {"Authorization": f"Bearer {token}"}


def call(c: TestClient, method: str, path: str, token: str | None, body: Any = None) -> Any:
    kw: dict[str, Any] = {"headers": bearer(token)}
    if body is not None:
        kw["json"] = body
    return c.request(method, path, **kw)


# Every protected route with the lowest role that may use it, and a body that is valid for it.
ROUTES: list[tuple[str, str, str, Any]] = [
    ("GET", "/api/keys", "viewer", None),
    ("GET", "/api/decisions", "viewer", None),
    ("GET", "/api/kills", "viewer", None),
    ("GET", "/api/audit", "viewer", None),
    ("GET", "/api/changes", "viewer", None),
    ("POST", "/api/kills", "operator", {"feature": "max_tokens", "tenant": "acme", "reason": "test"}),
    ("DELETE", "/api/kills", "operator", {"feature": "max_tokens", "tenant": "acme"}),
    ("POST", "/api/changes", "admin", {"kind": "policy", "payload": POLICY}),
    ("POST", "/api/changes/chg-none/approve", "admin", None),
    ("POST", "/api/changes/chg-none/reject", "admin", None),
    ("GET", "/api/admin-tokens", "admin", None),
    ("POST", "/api/admin-tokens", "admin", {"name": "newbie", "role": "viewer"}),
    ("DELETE", "/api/admin-tokens/0000000000000000", "admin", None),
]
RANK = {"viewer": 0, "operator": 1, "admin": 2}


@pytest.mark.parametrize(("method", "path", "need", "body"), ROUTES)
def test_every_route_by_role(tmp_path: Path, method: str, path: str, need: str, body: Any) -> None:
    # Given tokens of every role
    toks = tokens(tmp_path)
    c = make(tmp_path)
    # When the route is called with no token, a made-up one, and each role
    # Then no or a bad token is 401 and a role below the need is 403, whatever the body
    assert call(c, method, path, None, body).status_code == 401
    assert call(c, method, path, "adm-made-up", body).status_code == 401
    for role in ("viewer", "operator", "admin"):
        got = call(c, method, path, toks[role], body).status_code
        if RANK[role] < RANK[need]:
            assert got == 403, (role, got)
        else:
            assert got not in (401, 403), (role, got)  # allowed: 200/201, or 404/409 for an unknown id


def test_without_tokens_it_is_the_local_read_only_dashboard(tmp_path: Path) -> None:
    # Given no admin token and no --require-auth
    c = make(tmp_path)
    # Then reads work without a token and every write route is refused
    for path in ("/api/keys", "/api/decisions", "/api/kills", "/api/audit", "/api/changes"):
        assert c.get(path).status_code == 200, path
    assert c.get("/").status_code == 200
    for method, path, _need, body in ROUTES:
        if method != "GET":
            assert call(c, method, path, None, body).status_code == 403, path
    assert not (tmp_path / "policy.json").exists() and not (tmp_path / "kill.json").exists()


def test_require_auth_with_no_tokens_refuses_everything_under_api(tmp_path: Path) -> None:
    c = make(tmp_path, require_auth=True)
    assert c.get("/api/keys").status_code == 401
    assert c.get("/").status_code == 200  # the static page holds no data


def test_revoking_every_token_does_not_reopen_the_api(tmp_path: Path) -> None:
    # Given one admin token that is then revoked
    auth = tenancy.open_admin_auth(str(tmp_path))
    plaintext, token_id = auth.issue("only", "admin", actor="test")
    auth.revoke(token_id, actor="test")
    c = make(tmp_path)
    # Then the revoked token is refused and so is a request with none
    assert call(c, "GET", "/api/keys", plaintext).status_code == 401
    assert call(c, "GET", "/api/keys", None).status_code == 401


def test_kill_switch_add_and_remove_are_attributed_to_the_admin(tmp_path: Path) -> None:
    # Given an operator
    toks = tokens(tmp_path)
    c = make(tmp_path)
    # When they switch a feature off and on again
    assert call(c, "POST", "/api/kills", toks["operator"], {"feature": "max_tokens", "tenant": "acme"}).json() == {
        "changed": True
    }
    assert call(c, "POST", "/api/kills", toks["operator"], {"feature": "max_tokens", "tenant": "acme"}).json() == {
        "changed": False
    }
    listed = call(c, "GET", "/api/kills", toks["viewer"]).json()
    # Then kill.json names them, and the audit log has both changes
    assert [(k["feature"], k["tenant"], k["by"]) for k in listed] == [("max_tokens", "acme", "admin:operator-user")]
    assert call(c, "DELETE", "/api/kills", toks["operator"], {"feature": "max_tokens", "tenant": "acme"}).json() == {
        "changed": True
    }
    actions = [(e["action"], e["actor"]) for e in call(c, "GET", "/api/audit", toks["viewer"]).json()]
    assert ("kill_switch_on", "admin:operator-user") in actions and (
        "kill_switch_off",
        "admin:operator-user",
    ) in actions


def test_bad_kill_bodies_are_400(tmp_path: Path) -> None:
    toks = tokens(tmp_path)
    c = make(tmp_path)
    for body in ({}, {"feature": ""}, {"feature": 3}, {"feature": "x", "reason": "vk-abc"}, [1]):
        assert call(c, "POST", "/api/kills", toks["operator"], body).status_code == 400, body
    assert c.post("/api/kills", content=b"{not json", headers=bearer(toks["operator"])).status_code == 400


def test_policy_change_needs_a_second_admin_and_applies_once(tmp_path: Path) -> None:
    # Given two admins, one of whom proposes a policy
    toks = tokens(tmp_path)
    c = make(tmp_path)
    made = call(c, "POST", "/api/changes", toks["admin"], {"kind": "policy", "payload": POLICY})
    assert made.status_code == 201
    cid = made.json()["change_id"]
    # When the proposer approves their own change Then it is refused and policy.json is not written
    assert call(c, "POST", f"/api/changes/{cid}/approve", toks["admin"]).status_code == 403
    assert not (tmp_path / "policy.json").exists()
    # When the second admin approves Then it is applied
    done = call(c, "POST", f"/api/changes/{cid}/approve", toks["admin2"])
    assert done.status_code == 200 and done.json()["applied"] is True
    assert json.loads((tmp_path / "policy.json").read_text()) == POLICY
    # And approving again is a conflict, and so is rejecting it
    assert call(c, "POST", f"/api/changes/{cid}/approve", toks["admin2"]).status_code == 409
    assert call(c, "POST", f"/api/changes/{cid}/reject", toks["admin2"]).status_code == 409
    assert call(c, "POST", "/api/changes/chg-unknown/approve", toks["admin2"]).status_code == 404
    listed = call(c, "GET", "/api/changes", toks["viewer"]).json()
    assert [(x["status"], x["proposer"], x["decided_by"]) for x in listed] == [
        ("approved", "admin-user", "second-admin")
    ]


def test_rejected_change_is_not_applied(tmp_path: Path) -> None:
    toks = tokens(tmp_path)
    c = make(tmp_path)
    cid = call(c, "POST", "/api/changes", toks["admin"], {"kind": "policy", "payload": POLICY}).json()["change_id"]
    assert call(c, "POST", f"/api/changes/{cid}/reject", toks["admin2"]).json()["status"] == "rejected"
    assert call(c, "POST", f"/api/changes/{cid}/approve", toks["admin2"]).status_code == 409
    assert not (tmp_path / "policy.json").exists()


def test_bad_change_proposals_are_400(tmp_path: Path) -> None:
    toks = tokens(tmp_path)
    c = make(tmp_path)
    for body in ({}, {"kind": "policy"}, {"kind": "code", "payload": {"a": 1}}, {"kind": "policy", "payload": {}}):
        assert call(c, "POST", "/api/changes", toks["admin"], body).status_code == 400, body


def test_tokens_never_appear_in_responses_or_logs(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    # Given an admin and every kind of request, including refused ones, with the token in the header
    caplog.set_level(logging.DEBUG)
    toks = tokens(tmp_path)
    c = make(tmp_path)
    seen: list[str] = []
    for method, path, _need, body in ROUTES:
        for token in (None, "adm-wrong-token-value", toks["viewer"], toks["admin"]):
            r = call(c, method, path, token, body)
            seen.append(r.text + json.dumps(dict(r.headers)))
    issued = call(c, "POST", "/api/admin-tokens", toks["admin"], {"name": "fresh", "role": "viewer"}).json()
    # Then no response echoes a presented token; only the issue response carries the new one, once
    secrets_ = [*toks.values(), "adm-wrong-token-value"]
    assert not [s for s in seen for t in secrets_ if t in s]
    assert issued["token"].startswith("adm-")
    assert issued["token"] not in "".join(call(c, "GET", "/api/admin-tokens", toks["admin"]).text for _ in "x")
    assert issued["token"] not in "".join(call(c, "GET", "/api/audit", toks["admin"]).text for _ in "x")
    # And none is in the logs or on disk
    assert not [t for t in [*secrets_, issued["token"]] if t in caplog.text]
    on_disk = b"".join(p.read_bytes() for p in tmp_path.rglob("*") if p.is_file())
    assert not [t for t in [*secrets_, issued["token"]] if t.encode() in on_disk]


def test_issued_token_works_and_revocation_takes_effect_at_once(tmp_path: Path) -> None:
    toks = tokens(tmp_path)
    c = make(tmp_path)
    issued = call(c, "POST", "/api/admin-tokens", toks["admin"], {"name": "temp", "role": "viewer"}).json()
    assert call(c, "GET", "/api/keys", issued["token"]).status_code == 200
    assert call(c, "DELETE", f"/api/admin-tokens/{issued['token_id']}", toks["admin"]).json() == {"revoked": True}
    assert call(c, "GET", "/api/keys", issued["token"]).status_code == 401
    assert call(c, "POST", "/api/admin-tokens", toks["admin"], {"name": "temp", "role": "viewer"}).status_code == 400
    assert call(c, "POST", "/api/admin-tokens", toks["admin"], {"name": "x", "role": "root"}).status_code == 400


def test_missing_kill_service_is_a_503_not_a_crash(tmp_path: Path) -> None:
    toks = tokens(tmp_path)

    def no_kill(group: str, name: str) -> Any:
        if name == "kill":
            raise LookupError(name)
        return loader(group, name)

    c = TestClient(create_app(tmp_path, no_kill))
    assert call(c, "POST", "/api/kills", toks["operator"], {"feature": "f"}).status_code == 503
    assert call(c, "GET", "/api/kills", toks["viewer"]).status_code == 503


def test_listening_off_localhost_without_require_auth_refuses_to_start(monkeypatch: Any, tmp_path: Any) -> None:
    # Given a non-local host and no --require-auth
    from token_economics_app_admin_api.__main__ import main

    monkeypatch.setenv("TOKEN_ECONOMICS_STATE_DIR", str(tmp_path))
    started: list[Any] = []
    monkeypatch.setattr("uvicorn.run", lambda *a, **k: started.append(a))
    # When the admin app starts / Then it exits with an error and never serves
    assert main(["--host", "0.0.0.0"]) == 2 and started == []
