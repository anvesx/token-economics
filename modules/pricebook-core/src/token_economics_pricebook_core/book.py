"""The price book: append-only rows, looked up by exact model id, request date and context band (plan/04)."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta

from token_economics_contracts import NoPriceRow, PriceBookViolation, PriceRow

STALE_AFTER = timedelta(days=30)


def _key(row: PriceRow) -> tuple[str, str, str, int, str, datetime]:
    return (row.provider, row.model, row.service_tier, row.context_band_min, row.region, row.effective_from)


class PriceBookCore:
    """In-memory price book. Rows are only ever added; a row is never changed or removed."""

    def __init__(self, rows: Iterable[PriceRow] = ()) -> None:
        self._by_id: dict[str, PriceRow] = {}
        self._by_key: dict[tuple[str, str, str, int, str, datetime], PriceRow] = {}
        for row in rows:
            self.add(row)

    def add(self, row: PriceRow) -> bool:
        """Append a row. False when the identical row is already there. Raises PriceBookViolation on any conflict."""
        if row.effective_from.tzinfo is None:
            raise PriceBookViolation(f"{row.price_row_id}: effective_from has no time zone")
        if row.effective_to is not None and row.effective_to <= row.effective_from:
            raise PriceBookViolation(f"{row.price_row_id}: effective_to is not after effective_from")
        if row.band_scope != "all_tokens":
            raise PriceBookViolation(f"{row.price_row_id}: marginal context bands are not supported in P0")
        same_id, same_key = self._by_id.get(row.price_row_id), self._by_key.get(_key(row))
        if same_id is not None or same_key is not None:
            if same_id == row and same_key == row:
                return False
            raise PriceBookViolation(
                f"{row.price_row_id}: a different row already exists for this id or key; "
                "append a row with a new effective_from instead of changing one"
            )
        self._by_id[row.price_row_id] = row
        self._by_key[_key(row)] = row
        return True

    def rows(self) -> Sequence[PriceRow]:
        return list(self._by_id.values())

    def get(self, price_row_id: str) -> PriceRow:
        try:
            return self._by_id[price_row_id]
        except KeyError:
            raise NoPriceRow(price_row_id) from None

    def lookup(
        self,
        provider: str,
        model: str,
        at: datetime,
        prompt_tokens: int,
        service_tier: str = "standard",
        region: str = "",
    ) -> PriceRow:
        """The row in force at `at`. Exact model id only: a partial name is never matched (plan/03, rule 5).

        A row for the request's region wins over the default region "". Among rows in force, the newest
        effective_from wins per context band, then the highest band at or below `prompt_tokens`.
        """
        for want_region in dict.fromkeys((region, "")):
            per_band: dict[int, PriceRow] = {}
            for row in self._by_id.values():
                if (row.provider, row.model, row.service_tier, row.region) != (
                    provider,
                    model,
                    service_tier,
                    want_region,
                ):
                    continue
                if row.effective_from > at or (row.effective_to is not None and at >= row.effective_to):
                    continue
                best = per_band.get(row.context_band_min)
                if best is None or row.effective_from > best.effective_from:
                    per_band[row.context_band_min] = row
            bands = [b for b in per_band if b <= prompt_tokens]
            if bands:
                return per_band[max(bands)]
        raise NoPriceRow(f"no price row in force for {provider} {model!r} tier {service_tier!r} at {at.isoformat()}")

    def stale(self, now: datetime) -> Sequence[PriceRow]:
        """Rows in force that were not verified in the last 30 days, or that expire within 30 days."""
        out = []
        for row in self._by_id.values():
            if row.effective_to is not None and row.effective_to <= now:
                continue  # already out of force
            unverified = row.last_verified_at is None or now - row.last_verified_at > STALE_AFTER
            expiring = row.effective_to is not None and row.effective_to - now <= STALE_AFTER
            if unverified or expiring:
                out.append(row)
        return out
