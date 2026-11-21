from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st
from token_economics_contracts.types import Buckets, CostSource, LedgerRow, QuerySource
from token_economics_svc_ledger import SqliteLedger

text = st.text(max_size=20)
tokens = st.integers(min_value=0, max_value=2**62)
buckets = st.builds(
    Buckets, fresh_input=tokens, cache_read=tokens, cache_write_5m=tokens, cache_write_1h=tokens, output=tokens
)
zones = st.integers(-12 * 60, 14 * 60).map(lambda m: timezone(timedelta(minutes=m)))
stamps = st.datetimes(min_value=datetime(1970, 1, 2), max_value=datetime(9000, 1, 1), timezones=zones)
costs = st.none() | st.decimals(min_value=0, max_value=10**9, places=12, allow_nan=False, allow_infinity=False)
rows = st.builds(
    LedgerRow,
    provider=text, response_id=st.text(min_size=1, max_size=20), request_id=text, ts=stamps,
    tenant=text, team=text, caller=text, agent=text, harness=text, session_id=text, prompt_id=text,
    query_source=st.sampled_from(QuerySource), model=text, service_tier=text, speed=text, effort=text,
    inference_geo=text, ttl_class=text, buckets=buckets, cost_estimate_usd=costs,
    cost_source=st.sampled_from(CostSource), price_row_id=text, auth_mode=text,
    attempt=st.integers(0, 1000), task_id=text, success=st.none() | st.booleans(),
    http_status=st.integers(100, 599),
)  # fmt: skip


@given(rows)
def test_every_field_round_trips_exactly(row: LedgerRow):
    # Given any ledger row, including None cost and every enum value
    ledger = SqliteLedger(":memory:")
    # When it is written and read back
    assert ledger.write(row) is True
    (back,) = ledger.rows()
    # Then every field is equal, Decimal text included
    assert back == row
    assert back.ts.astimezone(UTC) == row.ts.astimezone(UTC)
    if row.cost_estimate_usd is not None:
        assert back.cost_estimate_usd is not None
        assert str(back.cost_estimate_usd) == str(row.cost_estimate_usd)
        assert isinstance(back.cost_estimate_usd, Decimal)
