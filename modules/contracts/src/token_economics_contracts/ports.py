"""Ports: the only way packages meet. Implementations register under an entry-point group (see registry)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .types import (
    Attempt,
    Buckets,
    BudgetStatus,
    Capabilities,
    Decision,
    DetectorCoverage,
    Finding,
    Identity,
    KillEntry,
    LedgerRow,
    Observation,
    PriceRow,
    RequestContext,
    RequestFacts,
    ResolvedKey,
    Rewrite,
    RewrittenRequest,
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

    def facts(self, headers: Mapping[str, str], body: bytes) -> RequestFacts:
        """Numbers and hashes the policy engine needs from one request body. Never raises; never returns text."""
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


@runtime_checkable
class Feature(Protocol):
    """One policy capability behind a flag (budgets, turn cap, loop guard). Registered as a factory
    `(env: FeatureEnv) -> Feature` under the entry-point group `token_economics.features`."""

    name: str
    fail_closed: bool  # True: if before() raises while the feature is enforced, the request is refused (budgets)

    def before(self, ctx: RequestContext) -> Decision | None:
        """Called before dispatch. None or an allowing Decision lets the request through."""
        ...

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        """Called once the response is over. `row` is the ledger row, or None when the response had no usage."""
        ...


@runtime_checkable
class Rewriter(Protocol):
    """A feature that may change a request before dispatch (P2: caps, masking, routing, cache plan). Optional: a
    Feature that also has `rewrite` is one. It must not mutate `body`; it returns a Rewrite with the new body, or None
    to leave the request alone. It runs only after every feature's `before` has allowed the request."""

    name: str

    def rewrite(self, ctx: RequestContext, body: dict[str, Any]) -> Rewrite | None: ...


@runtime_checkable
class PolicyEngine(Protocol):
    """Runs the features in order and applies their flags. Registered as SERVICES "policy"."""

    def before(self, ctx: RequestContext) -> Decision: ...

    def rewrite(self, ctx: RequestContext, body: bytes) -> RewrittenRequest | None:
        """The request to send instead of `body`, or None to send the original bytes unchanged. Never raises."""
        ...

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None: ...


@runtime_checkable
class EvalHarness(Protocol):
    """The eval harness (plan/07). Registered as SERVICES "eval", a factory taking no arguments."""

    def run(self, spec: Path, out_dir: Path | None = None, allow_dirty: bool = False) -> Path:
        """Run a preregistered spec; returns the result folder. Refuses a spec not committed to git unless allowed."""
        ...

    def analyse(self, attempts: Sequence[Attempt], spec: Mapping[str, Any]) -> dict[str, Any]:
        """Paired verdicts for each candidate arm against the baseline arm, from attempts already run."""
        ...

    def selftest(self, seed: int = 0) -> dict[str, Any]:
        """A synthetic no-op run: two identical arms. It must report no difference."""
        ...


@runtime_checkable
class ShadowSampler(Protocol):
    """Shadow runs (plan/07, Rollout). Registered as SERVICES "shadow", a factory taking state_dir. The gateway asks
    whether to mirror a request, sends the mirror through the candidate policy to a separate ledger, and reports both
    sides. A shadow response never reaches the client and never touches a budget."""

    def sample(self, ctx: RequestContext) -> bool: ...

    def record(self, ctx: RequestContext, side: str, row: LedgerRow | None, status: int) -> None:
        """`side` is "primary" or "shadow"."""
        ...

    def report(self) -> dict[str, Any]: ...


@runtime_checkable
class KeyResolver(Protocol):
    """Virtual keys, hashed at rest. Registered as SERVICES "keys"."""

    def resolve(self, presented: str) -> ResolvedKey: ...


@runtime_checkable
class HealthTracker(Protocol):
    """Backend health and rate-limit tracking. Registered as SERVICES "health"."""

    def record(self, provider: str, status: int, headers: Mapping[str, str]) -> None: ...

    def snapshot(self) -> dict[str, Any]: ...


@runtime_checkable
class BudgetReader(Protocol):
    """Read-only view of budgets for reports. Registered as SERVICES "budget_status" (a factory taking state_dir)."""

    def status(self) -> Sequence[BudgetStatus]: ...


@runtime_checkable
class KillSwitches(Protocol):
    """Read and write `kill.json`. Registered as SERVICES "kill" (a factory taking state_dir). Changes are audited."""

    def list(self) -> Sequence[KillEntry]: ...

    def add(self, feature: str, tenant: str = "*", reason: str = "", by: str = "") -> bool:
        """False when that switch was already off."""
        ...

    def remove(self, feature: str, tenant: str = "*", by: str = "") -> bool:
        """False when there was no such switch."""
        ...


@runtime_checkable
class RollbackChecker(Protocol):
    """Auto-rollback (plan/07). Registered as SERVICES "rollback", a factory taking state_dir. `check` compares canary
    with control traffic and kills a feature whose trigger fires; it returns what it did."""

    def check(self, now: datetime | None = None) -> Sequence[dict[str, Any]]: ...


@runtime_checkable
class Retention(Protocol):
    """Drops metadata log lines older than a tenant's retention. Registered as SERVICES "retention" (state_dir).
    Never touches the ledger or the price book, which are append-only."""

    def apply(self, now: datetime | None = None) -> dict[str, Any]: ...
