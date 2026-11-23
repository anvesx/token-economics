"""Auto-rollback (plan/07, Rollout). For each feature with a canary, compare the canary sessions with the control
sessions of the same tenants over the last day of ledger rows. A trigger that fires kills the feature through the kill
switch, so the next request goes to the provider unchanged; no deploy.

Triggers (thresholds are DevX proposals in `<state>/rollout.json`, all with defaults):
  cost       mean cost per session above the control's: the seeded bootstrap interval of the difference (canary minus
             control, both samples resampled) lies wholly above zero. Comparing the canary mean with the control's
             interval alone ignores the canary's own noise and fires on a third of healthy 5% canaries.
  errors     share of non-2xx rows above the control's share plus `error_margin`, and a one-sided two-proportion test
             below `error_alpha`
The check runs repeatedly over a sliding window, so false alarms add up; keep `level` high and `error_alpha` small.
  success    only with `<state>/outcomes.jsonl`: canary success rate below the control's minus `success_drop_pp`
  cache_hit  cache_read over prompt tokens below the control's minus `hit_drop`
  billing    only with `<state>/reconciliation.jsonl`: the latest line off by more than `billing_tolerance`; pricing is
             wrong, so every canaried feature is killed

p95 latency is not checked: the ledger has no latency. Files that cannot be read are reported, never raised.
"""

from __future__ import annotations

import contextlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from token_economics_contracts import SERVICES, LedgerRow, canary_slot, load
from token_economics_stats import mean_diff_interval, two_proportion_p

from .kill import open_kill

LATENCY_NOTE = "p95 latency is not measurable: the ledger has no latency"
DEFAULTS: dict[str, Any] = {  # DevX proposals until P2 measures them
    "window_hours": 24,
    "min_sessions": 30,
    "error_margin": 0.02,
    "error_alpha": 0.01,
    "success_drop_pp": 5,
    "hit_drop": 0.10,
    "billing_tolerance": 0.05,
    "level": 0.95,
    "n_boot": 1000,
    "seed": 0,
}
ORDER = ("cost", "errors", "success", "cache_hit", "billing")


@dataclass
class _Session:
    tenant: str
    cost: Decimal = Decimal(0)
    rows: int = 0
    errors: int = 0
    cache_read: int = 0
    prompt: int = 0


@dataclass
class _Side:
    sessions: dict[str, _Session] = field(default_factory=dict)

    def costs(self) -> list[float]:
        return [float(s.cost) for s in self.sessions.values()]

    def error_counts(self) -> tuple[int, int]:
        return sum(s.errors for s in self.sessions.values()), sum(s.rows for s in self.sessions.values())

    def error_share(self) -> float:
        rows = sum(s.rows for s in self.sessions.values())
        return sum(s.errors for s in self.sessions.values()) / rows if rows else 0.0

    def hit_rate(self) -> float | None:
        prompt = sum(s.prompt for s in self.sessions.values())
        return sum(s.cache_read for s in self.sessions.values()) / prompt if prompt else None


def _jsonl(path: Path, problems: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        text = path.read_text()
    except FileNotFoundError:
        return out
    except OSError as exc:
        problems.append(f"{path.name}: {exc}")
        return out
    bad = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError:
            bad += 1
            continue
        if isinstance(value, dict):
            out.append(value)
        else:
            bad += 1
    if bad:
        problems.append(f"{path.name}: {bad} unreadable line(s) skipped")
    return out


class Rollback:
    def __init__(self, state_dir: Path, kills: Any = None) -> None:
        self._dir = state_dir
        self._kills = kills if kills is not None else open_kill(str(state_dir))

    # ------------------------------------------------------------ inputs

    def _config(self, problems: list[str]) -> dict[str, Any]:
        cfg = dict(DEFAULTS)
        try:
            raw = json.loads((self._dir / "rollout.json").read_text())
        except FileNotFoundError:
            return cfg
        except (OSError, ValueError) as exc:
            problems.append(f"rollout.json: {exc}; defaults used")
            return cfg
        if not isinstance(raw, dict):
            problems.append("rollout.json: not an object; defaults used")
            return cfg
        for key, default in DEFAULTS.items():
            if key in raw:
                if isinstance(raw[key], (int, float)) and not isinstance(raw[key], bool):
                    cfg[key] = type(default)(raw[key]) if isinstance(default, int) else float(raw[key])
                else:
                    problems.append(f"rollout.json: {key} is not a number; default used")
        return cfg

    def _canaried(self, problems: list[str]) -> dict[str, dict[str, Any]]:
        try:
            policy = json.loads((self._dir / "policy.json").read_text())
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as exc:
            problems.append(f"policy.json: {exc}")
            return {}
        features = policy.get("features") if isinstance(policy, dict) else None
        if not isinstance(features, dict):
            return {}
        return {n: s for n, s in features.items() if isinstance(s, dict) and isinstance(s.get("canary"), dict)}

    def _rows(self, since: datetime, now: datetime, problems: list[str]) -> list[LedgerRow]:
        path = self._dir / "ledger.sqlite"
        if not path.exists():
            return []
        try:
            return list(load(SERVICES, "ledger")(str(path)).rows(since, now))
        except Exception as exc:  # a locked or damaged ledger must not stop the other checks
            problems.append(f"ledger: {exc}")
            return []

    def _outcomes(self, problems: list[str]) -> dict[str, bool] | None:
        path = self._dir / "outcomes.jsonl"
        if not path.exists():
            return None
        return {
            str(x["session_id"]): bool(x["success"])
            for x in _jsonl(path, problems)
            if "session_id" in x and "success" in x
        }

    # ------------------------------------------------------------ evaluation

    @staticmethod
    def _split(feature: str, section: dict[str, Any], rows: Iterable[LedgerRow]) -> tuple[_Side, _Side]:
        canary_cfg = section["canary"]
        try:
            share = float(canary_cfg.get("share", 0.0))
        except (TypeError, ValueError):
            share = 0.0
        listed = canary_cfg.get("tenants")
        tenants = {str(t) for t in listed} if isinstance(listed, list) else set()
        raw_overrides = section.get("tenants")
        overrides: dict[str, Any] = raw_overrides if isinstance(raw_overrides, dict) else {}
        base = str(section.get("mode", "off"))
        canary, control = _Side(), _Side()
        for row in rows:
            if not row.session_id or (tenants and row.tenant not in tenants):
                continue
            if str(overrides.get(row.tenant, base)) == "off":
                continue
            side = canary if canary_slot(row.session_id, feature) < share else control
            s = side.sessions.setdefault(row.session_id, _Session(row.tenant))
            s.rows += 1
            s.errors += not 200 <= row.http_status < 300
            if row.cost_estimate_usd is not None:
                s.cost += row.cost_estimate_usd
            s.cache_read += row.buckets.cache_read
            s.prompt += row.buckets.prompt_tokens
        return canary, control

    def _billing(self, cfg: dict[str, Any], problems: list[str]) -> dict[str, Any]:
        lines = _jsonl(self._dir / "reconciliation.jsonl", problems)
        if not lines:
            return {"status": "n/a", "note": "no reconciliation.jsonl"}
        latest = max(enumerate(lines), key=lambda p: (str(p[1].get("date", "")), p[0]))[1]
        try:
            billed, est = Decimal(str(latest["billed_usd"])), Decimal(str(latest["estimated_usd"]))
        except (KeyError, InvalidOperation):
            problems.append("reconciliation.jsonl: the latest line has no usable billed_usd and estimated_usd")
            return {"status": "n/a", "note": "unreadable latest line"}
        if est == 0:
            return {"status": "n/a", "note": "estimated_usd is zero"}
        gap = abs(float(billed / est) - 1)
        out = {"status": "breach" if gap > cfg["billing_tolerance"] else "ok", "gap": round(gap, 4)}
        return out | {
            "date": latest.get("date", ""),
            "provider": latest.get("provider", ""),
            "tolerance": cfg["billing_tolerance"],
        }

    def _triggers(
        self, canary: _Side, control: _Side, cfg: dict[str, Any], outcomes: dict[str, bool] | None
    ) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        enough = min(len(canary.sessions), len(control.sessions)) >= cfg["min_sessions"]
        if not enough:
            for name in ("cost", "errors", "cache_hit"):
                out[name] = {"status": "insufficient data"}
        else:
            c_cost, k_cost = canary.costs(), control.costs()
            diff = mean_diff_interval(c_cost, k_cost, cfg["level"], cfg["n_boot"], cfg["seed"])
            out["cost"] = {
                "status": "breach" if diff and diff[0] > 0 else "ok",
                "canary_mean_usd": round(sum(c_cost) / len(c_cost), 6),
                "control_mean_usd": round(sum(k_cost) / len(k_cost), 6),
                "diff_interval_usd": [round(diff[0], 6), round(diff[1], 6)] if diff else None,
            }
            ce, ke = canary.error_share(), control.error_share()
            p_err = two_proportion_p(*canary.error_counts(), *control.error_counts())
            out["errors"] = {
                "status": "breach" if ce > ke + cfg["error_margin"] and p_err < cfg["error_alpha"] else "ok",
                "canary": round(ce, 4),
                "control": round(ke, 4),
                "margin": cfg["error_margin"],
                "p": round(p_err, 6),
            }
            ch, kh = canary.hit_rate(), control.hit_rate()
            if ch is None or kh is None:
                out["cache_hit"] = {"status": "n/a", "note": "no prompt tokens"}
            else:
                out["cache_hit"] = {
                    "status": "breach" if ch < kh - cfg["hit_drop"] else "ok",
                    "canary": round(ch, 4),
                    "control": round(kh, 4),
                    "drop": cfg["hit_drop"],
                }
        out["success"] = self._success(canary, control, cfg, outcomes)
        return out

    @staticmethod
    def _success(
        canary: _Side, control: _Side, cfg: dict[str, Any], outcomes: dict[str, bool] | None
    ) -> dict[str, Any]:
        if outcomes is None:
            return {"status": "n/a", "note": "no outcomes.jsonl"}
        c = [outcomes[s] for s in canary.sessions if s in outcomes]
        k = [outcomes[s] for s in control.sessions if s in outcomes]
        if min(len(c), len(k)) < cfg["min_sessions"]:
            return {"status": "insufficient data", "canary_n": len(c), "control_n": len(k)}
        cr, kr = sum(c) / len(c), sum(k) / len(k)
        return {
            "status": "breach" if cr < kr - cfg["success_drop_pp"] / 100 else "ok",
            "canary": round(cr, 4),
            "control": round(kr, 4),
            "drop_pp": cfg["success_drop_pp"],
        }

    # ------------------------------------------------------------ the check

    def check(self, now: datetime | None = None) -> list[dict[str, Any]]:
        now = now or datetime.now(UTC)
        problems: list[str] = []
        cfg = self._config(problems)
        canaried = self._canaried(problems)
        rows = self._rows(now - timedelta(hours=cfg["window_hours"]), now, problems) if canaried else []
        outcomes = self._outcomes(problems) if canaried else None
        billing = self._billing(cfg, problems) if canaried else {"status": "n/a"}
        killed: set[str] | None
        try:
            killed = {k.feature for k in self._kills.list() if k.tenant == "*"}
        except Exception as exc:  # a broken kill.json: report it and take no action
            problems.append(f"kill.json: {exc}")
            killed = None
        results: list[dict[str, Any]] = []
        for feature, section in canaried.items():
            canary, control = self._split(feature, section, rows)
            triggers = self._triggers(canary, control, cfg, outcomes)
            triggers["billing"] = billing
            breached = {n: triggers[n] for n in ORDER if triggers[n]["status"] == "breach"}
            result: dict[str, Any] = {
                "feature": feature,
                "sessions": {"canary": len(canary.sessions), "control": len(control.sessions)},
                "status": "insufficient data"
                if all(t["status"] in ("insufficient data", "n/a") for t in triggers.values())
                and any(t["status"] == "insufficient data" for t in triggers.values())
                else "ok",
                "triggers": triggers,
                "action": "none",
                "latency": LATENCY_NOTE,
                "problems": problems,
            }
            if killed is None:
                result["action"] = "error" if breached else "none"
            elif feature in killed:
                result["action"] = "already_killed"
            elif breached:
                result["status"] = "breach"
                result["action"] = self._act(feature, breached, now, problems)
            results.append(result)
        if problems and not results:
            results.append({"feature": "", "status": "error", "action": "none", "problems": problems})
        return results

    def _act(self, feature: str, breached: dict[str, dict[str, Any]], now: datetime, problems: list[str]) -> str:
        first = next(iter(breached))
        reason = "; ".join(
            f"{n}: {json.dumps({k: v for k, v in t.items() if k != 'status'})}" for n, t in breached.items()
        )
        try:
            self._kills.add(feature, "*", reason=reason, by=f"rollback:{first}")
        except Exception as exc:
            problems.append(f"kill: {exc}")
            return "error"
        record = {"ts": now.isoformat(), "feature": feature, "trigger": first, "numbers": breached}
        for name, body in (
            ("rollbacks.jsonl", record),
            (
                "alerts.jsonl",
                {"ts": now.isoformat(), "kind": "rollback", "feature": feature, "trigger": first, "reason": reason},
            ),
        ):
            with contextlib.suppress(OSError), (self._dir / name).open("a") as f:
                f.write(json.dumps(body) + "\n")
        return "killed"


def open_rollback(state_dir: str) -> Rollback:
    return Rollback(Path(state_dir))
