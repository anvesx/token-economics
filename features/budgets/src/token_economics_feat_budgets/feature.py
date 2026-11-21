"""Budgets: reserve the worst-case cost before a request, replace it with the true cost after (plan/05).

Config (the feature's section of the policy file):
    {"limits": [{"scope": "caller", "match": "dhruv", "window": "day", "usd": "10"},
                {"scope": "tenant", "match": "*", "window": "month", "usd": "500"}],
     "status": 402, "alerts": ["0.75", "0.9", "1"], "reservation_ttl_s": 900,
     "input_safety": "1.5", "default_max_tokens": 8192, "unpriced": "block"}
Scopes: key, caller, team, tenant. Windows: day and month (UTC), total. A request counts against every limit it matches.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from typing import Any

from token_economics_contracts import (
    BudgetStatus,
    Decision,
    FeatureEnv,
    LedgerRow,
    NoPriceRow,
    RequestContext,
    TokenEconomicsError,
)

from .store import BudgetStore, Slot

MICRO = Decimal(1_000_000)
KINDS = ("key", "caller", "team", "tenant")
WINDOWS = ("day", "month", "total")
DB_NAME, ALERTS_NAME = "budgets.sqlite", "alerts.jsonl"


class BudgetConfigError(TokenEconomicsError):
    """The budgets section of the policy file is not valid."""


def to_micro(usd: Decimal) -> int:
    """Dollars to whole micro-dollars, rounded up so spend is never under-counted."""
    return int((usd * MICRO).to_integral_value(rounding=ROUND_CEILING))


def period_of(win: str, ts: datetime) -> str:
    ts = ts.astimezone(UTC)
    return ts.strftime("%Y-%m-%d") if win == "day" else ts.strftime("%Y-%m") if win == "month" else "all"


def period_start(win: str, ts: datetime) -> datetime | None:
    ts = ts.astimezone(UTC)
    if win == "day":
        return ts.replace(hour=0, minute=0, second=0, microsecond=0)
    if win == "month":
        return ts.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return None


def seconds_to_reset(win: str, ts: datetime) -> int | None:
    start = period_start(win, ts)
    if start is None:
        return None
    nxt = start + timedelta(days=1) if win == "day" else (start + timedelta(days=32)).replace(day=1)
    return max(1, int((nxt - ts.astimezone(UTC)).total_seconds()))


def parse_limits(config: dict[str, Any]) -> list[tuple[str, str, str, int]]:
    out = []
    for raw in config.get("limits") or []:
        try:
            kind, match, win = str(raw["scope"]), str(raw.get("match", "*")), str(raw["window"])
            micro = to_micro(Decimal(str(raw["usd"])))
        except (KeyError, TypeError, ArithmeticError) as exc:
            raise BudgetConfigError(f"bad budget limit {raw!r}") from exc
        if kind not in KINDS or win not in WINDOWS or micro <= 0 or not match:
            raise BudgetConfigError(f"bad budget limit {raw!r}")
        out.append((kind, match, win, micro))
    return out


class Budgets:
    name = "budgets"
    fail_closed = True  # if the budget store cannot be reached, an enforced budget refuses the request

    def __init__(self, env: FeatureEnv) -> None:
        cfg = env.config
        self._limits = parse_limits(cfg)
        self._status = int(cfg.get("status", 402))
        self._alerts = sorted(Decimal(str(a)) for a in cfg.get("alerts", ["0.75", "0.9", "1"]))
        self._ttl = float(cfg.get("reservation_ttl_s", 900))
        self._safety = Decimal(str(cfg.get("input_safety", "1.5")))
        self._default_max = int(cfg.get("default_max_tokens", 8192))
        self._block_unpriced = cfg.get("unpriced", "block") == "block"
        self._pricebook, self._alerts_path = env.pricebook, env.state_dir / ALERTS_NAME
        env.state_dir.mkdir(parents=True, exist_ok=True)
        self._store = BudgetStore(env.state_dir / DB_NAME)
        self._store.save_limits(self._limits)

    def slots(self, ctx: RequestContext) -> list[Slot]:
        """Every budget this request counts against. An empty value never matches a wildcard (no key, no budget)."""
        values = {"key": ctx.key_id, "caller": ctx.key.caller, "team": ctx.key.team, "tenant": ctx.key.tenant}
        out = []
        for kind, match, win, micro in self._limits:
            value = values[kind]
            if value and match in ("*", value):
                out.append(Slot(f"{kind}:{value}", win, period_of(win, ctx.ts), micro))
        return out

    def worst_case_micro(self, ctx: RequestContext) -> int:
        """Reserve as if the whole prompt were written to the dearest cache and every allowed output token used."""
        f = ctx.facts
        price = self._pricebook.lookup(ctx.provider, f.model, ctx.ts, f.est_input_tokens)
        dearest_in = max(price.input, price.cache_write_5m, price.cache_write_1h)
        tokens_in = Decimal(f.est_input_tokens) * self._safety
        tokens_out = Decimal(f.max_tokens if f.max_tokens is not None else self._default_max)
        factor = max((m.factor for m in price.multipliers), default=Decimal(1))
        return to_micro((tokens_in * dearest_in + tokens_out * price.output) * max(factor, Decimal(1)) / MICRO)

    def before(self, ctx: RequestContext) -> Decision | None:
        slots = self.slots(ctx)
        if not slots:
            return None
        try:
            micro = self.worst_case_micro(ctx)
        except NoPriceRow:
            if not self._block_unpriced:
                return None
            return Decision(
                allow=False,
                feature=self.name,
                status=self._status,
                code="unpriced_model",
                message=f"Budget: no price is known for model {ctx.facts.model!r}, so its cost cannot be capped. "
                "Ask an admin to add a price row.",
            )
        refusal = self._store.reserve(ctx.request_id, slots, micro, ctx.ts.timestamp(), self._ttl)
        if refusal is None:
            return None
        s = refusal.slot
        if self._store.mark_alert(s, "blocked"):
            self._alert(s, "blocked", refusal.spent_micro + refusal.reserved_micro, ctx.ts)
        when = {"day": "today (UTC)", "month": "this month (UTC)", "total": "in total"}[s.win]
        return Decision(
            allow=False,
            feature=self.name,
            status=self._status,
            code="budget_exhausted",
            message=f"Budget exhausted for {s.scope}: ${Decimal(refusal.spent_micro) / MICRO:.2f} spent of "
            f"${Decimal(s.limit_micro) / MICRO:.2f} {when}; this request could cost up to "
            f"${Decimal(micro) / MICRO:.2f}. Ask an admin to raise the budget.",
            retry_after_s=seconds_to_reset(s.win, ctx.ts),
        )

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        slots = self.slots(ctx)
        if not slots:
            return
        cost = row.cost_estimate_usd if row is not None else None
        for slot, before, after in self._store.settle(ctx.request_id, slots, to_micro(cost) if cost else 0):
            for threshold in self._alerts:
                line = int(threshold * slot.limit_micro)
                if before < line <= after and self._store.mark_alert(slot, str(threshold)):
                    self._alert(slot, str(threshold), after, ctx.ts)

    def _alert(self, slot: Slot, threshold: str, used_micro: int, ts: datetime) -> None:
        record = {
            "ts": ts.astimezone(UTC).isoformat(),
            "scope": slot.scope,
            "window": slot.win,
            "period": slot.period,
            "threshold": threshold,
            "used_usd": str(Decimal(used_micro) / MICRO),
            "limit_usd": str(Decimal(slot.limit_micro) / MICRO),
            "used_share": str((Decimal(used_micro) / Decimal(slot.limit_micro)).quantize(Decimal("0.0001"))),
        }
        try:
            with self._alerts_path.open("a") as f:
                f.write(json.dumps(record) + "\n")
        except OSError:
            pass


class BudgetStatusReader:
    """Read-only view for reports: every configured limit, for each scope that has spend this period."""

    def __init__(self, state_dir: Path) -> None:
        self._path = state_dir / DB_NAME

    def status(self, now: datetime | None = None) -> Sequence[BudgetStatus]:
        if not self._path.exists():
            return []
        now = now or datetime.now(UTC)
        store = BudgetStore(self._path)
        try:
            out = []
            for kind, match, win, micro in store.limits():
                period = period_of(win, now)
                scopes = store.scopes(kind, win, period) if match == "*" else [f"{kind}:{match}"]
                for scope in scopes:
                    spent, reserved = store.used(Slot(scope, win, period, micro))
                    out.append(
                        BudgetStatus(
                            scope=scope,
                            window=win,  # type: ignore[arg-type]
                            limit_usd=Decimal(micro) / MICRO,
                            spent_usd=Decimal(spent) / MICRO,
                            reserved_usd=Decimal(reserved) / MICRO,
                            period_start=period_start(win, now),
                        )
                    )
            return out
        finally:
            store.close()


def create(env: FeatureEnv) -> Budgets:
    return Budgets(env)


def open_status(state_dir: str) -> BudgetStatusReader:
    return BudgetStatusReader(Path(state_dir))
