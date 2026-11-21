from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError
from token_economics_contracts import Buckets, CostSource, LedgerRow


def test_buckets_are_exclusive_and_sum_to_the_total() -> None:
    b = Buckets(fresh_input=86, cache_read=17_817, cache_write_5m=10, cache_write_1h=5, output=1_186)
    assert b.prompt_tokens == 86 + 17_817 + 10 + 5
    assert b.total == b.prompt_tokens + 1_186


def test_negative_tokens_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Buckets(fresh_input=-1)


def test_ledger_row_is_frozen_and_takes_no_extra_fields() -> None:
    row = LedgerRow(
        provider="anthropic",
        response_id="msg_1",
        ts=datetime(2026, 11, 1, tzinfo=UTC),
        model="m",
        buckets=Buckets(),
        cost_estimate_usd=Decimal("0"),
        cost_source=CostSource.GATEWAY,
        price_row_id="p1",
    )
    with pytest.raises(ValidationError):
        row.model = "other"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        LedgerRow(**{**row.model_dump(), "prompt": "text must never be stored"})
