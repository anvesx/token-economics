"""Kill switches in `<state>/kill.json` (contracts KillFile). The policy engine re-reads the file when it changes, so a
switch takes effect on the next request without a deploy. Writers: the CLI, the admin API and auto-rollback.

Writes are serialised with a lock file and replace the file atomically; every change goes to the audit log when the
tenancy service is installed.
"""

from __future__ import annotations

import contextlib
import fcntl
import os
import tempfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from token_economics_contracts import KILL_FILE, SERVICES, KillEntry, KillFile, load


class KillSwitchFile:
    def __init__(self, state_dir: Path, audit: Any = None) -> None:
        self._path = state_dir / KILL_FILE
        self._lock_path = state_dir / (KILL_FILE + ".lock")
        self._audit = audit

    def read(self) -> KillFile:
        try:
            return KillFile.model_validate_json(self._path.read_text())
        except FileNotFoundError:
            return KillFile()

    def list(self) -> list[KillEntry]:
        return list(self.read().kills)

    @contextlib.contextmanager
    def _locked(self) -> Iterator[None]:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock_path.open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def _write(self, kill: KillFile) -> None:
        fd, tmp = tempfile.mkstemp(dir=self._path.parent, prefix=".kill-")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(kill.model_dump_json(indent=2) + "\n")
            os.replace(tmp, self._path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
            raise

    def add(self, feature: str, tenant: str = "*", reason: str = "", by: str = "") -> bool:
        with self._locked():
            current = self.read()  # a broken file raises: never overwrite what we cannot read
            if any(k.feature == feature and k.tenant == tenant for k in current.kills):
                return False
            entry = KillEntry(feature=feature, tenant=tenant, reason=reason, by=by, ts=datetime.now(UTC))
            self._write(KillFile(kills=(*current.kills, entry)))
        self._record("kill_switch_on", feature, {"tenant": tenant, "reason": reason}, by)
        return True

    def remove(self, feature: str, tenant: str = "*", by: str = "") -> bool:
        with self._locked():
            current = self.read()
            kept = tuple(k for k in current.kills if not (k.feature == feature and k.tenant == tenant))
            if len(kept) == len(current.kills):
                return False
            self._write(KillFile(kills=kept))
        self._record("kill_switch_off", feature, {"tenant": tenant}, by)
        return True

    def _record(self, action: str, subject: str, detail: dict[str, Any], by: str) -> None:
        if self._audit is not None:
            with contextlib.suppress(Exception):
                self._audit.record(action, subject, detail, actor=by or "unknown")


def open_kill(state_dir: str) -> KillSwitchFile:
    audit = None
    with contextlib.suppress(Exception):
        audit = load(SERVICES, "audit")(state_dir)
    return KillSwitchFile(Path(state_dir), audit)
