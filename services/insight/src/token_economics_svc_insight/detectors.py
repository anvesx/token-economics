"""The leak detectors in alert mode: hermes-engine's 43 curated categories behind contracts' `Detector` port.

The detection code is vendored unchanged under `hermes/` (see hermes/VENDORED.md). This module is the
adapter: it runs the vendored analysis over Claude Code transcripts, turns each costed item into a
`Finding`, and writes the 50-line coverage table (rows 1-50 of plan/12-fix-table-50-rows.md).
Costs are estimates from transcript usage at API list prices, so `cost_source` is always CLIENT, and
they rank work; they do not predict savings (plan/11).
"""
from __future__ import annotations

import threading
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from token_economics_contracts import CostSource, DetectorCoverage, Finding

from ._hermes_loader import HermesModules, load_hermes

ROWS = range(1, 51)
_CENTS = Decimal("0.000001")
_TTL = {"1h": (3600, 2.0), "5m": (300, 1.25)}  # (cache lifetime in seconds, write multiplier), as leak_report.main
_run_lock = threading.Lock()  # the vendored modules share one config dict per state dir


def _usd(x: float) -> Decimal:
    return Decimal(repr(float(x))).quantize(_CENTS)


class HermesDetectors:
    """Runs the vendored hermes detectors over `transcripts_root` (a `~/.claude/projects`-shaped tree).

    `state_dir` is where the vendored modules may keep their own files; it is never `~/.claude/metrics`.
    `prompt_check` lets a model (`claude -p`) read prompt text to label four categories. Off by default:
    with it off no prompt text leaves the machine and those rows fall back to heuristics.
    """

    name = "hermes"

    def __init__(
        self, transcripts_root: Path, state_dir: Path, *, prompt_check: bool = False, cache_ttl: str = "1h"
    ) -> None:
        if cache_ttl not in _TTL:
            raise ValueError(f"cache_ttl must be one of {sorted(_TTL)}, not {cache_ttl!r}")
        self.transcripts_root = Path(transcripts_root)
        self.state_dir = Path(state_dir)
        self.prompt_check = prompt_check
        self.cache_ttl = cache_ttl
        self.last_total_usd: Decimal | None = None  # API-equivalent spend of the sessions the last run read

    def run(self, since: datetime | None = None) -> tuple[Sequence[Finding], Sequence[DetectorCoverage]]:
        mods = load_hermes(self.state_dir)
        with _run_lock:
            # The vendored prompt check reads its switch from the shared config dict; set it for this run only.
            config: Any = mods.leak_config.CONFIG
            before = config.get("prompt_check")
            config["prompt_check"] = self.prompt_check
            try:
                result = self._analyse(mods, since)
            finally:
                config["prompt_check"] = before
        self.last_total_usd = result[2]
        return result[0], result[1]

    # ---- the boundary: everything from `mods` is untyped Any, and is converted here -------------------

    def _analyse(
        self, mods: HermesModules, since: datetime | None
    ) -> tuple[list[Finding], list[DetectorCoverage], Decimal | None]:
        report: Any = mods.leak_report
        cats: Any = mods.leak_categories
        report.set_units("usd")
        ttl_s, write_mult = _TTL[self.cache_ttl]
        raw: Any = report.analyse_all(
            str(self.transcripts_root), since.timestamp() if since else 0, write_mult, ttl_s, {}, log=None
        )
        sessions: list[Any] = list(raw["_sessions"])
        if not sessions:
            return [], _coverage_for({}, cats), None
        total = float(sum(s.cost + s.helper_cost for s in sessions))
        rows: list[Any] = report.curated_rows(raw, total, sessions)
        findings: list[Finding] = []
        lines: dict[int, DetectorCoverage] = {}
        for n, name, group, _cost, items, reason, note in rows:
            n = int(n)
            if reason:
                lines[n] = _line(cats, n, str(name), str(group), "unmeasurable", 0, Decimal(0), _join(reason, note))
                continue
            made = [
                Finding(
                    row=n,
                    name=str(name),
                    cost_estimate_usd=_usd(i["cost"]),
                    cost_source=CostSource.CLIENT,
                    scope=f"{i['project']}/{i['session']}",
                    detail=str(i["detail"]),
                )
                for i in items
            ]
            findings.extend(made)
            cost = sum((f.cost_estimate_usd for f in made), Decimal(0))
            status: Literal["fired", "not_fired"] = "fired" if made else "not_fired"
            lines[n] = _line(cats, n, str(name), str(group), status, len(made), cost, str(note))
        return findings, _coverage_for(lines, cats), _usd(total)


def _join(*parts: Any) -> str:
    return "; ".join(str(p) for p in parts if p)


def _line(
    cats: Any, n: int, name: str, group: str, status: Literal["fired", "not_fired", "unmeasurable"], fired: int,
    cost: Decimal, note: str,
) -> DetectorCoverage:
    return DetectorCoverage(
        row=n, name=name, group=group, status=status, fired=fired, cost_estimate_usd=cost,
        review=n in cats.REVIEW, note=note,
    )


def _coverage_for(have: dict[int, DetectorCoverage], cats: Any) -> list[DetectorCoverage]:
    """Exactly one line per row 1-50: measured rows, retired rows, and (with no data) active rows at zero."""
    out: list[DetectorCoverage] = []
    for n in ROWS:
        if n in cats.RETIRED:
            name, _, rest = str(cats.RETIRED[n]).partition(":")
            out.append(DetectorCoverage(row=n, name=name.strip(), status="retired", note=rest.strip()))
        elif n in have:
            out.append(have[n])
        elif n in cats.CATEGORIES:
            name, group, _sources = cats.CATEGORIES[n]
            out.append(_line(cats, n, str(name), str(group), "not_fired", 0, Decimal(0), ""))
        else:
            raise ValueError(f"fix-table row {n} is neither an active category nor retired in the vendored files")
    stray = sorted(set(have) - set(ROWS))
    if stray:
        raise ValueError(f"vendored hermes reports rows outside 1-50: {stray}")
    return out


# ---- the P0 deliverable: "docs(detectors): coverage table, 50 rows with fired counts" ----------------------


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _table(lines: Sequence[DetectorCoverage]) -> list[str]:
    out = ["| # | name | group | status | fired | est. cost | note |", "|---|---|---|---|---|---|---|"]
    for c in lines:
        cost = "-" if c.status == "unmeasurable" else f"${c.cost_estimate_usd:,.2f}"
        out.append(
            f"| {c.row} | {_cell(c.name)} | {_cell(c.group)} | {c.status} | {c.fired} | {cost} | {_cell(c.note)} |"
        )
    return out


def coverage_markdown(coverage: Sequence[DetectorCoverage], total_usd: Decimal | None = None) -> str:
    """The coverage table: leaks, then spend to review, then retired numbers. Costs overlap: do not add them up."""
    active = [c for c in coverage if c.status != "retired"]

    def order(c: DetectorCoverage) -> tuple[bool, Decimal, int]:
        return (c.status == "unmeasurable", -c.cost_estimate_usd, c.row)

    leaks = sorted((c for c in active if not c.review), key=order)
    review = sorted((c for c in active if c.review), key=order)
    retired = [c for c in coverage if c.status == "retired"]
    fired = sum(1 for c in active if c.status == "fired")
    quiet = sum(1 for c in active if c.status == "not_fired")
    blind = sum(1 for c in active if c.status == "unmeasurable")
    md = ["# Detector coverage", ""]
    md.append(
        f"{len(coverage)} rows: {fired} fired, {quiet} not fired, {blind} unmeasurable from this data, "
        f"{len(retired)} retired (numbers are never reused)."
    )
    if total_usd is not None:
        md.append(f"Spend read: ${total_usd:,.2f} (API list prices, estimated from transcript usage).")
    md += ["", *_table(leaks), "", "## Spend to review", "",
           "Normal spend that is sometimes avoidable. Not counted as waste.", "", *_table(review), "",
           "Costs overlap (one leaked tool result can sit in several rows), so do not add them up. They rank "
           "work to look at first; they do not predict savings.", "", "## Retired", ""]
    md += [f"- {c.row} {c.name}: {c.note}" for c in retired]
    return "\n".join(md) + "\n"
