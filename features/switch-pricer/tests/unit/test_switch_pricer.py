import copy
import json
from datetime import UTC, datetime
from decimal import Decimal
from importlib.metadata import entry_points
from pathlib import Path
from threading import Thread

from token_economics_contracts import NoPriceRow
from token_economics_contracts.types import FeatureEnv, Identity, KeyInfo, PriceRow, RequestContext, RequestFacts
from token_economics_feat_switch_pricer import create

OPUS, SONNET, MYSTERY = "claude-opus-5-5", "claude-sonnet-5-5", "mystery-1"
# USD per 1M tokens: (output, cache_read, cache_write_5m)
RATES = {OPUS: ("25", "0.5", "6.25"), SONNET: ("15", "0.3", "3.75")}


class FakeBook:
    def lookup(self, provider, model, at, prompt_tokens, service_tier="standard", region=""):
        if model not in RATES:
            raise NoPriceRow(model)
        out, read, write = (Decimal(x) for x in RATES[model])
        return PriceRow(
            price_row_id="p", provider=provider, model=model, effective_from=datetime(2026, 1, 1, tzinfo=UTC),
            input=Decimal(5), output=out, cache_read=read, cache_write_5m=write, cache_write_1h=write,
        )  # fmt: skip


def ctx(turns=1, est=100_000, session="s1", provider="anthropic"):
    return RequestContext(
        request_id="r",
        ts=datetime(2026, 1, 1, tzinfo=UTC),
        key=KeyInfo(tenant="acme"),
        provider=provider,
        identity=Identity(session_id=session),
        facts=RequestFacts(turns=turns, est_input_tokens=est),
    )


def feature(tmp_path, config=None, book=True):
    return create(FeatureEnv(state_dir=tmp_path, config=config or {}, pricebook=FakeBook() if book else None))


def body(model):
    return {"model": model, "messages": []}


def log(tmp_path):
    p = tmp_path / "switch_pricer.jsonl"
    return [json.loads(line) for line in p.read_text().splitlines()] if p.exists() else []


def test_switch_that_does_not_pay_back_is_reverted_with_both_numbers(tmp_path):
    # Given 100k tokens on opus and 2 expected turns / When switching to sonnet
    # Then saving per turn is 0.02 + 0.02 = 0.04, x2 = 0.08, below the 0.325 extra cost of the switch turn: reverted
    f = feature(tmp_path, {"expected_remaining_turns": 2})
    f.rewrite(ctx(0), body(OPUS))
    r = f.rewrite(ctx(1), body(SONNET))
    assert r is not None
    assert r.body["model"] == OPUS
    assert r.changes == (
        "model claude-sonnet-5-5->claude-opus-5-5 "
        "(switch reverted: saving $0.0800 over 2 turns <= cache rewrite $0.3250)",
    )
    (rec,) = log(tmp_path)
    assert (rec["from"], rec["to"], rec["verdict"], rec["saving_usd"], rec["cost_usd"]) == (
        OPUS, SONNET, "reverted", "0.0800", "0.3250",
    )  # fmt: skip


def test_switch_that_pays_back_is_allowed_and_becomes_the_new_baseline(tmp_path):
    # Given a saving of 0.40 over 10 turns vs a 0.325 switch cost / Then allowed, logged, later turns quiet
    f = feature(tmp_path)
    f.rewrite(ctx(0), body(OPUS))
    assert f.rewrite(ctx(1), body(SONNET)) is None
    assert f.rewrite(ctx(2), body(SONNET)) is None
    (rec,) = log(tmp_path)
    assert (rec["verdict"], rec["saving_usd"], rec["cost_usd"]) == ("allowed", "0.4000", "0.3250")


def test_unpriced_model_leaves_the_switch_alone_and_logs_it(tmp_path):
    # Given a model with no price row / Then no rewrite and verdict unpriced
    f = feature(tmp_path)
    f.rewrite(ctx(0), body(OPUS))
    assert f.rewrite(ctx(1), body(MYSTERY)) is None
    (rec,) = log(tmp_path)
    assert (rec["verdict"], rec["saving_usd"], rec["cost_usd"]) == ("unpriced", None, None)


def test_no_price_book_is_unpriced(tmp_path):
    # Given no price book / Then switches are left alone
    f = feature(tmp_path, book=False)
    f.rewrite(ctx(0), body(OPUS))
    assert f.rewrite(ctx(1), body(SONNET)) is None
    assert log(tmp_path)[0]["verdict"] == "unpriced"


def test_does_not_mutate_the_input_body(tmp_path):
    # Given a reverted switch / Then the input body is unchanged
    f = feature(tmp_path, {"expected_remaining_turns": 1})
    f.rewrite(ctx(0), body(OPUS))
    b = body(SONNET)
    before = copy.deepcopy(b)
    assert f.rewrite(ctx(1), b) is not None
    assert b == before


def test_first_request_same_model_and_new_conversation_are_not_priced(tmp_path):
    # Given first sight, the same model, and a turn-0 restart / Then nothing is priced or logged
    f = feature(tmp_path)
    assert f.rewrite(ctx(0), body(OPUS)) is None
    assert f.rewrite(ctx(1), body(OPUS)) is None
    assert f.rewrite(ctx(0), body(SONNET)) is None
    assert log(tmp_path) == []


def test_no_session_id_and_non_anthropic_return_none(tmp_path):
    # Given no session or another provider / Then None
    f = feature(tmp_path)
    assert f.rewrite(ctx(session=""), body(OPUS)) is None
    assert f.rewrite(ctx(provider="openai"), body(OPUS)) is None
    assert f.rewrite(ctx(), {"messages": []}) is None


def test_baseline_survives_a_restart(tmp_path):
    # Given opus recorded / When the gateway restarts / Then a later switch is still priced against opus
    feature(tmp_path, {"expected_remaining_turns": 1}).rewrite(ctx(0), body(OPUS))
    r = feature(tmp_path, {"expected_remaining_turns": 1}).rewrite(ctx(3), body(SONNET))
    assert r is not None and r.body["model"] == OPUS


def test_corrupt_state_file_is_tolerated(tmp_path):
    # Given garbage on disk / Then the feature starts empty
    (tmp_path / "switch_pricer.json").write_text("[[")
    assert feature(tmp_path).rewrite(ctx(1), body(OPUS)) is None


def test_bad_config_falls_back_to_defaults(tmp_path):
    # Given nonsense config / Then the defaults of 2000 tokens and 10 turns apply
    f = feature(tmp_path, {"expected_output_tokens": "x", "expected_remaining_turns": True})
    assert (f.expected_output_tokens, f.expected_remaining_turns) == (2000, 10)


def test_concurrent_decisions_all_log(tmp_path):
    # Given many conversations switching at once / Then each logs exactly one decision
    f = feature(tmp_path)
    for i in range(30):
        f.rewrite(ctx(0, session=f"s{i}"), body(OPUS))
    threads = [Thread(target=f.rewrite, args=(ctx(1, session=f"s{i}"), body(SONNET))) for i in range(30)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(log(tmp_path)) == 30


def test_registered_entry_point_creates_the_feature():
    # Given the entry point / Then it loads and creates a rewriter
    (ep,) = [e for e in entry_points(group="token_economics.features") if e.name == "switch_pricer"]
    f = ep.load()(FeatureEnv(state_dir=Path(".")))
    assert f.name == "switch_pricer" and hasattr(f, "rewrite")
