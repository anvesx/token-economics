"""Shadow sampling and the primary-versus-shadow report (plan/07, Rollout).

Config `<state_dir>/shadow/shadow.json`, re-read when it changes; a missing file means disabled:
    {"enabled": false, "share": 0.0, "tenants": [], "harnesses": [], "max_usd_per_day": "5.00"}
Empty lists mean all. Sampling is deterministic per conversation (a hash of the session id, or of the request id when
there is no session), so a whole session is mirrored or none of it is. Shadow spend is capped per UTC day.

Both sides report to `pairs.jsonl` (metadata only: ids, model, status, cost, bucket totals). The report joins them on
request_id. Nothing here raises into the request path.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import median
from threading import Lock
from typing import Any

from token_economics_contracts import LedgerRow, RequestContext

DIR_NAME, CONFIG_NAME, PAIRS_NAME = "shadow", "shadow.json", "pairs.jsonl"
DEFAULT_CAP = Decimal("5.00")
SIDES = ("primary", "shadow")


class Config:
    def __init__(
        self,
        enabled: bool = False,
        share: float = 0.0,
        tenants: frozenset[str] = frozenset(),
        harnesses: frozenset[str] = frozenset(),
        cap: Decimal = DEFAULT_CAP,
    ) -> None:
        self.enabled, self.share, self.tenants, self.harnesses, self.cap = enabled, share, tenants, harnesses, cap


def parse_config(data: Any) -> Config:
    if not isinstance(data, dict):
        return Config()
    try:
        share = float(data.get("share", 0.0))
        cap = Decimal(str(data.get("max_usd_per_day", DEFAULT_CAP)))
    except (TypeError, ValueError, InvalidOperation):
        return Config()
    if not cap.is_finite() or share != share:  # NaN
        return Config()
    tenants, harnesses = data.get("tenants") or [], data.get("harnesses") or []
    if not isinstance(tenants, list) or not isinstance(harnesses, list):
        return Config()
    return Config(
        enabled=data.get("enabled") is True,
        share=share,
        tenants=frozenset(str(t) for t in tenants),
        harnesses=frozenset(str(h) for h in harnesses),
        cap=cap,
    )


def bucket(key: str) -> float:
    """Map a key to [0, 1), the same way every time."""
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big") / 2**64


def percentile(values: list[Decimal], q: float) -> Decimal:
    """Nearest-rank percentile of a non-empty list."""
    ordered = sorted(values)
    rank = max(1, -(-int(q * len(ordered) * 1000) // 1000))  # ceil without float drift
    return ordered[min(rank, len(ordered)) - 1]


def _cost(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        return None
    return d if d.is_finite() else None


class Shadow:
    def __init__(self, state_dir: Path, clock: Callable[[], datetime] | None = None) -> None:
        self._dir = state_dir / DIR_NAME
        self._config_path, self._pairs = self._dir / CONFIG_NAME, self._dir / PAIRS_NAME
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lock = Lock()
        self._stamp: tuple[int, int] | None = (-1, -1)
        self._config = Config()
        self._day = ""
        self._spend = Decimal(0)
        try:
            with self._lock:
                self._rebuild_spend(self._today())
        except Exception:
            pass

    # -- configuration -----------------------------------------------------------------
    def _config_now(self) -> Config:
        try:
            st = self._config_path.stat()
            stamp: tuple[int, int] | None = (st.st_mtime_ns, st.st_size)
        except OSError:
            stamp = None
        if stamp == self._stamp:
            return self._config
        with self._lock:
            if stamp != self._stamp:
                try:
                    config = parse_config(json.loads(self._config_path.read_text())) if stamp else Config()
                except (OSError, ValueError):
                    config = Config()
                self._config, self._stamp = config, stamp
            return self._config

    # -- spend -------------------------------------------------------------------------
    def _today(self) -> str:
        return self._clock().astimezone(UTC).strftime("%Y-%m-%d")

    def _rebuild_spend(self, today: str) -> None:
        """Caller holds the lock. Sums today's shadow rows from the file."""
        total = Decimal(0)
        for rec in self._read_pairs():
            cost = _cost(rec.get("cost_usd"))
            if rec.get("side") == "shadow" and cost is not None and str(rec.get("ts", ""))[:10] == today:
                total += cost
        self._day, self._spend = today, total

    def _spend_today(self) -> Decimal:
        today = self._today()
        with self._lock:
            if self._day != today:
                self._rebuild_spend(today)
            return self._spend

    def _read_pairs(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        try:
            with self._pairs.open() as f:
                for line in f:
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(rec, dict):
                        out.append(rec)
        except OSError:
            pass
        return out

    # -- ShadowSampler -----------------------------------------------------------------
    def sample(self, ctx: RequestContext) -> bool:
        try:
            cfg = self._config_now()
            if not cfg.enabled or not cfg.share > 0:
                return False
            if cfg.tenants and ctx.key.tenant not in cfg.tenants:
                return False
            if cfg.harnesses and ctx.harness not in cfg.harnesses:
                return False
            if not bucket(ctx.identity.session_id or ctx.request_id) < cfg.share:
                return False
            return self._spend_today() < cfg.cap
        except Exception:
            return False

    def record(self, ctx: RequestContext, side: str, row: LedgerRow | None, status: int) -> None:
        try:
            now = self._clock().astimezone(UTC)
            cost = row.cost_estimate_usd if row is not None else None
            b = row.buckets if row is not None else None
            rec = {
                "ts": now.isoformat(),
                "request_id": ctx.request_id,
                "session_id": ctx.identity.session_id,
                "side": side,
                "tenant": ctx.key.tenant,
                "caller": ctx.key.caller,
                "harness": ctx.harness,
                "model": row.model if row is not None else ctx.facts.model,
                "status": status,
                "cost_usd": str(cost) if cost is not None else None,
                "buckets": {
                    "fresh_input": b.fresh_input if b else 0,
                    "cache_read": b.cache_read if b else 0,
                    "cache_write": (b.cache_write_5m + b.cache_write_1h) if b else 0,
                    "output": b.output if b else 0,
                },
            }
            with self._lock:
                self._dir.mkdir(parents=True, exist_ok=True)
                with self._pairs.open("a") as f:
                    f.write(json.dumps(rec) + "\n")
                if side == "shadow" and cost is not None:
                    today = now.strftime("%Y-%m-%d")
                    if self._day != today:
                        self._rebuild_spend(today)
                    else:
                        self._spend += cost
        except Exception:
            pass

    def report(self) -> dict[str, Any]:
        try:
            return self._report()
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    def _report(self) -> dict[str, Any]:
        cfg = self._config_now()
        with self._lock:
            records = self._read_pairs()
        sides: dict[str, dict[str, dict[str, Any]]] = {s: {} for s in SIDES}
        for rec in records:  # the last record of a side for a request wins (a retry replaces the failed try)
            side, rid = rec.get("side"), rec.get("request_id")
            if side in sides and isinstance(rid, str):
                sides[str(side)][rid] = rec
        matched = sorted(sides["primary"].keys() & sides["shadow"].keys())

        def costs(side: str, ids: list[str]) -> list[Decimal]:
            vals = (_cost(sides[side][i].get("cost_usd")) for i in ids)
            return [v for v in vals if v is not None]

        def summary(side: str, ids: list[str]) -> dict[str, Any]:
            vals = costs(side, ids)
            per_model: dict[str, Decimal] = {}
            for i in ids:
                c = _cost(sides[side][i].get("cost_usd"))
                if c is not None:
                    m = str(sides[side][i].get("model", ""))
                    per_model[m] = per_model.get(m, Decimal(0)) + c
            return {
                "requests": len(ids),
                "total_cost_usd": str(sum(vals, Decimal(0))),
                "cost_by_model": {m: str(v) for m, v in sorted(per_model.items())},
                "median_cost_usd": str(median(vals)) if vals else None,
                "p95_cost_usd": str(percentile(vals, 0.95)) if vals else None,
            }

        both = [
            i
            for i in matched
            if _cost(sides["primary"][i].get("cost_usd")) is not None
            and _cost(sides["shadow"][i].get("cost_usd")) is not None
        ]
        p_sum = sum((_cost(sides["primary"][i].get("cost_usd")) or Decimal(0) for i in both), Decimal(0))
        s_sum = sum((_cost(sides["shadow"][i].get("cost_usd")) or Decimal(0) for i in both), Decimal(0))
        mismatches = [
            i
            for i in matched
            if 200 <= int(sides["primary"][i].get("status", 0)) < 300
            and not 200 <= int(sides["shadow"][i].get("status", 0)) < 300
        ]
        return {
            "enabled": cfg.enabled,
            "share": cfg.share,
            "pairs": len(matched),
            "unmatched": {
                s: len(sides[s].keys() - sides[o].keys()) for s, o in (("primary", "shadow"), ("shadow", "primary"))
            },
            "primary": summary("primary", list(sides["primary"])),
            "shadow": summary("shadow", list(sides["shadow"])),
            "matched_primary_cost_usd": str(p_sum),
            "matched_shadow_cost_usd": str(s_sum),
            "cost_ratio_shadow_over_primary": str(s_sum / p_sum) if p_sum > 0 else None,
            "ratio_pairs": len(both),
            "status_mismatches": len(mismatches),
            "status_mismatch_request_ids": mismatches,
            "spend_today_usd": str(self._spend_today()),
            "max_usd_per_day": str(cfg.cap),
        }


def open_shadow(state_dir: str) -> Shadow:
    return Shadow(Path(state_dir))
