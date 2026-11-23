"""Per-conversation state kept in one small JSON file, so a gateway restart does not forget a live session.

Not thread-safe by itself: the owning feature holds its own lock around every call. Writes are atomic (temp file then
replace), throttled (a new key or a changed value is written at once, a mere "seen again" waits for the interval),
pruned (entries unseen for 24 h go) and bounded (the oldest go past `max_entries`). A corrupt file reads as empty.
Values are metadata only: model ids and flags, never text.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from token_economics_contracts.types import QuerySource, RequestContext

TTL_S = 24 * 3600
MAX_ENTRIES = 2000
FLUSH_INTERVAL_S = 30.0


def conversation_key(ctx: RequestContext) -> str | None:
    """(session_id, agent, query_source); None for a request without a session id (such a request has no state)."""
    if not ctx.identity.session_id:
        return None
    return f"{ctx.identity.session_id}|{ctx.identity.agent}|{ctx.identity.query_source.value}"


def is_auxiliary(ctx: RequestContext) -> bool:
    return ctx.identity.query_source is QuerySource.AUXILIARY


class ConversationState:
    def __init__(
        self,
        path: Path,
        *,
        ttl_s: float = TTL_S,
        max_entries: int = MAX_ENTRIES,
        flush_interval_s: float = FLUSH_INTERVAL_S,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._path, self._ttl, self._max = path, ttl_s, max_entries
        self._interval, self._clock = flush_interval_s, clock
        self._entries: dict[str, dict[str, Any]] = {}
        self._dirty, self._last_flush = False, clock()
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self._path.read_text())
            raw = data["entries"]
        except (OSError, ValueError, KeyError, TypeError):
            return
        if not isinstance(raw, dict):
            return
        now = self._clock()
        for key, entry in raw.items():
            if (
                isinstance(key, str)
                and isinstance(entry, dict)
                and isinstance(entry.get("v"), dict)
                and isinstance(entry.get("seen"), int | float)
                and now - entry["seen"] <= self._ttl
            ):
                self._entries[key] = {"seen": float(entry["seen"]), "v": entry["v"]}
        self._trim()

    def get(self, key: str) -> dict[str, Any] | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        entry["seen"] = self._clock()
        self._dirty = True
        return dict(entry["v"])

    def put(self, key: str, value: dict[str, Any]) -> None:
        old = self._entries.get(key)
        changed = old is None or old["v"] != value
        self._entries[key] = {"seen": self._clock(), "v": dict(value)}
        self._trim()
        self._dirty = True
        if changed:
            self._write()

    def flush_if_due(self) -> None:
        if self._dirty and self._clock() - self._last_flush >= self._interval:
            self._write()

    def __len__(self) -> int:
        return len(self._entries)

    def _trim(self) -> None:
        now = self._clock()
        for key in [k for k, e in self._entries.items() if now - e["seen"] > self._ttl]:
            del self._entries[key]
        excess = len(self._entries) - self._max
        if excess > 0:
            for key in sorted(self._entries, key=lambda k: self._entries[k]["seen"])[:excess]:
                del self._entries[key]

    def _write(self) -> None:
        self._dirty, self._last_flush = False, self._clock()
        tmp = self._path.with_name(self._path.name + f".{os.getpid()}.tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps({"version": 1, "entries": self._entries}, separators=(",", ":")))
            tmp.replace(self._path)
        except OSError:
            pass  # state is best effort: a failed write must never fail a request
