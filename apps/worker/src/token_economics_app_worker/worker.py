"""`token-economics-worker [--once] [--interval 300] [--state-dir D]`: scheduled jobs, one JSON line per tick."""

from __future__ import annotations

import argparse
import json
import os
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from token_economics_contracts import SERVICES, load

Lookup = Callable[[str], Any]


def _lookup(name: str) -> Any:
    return load(SERVICES, name)


def _job(name: str, run: Callable[[Any], Any], lookup: Lookup, state: Path, optional: bool) -> dict[str, Any]:
    try:
        factory = lookup(name)
    except LookupError as exc:
        return {"ok": True, "skipped": "not installed"} if optional else {"ok": False, "error": str(exc)}
    try:
        return {"ok": True, "result": run(factory(str(state)))}
    except Exception as exc:  # one failing job must not stop the others
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def tick(state: Path, lookup: Lookup = _lookup, now: datetime | None = None) -> dict[str, Any]:
    """Run every job once. Rollback is required; retention is skipped when the tenancy service is not installed."""
    now = now or datetime.now(UTC)
    return {
        "ts": now.isoformat(),
        "jobs": {
            "rollback": _job("rollback", lambda s: list(s.check(now)), lookup, state, optional=False),
            "retention": _job("retention", lambda s: s.apply(now), lookup, state, optional=True),
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="token-economics-worker", description="Scheduled jobs: auto-rollback, retention")
    ap.add_argument(
        "--once", action="store_true", help="run one tick and exit (for cron); the exit code is 1 on a failure"
    )
    ap.add_argument("--interval", type=float, default=300, help="seconds between ticks")
    ap.add_argument("--state-dir", default=os.environ.get("TOKEN_ECONOMICS_STATE_DIR", "~/.token-economics"))
    a = ap.parse_args(argv)
    state = Path(a.state_dir).expanduser()
    while True:
        record = tick(state, _lookup)
        print(json.dumps(record, default=str), flush=True)
        failed = not all(j["ok"] for j in record["jobs"].values())
        if a.once:
            return int(failed)
        try:
            time.sleep(a.interval)
        except KeyboardInterrupt:
            return 0
