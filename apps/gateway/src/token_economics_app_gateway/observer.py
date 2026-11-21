"""After a response has been sent: usage to five buckets, dedupe, price, one ledger row.

Runs off the request path. It fails open: any error here is counted and logged as metadata, and never reaches the
client (plan/02 adapter rule 9). Nothing from a request or response body is stored.
"""

from __future__ import annotations

import gzip
import json
import zlib
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from threading import Lock

import brotli
from token_economics_contracts import (
    Adapter,
    CostCalculator,
    CostSource,
    Deduper,
    Identity,
    KeyInfo,
    Ledger,
    LedgerRow,
    NoPriceRow,
    PriceBook,
    UnknownUsageKey,
    UsageNormaliser,
)


def decode_body(body: bytes, content_encoding: str) -> bytes | None:
    """The response body as the upstream wrote it before compression, or None for an encoding we cannot read."""
    data = body
    for enc in reversed([e.strip().lower() for e in content_encoding.split(",") if e.strip()]):
        try:
            if enc in ("identity", ""):
                continue
            if enc in ("gzip", "x-gzip"):
                data = gzip.decompress(data)
            elif enc == "deflate":
                data = zlib.decompress(data)
            elif enc == "br":
                data = brotli.decompress(data)
            else:
                return None
        except (OSError, zlib.error, brotli.error, EOFError):
            return None
    return data


@dataclass
class Observer:
    ledger: Ledger
    pricebook: PriceBook
    calculator: CostCalculator
    deduper: Deduper
    normalisers: Mapping[str, UsageNormaliser]
    rejects_path: Path | None = None
    stats: Counter[str] = field(default_factory=Counter)
    _lock: Lock = field(default_factory=Lock)

    def record(
        self, adapter: Adapter, key: KeyInfo, identity: Identity, status: int, headers: Mapping[str, str], body: bytes
    ) -> None:
        """Observe one complete response. Never raises."""
        try:
            self._record(adapter, key, identity, status, headers, body)
        except Exception as exc:  # fail open: observation must never break a response
            self._reject({"reason": "observer_error", "error": type(exc).__name__, "harness": adapter.name})
            self._count("observer_errors")

    def _record(
        self, adapter: Adapter, key: KeyInfo, identity: Identity, status: int, headers: Mapping[str, str], body: bytes
    ) -> None:
        decoded = decode_body(body, headers.get("content-encoding", ""))
        if decoded is None:
            self._count("unreadable_encoding")
            return
        obs = adapter.observe(status, headers, decoded)
        if obs is None:
            self._count("no_usage")
            return
        if not obs.response_id:
            self._reject({"reason": "no_response_id", "provider": obs.provider, "model": obs.model})
            self._count("no_response_id")
            return
        if not self.deduper.first_time(obs.provider, obs.response_id):
            self._count("duplicates")
            return
        normaliser = self.normalisers.get(obs.provider)
        if normaliser is None:
            self._count("no_normaliser")
            return
        try:
            buckets = normaliser.normalise(obs.usage)
        except UnknownUsageKey as exc:
            self._reject(
                {
                    "reason": "unknown_usage_key",
                    "provider": obs.provider,
                    "model": obs.model,
                    "response_id": obs.response_id,
                    "keys": exc.keys,
                }
            )
            self._count("unknown_usage_key")
            return
        except ValueError as exc:
            self._reject(
                {
                    "reason": "bad_usage",
                    "provider": obs.provider,
                    "model": obs.model,
                    "response_id": obs.response_id,
                    "error": str(exc),
                }
            )
            self._count("bad_usage")
            return
        now = datetime.now(UTC)
        cost: Decimal | None
        try:
            price = self.pricebook.lookup(obs.provider, obs.model, now, buckets.prompt_tokens, obs.service_tier)
            active = self.calculator.active_for(obs.service_tier, obs.speed, obs.inference_geo)
            cost, price_row_id = self.calculator.cost(buckets, price, active), price.price_row_id
        except NoPriceRow:
            cost, price_row_id = None, ""
            self._count("unpriced")
        row = LedgerRow(
            provider=obs.provider,
            response_id=obs.response_id,
            request_id=obs.request_id,
            ts=now,
            tenant=key.tenant,
            team=key.team,
            caller=key.caller,
            agent=identity.agent or key.agent,
            harness=adapter.name,
            session_id=identity.session_id,
            prompt_id=identity.prompt_id,
            query_source=identity.query_source,
            model=obs.model,
            service_tier=obs.service_tier,
            speed=obs.speed,
            effort=obs.effort,
            inference_geo=obs.inference_geo,
            buckets=buckets,
            cost_estimate_usd=cost,
            cost_source=CostSource.GATEWAY,
            price_row_id=price_row_id,
            auth_mode=identity.auth_mode,
            http_status=status,
        )
        self._count("rows" if self.ledger.write(row) else "duplicates")

    def _count(self, name: str) -> None:
        with self._lock:
            self.stats[name] += 1

    def _reject(self, record: dict[str, object]) -> None:
        """Append one metadata-only line about a response that produced no ledger row."""
        if self.rejects_path is None:
            return
        try:
            with self._lock, self.rejects_path.open("a") as f:
                f.write(json.dumps({"ts": datetime.now(UTC).isoformat(), **record}) + "\n")
        except OSError:
            pass
