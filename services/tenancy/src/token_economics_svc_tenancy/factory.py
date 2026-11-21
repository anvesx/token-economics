"""Entry-point factories registered under `token_economics.services` as `keys` and `audit`."""

from __future__ import annotations

from pathlib import Path

from .audit import AuditLog
from .keys import KeyStore


def open_keys(state_dir: str) -> KeyStore:
    """Open `state_dir/tenancy.sqlite`; import a P0 `keys.json` if one is there."""
    store = KeyStore(Path(state_dir))
    legacy = Path(state_dir) / "keys.json"
    if legacy.exists():
        store.import_legacy(legacy)
    return store


def open_audit(state_dir: str) -> AuditLog:
    return AuditLog.open(state_dir)
