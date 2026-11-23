"""Entry-point factories registered under `token_economics.services`: keys, audit, admin_auth, changes, retention."""

from __future__ import annotations

from pathlib import Path

from .admin import AdminAuth
from .audit import AuditLog
from .changes import ChangeStore
from .keys import KeyStore
from .retention import FileRetention


def open_keys(state_dir: str) -> KeyStore:
    """Open `state_dir/tenancy.sqlite`; import a P0 `keys.json` if one is there."""
    store = KeyStore(Path(state_dir))
    legacy = Path(state_dir) / "keys.json"
    if legacy.exists():
        store.import_legacy(legacy)
    return store


def open_audit(state_dir: str) -> AuditLog:
    return AuditLog.open(state_dir)


def open_admin_auth(state_dir: str) -> AdminAuth:
    return AdminAuth.open(state_dir)


def open_changes(state_dir: str) -> ChangeStore:
    return ChangeStore.open(state_dir)


def open_retention(state_dir: str) -> FileRetention:
    return FileRetention(state_dir)
