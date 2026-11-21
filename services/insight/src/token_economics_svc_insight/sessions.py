"""Session, task and category views for the dashboard, built from Claude Code transcripts with the vendored detectors.

How a session is split into tasks (the vendored `Session.tasks()`): each prompt the person typed is a candidate start.
With the model prompt check, a model labels each prompt as starting unrelated work or continuing; without a label the
fallback is an idle gap of 30+ minutes followed by a prompt that names no file touched so far. Each task says which
rule drew its boundary (`how`), so the split can be checked by eye. It is a heuristic and has not been validated.

Privacy: task and session titles are the first characters of the person's own prompt, read live from their own
transcripts for display on their own machine. Nothing here is written to disk or sent anywhere.
"""

from __future__ import annotations

import shutil
import threading
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ._hermes_loader import load_hermes
from .detectors import _TTL, _run_lock

TITLE_CHARS = 120
CACHE_S = 60.0
HOW = {
    "start": "first prompt of the session",
    "check": "a model judged this prompt to start unrelated work",
    "gap": "30+ minutes idle, and the prompt names no file touched before",
    "tag": "the prompt starts with a [tag]",
}
EDIT_TOOLS = {"Edit", "MultiEdit", "Write", "NotebookEdit"}


def _iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).isoformat().replace("+00:00", "Z")


def _title(text: str) -> str:
    flat = " ".join(str(text).split())
    return flat if len(flat) <= TITLE_CHARS else flat[: TITLE_CHARS - 1] + "…"


def _tokens(calls: list[Any]) -> dict[str, int]:
    return {
        "fresh_input": sum(c["in"] for c in calls),
        "cache_read": sum(c["cr"] for c in calls),
        "cache_write": sum(c["cw"] for c in calls),
        "output": sum(c["out"] for c in calls),
    }


def _money(x: float) -> float:
    return round(float(x), 6)


class SessionViews:
    """Read-only views over a transcript tree. Results are cached for a minute, because an analysis takes seconds."""

    def __init__(
        self,
        transcripts_root: Path,
        state_dir: Path,
        *,
        prompt_check: bool = False,
        seed_labels_from: Path | None = None,
        cache_ttl: str = "1h",
    ) -> None:
        self.transcripts_root, self.state_dir, self.prompt_check = transcripts_root, state_dir, prompt_check
        self._ttl_s, self._write_mult = _TTL[cache_ttl]
        self._lock = threading.Lock()
        self._cache: dict[int, tuple[float, dict[str, Any]]] = {}
        state_dir.mkdir(parents=True, exist_ok=True)
        # Labels a person already paid for with the Hermes plugin are reused: the file holds hashes and labels only.
        mine, theirs = (
            state_dir / "prompt_checks.json",
            (seed_labels_from / "prompt_checks.json" if seed_labels_from else None),
        )
        if theirs is not None and theirs.exists() and not mine.exists():
            shutil.copyfile(theirs, mine)

    # ---------------------------------------------------------------- analysis
    def _analysed(self, days: int) -> dict[str, Any]:
        with self._lock:
            hit = self._cache.get(days)
            if hit and time.monotonic() - hit[0] < CACHE_S:
                return hit[1]
            data = self._analyse(days)
            self._cache[days] = (time.monotonic(), data)
            return data

    def _analyse(self, days: int) -> dict[str, Any]:
        mods = load_hermes(self.state_dir)
        since = (datetime.now(UTC) - timedelta(days=days)).timestamp()
        with _run_lock:
            config: Any = mods.leak_config.CONFIG
            before = config.get("prompt_check")
            config["prompt_check"] = self.prompt_check
            try:
                report: Any = mods.leak_report
                report.set_units("usd")
                raw: Any = report.analyse_all(
                    str(self.transcripts_root), since, self._write_mult, self._ttl_s, {}, log=None
                )
                sessions: list[Any] = list(raw["_sessions"])
                total = float(sum(s.cost + s.helper_cost for s in sessions))
                rows: list[Any] = report.curated_rows(raw, total, sessions) if sessions else []
                return self._build(report, mods.leak_categories, sessions, rows, total, days)
            finally:
                config["prompt_check"] = before

    def _build(
        self, report: Any, cats: Any, sessions: list[Any], rows: list[Any], total: float, days: int
    ) -> dict[str, Any]:
        # leak findings per session: findings carry the project and the first 8 characters of the session id
        leaks: dict[tuple[str, str], dict[int, dict[str, Any]]] = defaultdict(dict)
        categories = []
        for n, name, group, cost, items, reason, note in rows:
            n = int(n)
            seen = set()
            for i in items:
                key = (str(i["project"]), str(i["session"]))
                seen.add(key)
                slot = leaks[key].setdefault(
                    n,
                    {
                        "row": n,
                        "name": str(name),
                        "group": str(group),
                        "usd": 0.0,
                        "count": 0,
                        "review": n in cats.REVIEW,
                        "details": [],
                    },
                )
                slot["usd"] += float(i["cost"])
                slot["count"] += 1
                slot["details"].append((float(i["cost"]), str(i["detail"])))
            categories.append(
                {
                    "row": n,
                    "name": str(name),
                    "group": str(group),
                    "usd": _money(cost),
                    "count": len(items),
                    "sessions": len(seen),
                    "share": round(float(cost) / total, 4) if total else 0.0,
                    "review": n in cats.REVIEW,
                    "part_of": cats.PART_OF.get(n),
                    "unmeasurable": str(reason or ""),
                    "note": str(note or ""),
                }
            )
        out_sessions, details = [], {}
        by_model: Counter[str] = Counter()
        by_project: Counter[str] = Counter()
        split: Counter[str] = Counter()
        for s in sessions:
            full = self._session(report, s, leaks.get((s.project, s.sid[:8]), {}))
            details[s.sid] = full
            out_sessions.append({k: v for k, v in full.items() if k not in ("tasks", "leaks")})
            by_project[full["project"]] += full["cost_usd"]
            for c in list(s.calls) + list(s.helper_calls):
                by_model[c["model"]] += c["cost"]
                pi, po, pr = report.price(c["model"])
                split["fresh input"] += c["in"] * pi / 1e6
                split["cache write"] += c["cw"] * pi * c["wmult"] / 1e6
                split["cache read"] += c["cr"] * pr / 1e6
                split["output"] += c["out"] * po / 1e6
        out_sessions.sort(key=lambda x: x["started"], reverse=True)
        labelled = sum(1 for s in out_sessions if s["split_by"] == "model")
        return {
            "generated_at": _iso(time.time()),
            "days": days,
            "total_usd": _money(total),
            "sessions": out_sessions,
            "details": details,
            "categories": categories,
            "retired": [
                {"row": int(n), "name": str(t).partition(":")[0], "why": str(t).partition(":")[2].strip()}
                for n, t in cats.RETIRED.items()
            ],
            "spend_by_token_type": [{"name": k, "usd": _money(v)} for k, v in split.most_common()],
            "spend_by_model": [{"name": k, "usd": _money(v)} for k, v in by_model.most_common()],
            "spend_by_project": [{"name": k, "usd": _money(v)} for k, v in by_project.most_common()],
            "task_split": {
                "prompt_check": self.prompt_check,
                "sessions_split_by_model": labelled,
                "sessions_split_by_heuristic": len(out_sessions) - labelled,
                "rules": HOW,
            },
        }

    def _session(self, report: Any, s: Any, leaks: dict[int, dict[str, Any]]) -> dict[str, Any]:
        calls, helpers = list(s.calls), list(s.helper_calls)
        typed = [p for p in s.prompts if report.typed(p)]
        uses = sorted(s.tool_uses.values(), key=lambda u: u["t"])
        tasks = []
        for n, tsk in enumerate(s.tasks(), 1):
            end = tsk["end"]
            mine = tsk["calls"]
            agent = [c for c in helpers if tsk["start"] <= c["t"] < end]
            prompts = [p for p in typed if tsk["start"] <= p["t"] < end]
            tools = [u for u in uses if tsk["start"] <= u["t"] < end]
            edits = [u for u in tools if u["name"] in EDIT_TOOLS]
            last = max([c["t"] for c in mine + agent] or [tsk["start"]])
            cost = sum(c["cost"] for c in mine) + sum(c["cost"] for c in agent)
            tasks.append(
                {
                    "n": n,
                    "title": _title(prompts[0]["text"]) if prompts else "(started by a command or system message)",
                    "started": _iso(tsk["start"]),
                    "ended": _iso(last),
                    "duration_s": int(last - tsk["start"]),
                    "how": str(tsk["by"]),
                    "how_text": HOW.get(str(tsk["by"]), str(tsk["by"])),
                    "tag": tsk["category"],
                    "prompts": len(prompts),
                    "calls": len(mine),
                    "agent_calls": len(agent),
                    "tool_calls": len(tools),
                    "edits": len(edits),
                    "files_edited": len({str(u["input"].get("file_path", "")) for u in edits}),
                    "tools": [
                        {"name": k, "count": v} for k, v in Counter(str(u["name"]) for u in tools).most_common(6)
                    ],
                    "models": sorted({c["model"] for c in mine + agent}),
                    "tokens": _tokens(mine + agent),
                    "cost_usd": _money(cost),
                }
            )
        leak_rows = sorted(leaks.values(), key=lambda x: -x["usd"])
        for row in leak_rows:
            row["usd"] = _money(row["usd"])
            row["details"] = [d for _, d in sorted(row["details"], reverse=True)[:3]]
        waste = [r for r in leak_rows if not r["review"]]
        every = calls + helpers
        start, end = min(c["t"] for c in every), max(c["t"] for c in every)
        return {
            "id": s.sid,
            "short": s.sid[:8],
            "project": Path(s.cwd).name if s.cwd else str(s.project),
            "project_path": str(s.cwd or ""),
            "title": _title(typed[0]["text"]) if typed else "(no typed prompt)",
            "started": _iso(start),
            "ended": _iso(end),
            "duration_s": int(end - start),
            "models": sorted({c["model"] for c in every}),
            "calls": len(calls),
            "agent_calls": len(helpers),
            "agents": len(s.agents),
            "prompts": len(typed),
            "compactions": len(s.compactions),
            "tokens": _tokens(every),
            "peak_context": max((c["ctx"] for c in calls), default=0),
            "cost_usd": _money(s.cost + s.helper_cost),
            "agent_cost_usd": _money(s.helper_cost),
            "task_count": len(tasks),
            "split_by": "model" if s.prompt_labels else "heuristic",
            "leak_usd": _money(sum(r["usd"] for r in waste)),
            "leak_count": sum(r["count"] for r in waste),
            "top_leak": {"row": waste[0]["row"], "name": waste[0]["name"], "usd": waste[0]["usd"]} if waste else None,
            "tasks": tasks,
            "leaks": leak_rows,
        }

    # ---------------------------------------------------------------- views
    def overview(self, days: int = 30) -> dict[str, Any]:
        """Everything but the per-session task and leak lists."""
        data = self._analysed(days)
        return {k: v for k, v in data.items() if k != "details"}

    def session(self, session_id: str, days: int = 30) -> dict[str, Any] | None:
        """One session with its tasks and leak categories. Accepts the full id or its first 8 characters."""
        details: dict[str, Any] = self._analysed(days)["details"]
        if session_id in details:
            return dict(details[session_id])
        return next((dict(v) for k, v in details.items() if k.startswith(session_id) and len(session_id) >= 8), None)


def open_session_views(transcripts_root: str, state_dir: str, prompt_check: bool = False) -> SessionViews:
    return SessionViews(
        Path(transcripts_root).expanduser(),
        Path(state_dir).expanduser(),
        prompt_check=prompt_check,
        seed_labels_from=Path("~/.claude/metrics").expanduser(),
    )
