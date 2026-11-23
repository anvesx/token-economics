import importlib
import json
from pathlib import Path

import pytest
from token_economics_app_cli import build_parser, main


def test_init_issues_a_key_that_is_shown_once_and_stored_only_as_a_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    pytest.importorskip("token_economics_svc_tenancy")  # without it the CLI falls back to the P0 plaintext file
    # Given an empty state directory
    monkeypatch.setenv("TOKEN_ECONOMICS_STATE_DIR", str(tmp_path / "state"))
    # When init runs
    assert main(["init", "--tenant", "devx", "--caller", "dhruv"]) == 0
    out = capsys.readouterr().out
    key = next(w for w in out.split() if w.startswith("vk-"))
    # Then the key is printed, and the plaintext is in no file on disk
    assert f"x-token-economics-key: {key}" in out
    for path in (tmp_path / "state").rglob("*"):
        if path.is_file():
            assert key.encode() not in path.read_bytes(), path


def test_budget_set_writes_the_policy_file_and_stays_off_until_a_mode_is_chosen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("TOKEN_ECONOMICS_STATE_DIR", str(tmp_path))
    assert main(["budget", "set", "--scope", "caller", "--match", "dhruv", "--usd", "10"]) == 0
    policy = json.loads((tmp_path / "policy.json").read_text())
    assert policy["features"]["budgets"] == {
        "mode": "off",
        "limits": [{"scope": "caller", "match": "dhruv", "window": "day", "usd": "10"}],
    }
    assert "budgets are off" in capsys.readouterr().out
    # Setting the same budget again replaces it, and a mode can be chosen in the same step
    assert main(["budget", "set", "--scope", "caller", "--match", "dhruv", "--usd", "25", "--mode", "enforced"]) == 0
    policy = json.loads((tmp_path / "policy.json").read_text())
    assert policy["features"]["budgets"]["mode"] == "enforced" and len(policy["features"]["budgets"]["limits"]) == 1
    assert main(["budget", "set", "--scope", "caller", "--usd", "0"]) == 2


def test_policy_mode_switches_one_feature_and_keeps_its_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TOKEN_ECONOMICS_STATE_DIR", str(tmp_path))
    assert main(["policy", "set", "turn_cap", "default", "60"]) == 0
    assert main(["policy", "mode", "turn_cap", "advisory"]) == 0
    assert json.loads((tmp_path / "policy.json").read_text())["features"]["turn_cap"] == {
        "mode": "advisory",
        "default": 60,
    }
    assert main(["policy"]) == 0


def test_report_without_a_ledger_says_what_to_do(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("TOKEN_ECONOMICS_STATE_DIR", str(tmp_path))
    assert main(["report"]) == 1
    assert "no ledger" in capsys.readouterr().out


def test_detect_keeps_the_prompt_check_off_unless_asked() -> None:
    assert build_parser().parse_args(["detect"]).prompt_check is False
    assert build_parser().parse_args(["detect", "--prompt-check"]).prompt_check is True


def test_eval_selftest_passes_on_a_known_no_op(capsys: pytest.CaptureFixture[str]) -> None:
    pytest.importorskip("token_economics_svc_eval")  # the CLI finds the harness by entry point
    # Given two identical synthetic arms When the self-test runs Then it reports no difference and exits 0
    assert main(["eval", "selftest"]) == 0
    assert "PASSED" in capsys.readouterr().out


def test_eval_run_refuses_an_uncommitted_spec_with_a_clear_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pytest.importorskip("token_economics_svc_eval")  # the CLI finds the harness by entry point
    spec = tmp_path / "spec.json"
    spec.write_text("{}")
    assert main(["eval", "run", str(spec), "--out", str(tmp_path / "out")]) == 2
    assert "token-economics eval:" in capsys.readouterr().err


def test_eval_report_reanalyses_a_result_folder(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pytest.importorskip("token_economics_svc_eval")  # the CLI finds the harness by entry point
    # Given a folder with a spec and four attempts, two tasks in each of two arms
    (tmp_path / "spec.json").write_text(
        json.dumps(
            {
                "name": "t",
                "tasks": "x",
                "baseline": "b",
                "arms": {"b": {}, "c": {}},
                "bound": {"success_pp": 5},
                "n_boot": 100,
            }
        )
    )
    rows = [
        {"task_id": t, "arm": arm, "seed": 0, "success": True, "cost_usd": cost}
        for t in ("a", "b")
        for arm, cost in (("b", "2"), ("c", "1"))
    ]
    (tmp_path / "attempts.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    # When reported Then the table has both arms and a verdict
    assert main(["eval", "report", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "| c |" in out and "verdict" in out
    assert main(["eval", "report", str(tmp_path / "missing")]) == 1


def test_policy_kill_and_unkill_switch_a_feature_off_through_kill_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    pytest.importorskip("token_economics_svc_rollout")
    monkeypatch.setenv("TOKEN_ECONOMICS_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("USER", "dhruv")
    # Given a feature, when it is killed for one tenant with a reason
    assert main(["policy", "kill", "output_cap", "--tenant", "acme", "--reason", "drill"]) == 0
    # Then kill.json holds it, attributed to the CLI user, and `kills` lists it
    (entry,) = json.loads((tmp_path / "kill.json").read_text())["kills"]
    assert (entry["feature"], entry["tenant"], entry["reason"], entry["by"]) == (
        "output_cap",
        "acme",
        "drill",
        "cli:dhruv",
    )
    capsys.readouterr()
    assert main(["policy", "kills"]) == 0 and "output_cap" in capsys.readouterr().out
    # And killing it again says so, and unkill removes it
    assert main(["policy", "kill", "output_cap", "--tenant", "acme"]) == 1
    assert main(["policy", "unkill", "output_cap", "--tenant", "acme"]) == 0
    assert json.loads((tmp_path / "kill.json").read_text())["kills"] == []
    assert main(["policy", "unkill", "output_cap", "--tenant", "acme"]) == 1


def test_policy_canary_sets_a_share_and_tenants_and_off_removes_it_keeping_the_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TOKEN_ECONOMICS_STATE_DIR", str(tmp_path))
    assert main(["policy", "mode", "output_cap", "enforced"]) == 0
    # When a canary is set
    assert main(["policy", "canary", "output_cap", "--share", "0.05", "--tenants", "acme,devx"]) == 0
    section = json.loads((tmp_path / "policy.json").read_text())["features"]["output_cap"]
    # Then the section has it beside the mode
    assert section == {"mode": "enforced", "canary": {"share": 0.05, "tenants": ["acme", "devx"]}}
    # And a share outside 0..1 is refused, and --off removes the canary only
    assert main(["policy", "canary", "output_cap", "--share", "1.5"]) == 2
    assert main(["policy", "canary", "output_cap", "--off"]) == 0
    assert json.loads((tmp_path / "policy.json").read_text())["features"]["output_cap"] == {"mode": "enforced"}


def test_rollout_check_prints_a_row_per_feature(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given a rollback checker that reports one feature
    class Fake:
        def __init__(self, state: str) -> None: ...

        def check(self) -> list[dict[str, object]]:
            return [
                {
                    "feature": "output_cap",
                    "status": "breach",
                    "action": "killed",
                    "sessions": {"canary": 40, "control": 40},
                    "triggers": {"cost": {"status": "breach"}, "errors": {"status": "ok"}},
                    "latency": "p95 latency is not measurable: the ledger has no latency",
                }
            ]

    monkeypatch.setenv("TOKEN_ECONOMICS_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(
        importlib.import_module("token_economics_app_cli.main"),
        "_optional",
        lambda name, *a: Fake(*a) if name == "rollback" else None,
    )
    # When rollout check runs
    assert main(["rollout", "check"]) == 0
    # Then the table names the feature, the breaching trigger and the action, and says latency is not measured
    out = capsys.readouterr().out
    assert "| output_cap |" in out and "cost" in out and "killed" in out and "not measurable" in out


def test_shadow_report_prints_the_service_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class Fake:
        def __init__(self, state: str) -> None: ...

        def report(self) -> dict[str, object]:
            return {"pairs": 12}

    monkeypatch.setenv("TOKEN_ECONOMICS_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(
        importlib.import_module("token_economics_app_cli.main"),
        "_optional",
        lambda name, *a: Fake(*a) if name == "shadow" else None,
    )
    assert main(["shadow", "report"]) == 0
    assert '"pairs": 12' in capsys.readouterr().out
