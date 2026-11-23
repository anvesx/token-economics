"""REPORT.md: a short human summary of an analysis. Numbers only; no prompt or response text."""

from __future__ import annotations

from typing import Any


def _pct(v: float | None) -> str:
    return "n/a" if v is None else f"{v * 100:.1f}%"


def _usd(v: str | None) -> str:
    return "n/a" if v is None else f"${float(v):,.4f}"


def report_markdown(result: dict[str, Any], preregistered: bool = True) -> str:
    lines = [f"# Eval report: {result['name']}", ""]
    if not preregistered:
        lines += [
            "**Not preregistered.** The spec was not committed before this run; the bound was not fixed in advance.",
            "",
        ]
    lines += [
        f"Baseline `{result['baseline']}`. Non-inferiority bound {result['bound_pp']} pp. Alpha {result['alpha']} "
        f"(Holm across candidates). Clustered by {result['cluster']}.",
        "",
        "| arm | attempts | success | total cost | CPS | failed-run waste | median cost geo-SD | errors |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for arm, s in result["arms"].items():
        sd = s["median_cost_geometric_sd"]
        lines.append(
            f"| {arm} | {s['attempts']} | {_pct(s['success_rate'])} | {_usd(s['total_cost_usd'])} "
            f"| {_usd(s['cps_usd'])} "
            f"| {_pct(s['failed_waste_share'])} | {'n/a' if sd is None else f'{sd:.2f}'} | {s['errors']} |"
        )
    lines += [
        "",
        "| candidate | CPS ratio (95% CI) | success diff pp (95% CI) | p (Holm) | verdict |",
        "|---|---|---|---|---|",
    ]
    for arm, c in result["comparisons"].items():
        ci, sci = c["ratio_ci"], c["success_diff_ci"]
        ratio = "n/a" if c["ratio"] is None or ci is None else f"{c['ratio']:.3f} ({ci[0]:.3f} to {ci[1]:.3f})"
        diff = "n/a" if sci is None else f"{c['success_diff'] * 100:+.1f} ({sci[0] * 100:+.1f} to {sci[1] * 100:+.1f})"
        lines.append(f"| {arm} | {ratio} | {diff} | {c['adjusted_p']:.4f} | **{c['verdict']}**: {c['reason']} |")
    lines += [
        "",
        "A candidate that does not win stays off. That is a valid result; list it in `docs/evals/OFF.md`.",
        "",
    ]
    return "\n".join(lines)
