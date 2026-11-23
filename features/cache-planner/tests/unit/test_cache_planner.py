import copy
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from importlib.metadata import entry_points
from pathlib import Path

from token_economics_contracts.errors import NoPriceRow
from token_economics_contracts.types import FeatureEnv, Identity, KeyInfo, PriceRow, RequestContext
from token_economics_feat_cache_planner import CachePlanner, create

T0 = datetime(2026, 1, 1, tzinfo=UTC)
M = "claude-test-1"


def body(ttl: str | None = None, system: str = "be brief") -> dict:
    cc: dict = {"type": "ephemeral"}
    if ttl:
        cc["ttl"] = ttl
    return {
        "model": M,
        "system": [{"type": "text", "text": system, "cache_control": dict(cc)}],
        "tools": [{"name": "t", "input_schema": {}, "cache_control": dict(cc)}],
        "messages": [{"role": "user", "content": [{"type": "text", "text": "hi", "cache_control": dict(cc)}]}],
    }


def ctx(at: float, session: str = "s1", provider: str = "anthropic") -> RequestContext:
    return RequestContext(
        request_id="r",
        ts=T0 + timedelta(seconds=at),
        key=KeyInfo(tenant="t", caller="dev"),
        harness="claude-code",
        provider=provider,
        identity=Identity(session_id=session),
    )


def planner(tmp_path: Path, pricebook=None, **config) -> CachePlanner:
    return create(FeatureEnv(state_dir=tmp_path, config=config, pricebook=pricebook))  # type: ignore[return-value]


def feed(p: CachePlanner, gap: float, n: int, sent: str | None, session: str = "s1"):
    """n+1 requests `gap` seconds apart; returns the last rewrite."""
    out = None
    for i in range(n + 1):
        out = p.rewrite(ctx(i * gap, session), body(sent))
    return out


def ttls(b: dict) -> list:
    blocks = [*b["system"], *b["tools"], *b["messages"][0]["content"]]
    return [blk["cache_control"].get("ttl") for blk in blocks]


def test_short_gaps_move_a_1h_breakpoint_down_to_5m(tmp_path):
    # Given prefixes reused every minute and a client that asked for 1h
    # When ten gaps have been seen / Then the 1h ttl is dropped for the cheaper 5m
    r = feed(planner(tmp_path), 60, 10, "1h")
    assert r is not None
    assert ttls(r.body) == [None, None, None]
    assert r.changes[0].startswith("cache ttl 1h->5m (n=10 gaps, p50 60s)")


def test_gaps_of_ten_to_fifty_minutes_move_a_5m_breakpoint_up_to_1h(tmp_path):
    # Given a prefix reused every 20 minutes / When ten gaps are seen / Then every breakpoint becomes 1h
    r = feed(planner(tmp_path), 1200, 10, None)
    assert r is not None
    assert ttls(r.body) == ["1h", "1h", "1h"]
    assert r.changes == ("cache ttl 5m->1h (n=10 gaps, p50 1200s)",)


def test_very_long_gaps_leave_a_5m_request_as_sent(tmp_path):
    # Given a prefix reused only every two hours / When ten gaps are seen / Then nothing is rewritten
    assert feed(planner(tmp_path), 7200, 10, None) is None


def test_fewer_than_min_samples_changes_nothing(tmp_path):
    # Given nine gaps of 20 minutes / When the tenth request arrives / Then there is no rewrite yet
    assert feed(planner(tmp_path), 1200, 9, None) is None


def test_min_samples_is_configurable(tmp_path):
    # Given min_samples 3 / When three gaps are seen / Then the plan applies
    assert feed(planner(tmp_path, min_samples=3), 1200, 3, None) is not None


def test_the_request_body_is_not_mutated(tmp_path):
    # Given a body and a planner that will rewrite it / When it is rewritten / Then the input is unchanged
    p = planner(tmp_path)
    feed(p, 1200, 9, None)
    b = body(None)
    snapshot = copy.deepcopy(b)
    assert p.rewrite(ctx(10 * 1200), b) is not None
    assert b == snapshot


def test_other_providers_are_ignored(tmp_path):
    # Given an openai request / When rewritten / Then None, and nothing is recorded
    p = planner(tmp_path)
    assert all(p.rewrite(ctx(i * 1200, provider="openai"), body()) is None for i in range(20))


def test_odd_bodies_never_raise(tmp_path):
    # Given bodies that are not Messages shaped / When rewritten / Then None
    p = planner(tmp_path)
    for odd in ({}, {"model": 5}, {"model": M, "system": 3, "tools": "x", "messages": [1, None]}):
        assert p.rewrite(ctx(0), odd) is None


def test_a_request_without_breakpoints_is_left_alone(tmp_path):
    # Given a client that placed no cache_control / When gaps favour 1h / Then no breakpoint is added
    p = planner(tmp_path)
    b = {"model": M, "system": "plain", "messages": [{"role": "user", "content": "hi"}]}
    assert all(p.rewrite(ctx(i * 1200), b) is None for i in range(20))


def test_a_session_keeps_its_ttl_once_chosen(tmp_path):
    # Given a session that was moved to 1h / When the observed gaps later look short / Then it stays on 1h
    p = planner(tmp_path)
    feed(p, 1200, 10, None, session="a")
    for i in range(200):  # the prefix is now hammered every second, which favours 5m
        p.rewrite(ctx(20_000 + i, session="other"), body(None))
    r = p.rewrite(ctx(30_000, session="a"), body(None))
    assert r is not None and ttls(r.body) == ["1h", "1h", "1h"]


def test_a_new_session_follows_the_latest_numbers(tmp_path):
    # Same history as above, but a session that has not chosen yet gets 5m, i.e. no change to a 5m request
    p = planner(tmp_path)
    feed(p, 1200, 10, None, session="a")
    for i in range(200):
        p.rewrite(ctx(20_000 + i, session="other"), body(None))
    assert p.rewrite(ctx(30_000, session="new"), body(None)) is None


def test_stats_survive_a_restart(tmp_path):
    # Given a planner that saw ten gaps and flushed / When a new planner starts on the same state dir
    # Then it already has enough samples to plan
    p = planner(tmp_path)
    feed(p, 1200, 10, None)
    p.flush()
    state = json.loads((tmp_path / "cache_planner.json").read_text())
    assert "be brief" not in json.dumps(state)  # hashes and numbers only
    again = planner(tmp_path)
    assert again.rewrite(ctx(11 * 1200, session="fresh"), body(None)) is not None


def test_a_corrupt_state_file_is_a_cold_start(tmp_path):
    # Given garbage in the state file / When the planner starts / Then it works with no samples
    (tmp_path / "cache_planner.json").write_text("{nope")
    assert planner(tmp_path).rewrite(ctx(0), body(None)) is None


def test_persistence_is_throttled(tmp_path):
    # Given a 30 s throttle and a fake clock / When requests arrive inside the window / Then the file is written once
    now = [0.0]
    p = CachePlanner(tmp_path, clock=lambda: now[0])
    p.rewrite(ctx(0), body())
    first = (tmp_path / "cache_planner.json").read_text()
    p.rewrite(ctx(5), body())
    assert (tmp_path / "cache_planner.json").read_text() == first
    now[0] = 31.0
    p.rewrite(ctx(40), body())
    assert (tmp_path / "cache_planner.json").read_text() != first


class FakeBook:
    def __init__(self, row: PriceRow | None) -> None:
        self.row = row

    def lookup(self, provider, model, at, prompt_tokens, service_tier="standard", region=""):
        if self.row is None:
            raise NoPriceRow("none")
        return self.row


def price(read: str, w5: str, w1h: str) -> PriceRow:
    return PriceRow(
        price_row_id="p",
        provider="anthropic",
        model=M,
        effective_from=T0,
        input=Decimal(1),
        output=Decimal(5),
        cache_read=Decimal(read),
        cache_write_5m=Decimal(w5),
        cache_write_1h=Decimal(w1h),
    )


def test_pricebook_ratios_decide_when_present(tmp_path):
    # Given gaps of 20 minutes and a price book where 1h writes cost the same as 5m writes
    # When the plan is made / Then 1h wins (reads instead of rewrites); with a 100x 1h write it does not
    cheap = planner(tmp_path / "a", FakeBook(price("0.1", "1.25", "1.25")))
    assert feed(cheap, 1200, 10, None) is not None
    dear = planner(tmp_path / "b", FakeBook(price("0.1", "1.25", "100")))
    assert feed(dear, 1200, 10, None) is None


def test_missing_price_row_falls_back_to_default_ratios(tmp_path):
    # Given a price book with no row / When gaps are 20 minutes / Then the default ratios still pick 1h
    assert feed(planner(tmp_path, FakeBook(None)), 1200, 10, None) is not None


def test_entry_point_is_registered():
    eps = entry_points(group="token_economics.features")
    assert eps["cache_planner"].load() is create
