"""Strong-model ceiling (plan/05): cap each tenant's share of calls (or spend) that go to strong models.

Config (the feature's section of the policy file):
    {"strong_models": ["claude-opus-5-5"], "max_share": 0.5, "window_hours": 24, "min_calls": 50,
     "measure": "calls", "downgrade_to": null, "alert_at": 0.45}
`strong_models` are exact model ids; empty means inert. Nothing acts before `min_calls` calls are in the window.
Over the share, a strong-model request is refused (429 `strong_share_exceeded`) when `downgrade_to` is null; with
`downgrade_to` set it is rewritten to that model, but only at a conversation start (`facts.turns == 0`), because a
mid-session model switch breaks the prompt cache. Mid-session requests are left alone.
State is hourly counts per tenant (numbers only, no text), written atomically and throttled.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from threading import Lock
from typing import Any

from token_economics_contracts.types import Decision, FeatureEnv, LedgerRow, RequestContext, Rewrite

STATE_FILE, ALERTS_FILE = "strong_share.json", "alerts.jsonl"
FLUSH_INTERVAL_S = 30.0
MAX_TENANTS = 1000
Bucket = list[Any]  # [calls, strong calls, cost usd (str), strong cost usd (str)]


def _num(value: Any, default: float, low: float, high: float) -> float:
    if isinstance(value, int | float) and not isinstance(value, bool) and low <= value <= high:
        return float(value)
    return default


def _dec(value: Any) -> Decimal:
    try:
        out = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal(0)
    return out if out.is_finite() and out >= 0 else Decimal(0)


class StrongShare:
    name = "strong_share"
    fail_closed = False

    def __init__(self, env: FeatureEnv, clock: Callable[[], float] = time.time) -> None:
        cfg = env.config
        models = cfg.get("strong_models")
        self._strong = (
            frozenset(m for m in models if isinstance(m, str) and m) if isinstance(models, list) else frozenset()
        )
        self._max = _num(cfg.get("max_share"), 0.5, 0.0, 1.0)
        self._window_h = int(_num(cfg.get("window_hours"), 24, 1, 24 * 90))
        self._min_calls = int(_num(cfg.get("min_calls"), 50, 0, 10**9))
        self._cost = cfg.get("measure") == "cost"
        down = cfg.get("downgrade_to")
        self._downgrade = down if isinstance(down, str) and down else None
        self._alert_at = _num(cfg.get("alert_at"), self._max * 0.9, 0.0, 1.0)
        self._state_path, self._alerts_path = env.state_dir / STATE_FILE, env.state_dir / ALERTS_FILE
        self._clock, self._lock = clock, Lock()
        self._tenants: dict[str, dict[int, Bucket]] = {}
        self._alerted: dict[str, str] = {}
        self._dirty, self._last_flush = False, clock()
        self._load()

    # -- state -------------------------------------------------------------------------
    def _load(self) -> None:
        try:
            data = json.loads(self._state_path.read_text())
            raw, alerted = data["tenants"], data.get("alerted", {})
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return
        if not isinstance(raw, dict):
            return
        for tenant, buckets in raw.items():
            if not isinstance(tenant, str) or not isinstance(buckets, dict):
                continue
            kept: dict[int, Bucket] = {}
            for hour, b in buckets.items():
                try:
                    if isinstance(b, list) and len(b) == 4:
                        kept[int(hour)] = [int(b[0]), int(b[1]), str(_dec(b[2])), str(_dec(b[3]))]
                except (ValueError, TypeError):
                    continue
            self._tenants[tenant] = kept
        if isinstance(alerted, dict):
            self._alerted = {str(k): str(v) for k, v in alerted.items()}

    def _write(self) -> None:
        self._dirty, self._last_flush = False, self._clock()
        tmp = self._state_path.with_name(self._state_path.name + f".{os.getpid()}.tmp")
        payload = {"version": 1, "tenants": self._tenants, "alerted": self._alerted}
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(payload, separators=(",", ":")))
            tmp.replace(self._state_path)
        except OSError:
            pass  # best effort: a failed write must never fail a request

    def _prune(self, tenant: str, now_hour: int) -> None:
        buckets = self._tenants.get(tenant, {})
        for hour in [h for h in buckets if h <= now_hour - self._window_h]:
            del buckets[hour]
        if len(self._tenants) > MAX_TENANTS:
            quiet = sorted(self._tenants, key=lambda t: max(self._tenants[t], default=0))
            for t in quiet[: len(self._tenants) - MAX_TENANTS]:
                del self._tenants[t]

    def _share(self, tenant: str, ts: datetime) -> tuple[float, int]:
        """(strong share over the window, calls in the window)."""
        now_hour = int(ts.timestamp()) // 3600
        calls = strong = 0
        cost = strong_cost = Decimal(0)
        for hour, b in self._tenants.get(tenant, {}).items():
            if now_hour - self._window_h < hour <= now_hour:
                calls, strong = calls + b[0], strong + b[1]
                cost, strong_cost = cost + Decimal(b[2]), strong_cost + Decimal(b[3])
        if self._cost:
            return (float(strong_cost / cost) if cost > 0 else 0.0), calls
        return (strong / calls if calls else 0.0), calls

    def _over(self, ctx: RequestContext) -> float | None:
        """The tenant's strong share when it is over the cap and enough calls are in the window, else None."""
        if not self._strong or not ctx.key.tenant:
            return None
        with self._lock:
            share, calls = self._share(ctx.key.tenant, ctx.ts)
        return share if calls >= self._min_calls and calls > 0 and share > self._max else None

    # -- feature -----------------------------------------------------------------------
    def before(self, ctx: RequestContext) -> Decision | None:
        try:
            if self._downgrade is not None or ctx.facts.model not in self._strong:
                return None
            share = self._over(ctx)
            if share is None:
                return None
            return Decision(
                allow=False,
                feature=self.name,
                status=429,
                code="strong_share_exceeded",
                message=f"Strong-model share {share:.2f} is over the cap of {self._max:.2f} for this tenant "
                f"(last {self._window_h} h, by {'cost' if self._cost else 'calls'}). "
                "Use a cheaper model or ask an admin to raise the cap.",
            )
        except Exception:  # noqa: BLE001 - a broken check must never block a request
            return None

    def rewrite(self, ctx: RequestContext, body: dict[str, Any]) -> Rewrite | None:
        try:
            old = ctx.facts.model
            if self._downgrade is None or old not in self._strong or ctx.facts.turns != 0 or old == self._downgrade:
                return None
            share = self._over(ctx)
            if share is None:
                return None
            return Rewrite(
                body={**body, "model": self._downgrade},
                changes=(f"model {old}->{self._downgrade} (strong share {share:.2f} > {self._max:.2f})",),
            )
        except Exception:  # noqa: BLE001 - rewrites fail open
            return None

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        if row is None or not self._strong:
            return
        tenant = row.tenant or ctx.key.tenant
        if not tenant:
            return
        is_strong = row.model in self._strong
        cost = row.cost_estimate_usd if row.cost_estimate_usd is not None and row.cost_estimate_usd > 0 else Decimal(0)
        hour = int(row.ts.timestamp()) // 3600
        alert: tuple[float, int] | None = None
        with self._lock:
            b = self._tenants.setdefault(tenant, {}).setdefault(hour, [0, 0, "0", "0"])
            b[0] += 1
            b[2] = str(Decimal(b[2]) + cost)
            if is_strong:
                b[1] += 1
                b[3] = str(Decimal(b[3]) + cost)
            self._prune(tenant, hour)
            self._dirty = True
            share, calls = self._share(tenant, row.ts)
            day = row.ts.astimezone(UTC).strftime("%Y-%m-%d")
            if calls >= self._min_calls and share >= self._alert_at and self._alerted.get(tenant) != day:
                self._alerted[tenant] = day
                alert = (share, calls)
                self._write()
            elif self._clock() - self._last_flush >= FLUSH_INTERVAL_S:
                self._write()
        if alert is not None:
            self._alert(tenant, row.ts, *alert)

    def flush(self) -> None:
        with self._lock:
            if self._dirty:
                self._write()

    def _alert(self, tenant: str, ts: datetime, share: float, calls: int) -> None:
        record = {
            "ts": ts.astimezone(UTC).isoformat(),
            "kind": "strong_share",
            "tenant": tenant,
            "share": round(share, 4),
            "alert_at": round(self._alert_at, 4),
            "max_share": self._max,
            "measure": "cost" if self._cost else "calls",
            "window_hours": self._window_h,
            "calls": calls,
        }
        try:
            self._alerts_path.parent.mkdir(parents=True, exist_ok=True)
            with self._alerts_path.open("a") as f:
                f.write(json.dumps(record) + "\n")
        except OSError:
            pass


def create(env: FeatureEnv) -> StrongShare:
    return StrongShare(env)
