from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path
from types import ModuleType

import pytest

TOOL = Path(__file__).resolve().parents[2] / "tools" / "sync_hermes.py"


@pytest.fixture
def sync() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sync_hermes_under_test", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_check_passes_on_the_vendored_files(sync: ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    # Given the files as committed, When checked, Then exit code 0
    assert sync.main(["--check"]) == 0
    assert "match" in capsys.readouterr().out


def test_check_fails_when_one_byte_of_a_vendored_file_changes(
    sync: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given a copy of the vendored folder with one byte appended to a file
    copy = tmp_path / "hermes"
    shutil.copytree(sync.VENDOR_DIR, copy)
    victim = copy / "leak_extra.py"
    victim.write_bytes(victim.read_bytes() + b" ")
    monkeypatch.setattr(sync, "VENDOR_DIR", copy)
    monkeypatch.setattr(sync, "MANIFEST", copy / "VENDORED.md")
    # When checked, Then it fails and names the file
    assert sync.main(["--check"]) == 1
    assert "leak_extra.py" in capsys.readouterr().err


def test_check_fails_when_a_vendored_file_is_missing(
    sync: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given a copy without prompt_check.py
    copy = tmp_path / "hermes"
    shutil.copytree(sync.VENDOR_DIR, copy)
    (copy / "prompt_check.py").unlink()
    monkeypatch.setattr(sync, "MANIFEST", copy / "VENDORED.md")
    # When / Then
    assert sync.check(copy) == ["prompt_check.py: missing"]


def test_manifest_records_the_commit_and_all_five_files(sync: ModuleType) -> None:
    # Given the manifest, Then it names a full commit hash and a sha256 for each of the five files
    text = sync.MANIFEST.read_text()
    assert sync._COMMIT.search(text)
    assert set(sync.recorded()) == set(sync.FILES)
