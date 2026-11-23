"""The policy engine: runs the registered features in order and applies each one's flag (plan/05, "Request flow").

Policy file `policy.json` in the state directory:
    {"order": ["budgets", "turn_cap", "loop_guard"],
     "features": {"budgets": {"mode": "enforced", "limits": [...]}, "turn_cap": {"mode": "advisory", "default": 60}}}
Every feature is off unless the file says otherwise. `advisory` records what the feature would have done and blocks
nothing. The file is re-read when it changes, so a budget set from the CLI applies without a restart.

Rewrites (P2): after every `before` has allowed a request, features that also implement `rewrite` may change the
body, in policy order. Enforced rewrites are sent; advisory ones are logged as `would_rewrite` and the original is sent.
A rewriter that raises is skipped (rewrites always fail open) and each one gets its own copy, so a broken one cannot
corrupt the request. With no rewrite applied the original bytes go upstream untouched.

Rollout (P3): a feature section may carry per-tenant modes and a canary, and `kill.json` beside the policy file turns a
feature off for one tenant or all. Per request: killed → off; else the tenant's own mode, else the section's mode; then
with a canary only sessions whose `canary_slot` falls below the share (and, if listed, only those tenants) get it, the
rest run without it. Both files are re-read when they change, so a kill or rollback needs no deploy:
    {"features": {"output_cap": {"mode": "enforced", "tenants": {"acme": "off"},
                                 "canary": {"share": 0.05, "tenants": ["devx"]}}}}

Failure posture (plan/08): a feature that raises is skipped (fail open), unless it is enforced and declares
`fail_closed` (budgets), in which case the request is refused. Every block, would-block and failure is appended to
`decisions.jsonl` as metadata only.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from token_economics_contracts import (
    ALLOW,
    FEATURES,
    KILL_FILE,
    Decision,
    Feature,
    FeatureEnv,
    KillFile,
    LedgerRow,
    PolicyMode,
    RequestContext,
    Rewriter,
    RewrittenRequest,
    canary_slot,
    load,
)

POLICY_NAME, DECISIONS_NAME = "policy.json", "decisions.jsonl"
DEFAULT_ORDER = ("budgets", "turn_cap", "loop_guard")
Factory = Callable[[FeatureEnv], Feature]
ROLLOUT_KEYS = ("mode", "tenants", "canary")  # policy keys the engine reads; the rest is the feature's own config


@dataclass(frozen=True)
class Rollout:
    """Who gets a feature: the section's mode, per-tenant modes and an optional canary slice."""

    mode: PolicyMode
    tenants: dict[str, PolicyMode] = field(default_factory=dict)
    canary_share: float | None = None
    canary_tenants: frozenset[str] = frozenset()

    @classmethod
    def parse(cls, section: Mapping[str, Any]) -> Rollout:
        raw = section.get("tenants")
        tenants = {str(t): mode_of({"mode": m}) for t, m in raw.items()} if isinstance(raw, dict) else {}
        canary = section.get("canary")
        share: float | None = None
        listed: frozenset[str] = frozenset()
        if isinstance(canary, dict):
            value = canary.get("share")
            if isinstance(value, int | float) and not isinstance(value, bool) and 0 <= value <= 1:
                share = float(value)
            else:
                share = 0.0  # a canary that cannot be read covers nobody, never everybody
            names = canary.get("tenants")
            listed = frozenset(str(t) for t in names) if isinstance(names, list) else frozenset()
        return cls(mode_of(section), tenants, share, listed)

    @property
    def can_run(self) -> bool:
        return self.mode is not PolicyMode.OFF or any(m is not PolicyMode.OFF for m in self.tenants.values())

    def for_request(self, feature: str, ctx: RequestContext) -> tuple[PolicyMode, bool]:
        """(mode, in_canary) for one request."""
        tenant = ctx.key.tenant
        mode = self.tenants.get(tenant, self.mode)
        if mode is PolicyMode.OFF or self.canary_share is None:
            return mode, False
        if self.canary_tenants and tenant not in self.canary_tenants:
            return PolicyMode.OFF, False
        inside = canary_slot(ctx.identity.session_id or ctx.request_id, feature) < self.canary_share
        return (mode, True) if inside else (PolicyMode.OFF, False)


def read_policy(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def mode_of(section: Mapping[str, Any]) -> PolicyMode:
    try:
        return PolicyMode(str(section.get("mode", "off")))
    except ValueError:
        return PolicyMode.OFF


class PolicyService:
    def __init__(
        self,
        state_dir: Path,
        pricebook: Any = None,
        calculator: Any = None,
        factories: Mapping[str, Factory] | None = None,
    ) -> None:
        self._state, self._pricebook, self._calculator = state_dir, pricebook, calculator
        self._factories = factories
        self._path, self._decisions = state_dir / POLICY_NAME, state_dir / DECISIONS_NAME
        self._lock, self._log_lock = Lock(), Lock()
        self._stamp: tuple[int, int] | None = (-1, -1)
        self._active: list[tuple[Feature, PolicyMode]] = []
        self._rollouts: dict[str, Rollout] = {}
        self._kill_path = state_dir / KILL_FILE
        self._kill_stamp: tuple[int, int] | None = (-1, -1)
        self._kill = KillFile()
        self.problems: list[str] = []

    # -- configuration -----------------------------------------------------------------
    def _file_stamp(self, path: Path | None = None) -> tuple[int, int] | None:
        try:
            st = (path or self._path).stat()
            return (st.st_mtime_ns, st.st_size)
        except OSError:
            return None

    def _features(self) -> list[tuple[Feature, PolicyMode]]:
        """The active features, rebuilt when the policy file changes."""
        stamp = self._file_stamp()
        if stamp == self._stamp:
            return self._active
        with self._lock:
            if stamp == self._stamp:
                return self._active
            policy = read_policy(self._path) if stamp is not None else {}
            raw = policy.get("features")
            sections: dict[str, Any] = raw if isinstance(raw, dict) else {}
            rollouts = {n: Rollout.parse(s) for n, s in sections.items() if isinstance(s, dict)}
            wanted = {n: sections[n] for n, r in rollouts.items() if r.can_run}
            order = [n for n in (policy.get("order") or DEFAULT_ORDER) if n in wanted]
            order += sorted(n for n in wanted if n not in order)
            active, problems = [], []
            for name in order:
                section, mode = wanted[name], mode_of(wanted[name])
                config = {k: v for k, v in section.items() if k not in ROLLOUT_KEYS}
                try:
                    # Only switched-on features are loaded, one at a time: a broken package breaks itself, not all.
                    if self._factories is None:
                        factory = load(FEATURES, name)
                    elif name in self._factories:
                        factory = self._factories[name]
                    else:
                        raise LookupError(f"no feature registered as {name!r}")
                    env = FeatureEnv(
                        state_dir=self._state, config=config, pricebook=self._pricebook, calculator=self._calculator
                    )
                    active.append((factory(env), mode))
                except Exception as exc:
                    # A feature that cannot start is a problem to show, never a silent pass for an enforced budget.
                    problems.append(f"{name}: {type(exc).__name__}: {exc}")
                    active.append((_Broken(name, f"{type(exc).__name__}: {exc}"), mode))
            self._active, self.problems, self._stamp = active, problems, stamp
            self._rollouts = {n: rollouts[n] for n in order}
            for p in problems:
                self._log({"action": "config_error", "detail": p})
            return self._active

    def modes(self) -> dict[str, str]:
        return {f.name: m.value for f, m in self._features()}

    def kills(self) -> KillFile:
        """The kill file, re-read when it changes. Unreadable means no kills, and is reported as a problem."""
        stamp = self._file_stamp(self._kill_path)
        if stamp == self._kill_stamp:
            return self._kill
        with self._lock:
            if stamp != self._kill_stamp:
                kill = KillFile()
                if stamp is not None:
                    try:
                        kill = KillFile.model_validate_json(self._kill_path.read_text())
                    except (OSError, ValueError) as exc:
                        self._log({"action": "config_error", "detail": f"{KILL_FILE}: {type(exc).__name__}"})
                self._kill, self._kill_stamp = kill, stamp
            return self._kill

    def _for(self, ctx: RequestContext) -> list[tuple[Feature, PolicyMode, bool]]:
        """The features that apply to this request, with their mode and whether it is a canary request."""
        active, kills = self._features(), self.kills()
        out: list[tuple[Feature, PolicyMode, bool]] = []
        for feature, base in active:
            if kills.killed(feature.name, ctx.key.tenant):
                continue
            rollout = self._rollouts.get(feature.name)
            mode, canary = rollout.for_request(feature.name, ctx) if rollout else (base, False)
            if mode is not PolicyMode.OFF:
                out.append((feature, mode, canary))
        return out

    # -- request path --------------------------------------------------------------------
    def before(self, ctx: RequestContext) -> Decision:
        passed: list[Feature] = []
        for feature, mode, _ in self._for(ctx):
            try:
                decision = feature.before(ctx)
            except Exception as exc:
                closed = feature.fail_closed and mode is PolicyMode.ENFORCED
                self._log_decision(
                    ctx,
                    feature.name,
                    mode,
                    "feature_error",
                    "blocked" if closed else "failed_open",
                    503 if closed else 0,
                    detail=type(exc).__name__,
                )
                if not closed:
                    continue
                self._release(passed, ctx, 503)
                return Decision(
                    allow=False,
                    feature=feature.name,
                    status=503,
                    code="policy_unavailable",
                    message=f"Token Economics: the {feature.name} check is unavailable, so this request "
                    "was refused. Try again shortly or contact an admin.",
                )
            if decision is None or decision.allow:
                passed.append(feature)
                continue
            if mode is PolicyMode.ADVISORY:
                self._log_decision(ctx, feature.name, mode, decision.code, "would_block", decision.status)
                passed.append(feature)  # it may hold state (a reservation) that after() must release
                continue
            self._log_decision(ctx, feature.name, mode, decision.code, "blocked", decision.status)
            self._release(passed, ctx, decision.status)
            return decision.model_copy(update={"feature": decision.feature or feature.name})
        return ALLOW

    def rewrite(self, ctx: RequestContext, body: bytes) -> RewrittenRequest | None:
        rewriters = [(f, m, c) for f, m, c in self._for(ctx) if isinstance(f, Rewriter)]
        if not rewriters:
            return None
        try:
            current = json.loads(body)
        except ValueError:
            return None
        if not isinstance(current, dict):
            return None
        applied: list[str] = []
        headers: list[tuple[str, str]] = []
        for feature, mode, canary in rewriters:
            try:
                result = feature.rewrite(ctx, copy.deepcopy(current))
            except Exception as exc:
                self._log_decision(
                    ctx, feature.name, mode, "rewrite_error", "failed_open", 0, detail=type(exc).__name__
                )
                continue
            if result is None or result.body == current:
                continue
            changes = [c[:200] for c in result.changes]
            if mode is PolicyMode.ADVISORY:
                self._log_decision(
                    ctx, feature.name, mode, "rewrite", "would_rewrite", 0, changes=changes, canary=canary
                )
                continue
            current = result.body
            applied.append(feature.name)
            headers += [(k, v) for k, v in result.add_headers if (k, v) not in headers]
            self._log_decision(ctx, feature.name, mode, "rewrite", "rewritten", 0, changes=changes, canary=canary)
        if not applied:
            return None
        return RewrittenRequest(
            body=json.dumps(current, ensure_ascii=False, separators=(",", ":")).encode(),
            add_headers=tuple(headers),
            features=tuple(applied),
        )

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        self._release([f for f, _ in self._features()], ctx, status, row)

    def _release(self, features: list[Feature], ctx: RequestContext, status: int, row: LedgerRow | None = None) -> None:
        for feature in features:
            try:
                feature.after(ctx, row, status)
            except Exception as exc:
                self._log_decision(ctx, feature.name, None, "after_error", "failed_open", 0, detail=type(exc).__name__)

    # -- decisions log ---------------------------------------------------------------------
    def _log_decision(
        self,
        ctx: RequestContext,
        feature: str,
        mode: PolicyMode | None,
        code: str,
        action: str,
        status: int,
        detail: str = "",
        changes: list[str] | None = None,
        canary: bool = False,
    ) -> None:
        self._log(
            {
                "feature": feature,
                "mode": mode.value if mode else "",
                "code": code,
                "action": action,
                "status": status,
                "tenant": ctx.key.tenant,
                "team": ctx.key.team,
                "caller": ctx.key.caller,
                "session_id": ctx.identity.session_id,
                "harness": ctx.harness,
                "model": ctx.facts.model,
                "request_id": ctx.request_id,
                **({"detail": detail} if detail else {}),
                **({"changes": changes} if changes else {}),
                **({"canary": True} if canary else {}),
            }
        )

    def _log(self, record: dict[str, Any]) -> None:
        try:
            with self._log_lock, self._decisions.open("a") as f:
                f.write(json.dumps({"ts": datetime.now(UTC).isoformat(), **record}) + "\n")
        except OSError:
            pass


class _Broken:
    """Stands in for a feature that could not be built: always raises, so the engine applies the failure posture."""

    fail_closed = True

    def __init__(self, name: str, why: str) -> None:
        self.name, self._why = name, why

    def before(self, ctx: RequestContext) -> Decision | None:
        raise RuntimeError(self._why)

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        return None


def open_policy(state_dir: str, pricebook: Any = None, calculator: Any = None) -> PolicyService:
    return PolicyService(Path(state_dir), pricebook, calculator)
