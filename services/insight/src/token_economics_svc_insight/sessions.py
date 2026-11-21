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


def _ratio(part: float, whole: float) -> float | None:
    return round(part / whole, 4) if whole else None


def _target(inp: Any) -> str:
    """What a tool call was aimed at: a file name, a command or a pattern, shortened. Shown locally only."""
    for key in ("file_path", "notebook_path", "command", "pattern", "url", "query", "description", "skill"):
        value = inp.get(key)
        if value:
            text = Path(str(value)).name if key in ("file_path", "notebook_path") else " ".join(str(value).split())
            return text if len(text) <= 80 else text[:79] + "…"
    return ""


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
            out_sessions.append({k: v for k, v in full.items() if k not in ("tasks", "leaks", "task_details")})
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
        task_details: dict[int, dict[str, Any]] = {}
        for n, tsk in enumerate(s.tasks(), 1):
            end = tsk["end"]
            mine = tsk["calls"]
            agent = [c for c in helpers if tsk["start"] <= c["t"] < end]
            prompts = [p for p in typed if tsk["start"] <= p["t"] < end]
            tools = [u for u in uses if tsk["start"] <= u["t"] < end]
            edits = [u for u in tools if u["name"] in EDIT_TOOLS]
            last = max([c["t"] for c in mine + agent] or [tsk["start"]])
            cost = sum(c["cost"] for c in mine) + sum(c["cost"] for c in agent)
            task_details[n] = self._task_detail(report, s, tsk, mine, agent, prompts)
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
            "task_details": task_details,
        }

    def _task_detail(
        self, report: Any, s: Any, tsk: Any, mine: list[Any], agent: list[Any], prompts: list[Any]
    ) -> dict[str, Any]:
        """Everything about one task beyond its summary line. Built from the same calls the summary counts."""
        start, end = tsk["start"], tsk["end"]
        every = sorted(mine + agent, key=lambda c: c["t"])
        spend = {"fresh input": 0.0, "cache write": 0.0, "cache read": 0.0, "output": 0.0}
        by_model: Counter[str] = Counter()
        for c in every:
            pi, po, pr = report.price(c["model"])
            spend["fresh input"] += c["in"] * pi / 1e6
            spend["cache write"] += c["cw"] * pi * c["wmult"] / 1e6
            spend["cache read"] += c["cr"] * pr / 1e6
            spend["output"] += c["out"] * po / 1e6
            by_model[c["model"]] += c["cost"]

        # tools: every call in the task (main thread and agents) with its result
        results = {r["id"]: r for r in list(s.results) + list(s.helper_results) if start <= r["t"] < end}
        uses = list(s.tool_uses.items()) + list(s.helper_tool_uses.items())
        per_tool: dict[str, dict[str, Any]] = {}
        files: dict[str, dict[str, Any]] = {}
        biggest = []
        for uid, u in uses:
            if not start <= u["t"] < end:
                continue
            name, r = str(u["name"]), results.get(uid)
            row = per_tool.setdefault(
                name, {"name": name, "calls": 0, "failed": 0, "result_tokens": 0, "input_tokens": 0}
            )
            size = (r["tokens"] + r["image_tokens"]) if r else 0
            row["calls"] += 1
            row["failed"] += bool(r and r["is_error"])
            row["result_tokens"] += size
            row["input_tokens"] += s.tok(len(str(u["input"])))
            path = str(u["input"].get("file_path") or u["input"].get("notebook_path") or "")
            if path:
                f = files.setdefault(path, {"file": Path(path).name, "path": path, "reads": 0, "edits": 0, "tokens": 0})
                f["reads"] += name == "Read"
                f["edits"] += name in EDIT_TOOLS
                f["tokens"] += size
            if r:
                biggest.append(
                    {
                        "tool": name,
                        "target": _target(u["input"]),
                        "tokens": size,
                        "failed": bool(r["is_error"]),
                        "at": _iso(r["t"]),
                        "agent": bool(r.get("agent")),
                    }
                )

        # turns: one per typed prompt, with the model calls it started
        marks = [p["t"] for p in prompts] + [end]
        turns = []
        for k, p in enumerate(prompts):
            mc = [c for c in every if marks[k] <= c["t"] < marks[k + 1]]
            turns.append(
                {
                    "n": k + 1,
                    "at": _iso(p["t"]),
                    "title": _title(p["text"]),
                    "calls": len(mc),
                    "tool_calls": sum(c["n_tools"] for c in mc),
                    "output_tokens": sum(c["out"] for c in mc),
                    "cost_usd": _money(sum(c["cost"] for c in mc)),
                }
            )

        # timeline: one row per model call, in order
        timeline = []
        for c in every:
            names = Counter(str(b.get("name")) for b in c["blocks"] if b.get("type") == "tool_use")
            timeline.append(
                {
                    "at": _iso(c["t"]),
                    "model": c["model"],
                    "agent": bool(c["helper"]),
                    "context": c["ctx"],
                    "fresh_input": c["in"],
                    "cache_read": c["cr"],
                    "cache_write": c["cw"],
                    "output": c["out"],
                    "thinking": c["think"] or 0,
                    "cost_usd": _money(c["cost"]),
                    "tools": [{"name": k, "count": v} for k, v in names.items()],
                }
            )
        agents = []
        for calls in s.agents.values():
            inside = [c for c in calls if start <= c["t"] < end]
            if inside:
                agents.append(
                    {
                        "started": _iso(inside[0]["t"]),
                        "model": inside[0]["model"],
                        "calls": len(inside),
                        "tool_calls": sum(c["n_tools"] for c in inside),
                        "start_context": inside[0]["ctx"],
                        "cost_usd": _money(sum(c["cost"] for c in inside)),
                    }
                )
        ctx = [c["ctx"] for c in mine]
        gaps = [b["t"] - a["t"] for a, b in zip(mine, mine[1:], strict=False)]
        rewrites = sum(
            1 for c, g in zip(mine[1:], gaps, strict=False) if g >= self._ttl_s and c["cw"] > max(5_000, 0.5 * c["ctx"])
        )
        return {
            "spend_by_token_type": [
                {"name": k, "usd": _money(v)} for k, v in sorted(spend.items(), key=lambda kv: -kv[1])
            ],
            "spend_by_model": [{"name": k, "usd": _money(v)} for k, v in by_model.most_common()],
            "main_cost_usd": _money(sum(c["cost"] for c in mine)),
            "agent_cost_usd": _money(sum(c["cost"] for c in agent)),
            "thinking_tokens": sum(c["think"] or 0 for c in every),
            "context": {
                "start": ctx[0] if ctx else 0,
                "end": ctx[-1] if ctx else 0,
                "peak": max(ctx, default=0),
                "series": ctx,
            },
            "cache": {
                "hit_rate": _ratio(sum(c["cr"] for c in every), sum(c["ctx"] for c in every)),
                "rewrites_after_idle": rewrites,
                "longest_idle_s": int(max(gaps, default=0)),
            },
            "counts": {
                "failed_tool_calls": sum(t["failed"] for t in per_tool.values()),
                "interrupted": sum(1 for t in s.interrupts if start <= t < end),
                "compactions": sum(1 for t in s.comp_sorted if start <= t < end),
                "agents": len(agents),
            },
            "tools": sorted(per_tool.values(), key=lambda t: -t["calls"]),
            "files": sorted(files.values(), key=lambda f: (-f["edits"], -f["tokens"]))[:40],
            "largest_results": sorted(biggest, key=lambda b: -b["tokens"])[:15],
            "turns": turns,
            "timeline": timeline,
            "agents": sorted(agents, key=lambda a: -a["cost_usd"]),
        }

    # ---------------------------------------------------------------- views
    def overview(self, days: int = 30) -> dict[str, Any]:
        """Everything but the per-session task and leak lists."""
        data = self._analysed(days)
        return {k: v for k, v in data.items() if k != "details"}

    def session(self, session_id: str, days: int = 30) -> dict[str, Any] | None:
        """One session with its tasks and leak categories. Accepts the full id or its first 8 characters."""
        found = self._find(session_id, days)
        return {k: v for k, v in found.items() if k != "task_details"} if found else None

    def task(self, session_id: str, n: int, days: int = 30) -> dict[str, Any] | None:
        """One task of a session in full: spend by token type, tools, files, largest results, turns, call timeline."""
        found = self._find(session_id, days)
        if not found or n not in found["task_details"]:
            return None
        summary = next(t for t in found["tasks"] if t["n"] == n)
        session = {k: found[k] for k in ("id", "short", "project", "title", "cost_usd", "task_count", "split_by")}
        share = _ratio(summary["cost_usd"], found["cost_usd"])
        return {**summary, **found["task_details"][n], "session": session, "share_of_session": share}

    def _find(self, session_id: str, days: int) -> dict[str, Any] | None:
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
