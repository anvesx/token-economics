import json
from pathlib import Path

import pytest
from token_economics_app_cli import build_parser, main


def test_init_creates_one_key_per_developer_and_keeps_it_private(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given an empty state directory
    monkeypatch.setenv("TOKEN_ECONOMICS_STATE_DIR", str(tmp_path / "state"))
    # When init runs twice for the same developer
    assert main(["init", "--tenant", "devx", "--caller", "dhruv"]) == 0
    assert main(["init", "--tenant", "devx", "--caller", "dhruv"]) == 0
    # Then there is one key, readable only by the owner
    keys_path = tmp_path / "state" / "keys.json"
    keys = json.loads(keys_path.read_text())
    assert len(keys) == 1 and next(iter(keys.values())) == {"tenant": "devx", "team": "", "caller": "dhruv"}
    assert keys_path.stat().st_mode & 0o777 == 0o600
    assert next(iter(keys)) in capsys.readouterr().out


def test_report_without_a_ledger_says_what_to_do(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("TOKEN_ECONOMICS_STATE_DIR", str(tmp_path))
    assert main(["report"]) == 1
    assert "no ledger" in capsys.readouterr().out


def test_detect_keeps_the_prompt_check_off_unless_asked() -> None:
    assert build_parser().parse_args(["detect"]).prompt_check is False
    assert build_parser().parse_args(["detect", "--prompt-check"]).prompt_check is True
