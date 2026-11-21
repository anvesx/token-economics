"""Metadata-only logging policy: what may be stored, and a scan that proves it."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from token_economics_contracts.errors import TokenEconomicsError
from token_economics_contracts.types import LedgerRow

# The only things stored by default: the ledger row's own fields. Bodies are opt-in elsewhere.
ALLOWED_FIELDS: frozenset[str] = frozenset(LedgerRow.model_fields)


class ContentNotAllowed(TokenEconomicsError):
    """A record carried a key outside the metadata-only allow-list."""

    def __init__(self, keys: list[str]) -> None:
        super().__init__(f"fields not allowed in stored metadata: {sorted(keys)}")
        self.keys = sorted(keys)


def check_metadata_only(record: Mapping[str, Any]) -> None:
    """Raise ContentNotAllowed naming every key that is not in ALLOWED_FIELDS."""
    extra = [str(k) for k in record if k not in ALLOWED_FIELDS]
    if extra:
        raise ContentNotAllowed(extra)


def _files(paths: Iterable[Path]) -> Iterable[Path]:
    for p in paths:
        if p.is_dir():
            yield from (f for f in sorted(p.rglob("*")) if f.is_file())
        elif p.is_file():
            yield p


def scan_for_content(paths: Iterable[Path], needles: Iterable[str]) -> list[tuple[Path, str]]:
    """Every (file, needle) where the needle's UTF-8 or UTF-16-LE bytes appear in the file's raw bytes.

    Directories are walked recursively. Reading raw bytes also finds text inside SQLite and other binary files.
    """
    encoded = [(n, {n.encode("utf-8"), n.encode("utf-16-le")}) for n in needles if n]
    hits: list[tuple[Path, str]] = []
    for f in _files(paths):
        data = f.read_bytes()
        hits.extend((f, n) for n, variants in encoded if any(v in data for v in variants))
    return hits
