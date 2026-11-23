"""Count compactions per session (a big drop in prompt tokens) and refuse once a session has had too many."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from token_economics_contracts.types import Decision, FeatureEnv, LedgerRow, QuerySource, RequestContext

DEFAULT_RESTART_AT = 3
DEFAULT_DROP_RATIO = 0.5
DEFAULT_MIN_PROMPT = 50_000
PRUNE_AFTER_S = 7 * 24 * 3600
STATE_FILE = "compaction_guard.json"


def _num(value: Any, default: float, low: float, high: float | None = None) -> float:
    ok = isinstance(value, (int, float)) and not isinstance(value, bool) and value >= low
    if ok and high is not None:
        ok = value <= high
    return float(value) if ok else default


class CompactionGuard:
    name = "compaction_guard"
    fail_closed = False

    def __init__(
        self,
        path: Path | None = None,
        restart_at: int = DEFAULT_RESTART_AT,
        drop_ratio: float = DEFAULT_DROP_RATIO,
        min_prompt: int = DEFAULT_MIN_PROMPT,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.path = path
        self.restart_at = restart_at
        self.drop_ratio = drop_ratio
        self.min_prompt = min_prompt
        self._clock = clock
        self._lock = threading.Lock()
        self._sessions: dict[str, dict[str, float]] = {}
        self._load()

    def _load(self) -> None:
        if self.path is None:
            return
        try:
            raw = json.loads(self.path.read_text())
            sessions: dict[str, dict[str, float]] = {}
            for sid, s in raw["sessions"].items():
                sessions[str(sid)] = {
                    "count": int(s["count"]),
                    "last_prompt": int(s["last_prompt"]),
                    "last_seen": float(s["last_seen"]),
                }
            self._sessions = sessions
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            self._sessions = {}

    def _save(self) -> None:
        if self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".compaction_guard-")
            with os.fdopen(fd, "w") as f:
                json.dump({"sessions": self._sessions}, f)
            os.replace(tmp, self.path)
        except OSError:
            pass  # losing a count is better than failing a request

    def before(self, ctx: RequestContext) -> Decision | None:
        sid = ctx.identity.session_id
        if not sid:
            return None
        with self._lock:
            count = int(self._sessions.get(sid, {}).get("count", 0))
        if count < self.restart_at:
            return None
        return Decision(
            allow=False,
            feature=self.name,
            status=429,
            code="compaction_limit",
            message=(
                f"Token Economics: this session has been compacted {count} times; start a new session "
                "(each compaction rewrites the cache and loses detail)."
            ),
        )

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        sid = ctx.identity.session_id
        if row is None or not sid or ctx.identity.query_source != QuerySource.MAIN:
            return
        prompt = row.buckets.prompt_tokens
        now = self._clock()
        with self._lock:
            state = self._sessions.get(sid)
            if state is None:
                state = {"count": 0, "last_prompt": 0, "last_seen": now}
                self._sessions[sid] = state
            prev = state["last_prompt"]
            if prev >= self.min_prompt and prompt < self.drop_ratio * prev:
                state["count"] = int(state["count"]) + 1
            state["last_prompt"] = prompt
            state["last_seen"] = now
            cutoff = now - PRUNE_AFTER_S
            self._sessions = {k: v for k, v in self._sessions.items() if v["last_seen"] >= cutoff}
            self._save()


def create(env: FeatureEnv) -> CompactionGuard:
    c = env.config
    return CompactionGuard(
        path=env.state_dir / STATE_FILE,
        restart_at=int(_num(c.get("restart_at"), DEFAULT_RESTART_AT, 1)),
        drop_ratio=_num(c.get("drop_ratio"), DEFAULT_DROP_RATIO, 0.0, 1.0),
        min_prompt=int(_num(c.get("min_prompt"), DEFAULT_MIN_PROMPT, 0)),
    )
