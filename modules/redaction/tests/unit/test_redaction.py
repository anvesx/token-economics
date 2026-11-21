import sqlite3
from pathlib import Path

import pytest
from token_economics_contracts.errors import TokenEconomicsError
from token_economics_contracts.types import LedgerRow
from token_economics_redaction import ALLOWED_FIELDS, ContentNotAllowed, check_metadata_only, scan_for_content


def test_allowed_fields_are_exactly_the_ledger_row_fields():
    # Given the ledger row type
    # When the allow-list is read
    # Then it is the set of its field names
    assert frozenset(LedgerRow.model_fields) == ALLOWED_FIELDS
    assert "response_id" in ALLOWED_FIELDS and "prompt" not in ALLOWED_FIELDS


def test_metadata_only_record_passes():
    # Given a record with only ledger fields
    record = {"response_id": "r", "model": "m", "buckets": {}}
    # When checked
    # Then nothing is raised
    check_metadata_only(record)


def test_record_with_content_keys_is_rejected_and_names_them():
    # Given a record carrying prompt and response bodies
    record = {"response_id": "r", "prompt": "secret", "body": "x"}
    # When checked
    # Then ContentNotAllowed names both offending keys
    with pytest.raises(ContentNotAllowed) as exc:
        check_metadata_only(record)
    assert exc.value.keys == ["body", "prompt"]
    assert isinstance(exc.value, TokenEconomicsError)
    assert "prompt" in str(exc.value)


def test_scan_finds_needle_in_nested_directory(tmp_path: Path):
    # Given a prompt string written deep in a directory tree
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    (deep / "log.txt").write_text("hello SECRET-PROMPT bye")
    (tmp_path / "clean.txt").write_text("nothing here")
    # When the tree is scanned
    hits = scan_for_content([tmp_path], ["SECRET-PROMPT", "absent"])
    # Then only the file holding it is reported
    assert hits == [(deep / "log.txt", "SECRET-PROMPT")]


def test_scan_finds_needle_hidden_in_sqlite_file(tmp_path: Path):
    # Given a SQLite database holding a prompt in a row
    db = tmp_path / "x.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE t (v TEXT)")
    con.execute("INSERT INTO t VALUES ('please refactor SECRET-PROMPT now')")
    con.commit()
    con.close()
    # When scanned
    # Then the hit is found in the raw bytes
    assert scan_for_content([db], ["SECRET-PROMPT"]) == [(db, "SECRET-PROMPT")]


def test_scan_finds_utf16_encoded_needle_and_non_ascii(tmp_path: Path):
    # Given files storing the needle as UTF-16-LE and as UTF-8 non-ascii text
    f16, f8 = tmp_path / "u16.bin", tmp_path / "u8.bin"
    f16.write_bytes(b"\x00\x01" + "SECRET-PROMPT".encode("utf-16-le"))
    f8.write_bytes("café secret".encode())
    # When scanned
    hits = scan_for_content([tmp_path], ["SECRET-PROMPT", "café secret"])
    # Then both are found
    assert hits == [(f16, "SECRET-PROMPT"), (f8, "café secret")]


def test_scan_accepts_single_files_and_ignores_missing_paths_and_empty_needles(tmp_path: Path):
    # Given one file, a missing path and an empty needle
    f = tmp_path / "f.txt"
    f.write_text("abc")
    # When scanned
    # Then the empty needle matches nothing and the missing path is skipped
    assert scan_for_content([f, tmp_path / "nope"], ["", "abc"]) == [(f, "abc")]


def test_scan_of_clean_storage_returns_nothing(tmp_path: Path):
    # Given storage with no prompt text
    (tmp_path / "f").write_bytes(b"\x00\xff metadata only")
    # When scanned
    # Then there are no hits
    assert scan_for_content([tmp_path], ["SECRET-PROMPT"]) == []
