import json
from pathlib import Path
from threading import Thread
from typing import Any

import pytest
from token_economics_contracts import KillFile, KillSwitches
from token_economics_svc_rollout import KillSwitchFile


class Audit:
    def __init__(self) -> None:
        self.entries: list[tuple[str, str, dict[str, Any], str]] = []

    def record(self, action: str, subject: str, detail: dict[str, Any], actor: str = "system") -> None:
        self.entries.append((action, subject, detail, actor))


def test_a_kill_is_written_once_audited_and_removed(tmp_path: Path) -> None:
    # Given an empty state dir
    audit = Audit()
    k = KillSwitchFile(tmp_path, audit)
    assert isinstance(k, KillSwitches)
    # When a switch is added twice and then removed
    assert k.add("output_cap", "acme", reason="drill", by="cli:dhruv")
    assert not k.add("output_cap", "acme")
    data = KillFile.model_validate_json((tmp_path / "kill.json").read_text())
    # Then the file holds one entry the engine understands, and both changes are audited
    assert data.killed("output_cap", "acme") and not data.killed("output_cap", "devx")
    assert k.remove("output_cap", "acme", by="cli:dhruv") and not k.remove("output_cap", "acme")
    assert k.list() == []
    assert [e[0] for e in audit.entries] == ["kill_switch_on", "kill_switch_off"]


def test_a_broken_kill_file_is_never_overwritten(tmp_path: Path) -> None:
    (tmp_path / "kill.json").write_text("{broken")
    with pytest.raises(ValueError):
        KillSwitchFile(tmp_path).add("output_cap")
    assert (tmp_path / "kill.json").read_text() == "{broken"


def test_concurrent_writers_lose_no_switch(tmp_path: Path) -> None:
    # Given 20 writers adding different switches at once
    k = KillSwitchFile(tmp_path)
    threads = [Thread(target=k.add, args=(f"f{i}",)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # Then all 20 are in the file
    assert len(json.loads((tmp_path / "kill.json").read_text())["kills"]) == 20
