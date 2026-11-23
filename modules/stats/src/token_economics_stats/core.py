"""Cost per successful task, the paired task-clustered bootstrap, non-inferiority, Holm and the verdict (plan/07).

Pure functions. The only randomness is `random.Random(seed)`, so a result is the same for the same seed.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from token_economics_contracts import Attempt

MAX_DROPPED_SHARE = 0.05  # more dropped resamples than this and the interval is not trusted


def cps(attempts: Iterable[Attempt]) -> Decimal | None:
    """Cost per successful task: all spend, failed attempts included, over the number of successes."""
    cost, wins = Decimal(0), 0
    for a in attempts:
        cost += a.cost_usd
        wins += a.success
    return cost / wins if wins else None


@dataclass(frozen=True)
class PairedResult:
    baseline: str
    candidate: str
    cluster: str
    n_clusters: int
    attempts_base: int
    attempts_cand: int
    cps_base: Decimal | None
    cps_cand: Decimal | None
    ratio: float | None  # candidate CPS over baseline CPS; below 1 is cheaper
    ratio_ci: tuple[float, float] | None
    success_base: float
    success_cand: float
    success_diff: float  # candidate minus baseline, as proportions
    success_diff_ci: tuple[float, float] | None
    p_value: float  # one-sided: share of resamples with ratio >= 1, with a +1 correction
    n_boot: int
    level: float
    dropped_resamples: int
    unstable: bool


def _percentile(sorted_values: Sequence[float], q: float) -> float:
    pos = q * (len(sorted_values) - 1)
    lo = math.floor(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def _interval(values: list[float], level: float) -> tuple[float, float] | None:
    if not values:
        return None
    values.sort()
    tail = (1 - level) / 2
    return _percentile(values, tail), _percentile(values, 1 - tail)


@dataclass
class _Cell:
    """One cluster's totals for both arms."""

    cost_base: Decimal = Decimal(0)
    cost_cand: Decimal = Decimal(0)
    wins_base: int = 0
    wins_cand: int = 0
    n_base: int = 0
    n_cand: int = 0


def paired_bootstrap(
    attempts: Iterable[Attempt],
    baseline: str,
    candidate: str,
    *,
    n_boot: int = 10_000,
    level: float = 0.95,
    seed: int = 0,
    cluster: Literal["task", "repo"] = "task",
) -> PairedResult:
    """Candidate against baseline on tasks both arms ran. Each draw takes every attempt of a cluster, both arms."""
    by_task: dict[str, list[Attempt]] = defaultdict(list)
    for a in attempts:
        if a.arm in (baseline, candidate):
            by_task[a.task_id].append(a)
    cells: dict[str, _Cell] = defaultdict(_Cell)
    for task, rows in by_task.items():
        if not ({a.arm for a in rows} >= {baseline, candidate}):
            continue  # a task only one arm ran cannot be paired
        key = (rows[0].repo or task) if cluster == "repo" else task
        cell = cells[key]
        for a in rows:
            if a.arm == baseline:
                cell.cost_base, cell.wins_base, cell.n_base = (
                    cell.cost_base + a.cost_usd,
                    cell.wins_base + a.success,
                    cell.n_base + 1,
                )
            else:
                cell.cost_cand, cell.wins_cand, cell.n_cand = (
                    cell.cost_cand + a.cost_usd,
                    cell.wins_cand + a.success,
                    cell.n_cand + 1,
                )
    data = [cells[k] for k in sorted(cells)]

    def totals(sample: Sequence[_Cell]) -> tuple[Decimal, Decimal, int, int, int, int]:
        return (
            sum((c.cost_base for c in sample), Decimal(0)),
            sum((c.cost_cand for c in sample), Decimal(0)),
            sum(c.wins_base for c in sample),
            sum(c.wins_cand for c in sample),
            sum(c.n_base for c in sample),
            sum(c.n_cand for c in sample),
        )

    def ratio_of(cb: Decimal, cc: Decimal, wb: int, wc: int) -> float | None:
        if wb == 0 or wc == 0 or cb == 0:
            return None
        return float((cc * wb) / (cb * wc))

    cb, cc, wb, wc, nb, nc = totals(data)
    point = ratio_of(cb, cc, wb, wc)
    sb, sc = (wb / nb if nb else 0.0), (wc / nc if nc else 0.0)
    ratios: list[float] = []
    diffs: list[float] = []
    dropped = 0
    if data:
        rng = random.Random(seed)
        n = len(data)
        for _ in range(n_boot):
            sample = [data[i] for i in rng.choices(range(n), k=n)]
            rcb, rcc, rwb, rwc, rnb, rnc = totals(sample)
            if rnb and rnc:
                diffs.append(rwc / rnc - rwb / rnb)
            r = ratio_of(rcb, rcc, rwb, rwc)
            if r is None:
                dropped += 1
            else:
                ratios.append(r)
    kept = len(ratios)
    p = (sum(r >= 1 for r in ratios) + 1) / (kept + 1)
    return PairedResult(
        baseline=baseline,
        candidate=candidate,
        cluster=cluster,
        n_clusters=len(data),
        attempts_base=nb,
        attempts_cand=nc,
        cps_base=cb / wb if wb else None,
        cps_cand=cc / wc if wc else None,
        ratio=point,
        ratio_ci=_interval(ratios, level),
        success_base=sb,
        success_cand=sc,
        success_diff=sc - sb,
        success_diff_ci=_interval(diffs, level),
        p_value=p,
        n_boot=n_boot,
        level=level,
        dropped_resamples=dropped,
        unstable=(not data) or dropped > MAX_DROPPED_SHARE * n_boot,
    )


def non_inferior(result: PairedResult, bound_pp: float) -> bool:
    """True when the lower end of the success difference interval is no worse than minus the bound (pp)."""
    ci = result.success_diff_ci
    return ci is not None and ci[0] >= -bound_pp / 100


def holm(pvalues: Mapping[str, float], alpha: float) -> dict[str, tuple[float, bool]]:
    """Holm step-down adjustment: name -> (adjusted p, rejected at alpha)."""
    ordered = sorted(pvalues.items(), key=lambda kv: kv[1])
    m, running, out = len(ordered), 0.0, {}
    for i, (name, p) in enumerate(ordered):
        running = max(running, min(1.0, (m - i) * p))
        out[name] = (running, running < alpha)
    return {name: out[name] for name in pvalues}


def geometric_sd(values: Sequence[float]) -> float:
    """Multiplicative spread of positive values: exp of the sample SD of the logs. 1.0 means no spread."""
    if any(v <= 0 for v in values):
        raise ValueError("geometric_sd needs positive values")
    if len(values) < 2:
        return 1.0
    logs = [math.log(v) for v in values]
    mean = sum(logs) / len(logs)
    return math.exp(math.sqrt(sum((x - mean) ** 2 for x in logs) / (len(logs) - 1)))


def verdict(result: PairedResult, bound_pp: float, alpha: float, adjusted_p: float | None = None) -> tuple[str, str]:
    """("win" | "fails_success_bound" | "no_win", reason). A row that does not win stays off; that is a valid result."""
    if not non_inferior(result, bound_pp):
        ci = result.success_diff_ci
        shown = f"{ci[0] * 100:+.1f} pp" if ci else "not estimable"
        return "fails_success_bound", f"lower end of the success difference is {shown}, worse than -{bound_pp} pp"
    p = result.p_value if adjusted_p is None else adjusted_p
    if result.unstable:
        return "no_win", f"{result.dropped_resamples} of {result.n_boot} resamples dropped: too few successes to trust"
    if result.ratio_ci is None or result.ratio is None:
        return "no_win", "cost per success cannot be estimated"
    lo, hi = result.ratio_ci
    if hi < 1 and p < alpha:
        return "win", f"cost per success ratio {result.ratio:.3f} (CI {lo:.3f} to {hi:.3f}), p {p:.4f} < {alpha}"
    why = f"CI upper end {hi:.3f} is not below 1" if hi >= 1 else f"p {p:.4f} is not below {alpha}"
    return "no_win", f"ratio {result.ratio:.3f} (CI {lo:.3f} to {hi:.3f}): {why}"
