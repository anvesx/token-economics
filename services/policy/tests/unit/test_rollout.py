import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from token_economics_contracts import (
    Decision,
    Identity,
    KeyInfo,
    KillEntry,
    KillFile,
    LedgerRow,
    RequestContext,
    Rewrite,
    canary_slot,
)
from token_economics_svc_policy import PolicyService

BODY = json.dumps({"model": "claude-sonnet-5-5", "max_tokens": 64000, "messages": []}).encode()


def ctx(tenant: str = "devx", session: str = "s1") -> RequestContext:
    return RequestContext(
        request_id="r1",
        ts=datetime(2026, 11, 23, tzinfo=UTC),
        key=KeyInfo(tenant=tenant),
        identity=Identity(session_id=session),
    )


class Cap:
    name, fail_closed = "max_tokens", False

    def before(self, ctx: RequestContext) -> Decision | None:
        return None

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        return None

    def rewrite(self, ctx: RequestContext, body: dict[str, Any]) -> Rewrite | None:
        return Rewrite(body={**body, "max_tokens": 8192}, changes=("max_tokens 64000->8192",))


def svc(tmp_path: Path, section: dict[str, Any]) -> PolicyService:
    (tmp_path / "policy.json").write_text(json.dumps({"features": {"max_tokens": section}}))
    return PolicyService(tmp_path, factories={"max_tokens": lambda env: Cap()})


def kill(tmp_path: Path, *entries: KillEntry) -> None:
    path = tmp_path / "kill.json"
    path.write_text(KillFile(kills=entries).model_dump_json())
    os.utime(path, ns=(path.stat().st_mtime_ns + 1_000_000, path.stat().st_mtime_ns + 1_000_000))


def test_a_kill_switch_turns_a_feature_off_for_one_tenant_without_a_restart(tmp_path: Path) -> None:
    # Given an enforced rewrite that applies to every tenant
    s = svc(tmp_path, {"mode": "enforced"})
    assert s.rewrite(ctx("acme"), BODY) is not None
    # When acme's switch is killed in kill.json
    kill(tmp_path, KillEntry(feature="max_tokens", tenant="acme", by="cli:test"))
    # Then acme's requests go out untouched and devx is unaffected
    assert s.rewrite(ctx("acme"), BODY) is None
    assert s.rewrite(ctx("devx"), BODY) is not None
    # And a kill for "*" turns it off for everyone; removing it turns it back on
    kill(tmp_path, KillEntry(feature="max_tokens", tenant="*"))
    assert s.rewrite(ctx("devx"), BODY) is None
    kill(tmp_path)
    assert s.rewrite(ctx("devx"), BODY) is not None


def test_a_broken_kill_file_means_no_kills_and_is_logged(tmp_path: Path) -> None:
    s = svc(tmp_path, {"mode": "enforced"})
    (tmp_path / "kill.json").write_text("{not json")
    assert s.rewrite(ctx(), BODY) is not None
    assert "config_error" in (tmp_path / "decisions.jsonl").read_text()


def test_a_tenant_mode_overrides_the_section_mode(tmp_path: Path) -> None:
    # Given off by default, enforced for devx, advisory for acme
    s = svc(tmp_path, {"mode": "off", "tenants": {"devx": "enforced", "acme": "advisory"}})
    assert s.rewrite(ctx("devx"), BODY) is not None
    assert s.rewrite(ctx("acme"), BODY) is None and s.rewrite(ctx("other"), BODY) is None
    actions = [json.loads(x)["action"] for x in (tmp_path / "decisions.jsonl").read_text().splitlines()]
    assert actions == ["rewritten", "would_rewrite"]


def test_a_canary_covers_whole_sessions_below_its_share_and_logs_them(tmp_path: Path) -> None:
    # Given a 30% canary
    s = svc(tmp_path, {"mode": "enforced", "canary": {"share": 0.3}})
    sessions = [f"s{i}" for i in range(400)]
    # When each session sends two requests
    hit = [sid for sid in sessions if s.rewrite(ctx(session=sid), BODY) is not None]
    again = [sid for sid in sessions if s.rewrite(ctx(session=sid), BODY) is not None]
    # Then the same sessions get it both times, they are exactly those below the share, and about 30% of all
    assert hit == again == [sid for sid in sessions if canary_slot(sid, "max_tokens") < 0.3]
    assert 0.22 < len(hit) / len(sessions) < 0.38
    assert all(json.loads(x).get("canary") for x in (tmp_path / "decisions.jsonl").read_text().splitlines())


def test_a_canary_limited_to_tenants_leaves_others_off(tmp_path: Path) -> None:
    s = svc(tmp_path, {"mode": "enforced", "canary": {"share": 1.0, "tenants": ["devx"]}})
    assert s.rewrite(ctx("devx"), BODY) is not None and s.rewrite(ctx("acme"), BODY) is None


def test_an_unreadable_canary_share_covers_nobody(tmp_path: Path) -> None:
    s = svc(tmp_path, {"mode": "enforced", "canary": {"share": "lots"}})
    assert all(s.rewrite(ctx(session=f"s{i}"), BODY) is None for i in range(50))


def test_rollout_keys_are_not_passed_to_the_feature(tmp_path: Path) -> None:
    seen: dict[str, Any] = {}

    def factory(env: Any) -> Cap:
        seen.update(env.config)
        return Cap()

    (tmp_path / "policy.json").write_text(
        json.dumps({"features": {"max_tokens": {"mode": "enforced", "tenants": {}, "canary": {}, "default": 1}}})
    )
    PolicyService(tmp_path, factories={"max_tokens": factory}).rewrite(ctx(), BODY)
    assert seen == {"default": 1}
