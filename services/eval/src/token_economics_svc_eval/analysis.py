"""Attempts in, per-arm summaries and paired verdicts out. JSON-serialisable: Decimal becomes a string."""

from __future__ import annotations

import dataclasses
import random
import statistics
from collections import defaultdict
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from token_economics_contracts import Attempt
from token_economics_stats import cps, geometric_sd, holm, non_inferior, paired_bootstrap, verdict

from .spec import EvalSpec, parse_spec


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, tuple | list):
        return [_jsonable(v) for v in value]
    return value


def summarise_arm(rows: Sequence[Attempt]) -> dict[str, Any]:
    total = sum((a.cost_usd for a in rows), Decimal(0))
    failed = sum((a.cost_usd for a in rows if not a.success), Decimal(0))
    by_task: dict[str, list[float]] = defaultdict(list)
    for a in rows:
        by_task[a.task_id].append(float(a.cost_usd))
    spreads = [geometric_sd(c) for c in by_task.values() if len(c) > 1 and all(x > 0 for x in c)]
    wins = sum(a.success for a in rows)
    return {
        "attempts": len(rows),
        "successes": wins,
        "success_rate": wins / len(rows) if rows else None,
        "total_cost_usd": str(total),
        "cps_usd": _jsonable(cps(rows)),
        "failed_waste_share": float(failed / total) if total else None,
        "median_cost_geometric_sd": statistics.median(spreads) if spreads else None,
        "errors": sum(1 for a in rows if a.error),
    }


def analyse_attempts(attempts: Sequence[Attempt], spec: EvalSpec) -> dict[str, Any]:
    by_arm: dict[str, list[Attempt]] = defaultdict(list)
    for a in attempts:
        by_arm[a.arm].append(a)
    results = {
        c: paired_bootstrap(attempts, spec.baseline, c, n_boot=spec.n_boot, seed=0, cluster=spec.cluster)  # type: ignore[arg-type]
        for c in spec.candidates
    }
    adjusted = holm({c: r.p_value for c, r in results.items()}, spec.alpha)
    comparisons: dict[str, Any] = {}
    for c, r in results.items():
        adj_p, _ = adjusted[c]
        kind, reason = verdict(r, spec.bound_pp, spec.alpha, adjusted_p=adj_p)
        comparisons[c] = {
            **{k: _jsonable(v) for k, v in dataclasses.asdict(r).items()},
            "adjusted_p": adj_p,
            "non_inferior": non_inferior(r, spec.bound_pp),
            "verdict": kind,
            "reason": reason,
        }
    return {
        "name": spec.name,
        "baseline": spec.baseline,
        "bound_pp": spec.bound_pp,
        "alpha": spec.alpha,
        "cluster": spec.cluster,
        "arms": {arm: summarise_arm(rows) for arm, rows in sorted(by_arm.items())},
        "comparisons": comparisons,
    }


def analyse(attempts: Sequence[Attempt], spec: Mapping[str, Any]) -> dict[str, Any]:
    return analyse_attempts(attempts, parse_spec(spec))


def synthetic_noop(seed: int = 0, tasks: int = 80, seeds: int = 3) -> list[Attempt]:
    """Two arms drawn from the same distribution: nothing differs, so nothing may be reported as a win."""
    rng = random.Random(seed)
    out = []
    for i in range(tasks):
        p_success, base_cost = rng.uniform(0.3, 0.95), rng.lognormvariate(0, 0.6)
        for arm in ("baseline", "candidate"):
            for s in range(seeds):
                cost = base_cost * rng.lognormvariate(0, 0.3)
                out.append(
                    Attempt(
                        task_id=f"task-{i:03d}",
                        arm=arm,
                        seed=s,
                        success=rng.random() < p_success,
                        cost_usd=Decimal(f"{cost:.4f}"),
                    )
                )
    return out


def selftest(seed: int = 0) -> dict[str, Any]:
    spec = {
        "name": "selftest-noop",
        "tasks": "-",
        "baseline": "baseline",
        "arms": {"baseline": {}, "candidate": {}},
        "bound": {"success_pp": 5},
        "n_boot": 2000,
    }
    result = analyse(synthetic_noop(seed), spec)
    c = result["comparisons"]["candidate"]
    lo, hi = c["ratio_ci"] if c["ratio_ci"] else (None, None)
    covers = lo is not None and hi is not None and lo <= 1 <= hi
    return {
        "passed": c["verdict"] != "win" and covers,
        "verdict": c["verdict"],
        "reason": c["reason"],
        "ratio": c["ratio"],
        "ratio_ci": c["ratio_ci"],
        "seed": seed,
        "analysis": result,
    }
