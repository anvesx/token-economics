"""Pending policy and price-book changes that need a second approver (plan/08).

State is the fold of append-only events: proposed, then rejected or approved (and, for a policy change, applied in the
same transaction). The approver must be a different admin than the proposer, and a change is approved once.

Applying a policy change writes `<state>/policy.json` atomically (temp file, then replace). A price-book change is
stored and approved only: the price book is append-only and has its own path for new rows, so nothing is applied here.
"""

from __future__ import annotations

import contextlib
import json
import os
import secrets
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from ._db import Database
from .audit import append, now_text

Kind = Literal["policy", "price_book"]
KINDS: tuple[Kind, ...] = ("policy", "price_book")
POLICY_FILE = "policy.json"
_FORBIDDEN = ("vk-", "sk-ant", "adm-")


class ChangeError(Exception):
    """A refused operation. `status` is the HTTP status the admin API maps it to. The message never holds a payload."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


class Change(BaseModel):
    model_config = ConfigDict(frozen=True)

    change_id: str
    kind: Kind
    payload: dict[str, Any]
    proposer: str
    proposed_at: datetime
    status: Literal["pending", "approved", "rejected"]
    decided_by: str | None = None
    decided_at: datetime | None = None
    applied: bool = False  # True when approval wrote the change (policy); price-book changes are never applied here


class ChangeStore:
    def __init__(self, db: Database, state_dir: Path | str) -> None:
        self._db = db
        self._state = Path(state_dir)

    @classmethod
    def open(cls, state_dir: Path | str) -> ChangeStore:
        path = Path(state_dir)
        path.mkdir(parents=True, exist_ok=True)
        return cls(Database(path / "tenancy.sqlite"), path)

    def propose(self, kind: str, payload: dict[str, Any], proposer: str) -> str:
        if kind not in KINDS:
            raise ChangeError(400, f"kind must be one of {KINDS}")
        if not isinstance(payload, dict) or not payload:
            raise ChangeError(400, "payload must be a non-empty JSON object")
        text = json.dumps(payload, sort_keys=True)
        if any(bad in text for bad in _FORBIDDEN):
            raise ChangeError(400, "payload refused: it contains something that looks like a key or token")
        change_id = "chg-" + secrets.token_hex(8)
        with self._db.lock:
            conn = self._db.conn
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT INTO change_events (change_id, event, actor, ts, kind, payload) "
                    "VALUES (?, 'proposed', ?, ?, ?, ?)",
                    (change_id, proposer, now_text(), kind, text),
                )
                append(conn, "change_proposed", change_id, {"kind": kind}, proposer)
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return change_id

    def approve(self, change_id: str, approver: str) -> Change:
        """Approve once, by an admin other than the proposer; a policy change is written to `policy.json`."""
        with self._db.lock:
            conn = self._db.conn
            conn.execute("BEGIN IMMEDIATE")
            try:
                change = self._fold(change_id)
                if change.proposer == approver:
                    raise ChangeError(403, "the proposer cannot approve their own change")
                if change.status != "pending":
                    raise ChangeError(409, f"change is already {change.status}")
                if change.kind == "policy":
                    self._write_policy(change.payload)  # inside the transaction: a failed write rolls the approval back
                conn.execute(
                    "INSERT INTO change_events (change_id, event, actor, ts) VALUES (?, 'approved', ?, ?)",
                    (change_id, approver, now_text()),
                )
                if change.kind == "policy":
                    conn.execute(
                        "INSERT INTO change_events (change_id, event, actor, ts) VALUES (?, 'applied', ?, ?)",
                        (change_id, approver, now_text()),
                    )
                append(conn, "change_approved", change_id, {"kind": change.kind, "proposer": change.proposer}, approver)
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return self.get(change_id)

    def reject(self, change_id: str, rejecter: str) -> Change:
        """Reject a pending change. The proposer may withdraw their own."""
        with self._db.lock:
            conn = self._db.conn
            conn.execute("BEGIN IMMEDIATE")
            try:
                change = self._fold(change_id)
                if change.status != "pending":
                    raise ChangeError(409, f"change is already {change.status}")
                conn.execute(
                    "INSERT INTO change_events (change_id, event, actor, ts) VALUES (?, 'rejected', ?, ?)",
                    (change_id, rejecter, now_text()),
                )
                append(conn, "change_rejected", change_id, {"kind": change.kind}, rejecter)
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return self.get(change_id)

    def get(self, change_id: str) -> Change:
        with self._db.lock:
            return self._fold(change_id)

    def list(self) -> list[Change]:
        with self._db.lock:
            ids = [
                r[0]
                for r in self._db.conn.execute(
                    "SELECT change_id FROM change_events WHERE event = 'proposed' ORDER BY seq"
                )
            ]
            return [self._fold(i) for i in ids]

    def _fold(self, change_id: str) -> Change:
        events = self._db.conn.execute(
            "SELECT event, actor, ts, kind, payload FROM change_events WHERE change_id = ? ORDER BY seq", (change_id,)
        ).fetchall()
        if not events or events[0][0] != "proposed":
            raise ChangeError(404, "no such change")
        _, proposer, proposed_at, kind, payload = events[0]
        status: Literal["pending", "approved", "rejected"] = "pending"
        decided_by: str | None = None
        decided_at: str | None = None
        applied = False
        for event, actor, ts, _k, _p in events[1:]:
            if event in ("approved", "rejected") and status == "pending":
                status = event
                decided_by, decided_at = actor, ts
            elif event == "applied":
                applied = True
        return Change(
            change_id=change_id,
            kind=kind,
            payload=json.loads(payload),
            proposer=proposer,
            proposed_at=datetime.fromisoformat(proposed_at),
            status=status,
            decided_by=decided_by,
            decided_at=None if decided_at is None else datetime.fromisoformat(decided_at),
            applied=applied,
        )

    def _write_policy(self, payload: dict[str, Any]) -> None:
        self._state.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self._state, prefix=".policy-")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            os.replace(tmp, self._state / POLICY_FILE)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
            raise

    def close(self) -> None:
        self._db.close()
