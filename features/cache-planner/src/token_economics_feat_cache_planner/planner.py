"""Choose the 5-minute or 1-hour cache TTL for each prompt prefix from how often it is reused (plan/05).

Config (the feature's section of the policy file, all optional):
    {"min_samples": 10, "max_gaps": 100, "max_keys": 5000, "max_sessions": 10000, "persist_interval_s": 30}
Only Anthropic Messages bodies, and only breakpoints the client already placed; none are added.
"""

from __future__ import annotations

import json
import os
import statistics
import time
from collections import OrderedDict
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

from token_economics_contracts.types import FeatureEnv, LedgerRow, RequestContext, Rewrite

from .providers.anthropic import DEFAULT_TTL, prefix_hash, ttls_in, with_ttl

STATE_NAME = "cache_planner.json"
TTL_5M_S, TTL_1H_S = 300.0, 3600.0
DEFAULT_RATIOS = (0.1, 1.25, 2.0)  # cache_read, cache_write_5m, cache_write_1h as a multiple of the input price
KEEP = "as_sent"


def choose_ttl(gaps: list[float], ratios: tuple[float, float, float]) -> str | None:
    """The cheaper TTL for these reuse gaps, in units of the input price, or None on a tie.

    One initial write plus, per gap, a read when the gap fits inside the TTL and a rewrite when it does not.
    """
    read, w5, w1h = ratios
    cost_5m = w5 + sum(read if g <= TTL_5M_S else w5 for g in gaps)
    cost_1h = w1h + sum(read if g <= TTL_1H_S else w1h for g in gaps)
    if cost_5m == cost_1h:
        return None
    return DEFAULT_TTL if cost_5m < cost_1h else "1h"


def _int(value: Any, default: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else default


class CachePlanner:
    name = "cache_planner"
    fail_closed = False

    def __init__(
        self,
        state_dir: Path,
        pricebook: Any = None,
        config: dict[str, Any] | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        cfg = config or {}
        self.min_samples = _int(cfg.get("min_samples"), 10)
        self.max_gaps = _int(cfg.get("max_gaps"), 100)
        self.max_keys = _int(cfg.get("max_keys"), 5000)
        self.max_sessions = _int(cfg.get("max_sessions"), 10_000)
        self.persist_interval_s = float(cfg.get("persist_interval_s", 30))
        self._pricebook, self._path = pricebook, state_dir / STATE_NAME
        self._clock = clock or time.monotonic
        self._lock = Lock()
        self._keys: OrderedDict[str, tuple[float, list[float]]] = OrderedDict()  # hash -> (last use, gaps)
        self._sessions: OrderedDict[str, str] = OrderedDict()  # session id -> frozen choice
        self._ratios: dict[str, tuple[float, float, float]] = {}
        self._last_persist = float("-inf")
        self._load()

    # -- Feature -------------------------------------------------------------------------
    def before(self, ctx: RequestContext) -> None:
        return None

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        return None

    def rewrite(self, ctx: RequestContext, body: dict[str, Any]) -> Rewrite | None:
        if ctx.provider != "anthropic":
            return None
        scope = ctx.key.caller or ctx.key_id or ctx.key.tenant
        key = prefix_hash(body, scope, ctx.harness)
        if key is None:
            return None
        gaps = self._record(key, ctx.ts.timestamp())
        self._maybe_persist()
        sent = ttls_in(body)
        if not sent:
            return None
        sid = ctx.identity.session_id
        with self._lock:
            frozen = self._sessions.get(sid) if sid else None
            if frozen is not None:
                self._sessions.move_to_end(sid)
        if frozen is None:
            if len(gaps) < self.min_samples:
                return None
            model = str(body.get("model"))
            choice = choose_ttl(gaps, self._ratios_for(model, ctx.ts)) or KEEP
            if sid:
                self._freeze(sid, choice)
        else:
            choice = frozen
        if choice == KEEP or sent == {choice}:
            return None
        before = sent.pop() if len(sent) == 1 else "mixed"
        note = f"cache ttl {before}->{choice} (n={len(gaps)} gaps, p50 {statistics.median(gaps):.0f}s)"
        return Rewrite(body=with_ttl(body, choice), changes=(note,))

    # -- state ---------------------------------------------------------------------------
    def _record(self, key: str, now: float) -> list[float]:
        with self._lock:
            entry = self._keys.pop(key, None)
            gaps: list[float] = []
            if entry is not None:  # the first sighting of a prefix has no gap
                gaps = [*entry[1], max(0.0, now - entry[0])][-self.max_gaps :]
            self._keys[key] = (now, gaps)
            while len(self._keys) > self.max_keys:
                self._keys.popitem(last=False)
            return list(gaps)

    def _freeze(self, sid: str, choice: str) -> None:
        with self._lock:
            self._sessions[sid] = choice
            while len(self._sessions) > self.max_sessions:
                self._sessions.popitem(last=False)

    def _ratios_for(self, model: str, at: datetime) -> tuple[float, float, float]:
        if self._pricebook is None:
            return DEFAULT_RATIOS
        with self._lock:
            cached = self._ratios.get(model)
        if cached is not None:
            return cached
        try:
            row = self._pricebook.lookup("anthropic", model, at, 0)
            if row.input <= 0:
                raise ValueError("no input price")
            ratios = (
                float(row.cache_read / row.input),
                float(row.cache_write_5m / row.input),
                float(row.cache_write_1h / row.input),
            )
        except Exception:
            return DEFAULT_RATIOS
        with self._lock:
            self._ratios[model] = ratios
        return ratios

    # -- persistence: hashes and numbers only ----------------------------------------------
    def _load(self) -> None:
        try:
            data = json.loads(self._path.read_text())
            for key, entry in data["keys"].items():
                last, gaps = float(entry["last"]), [float(g) for g in entry["gaps"]]
                self._keys[str(key)] = (last, gaps[-self.max_gaps :])
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            self._keys.clear()  # a corrupt file is a cold start, never an error

    def _maybe_persist(self) -> None:
        now = self._clock()
        with self._lock:
            if now - self._last_persist < self.persist_interval_s:
                return
            self._last_persist = now
        self.flush()

    def flush(self) -> None:
        """Write the key stats now (atomic: temp file, then replace). Failures are ignored."""
        with self._lock:
            snap = {"keys": {k: {"last": last, "gaps": gaps} for k, (last, gaps) in self._keys.items()}}
        tmp = self._path.with_name(self._path.name + f".{os.getpid()}.tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(snap))
            tmp.replace(self._path)
        except OSError:
            pass


def create(env: FeatureEnv) -> CachePlanner:
    return CachePlanner(env.state_dir, env.pricebook, env.config)
