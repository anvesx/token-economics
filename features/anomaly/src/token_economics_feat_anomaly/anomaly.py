"""Spend anomaly alerts per caller against its own trailing baseline (plan/07 leaves the method open; this is ours).

Method: robust z-score on daily spend. Baseline = median and MAD (median absolute deviation) of the caller's spend on
the previous `baseline_days` calendar days (UTC) that had any spend. Today's running spend is anomalous when
    today > median + k * 1.4826 * MAD     and     today > min_usd     and     history days >= min_days.
1.4826 scales MAD to a standard deviation under normality. Median and MAD, unlike mean and stdev, are not dragged up
by the one bad day an anomaly detector exists to find. When MAD is 0 (very steady spend) the threshold is the median,
and `min_usd` is what stops a trivial rise from alerting. A session that alone spends over `session_usd` is a second,
independent trigger. This is a first pick, to be checked against the P0 baseline (see README).

Also today > min_ratio (default 1.25) x median, so a caller with very steady spend (MAD 0) does not alert on a few cents.
Config: {"baseline_days": 14, "k": 5, "min_usd": 5, "min_ratio": 1.25, "min_days": 7, "session_usd": null, "block": false}
Alerts go to `alerts.jsonl` (`kind: "spend_anomaly"`, `trigger: "daily" | "session"`), once per caller per trigger per
UTC day. With `block` true, further calls from the caller are refused with 429 `spend_anomaly` for the rest of that day.
State: daily totals per caller (bounded), today's per-session totals; numbers only.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from threading import Lock
from typing import Any

from token_economics_contracts.types import Decision, FeatureEnv, LedgerRow, RequestContext

STATE_FILE, ALERTS_FILE = "anomaly.json", "alerts.jsonl"
FLUSH_INTERVAL_S = 30.0
MAX_CALLERS, MAX_SESSIONS = 5000, 5000
MAD_SCALE = Decimal("1.4826")


def median(values: Sequence[Decimal]) -> Decimal:
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def _dec(value: Any, default: Decimal | None = Decimal(0)) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return default
    try:
        out = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default
    return out if out.is_finite() and out >= 0 else default


def _day(ts: datetime) -> str:
    return ts.astimezone(UTC).strftime("%Y-%m-%d")


class Anomaly:
    name = "anomaly"
    fail_closed = False

    def __init__(self, env: FeatureEnv, clock: Callable[[], float] = time.time) -> None:
        cfg = env.config
        days, min_days = cfg.get("baseline_days"), cfg.get("min_days")
        self._baseline_days = days if isinstance(days, int) and not isinstance(days, bool) and days > 0 else 14
        self._min_days = (
            min_days if isinstance(min_days, int) and not isinstance(min_days, bool) and min_days > 0 else 7
        )
        self._k = _dec(cfg.get("k"), Decimal(5)) or Decimal(5)
        self._min_usd = _dec(cfg.get("min_usd"), Decimal(5)) or Decimal(0)
        self._min_ratio = _dec(cfg.get("min_ratio"), Decimal("1.25")) or Decimal(0)
        self._session_usd = _dec(cfg.get("session_usd"), None)
        self._block = cfg.get("block") is True
        self._keep_days = max(self._baseline_days * 2, 30)
        self._state_path, self._alerts_path = env.state_dir / STATE_FILE, env.state_dir / ALERTS_FILE
        self._clock, self._lock = clock, Lock()
        self._daily: dict[str, dict[str, Decimal]] = {}
        self._sessions: dict[str, Decimal] = {}
        self._sessions_day = ""
        self._alerted: set[str] = set()  # "caller|trigger|day"
        self._blocked: dict[str, str] = {}
        self._dirty, self._last_flush = False, clock()
        self._load()

    # -- state -------------------------------------------------------------------------
    def _load(self) -> None:
        try:
            data = json.loads(self._state_path.read_text())
            callers = data["callers"]
        except (OSError, ValueError, KeyError, TypeError):
            return
        if not isinstance(data, dict) or not isinstance(callers, dict):
            return
        for caller, days in callers.items():
            if isinstance(caller, str) and isinstance(days, dict):
                self._daily[caller] = {str(d): v for d, v in ((d, _dec(x)) for d, x in days.items()) if v is not None}
        sessions = data.get("sessions")
        if isinstance(sessions, dict) and isinstance(sessions.get("spend"), dict):
            self._sessions_day = str(sessions.get("day", ""))
            self._sessions = {
                str(k): v for k, v in ((k, _dec(x)) for k, x in sessions["spend"].items()) if v is not None
            }
        if isinstance(data.get("alerted"), list):
            self._alerted = {str(x) for x in data["alerted"]}
        if isinstance(data.get("blocked"), dict):
            self._blocked = {str(k): str(v) for k, v in data["blocked"].items()}

    def _write(self) -> None:
        self._dirty, self._last_flush = False, self._clock()
        payload = {
            "version": 1,
            "callers": {c: {d: str(v) for d, v in days.items()} for c, days in self._daily.items()},
            "sessions": {"day": self._sessions_day, "spend": {k: str(v) for k, v in self._sessions.items()}},
            "alerted": sorted(self._alerted),
            "blocked": self._blocked,
        }
        tmp = self._state_path.with_name(self._state_path.name + f".{os.getpid()}.tmp")
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(payload, separators=(",", ":")))
            tmp.replace(self._state_path)
        except OSError:
            pass  # best effort: a failed write must never fail a request

    def _prune(self, today: str) -> None:
        cutoff = (date.fromisoformat(today) - timedelta(days=self._keep_days)).isoformat()
        for days in self._daily.values():
            for d in [d for d in days if d < cutoff]:
                del days[d]
        if len(self._daily) > MAX_CALLERS:
            quiet = sorted(self._daily, key=lambda c: max(self._daily[c], default=""))
            for c in quiet[: len(self._daily) - MAX_CALLERS]:
                del self._daily[c]
        self._alerted = {a for a in self._alerted if a.rsplit("|", 1)[-1] >= today}
        self._blocked = {c: d for c, d in self._blocked.items() if d >= today}

    # -- detection ---------------------------------------------------------------------
    def _baseline(self, caller: str, today: str) -> tuple[Decimal, Decimal, int] | None:
        """(median, MAD, days of history) over the previous `baseline_days` days that had spend."""
        start = date.fromisoformat(today)
        values = []
        for back in range(1, self._baseline_days + 1):
            v = self._daily.get(caller, {}).get((start - timedelta(days=back)).isoformat())
            if v is not None and v > 0:
                values.append(v)
        if len(values) < self._min_days:
            return None
        med = median(values)
        return med, median([abs(v - med) for v in values]), len(values)

    # -- feature -----------------------------------------------------------------------
    def before(self, ctx: RequestContext) -> Decision | None:
        if not self._block or not ctx.key.caller:
            return None
        with self._lock:
            blocked = self._blocked.get(ctx.key.caller) == _day(ctx.ts)
        if not blocked:
            return None
        return Decision(
            allow=False,
            feature=self.name,
            status=429,
            code="spend_anomaly",
            message=f"Spend for {ctx.key.caller} today (UTC) is far above its usual level, so further calls are "
            "paused until midnight UTC. Ask an admin to review the alert.",
        )

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        if row is None:
            return
        caller = row.caller or ctx.key.caller
        cost = row.cost_estimate_usd
        if not caller or cost is None or cost <= 0:
            return
        day = _day(row.ts)
        alerts: list[dict[str, Any]] = []
        with self._lock:
            days = self._daily.setdefault(caller, {})
            today_total = days[day] = days.get(day, Decimal(0)) + cost
            alerts += self._check_daily(caller, day, today_total)
            if self._session_usd is not None and row.session_id:
                alerts += self._check_session(caller, day, row.session_id, cost)
            for a in alerts:
                self._alerted.add(f"{caller}|{a['trigger']}|{day}")
                if self._block:
                    self._blocked[caller] = day
            self._prune(day)
            self._dirty = True
            if alerts or self._clock() - self._last_flush >= FLUSH_INTERVAL_S:
                self._write()
        for a in alerts:
            self._emit(row.ts, a)

    def _check_daily(self, caller: str, day: str, today: Decimal) -> list[dict[str, Any]]:
        if f"{caller}|daily|{day}" in self._alerted or today <= self._min_usd:
            return []
        base = self._baseline(caller, day)
        if base is None:
            return []
        med, mad, n = base
        # With very steady spend MAD is 0 and the threshold would be the median itself: also require min_ratio x median.
        threshold = max(med + self._k * MAD_SCALE * mad, med * self._min_ratio)
        if today <= threshold:
            return []
        return [
            {
                "trigger": "daily",
                "caller": caller,
                "day": day,
                "today_usd": str(today),
                "median_usd": str(med),
                "mad_usd": str(mad),
                "threshold_usd": str(threshold),
                "history_days": n,
                "k": str(self._k),
            }
        ]

    def _check_session(self, caller: str, day: str, session: str, cost: Decimal) -> list[dict[str, Any]]:
        if self._sessions_day != day:
            self._sessions, self._sessions_day = {}, day
        spent = self._sessions[session] = self._sessions.get(session, Decimal(0)) + cost
        if len(self._sessions) > MAX_SESSIONS:
            for s in sorted(self._sessions, key=lambda s: self._sessions[s])[: len(self._sessions) - MAX_SESSIONS]:
                del self._sessions[s]
        limit = self._session_usd
        if limit is None or spent <= limit or f"{caller}|session|{day}" in self._alerted:
            return []
        return [
            {
                "trigger": "session",
                "caller": caller,
                "day": day,
                "session_usd": str(spent),
                "limit_usd": str(limit),
            }
        ]

    def flush(self) -> None:
        with self._lock:
            if self._dirty:
                self._write()

    def _emit(self, ts: datetime, detail: dict[str, Any]) -> None:
        record = {"ts": ts.astimezone(UTC).isoformat(), "kind": "spend_anomaly", "blocking": self._block, **detail}
        try:
            self._alerts_path.parent.mkdir(parents=True, exist_ok=True)
            with self._alerts_path.open("a") as f:
                f.write(json.dumps(record) + "\n")
        except OSError:
            pass


def create(env: FeatureEnv) -> Anomaly:
    return Anomaly(env)
