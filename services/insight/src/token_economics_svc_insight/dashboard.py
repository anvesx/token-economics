"""The dashboard summary: spend by day, tenant, caller, model and harness, top sessions and recent requests.

Conventions (shared with baseline.py, so the numbers can be reproduced by hand):
- The window is `days` whole UTC days ending with the UTC day of `now`; it starts at 00:00 UTC of its first day.
  A row counts when `window start <= ts <= now`. `period_start` and `period_end` are the window bounds.
- A day is the UTC date of `ts`. `by_day` has one entry for every day in the window, zero where nothing happened.
- A group's caller is the row's `caller`, else its `agent`, else "unknown". Tenant and harness fall back to "unknown".
- Rows with `cost_estimate_usd` None are counted as unpriced and left out of every spend figure.
- Median and P95 per day cover the group's days with at least one priced request (nearest-rank P95, as baseline.py).
- Shares and the cache hit rate are Decimals rounded to four places. Groups are sorted by spend, largest first.
- Only fields of a LedgerRow appear here: no prompt or response text exists in the ledger and none is added.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from pydantic import BaseModel, ConfigDict
from token_economics_contracts import LedgerRow

from .baseline import _median, _p95, _share

_ZERO = Decimal(0)
TOP_SESSIONS = 20
RECENT_ROWS = 50


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TokenTotals(_Frozen):
    fresh_input: int = 0
    cache_read: int = 0
    cache_write_5m: int = 0
    cache_write_1h: int = 0
    output: int = 0


class DayTotals(_Frozen):
    day: date
    spend_usd: Decimal
    requests: int
    tokens: TokenTotals


class GroupTotals(_Frozen):
    name: str
    requests: int
    unpriced_requests: int
    spend_usd: Decimal
    share_of_spend: Decimal | None  # None when the whole window has no priced spend
    tokens: TokenTotals
    cache_hit_rate: Decimal | None
    active_days: int  # days with at least one priced request
    median_daily_usd: Decimal | None
    p95_daily_usd: Decimal | None


class SessionTotals(_Frozen):
    session_id: str
    caller: str
    models: tuple[str, ...]
    requests: int
    spend_usd: Decimal
    first_ts: datetime
    last_ts: datetime


class RecentRequest(_Frozen):
    ts: datetime
    caller: str
    harness: str
    model: str
    tokens: TokenTotals
    cost_usd: Decimal | None
    cost_source: str
    http_status: int


class DashboardSummary(_Frozen):
    period_start: datetime
    period_end: datetime
    days: int
    requests: int
    unpriced_requests: int
    spend_usd: Decimal
    tokens: TokenTotals
    cache_hit_rate: Decimal | None
    by_day: tuple[DayTotals, ...]
    by_tenant: tuple[GroupTotals, ...]
    by_caller: tuple[GroupTotals, ...]
    by_model: tuple[GroupTotals, ...]
    by_harness: tuple[GroupTotals, ...]
    by_session: tuple[SessionTotals, ...]
    recent: tuple[RecentRequest, ...]


def _utc_day(ts: datetime) -> date:
    return ts.astimezone(UTC).date()


def _caller(r: LedgerRow) -> str:
    return r.caller or r.agent or "unknown"


def _tokens(rows: Sequence[LedgerRow]) -> TokenTotals:
    return TokenTotals(
        fresh_input=sum(r.buckets.fresh_input for r in rows),
        cache_read=sum(r.buckets.cache_read for r in rows),
        cache_write_5m=sum(r.buckets.cache_write_5m for r in rows),
        cache_write_1h=sum(r.buckets.cache_write_1h for r in rows),
        output=sum(r.buckets.output for r in rows),
    )


def _spend(rows: Iterable[LedgerRow]) -> Decimal:
    return sum((r.cost_estimate_usd for r in rows if r.cost_estimate_usd is not None), _ZERO)


def _hit_rate(rows: Sequence[LedgerRow]) -> Decimal | None:
    return _share(sum(r.buckets.cache_read for r in rows), sum(r.buckets.prompt_tokens for r in rows))


def _groups(
    rows: Sequence[LedgerRow], key: Callable[[LedgerRow], str], total_spend: Decimal
) -> tuple[GroupTotals, ...]:
    grouped: dict[str, list[LedgerRow]] = defaultdict(list)
    for r in rows:
        grouped[key(r)].append(r)
    out: list[GroupTotals] = []
    for name, members in grouped.items():
        per_day: dict[date, Decimal] = defaultdict(Decimal)
        for r in members:
            if r.cost_estimate_usd is not None:
                per_day[_utc_day(r.ts)] += r.cost_estimate_usd
        daily = sorted(per_day.values())
        spend = _spend(members)
        out.append(
            GroupTotals(
                name=name,
                requests=len(members),
                unpriced_requests=sum(1 for r in members if r.cost_estimate_usd is None),
                spend_usd=spend,
                share_of_spend=_share(spend, total_spend),
                tokens=_tokens(members),
                cache_hit_rate=_hit_rate(members),
                active_days=len(daily),
                median_daily_usd=_median(daily) if daily else None,
                p95_daily_usd=_p95(daily) if daily else None,
            )
        )
    return tuple(sorted(out, key=lambda g: (-g.spend_usd, g.name)))


def _sessions(rows: Sequence[LedgerRow]) -> tuple[SessionTotals, ...]:
    grouped: dict[str, list[LedgerRow]] = defaultdict(list)
    for r in rows:
        if r.session_id:
            grouped[r.session_id].append(r)
    out = []
    for sid, members in grouped.items():
        ordered = sorted(members, key=lambda r: r.ts)
        out.append(
            SessionTotals(
                session_id=sid,
                caller=_caller(ordered[0]),
                models=tuple(sorted({r.model for r in members})),
                requests=len(members),
                spend_usd=_spend(members),
                first_ts=ordered[0].ts,
                last_ts=ordered[-1].ts,
            )
        )
    return tuple(sorted(out, key=lambda s: (-s.spend_usd, s.session_id))[:TOP_SESSIONS])


def dashboard_summary(rows: Iterable[LedgerRow], *, now: datetime, days: int = 30) -> DashboardSummary:
    """The dashboard numbers for the last `days` UTC days up to `now`. Pure: no I/O, no clock."""
    if days < 1:
        raise ValueError("days must be at least 1")
    today = _utc_day(now)
    first_day = today - timedelta(days=days - 1)
    start = datetime(first_day.year, first_day.month, first_day.day, tzinfo=UTC)
    window = [r for r in rows if start <= r.ts <= now]

    by_date: dict[date, list[LedgerRow]] = defaultdict(list)
    for r in window:
        by_date[_utc_day(r.ts)].append(r)
    by_day = tuple(
        DayTotals(day=d, spend_usd=_spend(by_date[d]), requests=len(by_date[d]), tokens=_tokens(by_date[d]))
        for d in (first_day + timedelta(days=i) for i in range(days))
    )
    total_spend = _spend(window)
    return DashboardSummary(
        period_start=start,
        period_end=now,
        days=days,
        requests=len(window),
        unpriced_requests=sum(1 for r in window if r.cost_estimate_usd is None),
        spend_usd=total_spend,
        tokens=_tokens(window),
        cache_hit_rate=_hit_rate(window),
        by_day=by_day,
        by_tenant=_groups(window, lambda r: r.tenant or "unknown", total_spend),
        by_caller=_groups(window, _caller, total_spend),
        by_model=_groups(window, lambda r: r.model, total_spend),
        by_harness=_groups(window, lambda r: r.harness or "unknown", total_spend),
        by_session=_sessions(window),
        recent=tuple(
            RecentRequest(
                ts=r.ts,
                caller=_caller(r),
                harness=r.harness,
                model=r.model,
                tokens=_tokens([r]),
                cost_usd=r.cost_estimate_usd,
                cost_source=r.cost_source.value,
                http_status=r.http_status,
            )
            for r in sorted(window, key=lambda r: (r.ts, r.response_id), reverse=True)[:RECENT_ROWS]
        ),
    )
