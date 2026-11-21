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
