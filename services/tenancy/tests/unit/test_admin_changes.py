import json
import sqlite3
from pathlib import Path

import pytest
from token_economics_svc_tenancy import AdminAuth, ChangeError, ChangeStore, role_at_least
from token_economics_svc_tenancy._db import Database


def stores(tmp_path: Path) -> tuple[AdminAuth, ChangeStore]:
    db = Database(tmp_path / "tenancy.sqlite")
    return AdminAuth(db), ChangeStore(db, tmp_path)


def test_token_is_shown_once_and_stored_only_as_a_hash(tmp_path: Path):
    # Given an issued admin token
    auth, _ = stores(tmp_path)
    plaintext, token_id = auth.issue("ann", "admin")
    # When the database file is scanned and the token is resolved
    data = (tmp_path / "tenancy.sqlite").read_bytes() + (tmp_path / "tenancy.sqlite-wal").read_bytes()
    # Then the plaintext is nowhere, and it resolves to the name and role
    assert plaintext.startswith("adm-") and plaintext.encode() not in data
    assert auth.resolve(plaintext).name == "ann"  # type: ignore[union-attr]
    assert plaintext not in repr(auth.list())
    assert token_id in repr(auth.list())


def test_revoked_unknown_and_empty_tokens_do_not_resolve(tmp_path: Path):
    # Given one token that is then revoked
    auth, _ = stores(tmp_path)
    plaintext, token_id = auth.issue("ann", "operator")
    assert auth.revoke(token_id, actor="root") is True
    # Then it, a made-up token and an empty one all resolve to nobody; a second revoke is False
    assert auth.resolve(plaintext) is None and auth.resolve("adm-nope") is None and auth.resolve("") is None
    assert auth.revoke(token_id) is False
    # And revoking the last token does not make the store look empty
    assert auth.has_tokens() is True


def test_roles_are_ordered_and_names_unique(tmp_path: Path):
    auth, _ = stores(tmp_path)
    auth.issue("ann", "viewer")
    with pytest.raises(ValueError):
        auth.issue("ann", "admin")
    with pytest.raises(ValueError):
        auth.issue("bob", "root")  # type: ignore[arg-type]
    assert role_at_least("admin", "operator") and role_at_least("operator", "operator")
    assert not role_at_least("viewer", "operator") and not role_at_least("nonsense", "viewer")


def test_token_changes_are_audited_without_the_token(tmp_path: Path):
    auth, _ = stores(tmp_path)
    plaintext, token_id = auth.issue("ann", "admin", actor="root")
    auth.revoke(token_id, actor="root")
    conn = sqlite3.connect(tmp_path / "tenancy.sqlite")
    rows = conn.execute("SELECT actor, action, subject, detail FROM audit").fetchall()
    assert [r[1] for r in rows] == ["admin_token_issued", "admin_token_revoked"]
    assert all(plaintext not in "".join(r) for r in rows)


def test_policy_change_needs_a_different_admin_and_applies_once(tmp_path: Path):
    # Given a policy change proposed by ann
    _, changes = stores(tmp_path)
    new = {"features": {"max_tokens": {"mode": "enforced"}}}
    cid = changes.propose("policy", new, "ann")
    # When ann approves her own change Then it is refused and nothing is written
    with pytest.raises(ChangeError) as e:
        changes.approve(cid, "ann")
    assert e.value.status == 403 and not (tmp_path / "policy.json").exists()
    # When bob approves Then policy.json holds the new policy and the change is applied
    done = changes.approve(cid, "bob")
    assert (done.status, done.applied, done.decided_by) == ("approved", True, "bob")
    assert json.loads((tmp_path / "policy.json").read_text()) == new
    # And a second approval (even by a third admin) is refused, as is a reject
    for call in (lambda: changes.approve(cid, "cy"), lambda: changes.reject(cid, "cy")):
        with pytest.raises(ChangeError) as e:
            call()
        assert e.value.status == 409
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".policy-")]


def test_rejected_change_is_never_applied(tmp_path: Path):
    _, changes = stores(tmp_path)
    cid = changes.propose("policy", {"features": {}}, "ann")
    assert changes.reject(cid, "bob").status == "rejected"
    with pytest.raises(ChangeError):
        changes.approve(cid, "cy")
    assert not (tmp_path / "policy.json").exists()


def test_price_book_change_is_approved_but_not_applied(tmp_path: Path):
    _, changes = stores(tmp_path)
    cid = changes.propose("price_book", {"model": "m", "input": "1"}, "ann")
    done = changes.approve(cid, "bob")
    assert done.status == "approved" and done.applied is False
    assert [c.change_id for c in changes.list()] == [cid]


def test_bad_proposals_and_unknown_ids_are_refused(tmp_path: Path):
    _, changes = stores(tmp_path)
    for kind, payload in (("code", {"a": 1}), ("policy", {}), ("policy", {"k": "vk-abc"}), ("policy", {"k": "adm-x"})):
        with pytest.raises(ChangeError) as e:
            changes.propose(kind, payload, "ann")
        assert e.value.status == 400
    with pytest.raises(ChangeError) as e:
        changes.approve("chg-missing", "bob")
    assert e.value.status == 404


def test_change_events_and_admin_tables_are_append_only(tmp_path: Path):
    auth, changes = stores(tmp_path)
    _, token_id = auth.issue("ann", "admin")
    auth.revoke(token_id)
    changes.propose("policy", {"a": 1}, "ann")
    conn = sqlite3.connect(tmp_path / "tenancy.sqlite")
    for sql in (
        "UPDATE change_events SET actor = 'x'",
        "DELETE FROM change_events",
        "UPDATE admin_tokens SET role = 'admin'",
        "DELETE FROM admin_tokens",
        "DELETE FROM admin_revocations",
    ):
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute(sql)
