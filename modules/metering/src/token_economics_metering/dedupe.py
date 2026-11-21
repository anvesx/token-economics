"""Dedupe guard: one ledger row per provider response id (plan/03, ledger rules 1, 2 and 4).

The ledger's unique key is the guarantee. This guard is the cheap first check in the request path, so a response the
provider delivered twice, or one seen by two observers, is not normalised and priced twice.
"""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock


class DedupeGuard:
    def __init__(self, capacity: int = 100_000) -> None:
        self._seen: OrderedDict[tuple[str, str], None] = OrderedDict()
        self._capacity, self._lock = capacity, Lock()

    def first_time(self, provider: str, response_id: str) -> bool:
        """True the first time a response id is seen. An empty id is never a duplicate (it cannot be deduped)."""
        if not response_id:
            return True
        key = (provider, response_id)
        with self._lock:
            if key in self._seen:
                self._seen.move_to_end(key)
                return False
            self._seen[key] = None
            if len(self._seen) > self._capacity:
                self._seen.popitem(last=False)
            return True


def open_dedupe(capacity: int = 100_000) -> DedupeGuard:
    return DedupeGuard(capacity)
