import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from token_economics_contracts import Decision, KeyInfo, LedgerRow, RequestContext, Rewrite, Rewriter
from token_economics_svc_policy import PolicyService

CTX = RequestContext(request_id="r1", ts=datetime(2026, 11, 23, tzinfo=UTC), key=KeyInfo(tenant="devx", caller="dhruv"))


def decisions(tmp_path: Path) -> list[dict[str, Any]]:
    p = tmp_path / "decisions.jsonl"
    return [json.loads(line) for line in p.read_text().splitlines()] if p.exists() else []


BODY = json.dumps({"model": "claude-sonnet-5-5", "max_tokens": 64000, "messages": []}).encode()


class Capper:
    """Caps max_tokens; optionally raises or mutates its input to check the engine protects the request."""

    fail_closed = False

    def __init__(self, name: str, cap: int, boom: bool = False, mutate: bool = False) -> None:
        self.name, self.cap, self.boom, self.mutate = name, cap, boom, mutate

    def before(self, ctx: RequestContext) -> Decision | None:
        return None

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        return None

    def rewrite(self, ctx: RequestContext, body: dict[str, Any]) -> Rewrite | None:
        if self.mutate:
            body["max_tokens"] = 1
        if self.boom:
            raise ValueError("bad")
        if body.get("max_tokens", 0) <= self.cap:
            return None
        return Rewrite(
            body={**body, "max_tokens": self.cap},
            changes=(f"max_tokens {body['max_tokens']}->{self.cap}",),
            add_headers=(("anthropic-beta", "cap-1"),),
        )


def svc(tmp_path: Path, features: dict[str, Capper], modes: dict[str, str]) -> PolicyService:
    (tmp_path / "policy.json").write_text(
        json.dumps({"order": list(features), "features": {n: {"mode": m} for n, m in modes.items()}})
    )
    return PolicyService(tmp_path, factories={n: (lambda env, f=f: f) for n, f in features.items()})


def test_an_enforced_rewriter_changes_the_body_and_logs_only_the_change_note(tmp_path: Path) -> None:
    # Given an enforced feature that caps max_tokens at 8192
    s = svc(tmp_path, {"max_tokens": Capper("max_tokens", 8192)}, {"max_tokens": "enforced"})
    assert isinstance(Capper("x", 1), Rewriter)
    # When the engine rewrites a request asking for 64000
    out = s.rewrite(CTX, BODY)
    # Then the new body carries the cap and the log has the note, not the body
    assert out is not None and json.loads(out.body)["max_tokens"] == 8192
    (rec,) = decisions(tmp_path)
    assert rec["action"] == "rewritten" and rec["changes"] == ["max_tokens 64000->8192"]
    assert "messages" not in json.dumps(rec)


def test_an_advisory_rewriter_logs_what_it_would_change_and_sends_the_original(tmp_path: Path) -> None:
    s = svc(tmp_path, {"max_tokens": Capper("max_tokens", 8192)}, {"max_tokens": "advisory"})
    assert s.rewrite(CTX, BODY) is None
    assert decisions(tmp_path)[0]["action"] == "would_rewrite"


def test_no_rewrite_returns_none_so_the_original_bytes_are_sent_untouched(tmp_path: Path) -> None:
    s = svc(tmp_path, {"max_tokens": Capper("max_tokens", 100000)}, {"max_tokens": "enforced"})
    assert s.rewrite(CTX, BODY) is None and decisions(tmp_path) == []


def test_a_failing_or_mutating_rewriter_fails_open_and_cannot_corrupt_the_next_one(tmp_path: Path) -> None:
    # Given a rewriter that mutates its input and then raises, followed by a good one
    bad, good = Capper("bad", 10, boom=True, mutate=True), Capper("good", 8192)
    s = svc(tmp_path, {"bad": bad, "good": good}, {"bad": "enforced", "good": "enforced"})
    out = s.rewrite(CTX, BODY)
    # Then the bad change is dropped and the good one applies to the original body
    assert out is not None and json.loads(out.body)["max_tokens"] == 8192
    assert [r["action"] for r in decisions(tmp_path)] == ["failed_open", "rewritten"]


def test_rewrites_chain_in_policy_order(tmp_path: Path) -> None:
    s = svc(
        tmp_path,
        {"a": Capper("a", 20000), "b": Capper("b", 4096)},
        {"a": "enforced", "b": "enforced"},
    )
    out = s.rewrite(CTX, BODY)
    assert out is not None and json.loads(out.body)["max_tokens"] == 4096
    # And a header two rewriters both ask for is sent once
    assert out.add_headers == (("anthropic-beta", "cap-1"),) and out.features == ("a", "b")
    assert [r["changes"] for r in decisions(tmp_path)] == [["max_tokens 64000->20000"], ["max_tokens 20000->4096"]]


def test_a_body_that_is_not_a_json_object_is_never_rewritten(tmp_path: Path) -> None:
    s = svc(tmp_path, {"max_tokens": Capper("max_tokens", 1)}, {"max_tokens": "enforced"})
    assert s.rewrite(CTX, b"not json") is None and s.rewrite(CTX, b"[1]") is None


def test_a_broken_feature_package_breaks_only_itself(tmp_path: Path, monkeypatch: Any) -> None:
    # Given two switched-on features where one package cannot even be imported
    import token_economics_svc_policy.engine as engine

    def fake_load(group: str, name: str) -> Any:
        if name == "broken":
            raise ModuleNotFoundError("no module named broken._stub")
        return lambda env: Capper(name, 8192)

    monkeypatch.setattr(engine, "load", fake_load)
    (tmp_path / "policy.json").write_text(
        json.dumps({"features": {"broken": {"mode": "advisory"}, "max_tokens": {"mode": "enforced"}}})
    )
    s = PolicyService(tmp_path)
    # When a request is checked and rewritten
    allowed, out = s.before(CTX).allow, s.rewrite(CTX, BODY)
    # Then the broken one is reported and fails open (advisory), and the good one still works
    assert allowed and out is not None and json.loads(out.body)["max_tokens"] == 8192
    assert any(p.startswith("broken:") for p in s.problems)
