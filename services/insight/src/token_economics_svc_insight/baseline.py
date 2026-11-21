"""The P0 baseline report: spend per developer, cache hit per caller and failed-run share, from ledger rows only.

Conventions (stated here so the numbers can be reproduced by hand):
- A developer is the row's `caller`, else its `agent`, else "unknown".
- A day is the UTC date of `ts`. Daily statistics cover days with at least one priced request.
- P95 is the nearest-rank percentile: the value at rank ceil(0.95 * n) of the sorted daily totals.
  The median of an even count is the mean of the two middle values.
- Rows with `cost_estimate_usd` None are counted as unpriced and left out of every spend figure.
- Shares and the hit rate are Decimals rounded to four places.
"""
from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict
from token_economics_contracts import LedgerRow

_ZERO = Decimal(0)
_SHARE = Decimal("0.0001")


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class DeveloperBaseline(_Frozen):
    developer: str
    requests: int
    unpriced_requests: int
    total_spend_usd: Decimal
    active_days: int  # days with at least one priced request
    mean_daily_usd: Decimal | None
    median_daily_usd: Decimal | None
    p95_daily_usd: Decimal | None
    cache_hit_rate: Decimal | None  # cache_read / prompt tokens; None when no prompt tokens


class BaselineReport(_Frozen):
    period_start: datetime | None
    period_end: datetime | None
    requests: int
    unpriced_requests: int
    total_spend_usd: Decimal
    developers: tuple[DeveloperBaseline, ...]
    spend_by_model: dict[str, Decimal]
    cost_source_share: dict[str, Decimal]  # share of rows, not of spend
    known_outcome_requests: int  # rows whose `success` is not None
    failed_share_by_count: Decimal | None  # None when no row has a known outcome
    failed_share_by_spend: Decimal | None


def _share(part: Decimal | int, whole: Decimal | int) -> Decimal | None:
    return (Decimal(part) / Decimal(whole)).quantize(_SHARE) if whole else None


def _median(sorted_values: Sequence[Decimal]) -> Decimal:
    n = len(sorted_values)
    mid = n // 2
    return sorted_values[mid] if n % 2 else (sorted_values[mid - 1] + sorted_values[mid]) / 2


def _p95(sorted_values: Sequence[Decimal]) -> Decimal:
    return sorted_values[math.ceil(Decimal("0.95") * len(sorted_values)) - 1]


def _developer(name: str, rows: Sequence[LedgerRow]) -> DeveloperBaseline:
    per_day: dict[date, Decimal] = defaultdict(Decimal)
    unpriced = 0
    for r in rows:
        if r.cost_estimate_usd is None:
            unpriced += 1
        else:
            per_day[r.ts.date()] += r.cost_estimate_usd
    days = sorted(per_day.values())
    reads = sum(r.buckets.cache_read for r in rows)
    prompt = sum(r.buckets.prompt_tokens for r in rows)
    return DeveloperBaseline(
        developer=name,
        requests=len(rows),
        unpriced_requests=unpriced,
        total_spend_usd=sum(days, _ZERO),
        active_days=len(days),
        mean_daily_usd=sum(days, _ZERO) / len(days) if days else None,
        median_daily_usd=_median(days) if days else None,
        p95_daily_usd=_p95(days) if days else None,
        cache_hit_rate=_share(reads, prompt),
    )


def baseline(rows: Iterable[LedgerRow]) -> BaselineReport:
    """The baseline from ledger rows. Pure: no I/O, no clock."""
    all_rows = list(rows)
    by_dev: dict[str, list[LedgerRow]] = defaultdict(list)
    by_model: dict[str, Decimal] = defaultdict(Decimal)
    by_source: dict[str, int] = defaultdict(int)
    for r in all_rows:
        by_dev[r.caller or r.agent or "unknown"].append(r)
        by_source[r.cost_source.value] += 1
        if r.cost_estimate_usd is not None:
            by_model[r.model] += r.cost_estimate_usd
    developers = tuple(_developer(d, by_dev[d]) for d in sorted(by_dev))
    known = [r for r in all_rows if r.success is not None]
    failed = [r for r in known if r.success is False]
    known_spend = sum((r.cost_estimate_usd or _ZERO for r in known), _ZERO)
    failed_spend = sum((r.cost_estimate_usd or _ZERO for r in failed), _ZERO)
    return BaselineReport(
        period_start=min((r.ts for r in all_rows), default=None),
        period_end=max((r.ts for r in all_rows), default=None),
        requests=len(all_rows),
        unpriced_requests=sum(d.unpriced_requests for d in developers),
        total_spend_usd=sum((d.total_spend_usd for d in developers), _ZERO),
        developers=developers,
        spend_by_model=dict(sorted(by_model.items(), key=lambda kv: (-kv[1], kv[0]))),
        cost_source_share={k: _share(v, len(all_rows)) or _ZERO for k, v in sorted(by_source.items())},
        known_outcome_requests=len(known),
        failed_share_by_count=_share(len(failed), len(known)),
        failed_share_by_spend=_share(failed_spend, known_spend),
    )


def _usd(x: Decimal | None) -> str:
    return "-" if x is None else f"${x:,.2f}"


def _pct(x: Decimal | None) -> str:
    return "-" if x is None else f"{x * 100:.1f}%"


def baseline_markdown(report: BaselineReport) -> str:
    md = ["# Baseline", ""]
    if report.period_start is None or report.period_end is None:
        md += ["No ledger rows in the period.", ""]
        return "\n".join(md)
    md += [
        f"Period: {report.period_start:%Y-%m-%d} to {report.period_end:%Y-%m-%d} (UTC). "
        f"{report.requests:,} requests, {_usd(report.total_spend_usd)} spend"
        + (f", {report.unpriced_requests:,} unpriced (not in spend)." if report.unpriced_requests else "."),
        "",
        "## Spend per developer",
        "",
        "Per-day figures cover days with at least one priced request (UTC). P95 is the nearest-rank percentile.",
        "",
        "| developer | requests | unpriced | spend | days | mean/day | median/day | P95/day | cache hit |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for d in report.developers:
        md.append(
            f"| {d.developer} | {d.requests:,} | {d.unpriced_requests:,} | {_usd(d.total_spend_usd)} | {d.active_days} "
            f"| {_usd(d.mean_daily_usd)} | {_usd(d.median_daily_usd)} | {_usd(d.p95_daily_usd)} "
            f"| {_pct(d.cache_hit_rate)} |"
        )
    md += ["", "Cache hit = cache read / (fresh input + cache read + cache write 5m + cache write 1h).", ""]
    md += ["## Failed-run share", ""]
    if report.failed_share_by_count is None:
        md.append(
            "Not known: no row has a recorded outcome (`success` is empty on every row). In P0 nothing sets it yet, "
            "so this stays empty until task outcomes are recorded."
        )
    else:
        md.append(
            f"{_pct(report.failed_share_by_count)} of rows with a known outcome failed "
            f"({_pct(report.failed_share_by_spend)} of their spend); {report.known_outcome_requests:,} of "
            f"{report.requests:,} rows have a known outcome."
        )
    md += ["", "## Spend by model", "", "| model | spend |", "|---|---|"]
    md += [f"| {m} | {_usd(v)} |" for m, v in report.spend_by_model.items()]
    md += ["", "## Cost source", "", "Share of rows by who computed the cost (bill, then gateway, then client).", ""]
    md += [f"- {k}: {_pct(v)}" for k, v in report.cost_source_share.items()]
    return "\n".join(md) + "\n"
