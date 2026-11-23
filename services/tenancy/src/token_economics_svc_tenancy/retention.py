"""Retention for the metadata logs in the state directory, from `<state>/retention.json`:

    {"default_days": 90, "tenants": {"acme": 30}}

Drops lines older than the tenant's days from the JSONL logs named below. A line without a `tenant` uses the default; a
line without a parsable `ts` is kept; a missing or absent config does nothing. The ledger, the price book and the audit
log are append-only by project rule and are never touched.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

CONFIG_NAME = "retention.json"
LOGS = (
    "decisions.jsonl",
    "alerts.jsonl",
    "cache_misses.jsonl",
    "rejects.jsonl",
    "switch_pricer.jsonl",
    "rollbacks.jsonl",
    "shadow/pairs.jsonl",
)


def _days(value: Any, where: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"retention.json: {where} must be a whole number of days, at least 1")
    return value


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return ts if ts.tzinfo is not None else ts.replace(tzinfo=UTC)


class FileRetention:
    def __init__(self, state_dir: Path | str) -> None:
        self._state = Path(state_dir)

    def _config(self) -> tuple[int | None, dict[str, int | None]] | None:
        path = self._state / CONFIG_NAME
        if not path.is_file():
            return None
        raw = json.loads(path.read_text())
        if not isinstance(raw, dict):
            raise ValueError("retention.json must be a JSON object")
        tenants = raw.get("tenants", {})
        if not isinstance(tenants, dict):
            raise ValueError("retention.json: tenants must be an object")
        return _days(raw.get("default_days"), "default_days"), {t: _days(d, f"tenants.{t}") for t, d in tenants.items()}

    def apply(self, now: datetime | None = None) -> dict[str, Any]:
        """Rewrite each log without its expired lines. Returns the dropped count and per-file counts."""
        config = self._config()
        if config is None:
            return {"dropped": 0, "files": {}}
        default, tenants = config
        clock = now if now is not None else datetime.now(UTC)
        files: dict[str, dict[str, int]] = {}
        for name in LOGS:
            path = self._state / name
            if path.is_file():
                files[name] = self._prune(path, clock, default, tenants)
        return {"dropped": sum(f["dropped"] for f in files.values()), "files": files}

    def _expired(self, line: bytes, clock: datetime, default: int | None, tenants: dict[str, int | None]) -> bool:
        try:
            obj = json.loads(line)
        except ValueError:
            return False
        if not isinstance(obj, dict):
            return False
        ts = _parse_ts(obj.get("ts"))
        if ts is None:
            return False
        tenant = obj.get("tenant")
        days = tenants.get(tenant, default) if isinstance(tenant, str) else default
        return days is not None and ts < clock - timedelta(days=days)

    def _prune(
        self, path: Path, clock: datetime, default: int | None, tenants: dict[str, int | None]
    ) -> dict[str, int]:
        data = path.read_bytes()
        lines = data.splitlines(keepends=True)
        kept = [x for x in lines if not self._expired(x, clock, default, tenants)]
        dropped = len(lines) - len(kept)
        if dropped:
            self._replace(path, b"".join(kept), len(data))
        return {"kept": len(kept), "dropped": dropped}

    def _replace(self, path: Path, content: bytes, read_size: int) -> None:
        """Atomic replace. A writer that appended since we read gets its new bytes carried over; a line appended in the
        instant between that check and the replace can still be lost (the gateway holds no lock we can take)."""
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".retention-")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(content)
                with path.open("rb") as current:
                    current.seek(read_size)
                    f.write(current.read())
            os.replace(tmp, path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
            raise
