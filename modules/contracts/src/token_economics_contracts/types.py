"""Shared types. Shapes follow plan/03-data-model.md and plan/04-cost-formula.md."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Buckets(_Frozen):
    """The five mutually exclusive token buckets. Reasoning tokens are inside `output`, never added twice."""

    fresh_input: int = Field(default=0, ge=0)
    cache_read: int = Field(default=0, ge=0)
    cache_write_5m: int = Field(default=0, ge=0)
    cache_write_1h: int = Field(default=0, ge=0)
    output: int = Field(default=0, ge=0)

    @property
    def prompt_tokens(self) -> int:
        """Everything the model read: the number a context band is picked from."""
        return self.fresh_input + self.cache_read + self.cache_write_5m + self.cache_write_1h

    @property
    def total(self) -> int:
        return self.prompt_tokens + self.output


class CostSource(StrEnum):
    """Who computed a cost. Trust order: bill, then gateway, then client."""

    CLIENT = "client"
    GATEWAY = "gateway"
    BILL = "bill"


class QuerySource(StrEnum):
    MAIN = "main"
    SUBAGENT = "subagent"
    AUXILIARY = "auxiliary"


class Capabilities(_Frozen):
    """The eight capability flags of a harness. A false flag degrades that control to observation."""

    base_url: bool = False
    oauth_passthrough: bool = False
    hooks_blocking: bool = False
    otel: bool = False
    budget_flag: bool = False
    headless: bool = False
    model_rewrite: bool = False
    transcript_path: bool = False


class KeyInfo(_Frozen):
    """What a virtual key resolves to."""

    tenant: str
    team: str = ""
    caller: str = ""
    agent: str = ""


class Identity(_Frozen):
    """What an adapter reads from one request."""

    session_id: str = ""
    prompt_id: str = ""
    agent: str = ""
    tool: str = ""
    query_source: QuerySource = QuerySource.MAIN
    auth_mode: str = ""  # api_key, oauth, unknown


class Observation(_Frozen):
    """One provider response as an adapter saw it: ids, routing key and the provider's raw usage object."""

    provider: str
    response_id: str
    model: str
    usage: dict[str, Any]
    request_id: str = ""
    service_tier: str = "standard"
    speed: str = ""
    effort: str = ""
    inference_geo: str = ""
    cost_reported_usd: Decimal | None = None  # a cost the provider itself reported, when it does


class Multiplier(_Frozen):
    """A price multiplier that applies when `name` is active on the request, e.g. "region:us", "fast", "batch"."""

    name: str
    factor: Decimal
    applies_to: Literal["input", "output", "cached", "all"] = "all"


class PriceRow(_Frozen):
    """One append-only price book row. Rates are USD per 1M tokens."""

    price_row_id: str
    provider: str
    model: str  # exact model id; partial names are never matched
    service_tier: str = "standard"
    context_band_min: int = Field(default=0, ge=0)  # the row applies from this many prompt tokens
    band_scope: Literal["all_tokens", "marginal"] = "all_tokens"
    region: str = ""
    effective_from: datetime
    effective_to: datetime | None = None
    input: Decimal
    output: Decimal
    cache_read: Decimal
    cache_write_5m: Decimal
    cache_write_1h: Decimal
    multipliers: tuple[Multiplier, ...] = ()
    source_id: str = ""
    snapshot_date: datetime | None = None
    last_verified_at: datetime | None = None
    confidence: Literal["verified", "unverified"] = "unverified"


class LedgerRow(_Frozen):
    """One row per provider response id. Metadata only: no prompt, tool or response text."""

    # identity
    provider: str
    response_id: str
    request_id: str = ""
    ts: datetime
    # attribution
    tenant: str = ""
    team: str = ""
    caller: str = ""
    agent: str = ""
    harness: str = ""
    session_id: str = ""
    prompt_id: str = ""
    query_source: QuerySource = QuerySource.MAIN
    # routing key
    model: str
    service_tier: str = "standard"
    speed: str = ""
    effort: str = ""
    inference_geo: str = ""
    ttl_class: str = ""
    # tokens
    buckets: Buckets
    # cost
    cost_estimate_usd: Decimal | None  # None when no price row was in force
    cost_source: CostSource
    price_row_id: str  # "" only with cost_estimate_usd None
    auth_mode: str = ""
    # outcome
    attempt: int = 1
    task_id: str = ""
    success: bool | None = None
    http_status: int = 200


class Finding(_Frozen):
    """One detector finding. `row` is the fix-table row number (1-50)."""

    row: int
    name: str
    cost_estimate_usd: Decimal
    cost_source: CostSource
    scope: str = ""  # session, caller or tenant the finding is about
    detail: str = ""


class DetectorCoverage(_Frozen):
    """One line of the coverage table: how often a fix-table row fired over a period."""

    row: int
    name: str
    group: str = ""
    status: Literal["fired", "not_fired", "unmeasurable", "retired"]
    fired: int = 0
    cost_estimate_usd: Decimal = Decimal(0)
    review: bool = False  # spend to review, not counted as waste
    note: str = ""
