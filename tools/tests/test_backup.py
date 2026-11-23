"""The disaster recovery drill: back up a live state dir, lose it, restore it, check nothing was lost."""

from __future__ import annotations

import json
import shutil
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import backup
import pytest
from token_economics_contracts import SERVICES, Buckets, CostSource, LedgerRow, load


def row(i: int) -> LedgerRow:
    return LedgerRow(
        provider="anthropic",
        response_id=f"msg_{i}",
        ts=datetime(2026, 11, 1, tzinfo=UTC),
        tenant="devx",
        model="claude-opus-5-5",
        buckets=Buckets(fresh_input=10, output=5),
        cost_estimate_usd=None,
        cost_source=CostSource.GATEWAY,
        price_row_id="",
    )


def make_state(root: Path, seed_rows: int = 50) -> tuple[Path, Any]:
    state = root / "state"
    (state / "shadow").mkdir(parents=True)
    ledger = load(SERVICES, "ledger")(str(state / "ledger.sqlite"))
    for i in range(seed_rows):
        ledger.write(row(i))
    (state / "keys.json").write_text(json.dumps({"vk-1": {"tenant": "devx"}}))
    (state / "policy.json").write_text('{"turn_cap": {"mode": "advisory"}}')
    (state / "alerts.jsonl").write_text('{"kind": "cache_hit_rate"}\n')
    (state / "shadow" / "pairs.jsonl").write_text('{"id": "p1"}\n')
    return state, ledger


def ledger_ids(db: Path) -> set[str]:
    con = sqlite3.connect(db)
    try:
        return {r[0] for r in con.execute("SELECT response_id FROM ledger")}
    finally:
        con.close()


def test_dr_drill_restores_every_ledger_row_written_before_the_backup_while_the_gateway_keeps_writing(
    tmp_path: Path,
) -> None:
    # Given a state dir with 50 ledger rows, keys, logs and shadow files, and a writer that keeps appending
    state, ledger = make_state(tmp_path)
    stop, appended, errors = threading.Event(), [], []
    half_way = threading.Event()

    def writer() -> None:
        i = 1000
        try:
            while not stop.is_set():
                ledger.write(row(i))
                i += 1
                appended.append(i)
                if len(appended) >= 30:
                    half_way.set()
        except Exception as e:  # noqa: BLE001
            errors.append(e)
            half_way.set()

    t = threading.Thread(target=writer)
    t.start()
    assert half_way.wait(10)
    before = len(ledger.rows())

    # When the state dir is backed up while the writer is still appending
    manifest = backup.backup(state, tmp_path / "backup")
    stop.set()
    t.join()
    assert not errors

    # Then the backup verifies and holds at least the rows written before it started
    assert backup.verify(tmp_path / "backup") == []
    in_backup = manifest["files"]["ledger.sqlite"]["rows"]["ledger"]
    assert in_backup >= before

    # When the state dir is lost and restored into the empty place
    backup_ids = ledger_ids(tmp_path / "backup" / "ledger.sqlite")
    shutil.rmtree(state)
    assert backup.restore(tmp_path / "backup", state) == []

    # Then every row in the manifest is present, and keys, logs and shadow files are back byte for byte
    restored = ledger_ids(state / "ledger.sqlite")
    assert len(restored) == in_backup and restored == backup_ids
    assert {f"msg_{i}" for i in range(50)} <= restored
    assert json.loads((state / "keys.json").read_text()) == {"vk-1": {"tenant": "devx"}}
    assert (state / "alerts.jsonl").read_text() == '{"kind": "cache_hit_rate"}\n'
    assert (state / "shadow" / "pairs.jsonl").read_text() == '{"id": "p1"}\n'

    # And the ledger is still append-only
    con = sqlite3.connect(state / "ledger.sqlite")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        con.execute("UPDATE ledger SET tenant = 'x'")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        con.execute("DELETE FROM ledger")
    con.close()
    # And the restored ledger accepts new rows and still dedupes
    reopened = load(SERVICES, "ledger")(str(state / "ledger.sqlite"))
    assert reopened.write(row(99_999)) is True
    assert reopened.write(row(0)) is False


def test_restore_refuses_a_state_dir_that_is_not_empty(tmp_path: Path) -> None:
    # Given a backup and a state dir that already has a file
    state, _ = make_state(tmp_path)
    backup.backup(state, tmp_path / "backup")
    target = tmp_path / "live"
    target.mkdir()
    (target / "keys.json").write_text("{}")
    # When restoring into it, then it is refused and nothing is overwritten
    problems = backup.restore(tmp_path / "backup", target)
    assert problems and "not empty" in problems[0]
    assert (target / "keys.json").read_text() == "{}"


def test_verify_reports_a_file_changed_after_the_backup(tmp_path: Path) -> None:
    # Given a good backup
    state, _ = make_state(tmp_path)
    backup.backup(state, tmp_path / "backup")
    assert backup.verify(tmp_path / "backup") == []
    # When a file in it is altered and another removed
    (tmp_path / "backup" / "keys.json").write_text("{}")
    (tmp_path / "backup" / "policy.json").unlink()
    # Then verify names both, and restore writes nothing
    problems = backup.verify(tmp_path / "backup")
    assert any("keys.json" in p and "sha256" in p for p in problems)
    assert any("policy.json" in p and "missing" in p for p in problems)
    assert backup.restore(tmp_path / "backup", tmp_path / "new") and not (tmp_path / "new").exists()


def test_backup_refuses_a_non_empty_output_dir(tmp_path: Path) -> None:
    # Given a non-empty output directory, when backing up into it, then it is refused
    state, _ = make_state(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    (out / "old").write_text("x")
    with pytest.raises(ValueError, match="not empty"):
        backup.backup(state, out)


def test_cli_round_trip(tmp_path: Path) -> None:
    # Given a state dir, when backing up, verifying and restoring through the command line entry point
    state, _ = make_state(tmp_path)
    assert backup.main(["backup", str(state), str(tmp_path / "b")]) == 0
    assert backup.main(["verify", str(tmp_path / "b")]) == 0
    assert backup.main(["restore", str(tmp_path / "b"), str(tmp_path / "r")]) == 0
    # Then restoring again into the same place fails
    assert backup.main(["restore", str(tmp_path / "b"), str(tmp_path / "r")]) == 1
