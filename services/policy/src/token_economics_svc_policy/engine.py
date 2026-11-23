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

Failure posture (plan/08): a feature that raises is skipped (fail open), unless it is enforced and declares
`fail_closed` (budgets), in which case the request is refused. Every block, would-block and failure is appended to
`decisions.jsonl` as metadata only.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from token_economics_contracts import (
    ALLOW,
    FEATURES,
    Decision,
    Feature,
    FeatureEnv,
    LedgerRow,
    PolicyMode,
    RequestContext,
    Rewriter,
    RewrittenRequest,
    load_all,
)

POLICY_NAME, DECISIONS_NAME = "policy.json", "decisions.jsonl"
DEFAULT_ORDER = ("budgets", "turn_cap", "loop_guard")
Factory = Callable[[FeatureEnv], Feature]


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
        self.problems: list[str] = []

    # -- configuration -----------------------------------------------------------------
    def _file_stamp(self) -> tuple[int, int] | None:
        try:
            st = self._path.stat()
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
            wanted = {n: s for n, s in sections.items() if isinstance(s, dict) and mode_of(s) is not PolicyMode.OFF}
            factories = dict(self._factories) if self._factories is not None else (load_all(FEATURES) if wanted else {})
            order = [n for n in (policy.get("order") or DEFAULT_ORDER) if n in wanted]
            order += sorted(n for n in wanted if n not in order)
            active, problems = [], []
            for name in order:
                section, mode = wanted[name], mode_of(wanted[name])
                config = {k: v for k, v in section.items() if k != "mode"}
                try:
                    if name not in factories:
                        raise LookupError(f"no feature registered as {name!r}")
                    env = FeatureEnv(
                        state_dir=self._state, config=config, pricebook=self._pricebook, calculator=self._calculator
                    )
                    active.append((factories[name](env), mode))
                except Exception as exc:
                    # A feature that cannot start is a problem to show, never a silent pass for an enforced budget.
                    problems.append(f"{name}: {type(exc).__name__}: {exc}")
                    active.append((_Broken(name, f"{type(exc).__name__}: {exc}"), mode))
            self._active, self.problems, self._stamp = active, problems, stamp
            for p in problems:
                self._log({"action": "config_error", "detail": p})
            return self._active

    def modes(self) -> dict[str, str]:
        return {f.name: m.value for f, m in self._features()}

    # -- request path --------------------------------------------------------------------
    def before(self, ctx: RequestContext) -> Decision:
        passed: list[Feature] = []
        for feature, mode in self._features():
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
        rewriters = [(f, m) for f, m in self._features() if isinstance(f, Rewriter)]
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
        for feature, mode in rewriters:
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
                self._log_decision(ctx, feature.name, mode, "rewrite", "would_rewrite", 0, changes=changes)
                continue
            current = result.body
            applied.append(feature.name)
            headers += [(k, v) for k, v in result.add_headers if (k, v) not in headers]
            self._log_decision(ctx, feature.name, mode, "rewrite", "rewritten", 0, changes=changes)
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
