"""Ports: the only way packages meet. Implementations register under an entry-point group (see registry)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .types import (
    Buckets,
    Capabilities,
    DetectorCoverage,
    Finding,
    Identity,
    LedgerRow,
    Observation,
    PriceRow,
)


@runtime_checkable
class Adapter(Protocol):
    """A harness adapter: the five functions of plan/02-harness-adapters.md."""

    name: str
    provider: str  # the wire protocol's provider: "anthropic", "openai"
    capabilities: Capabilities

    def route(self, gateway_url: str, key: str) -> dict[str, str]:
        """Settings that point the harness at the gateway (environment variables or config keys)."""
        ...

    def matches(self, method: str, path: str, headers: Mapping[str, str]) -> bool:
        """True when a request comes from this harness."""
        ...

    def identify(self, headers: Mapping[str, str], body: bytes) -> Identity:
        """Session, prompt and agent ids from one request. Never raises: unknown fields stay empty."""
        ...

    def observe(self, status: int, headers: Mapping[str, str], body: bytes) -> Observation | None:
        """One observation from a complete response body (JSON or an SSE stream), or None if it carries no usage."""
        ...

    def cap(self, policy: Mapping[str, Any]) -> dict[str, str]:
        """Flags or config the harness accepts for a policy. Empty when the harness can only be observed."""
        ...

    def replay(self, transcript: Path) -> Iterable[Observation]:
        """Observations rebuilt from a local transcript: lowest trust, cost_source = client."""
        ...


@runtime_checkable
class UsageNormaliser(Protocol):
    provider: str

    def normalise(self, usage: Mapping[str, Any]) -> Buckets:
        """A provider usage object as five exclusive buckets. Raises UnknownUsageKey on an unknown key."""
        ...


@runtime_checkable
class CostCalculator(Protocol):
    def cost(self, buckets: Buckets, price: PriceRow, active: Iterable[str] = ()) -> Decimal:
        """USD for one response. `active` names the multipliers in force, e.g. {"region:us"}."""
        ...

    def active_for(self, service_tier: str = "", speed: str = "", inference_geo: str = "") -> frozenset[str]:
        """The multiplier names in force for a response's routing key."""
        ...


@runtime_checkable
class Deduper(Protocol):
    def first_time(self, provider: str, response_id: str) -> bool:
        """True the first time a provider response id is seen."""
        ...


@runtime_checkable
class PriceBook(Protocol):
    def lookup(
        self,
        provider: str,
        model: str,
        at: datetime,
        prompt_tokens: int,
        service_tier: str = "standard",
        region: str = "",
    ) -> PriceRow:
        """The row in force at `at` for the exact model id. Raises NoPriceRow."""
        ...

    def stale(self, now: datetime) -> Sequence[PriceRow]:
        """Rows unverified for 30 days or within 30 days of expiry."""
        ...


@runtime_checkable
class Ledger(Protocol):
    def write(self, row: LedgerRow) -> bool:
        """Append a row. False when the provider response id is already there (the row is not changed)."""
        ...

    def rows(self, since: datetime | None = None, until: datetime | None = None) -> Iterable[LedgerRow]: ...

    def count(self, response_id: str) -> int: ...


@runtime_checkable
class Upstream(Protocol):
    """Where a provider's requests go, and which headers must never be stored."""

    provider: str
    base_url: str

    def url(self, path: str, query: str) -> str: ...

    def forward_headers(self, headers: Mapping[str, str]) -> dict[str, str]:
        """Request headers to send upstream: everything except hop-by-hop headers and the virtual key."""
        ...


@runtime_checkable
class Detector(Protocol):
    """Alert-mode detectors. They run after the fact, never in the request path (plan/11)."""

    name: str

    def run(self, since: datetime | None = None) -> tuple[Sequence[Finding], Sequence[DetectorCoverage]]: ...
