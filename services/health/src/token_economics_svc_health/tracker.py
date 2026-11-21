"""In-memory backend health and rate-limit tracking over a sliding window. No disk."""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

WINDOW_S = 300.0
DEGRADED_RATE = 0.2
DEGRADED_MIN_REQUESTS = 5
DEGRADED_CONSECUTIVE = 3

# Header names are from provider documentation and are not verified against live traffic.
_LIMIT_HEADERS = {
    "anthropic-ratelimit-requests-remaining": "requests_remaining",
    "anthropic-ratelimit-tokens-remaining": "tokens_remaining",
    "anthropic-ratelimit-requests-reset": "requests_reset",
    "anthropic-ratelimit-tokens-reset": "tokens_reset",
    "x-ratelimit-remaining-requests": "requests_remaining",
    "x-ratelimit-remaining-tokens": "tokens_remaining",
}


def _is_failure(status: int) -> bool:
    return status == 429 or 500 <= status <= 599


def _retry_after(value: str, now: float) -> float | None:
    """Epoch seconds at which the provider said to retry, from delay-seconds or an HTTP date."""
    value = value.strip()
    try:
        seconds = float(value)
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        return when.timestamp()
    return now + seconds if seconds >= 0 else None


class _Provider:
    def __init__(self) -> None:
        self.events: deque[tuple[float, int]] = deque()
        self.last_status = 0
        self.last_error_at: float | None = None
        self.consecutive_failures = 0
        self.retry_until: float | None = None
        self.limits: dict[str, str] = {}


class InMemoryHealth:
    """The `HealthTracker` port. Safe to share between threads."""

    def __init__(self, clock: Callable[[], float] = time.time, window_s: float = WINDOW_S) -> None:
        self._clock = clock
        self._window = window_s
        self._lock = threading.Lock()
        self._providers: dict[str, _Provider] = {}

    def record(self, provider: str, status: int, headers: Mapping[str, str]) -> None:
        now = self._clock()
        lowered = {k.lower(): v for k, v in headers.items()}
        with self._lock:
            p = self._providers.setdefault(provider, _Provider())
            p.events.append((now, status))
            p.last_status = status
            if _is_failure(status):
                p.consecutive_failures += 1
                p.last_error_at = now
            elif 200 <= status < 300:
                p.consecutive_failures = 0
            if status in (429, 529) and "retry-after" in lowered:
                until = _retry_after(lowered["retry-after"], now)
                if until is not None:
                    p.retry_until = until
            for name, key in _LIMIT_HEADERS.items():
                if name in lowered:
                    p.limits[key] = lowered[name]

    def snapshot(self) -> dict[str, Any]:
        now = self._clock()
        with self._lock:
            return {name: self._one(p, now) for name, p in sorted(self._providers.items())}

    def healthy(self, provider: str) -> bool:
        """True when the provider is healthy or has not been seen."""
        return bool(self.snapshot().get(provider, {}).get("state", "healthy") == "healthy")

    def _one(self, p: _Provider, now: float) -> dict[str, Any]:
        while p.events and p.events[0][0] <= now - self._window:
            p.events.popleft()
        statuses = [s for _, s in p.events]
        total = len(statuses)
        ok = sum(1 for s in statuses if 200 <= s < 300)
        limited = sum(1 for s in statuses if s == 429)
        server = sum(1 for s in statuses if 500 <= s <= 599)
        errors = limited + server
        rate = errors / total if total else 0.0
        if p.retry_until is not None and now < p.retry_until:
            state = "rate_limited"
        elif (total >= DEGRADED_MIN_REQUESTS and rate >= DEGRADED_RATE) or (
            p.consecutive_failures >= DEGRADED_CONSECUTIVE
        ):
            state = "degraded"
        else:
            state = "healthy"
        return {
            "window_s": self._window,
            "requests": total,
            "ok_2xx": ok,
            "rate_limited_429": limited,
            "errors_5xx": server,
            "other": total - ok - limited - server,
            "error_rate": rate,
            "last_status": p.last_status,
            "last_error_at": None if p.last_error_at is None else _iso(p.last_error_at),
            "consecutive_failures": p.consecutive_failures,
            "state": state,
            "retry_until": None if p.retry_until is None or now >= p.retry_until else _iso(p.retry_until),
            "limits": dict(p.limits),
        }


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).isoformat(timespec="seconds")


def open_health() -> InMemoryHealth:
    """Factory registered under the `token_economics.services` entry point as `health`."""
    return InMemoryHealth()
