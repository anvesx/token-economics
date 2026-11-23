import json
import stat
from decimal import Decimal
from pathlib import Path

import pytest
from token_economics_contracts import SERVICES, Buckets, CostSource, LedgerRow, load
from token_economics_svc_eval import ClaudeCodeRunner, HarnessConfigError, LedgerCostReader


def test_claude_code_runner_refuses_a_user_settings_file_that_pins_the_base_url(tmp_path: Path) -> None:
    # Given ~/.claude/settings.json with env.ANTHROPIC_BASE_URL
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"env": {"ANTHROPIC_BASE_URL": "https://example.test"}}))
    # When preflight runs Then it says why the arm gateway would be skipped
    with pytest.raises(HarnessConfigError, match="overrides the shell variable"):
        ClaudeCodeRunner(settings_path=settings).preflight()
    ClaudeCodeRunner(settings_path=tmp_path / "missing.json").preflight()  # nothing to override: fine


def test_claude_code_runner_closes_stdin_sets_the_gateway_and_keeps_only_the_session_id(tmp_path: Path) -> None:
    # Given a fake `claude` that reports its stdin, base url and arguments in a log and replies with JSON
    log = tmp_path / "log.json"
    fake = tmp_path / "claude"
    fake.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        f"json.dump({{'stdin': sys.stdin.read(), 'base': os.environ['ANTHROPIC_BASE_URL'], 'argv': sys.argv[1:],"
        f" 'effort': os.environ.get('EFFORT')}}, open({str(log)!r}, 'w'))\n"
        "print(json.dumps({'session_id': 'reported-id', 'result': 'SECRET REPLY'}))\n"
    )
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    # When run
    res = ClaudeCodeRunner(["--x"], settings_path=tmp_path / "none", command=str(fake)).run(
        "do it", tmp_path, "http://gw", {"EFFORT": "low"}, 30, "sess-1"
    )
    # Then stdin was empty, the gateway and env were set, and only the session id came back
    seen = json.loads(log.read_text())
    assert seen["stdin"] == "" and seen["base"] == "http://gw" and seen["effort"] == "low"
    assert seen["argv"][:4] == ["-p", "do it", "--output-format", "json"] and "--x" in seen["argv"]
    assert res.session_id == "reported-id" and res.error == "" and "SECRET" not in repr(res)


def test_claude_code_runner_reports_a_timeout_with_the_session_it_chose(tmp_path: Path) -> None:
    fake = tmp_path / "claude"
    fake.write_text("#!/bin/sh\nsleep 5\n")
    fake.chmod(0o755)
    res = ClaudeCodeRunner(settings_path=tmp_path / "none", command=str(fake)).run(
        "p", tmp_path, "u", {}, 0.2, "sess-2"
    )
    assert res.error == "timeout" and res.session_id == "sess-2"


def test_ledger_cost_reader_sums_one_session_and_lists_features_that_rewrote(tmp_path: Path) -> None:
    try:
        ledger = load(SERVICES, "ledger")(str(tmp_path / "ledger.sqlite"))
    except LookupError:
        pytest.skip("ledger service not installed")
    from datetime import UTC, datetime

    def row(rid: str, session: str, cost: str | None) -> LedgerRow:
        return LedgerRow(
            provider="anthropic",
            response_id=rid,
            ts=datetime.now(UTC),
            session_id=session,
            model="m",
            buckets=Buckets(fresh_input=100, output=10),
            cost_estimate_usd=None if cost is None else Decimal(cost),
            cost_source=CostSource.GATEWAY,
            price_row_id="" if cost is None else "p1",
        )

    # Given two sessions in one ledger, and decisions for both
    for r in (row("r1", "s1", "0.10"), row("r2", "s1", "0.25"), row("r3", "s2", "9"), row("r4", "s3", None)):
        assert ledger.write(r)
    (tmp_path / "decisions.jsonl").write_text(
        "\n".join(
            json.dumps(d)
            for d in (
                {"action": "rewritten", "feature": "max_tokens", "session_id": "s1"},
                {"action": "would_rewrite", "feature": "other", "session_id": "s1"},
                {"action": "rewritten", "feature": "elsewhere", "session_id": "s2"},
            )
        )
        + "\nnot json\n"
    )
    reader = LedgerCostReader(wait_s=0)
    # When read Then only that session counts
    u = reader.read(tmp_path, "s1")
    assert (
        u.cost_usd == Decimal("0.35") and u.calls == 2 and u.buckets.fresh_input == 200 and u.fired == ("max_tokens",)
    )
    assert reader.read(tmp_path, "s3").cost_usd is None
    assert reader.read(tmp_path, "nope").calls == 0
