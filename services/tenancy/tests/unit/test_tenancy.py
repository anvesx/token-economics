import json
import sqlite3
import threading
import time
from pathlib import Path

import pytest
from token_economics_contracts import KeyInfo, KeyResolver, load
from token_economics_svc_tenancy import AuditLog, KeyStore, open_audit, open_keys

INFO = KeyInfo(tenant="acme", team="core", caller="alice", agent="claude-code")


def all_bytes(d: Path) -> bytes:
    return b"".join(p.read_bytes() for p in sorted(d.iterdir()) if p.is_file())


def test_plaintext_and_hash_are_not_in_the_database_file(tmp_path: Path):
    # Given an issued key
    store = KeyStore(tmp_path)
    plaintext, key_id = store.issue(INFO)
    assert plaintext.startswith("vk-") and len(key_id) == 16
    # When the files on disk are scanned
    import hashlib

    full = hashlib.sha256(plaintext.encode()).hexdigest()
    data = all_bytes(tmp_path)
    # Then neither the plaintext nor the hex hash is there
    assert plaintext.encode() not in data
    assert full.encode() not in data
    assert (tmp_path / "tenancy.sqlite").exists()
    assert plaintext not in repr(store.list())


def test_resolve_active_unknown_none_and_revoked():
    # Given one issued key
    store = KeyStore.in_memory()
    plaintext, key_id = store.issue(INFO)
    # Then it resolves as active with its identity
    r = store.resolve(plaintext)
    assert (r.status, r.key_id, r.info) == ("active", key_id, INFO)
    # And a wrong key is unknown, an empty one none
    assert store.resolve("vk-nope").status == "unknown"
    assert store.resolve("vk-nope").info.tenant == "unknown"
    assert store.resolve("").status == "none"
    # When revoked
    assert store.revoke(key_id) is True
    r = store.resolve(plaintext)
    # Then it resolves as revoked with its info
    assert (r.status, r.key_id, r.info) == ("revoked", key_id, INFO)
    assert store.revoke(key_id) is False
    assert store.revoke("0" * 16) is False
    assert isinstance(store, KeyResolver)


def test_revocation_by_another_instance_is_seen_within_two_seconds(tmp_path: Path):
    # Given a gateway-side store that has resolved a key as active
    gateway = KeyStore(tmp_path)
    plaintext, key_id = gateway.issue(INFO)
    assert gateway.resolve(plaintext).status == "active"
    # When the CLI (another instance on the same file) revokes it
    cli = KeyStore(tmp_path)
    assert cli.revoke(key_id, actor="ops") is True
    # Then the gateway sees it revoked within 2 seconds
    deadline = time.monotonic() + 2
    while gateway.resolve(plaintext).status != "revoked":
        assert time.monotonic() < deadline, "revocation not seen"
        time.sleep(0.05)
    # And the audit log records who did it
    entries = [e for e in gateway.audit.entries() if e.action == "key_revoked"]
    assert [(e.subject, e.actor) for e in entries] == [(key_id, "ops")]


def test_issue_and_revoke_are_audited_without_secrets():
    store = KeyStore.in_memory()
    plaintext, key_id = store.issue(INFO, actor="dhruv")
    store.revoke(key_id)
    got = [(e.action, e.subject, e.actor) for e in store.audit.entries()]
    assert got == [("key_issued", key_id, "dhruv"), ("key_revoked", key_id, "cli")]
    assert plaintext not in json.dumps([e.model_dump(mode="json") for e in store.audit.entries()])


def test_update_and_delete_fail_on_every_table(tmp_path: Path):
    # Given a store with a key, a revocation and an audit entry
    store = KeyStore(tmp_path)
    _, key_id = store.issue(INFO)
    store.revoke(key_id)
    raw = sqlite3.connect(tmp_path / "tenancy.sqlite", isolation_level=None)
    # When raw UPDATE and DELETE run on each table, Then SQLite aborts them
    for table, col in (("keys", "tenant"), ("revocations", "actor"), ("audit", "actor")):
        assert raw.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] >= 1
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            raw.execute(f"UPDATE {table} SET {col} = 'x'")
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            raw.execute(f"DELETE FROM {table}")
    raw.close()


def test_legacy_import_keeps_plaintext_working_and_leaves_none_on_disk(tmp_path: Path):
    # Given a P0 keys.json
    legacy = {
        "vk-old-one": {"tenant": "acme", "team": "t", "caller": "bob", "agent": "a"},
        "vk-old-two": {"tenant": "x"},
    }
    (tmp_path / "keys.json").write_text(json.dumps(legacy))
    # When the factory opens the store
    store = open_keys(str(tmp_path))
    # Then the old keys still work
    r = store.resolve("vk-old-one")
    assert r.status == "active" and r.info.caller == "bob"
    assert store.resolve("vk-old-two").info.tenant == "x"
    # And no plaintext stays on disk
    assert not (tmp_path / "keys.json").exists()
    assert (tmp_path / "keys.json.imported").exists()
    data = all_bytes(tmp_path)
    assert b"vk-old-one" not in data and b"vk-old-two" not in data
    # And the import is idempotent
    (tmp_path / "keys.json").write_text(json.dumps(legacy))
    assert store.import_legacy(tmp_path / "keys.json") == 0
    assert len(store.list()) == 2
    assert b"vk-old-one" not in all_bytes(tmp_path)


def test_audit_rejects_secret_looking_values():
    log = KeyStore.in_memory().audit
    with pytest.raises(ValueError):
        log.record("x", "s", {"note": "key vk-abc123"})
    with pytest.raises(ValueError):
        log.record("x", "s", {"nested": {"h": ["sk-ant-api03-zzz"]}})
    assert log.entries() == []
    log.record("ok", "s", {"n": 1})
    assert len(log.entries()) == 1


def test_audit_entries_since(tmp_path: Path):
    from datetime import UTC, datetime, timedelta

    log = open_audit(str(tmp_path))
    log.record("a", "s", {})
    assert len(log.entries(since=datetime.now(UTC) - timedelta(minutes=1))) == 1
    assert log.entries(since=datetime.now(UTC) + timedelta(minutes=1)) == []


def test_resolving_from_20_threads_while_issuing_does_not_error(tmp_path: Path):
    # Given a store with one key and a short refresh so reloads happen during the run
    store = KeyStore(tmp_path, refresh_s=0.0)
    plaintext, _ = store.issue(INFO)
    errors: list[BaseException] = []

    def resolve() -> None:
        try:
            for _ in range(100):
                assert store.resolve(plaintext).status == "active"
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    def issue() -> None:
        try:
            for _ in range(20):
                store.issue(INFO)
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=resolve) for _ in range(20)] + [threading.Thread(target=issue)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert errors == []
    assert len(store.list()) == 21


def test_entry_points_resolve(tmp_path: Path):
    keys = load("token_economics.services", "keys")(str(tmp_path / "new"))
    assert isinstance(keys, KeyStore) and isinstance(keys, KeyResolver)
    audit = load("token_economics.services", "audit")(str(tmp_path / "new"))
    assert isinstance(audit, AuditLog)
