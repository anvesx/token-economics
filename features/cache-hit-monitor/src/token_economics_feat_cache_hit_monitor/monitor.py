"""Observe cache use per caller and model; never change a request (plan/05, plan/07).

Config (all optional):
    {"alert_below": null, "min_calls": 50, "window": 200, "max_sessions": 10000, "persist_interval_s": 30}
Files in the state dir: `cache_misses.jsonl` (one line per miss), `cache_monitor.json` (snapshot for the dashboard),
`alerts.jsonl` (one hit-rate drop alert per caller per UTC day, only when `alert_below` is set).
A miss: a call that is not the first in its conversation reprocessed at least 2,000 tokens and over 5 percent of its
prompt. Reprocessed = the part of the previous call's prompt (which that call cached) not read back from cache now. New
turn content written to cache is normal growth, not a miss.
"""

from __future__ import annotations

import json
import os
import time
from collections import OrderedDict, deque
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from token_economics_contracts.types import Decision, FeatureEnv, LedgerRow, RequestContext

MISSES_NAME, SNAPSHOT_NAME, ALERTS_NAME = "cache_misses.jsonl", "cache_monitor.json", "alerts.jsonl"
MISS_MIN_TOKENS, MISS_MIN_SHARE = 2000, 0.05
TTL_5M_S, TTL_1H_S = 300.0, 3600.0


def _int(value: Any, default: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else default


def _rate(read: int, total: int) -> float:
    return round(read / total, 4) if total else 0.0


class _Stats:
    __slots__ = ("calls", "fresh", "misses", "read", "write")

    def __init__(self) -> None:
        self.calls = self.read = self.write = self.fresh = self.misses = 0

    def view(self) -> dict[str, Any]:
        total = self.read + self.write + self.fresh
        return {
            "calls": self.calls,
            "read": self.read,
            "write": self.write,
            "fresh": self.fresh,
            "hit_rate": _rate(self.read, total),
            "misses": self.misses,
        }


class CacheHitMonitor:
    name = "cache_hit_monitor"
    fail_closed = False

    def __init__(
        self, state_dir: Path, config: dict[str, Any] | None = None, clock: Callable[[], float] | None = None
    ) -> None:
        cfg = config or {}
        below = cfg.get("alert_below")
        self.alert_below = float(below) if isinstance(below, (int, float)) and not isinstance(below, bool) else None
        self.min_calls = _int(cfg.get("min_calls"), 50)
        self.window = _int(cfg.get("window"), 200)
        self.max_sessions = _int(cfg.get("max_sessions"), 10_000)
        self.persist_interval_s = float(cfg.get("persist_interval_s", 30))
        self._dir, self._clock = state_dir, clock or time.monotonic
        self._lock = Lock()
        self._stats: dict[str, dict[str, _Stats]] = {}  # caller scope -> model -> totals
        self._recent: dict[str, deque[tuple[int, int]]] = {}  # caller scope -> (read, total) of the last calls
        # conversation -> (ts, model, any 1h write, prompt tokens) of its previous call
        self._sessions: OrderedDict[str, tuple[datetime, str, bool, int]] = OrderedDict()
        self._alerted: dict[str, str] = {}  # caller scope -> UTC day of its last alert
        self._last_persist = float("-inf")

    def before(self, ctx: RequestContext) -> Decision | None:
        return None

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        if row is None:
            return
        b = row.buckets
        scope = row.caller or ctx.key.caller or ctx.key_id or ctx.key.tenant
        write, prompt = b.cache_write_5m + b.cache_write_1h, b.prompt_tokens
        miss: dict[str, Any] | None = None
        alert: dict[str, Any] | None = None
        with self._lock:
            s = self._stats.setdefault(scope, {}).setdefault(row.model, _Stats())
            s.calls += 1
            s.read += b.cache_read
            s.write += write
            s.fresh += b.fresh_input
            sid = row.session_id or ctx.identity.session_id
            conv = f"{sid}|{ctx.identity.agent}|{ctx.identity.query_source.value}" if sid else ""
            prev = self._sessions.pop(conv, None) if conv else None
            if conv:
                one_hour = (prev[2] if prev else False) or b.cache_write_1h > 0
                self._sessions[conv] = (row.ts, row.model, one_hour, prompt)
                while len(self._sessions) > self.max_sessions:
                    self._sessions.popitem(last=False)
            reprocessed = max(0, min(prev[3], prompt) - b.cache_read) if prev is not None else 0
            if prev is not None and reprocessed >= MISS_MIN_TOKENS and reprocessed > MISS_MIN_SHARE * prompt:
                gap = (row.ts - prev[0]).total_seconds()
                limit = TTL_1H_S if prev[2] else TTL_5M_S
                reason = "model_changed" if prev[1] != row.model else "ttl_expired" if gap > limit else "prefix_changed"
                s.misses += 1
                miss = {
                    "ts": row.ts.astimezone(UTC).isoformat(),
                    "caller": scope,
                    "session_id": sid,
                    "model": row.model,
                    "reprocessed": reprocessed,
                    "prompt_tokens": prompt,
                    "gap_s": round(gap, 1),
                    "reason": reason,
                }
            recent = self._recent.setdefault(scope, deque(maxlen=self.window))
            recent.append((b.cache_read, prompt))
            if self.alert_below is not None and len(recent) >= self.min_calls:
                rate = _rate(sum(r for r, _ in recent), sum(t for _, t in recent))
                day = row.ts.astimezone(UTC).date().isoformat()
                if rate < self.alert_below and self._alerted.get(scope) != day:
                    self._alerted[scope] = day
                    alert = {
                        "ts": row.ts.astimezone(UTC).isoformat(),
                        "scope": f"caller:{scope}",
                        "window": "day",
                        "period": day,
                        "kind": "cache_hit_rate",
                        "threshold": str(self.alert_below),
                        "hit_rate": rate,
                        "calls": len(recent),
                    }
        if miss:
            self._append(MISSES_NAME, miss)
        if alert:
            self._append(ALERTS_NAME, alert)
        self._maybe_persist()

    # -- files -----------------------------------------------------------------------------
    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "updated": datetime.now(UTC).isoformat(),
                "callers": {c: {m: s.view() for m, s in models.items()} for c, models in self._stats.items()},
            }

    def _append(self, name: str, record: dict[str, Any]) -> None:
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            with self._lock, (self._dir / name).open("a") as f:
                f.write(json.dumps(record) + "\n")
        except OSError:
            pass

    def _maybe_persist(self) -> None:
        now = self._clock()
        with self._lock:
            if now - self._last_persist < self.persist_interval_s:
                return
            self._last_persist = now
        self.flush()

    def flush(self) -> None:
        """Write the snapshot now (atomic: temp file, then replace). Failures are ignored."""
        path = self._dir / SNAPSHOT_NAME
        tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(self.snapshot()))
            tmp.replace(path)
        except OSError:
            pass


def create(env: FeatureEnv) -> CacheHitMonitor:
    return CacheHitMonitor(env.state_dir, env.config)
