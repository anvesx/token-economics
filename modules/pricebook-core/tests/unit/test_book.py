from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from token_economics_contracts import NoPriceRow, PriceBook, PriceBookViolation, PriceRow
from token_economics_pricebook_core import PriceBookCore, seed_rows

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def row(rid: str, model: str = "claude-sonnet-5-5", read: str = "0.20", **kw: object) -> PriceRow:
    base = dict(
        price_row_id=rid,
        provider="anthropic",
        model=model,
        effective_from=T0,
        input=Decimal("2"),
        output=Decimal("10"),
        cache_read=Decimal(read),
        cache_write_5m=Decimal("2.5"),
        cache_write_1h=Decimal("4"),
    )
    return PriceRow(**{**base, **kw})  # type: ignore[arg-type]


def test_core_implements_the_price_book_port() -> None:
    assert isinstance(PriceBookCore(), PriceBook)


def test_history_is_repriced_with_the_row_in_force_on_the_request_date() -> None:
    # Given a cache-read price that changed on 2026-10-07
    cut = datetime(2026, 10, 7, tzinfo=UTC)
    book = PriceBookCore([row("old", read="0.20"), row("new", read="0.10", effective_from=cut)])
    # When a request from before and one from after the cutover are priced
    # Then each gets the row in force on its own date
    assert book.lookup("anthropic", "claude-sonnet-5-5", cut - timedelta(days=1), 10).price_row_id == "old"
    assert book.lookup("anthropic", "claude-sonnet-5-5", cut, 10).price_row_id == "new"


def test_a_row_can_never_be_changed_only_appended() -> None:
    book = PriceBookCore([row("a")])
    assert book.add(row("a")) is False  # the identical row again is a no-op
    with pytest.raises(PriceBookViolation):
        book.add(row("a", read="0.10"))  # same id, different price
    with pytest.raises(PriceBookViolation):
        book.add(row("b", read="0.10"))  # same key, different id
    assert book.get("a").cache_read == Decimal("0.20")


def test_only_the_exact_model_id_matches() -> None:
    book = PriceBookCore([row("a", model="claude-sonnet-5-5")])
    for near in ("claude-sonnet-5", "claude-sonnet-5-5-20261001", "sonnet", "CLAUDE-SONNET-5-5"):
        with pytest.raises(NoPriceRow):
            book.lookup("anthropic", near, T0, 10)


def test_context_band_is_picked_from_total_prompt_tokens() -> None:
    # Given Haiku 5.5, which reprices the whole request above 100K prompt tokens
    book = PriceBookCore(seed_rows())
    at = datetime(2026, 11, 1, tzinfo=UTC)
    assert book.lookup("anthropic", "claude-haiku-5-5", at, 100_000).input == Decimal("0.10")
    assert book.lookup("anthropic", "claude-haiku-5-5", at, 100_001).input == Decimal("0.50")


def test_no_row_before_its_effective_date_or_after_its_end() -> None:
    book = PriceBookCore([row("a", effective_to=T0 + timedelta(days=10))])
    with pytest.raises(NoPriceRow):
        book.lookup("anthropic", "claude-sonnet-5-5", T0 - timedelta(seconds=1), 10)
    with pytest.raises(NoPriceRow):
        book.lookup("anthropic", "claude-sonnet-5-5", T0 + timedelta(days=10), 10)


def test_region_row_wins_over_the_default_region() -> None:
    book = PriceBookCore([row("default"), row("eu", region="eu", input=Decimal("3"))])
    assert book.lookup("anthropic", "claude-sonnet-5-5", T0, 10, region="eu").price_row_id == "eu"
    assert book.lookup("anthropic", "claude-sonnet-5-5", T0, 10, region="us").price_row_id == "default"


def test_rows_unverified_for_30_days_or_about_to_expire_are_flagged_stale() -> None:
    now = datetime(2026, 11, 21, tzinfo=UTC)
    fresh = row("fresh", model="m1", last_verified_at=now - timedelta(days=29))
    old = row("old", model="m2", last_verified_at=now - timedelta(days=31))
    never = row("never", model="m3")
    expiring = row("expiring", model="m4", last_verified_at=now, effective_to=now + timedelta(days=7))
    gone = row("gone", model="m5", effective_to=now - timedelta(days=1))
    assert {r.price_row_id for r in PriceBookCore([fresh, old, never, expiring, gone]).stale(now)} == {
        "old",
        "never",
        "expiring",
    }


def test_every_seed_row_is_marked_unverified_and_cache_rates_follow_the_multiples() -> None:
    rows = seed_rows()
    assert rows and all(r.confidence == "unverified" and r.last_verified_at is None for r in rows)
    by = {r.model: r for r in rows if r.context_band_min == 0}
    assert by["claude-sonnet-5-5"].cache_read == Decimal("0.10")  # 0.05x of $2, not the stale $0.20
    assert by["claude-opus-5-5"].cache_read == Decimal("0.20")
    assert by["claude-fable-5-2"].cache_read == Decimal("0.250")
    assert by["claude-opus-5-5"].cache_write_1h == Decimal("8") and by["claude-opus-5-5"].cache_write_5m == Decimal(
        "5.00"
    )
