import copy
import json
from datetime import UTC, datetime
from decimal import Decimal
from importlib.metadata import entry_points
from pathlib import Path
from threading import Thread

from token_economics_contracts import NoPriceRow
from token_economics_contracts.types import (
    FeatureEnv,
    Identity,
    KeyInfo,
    PriceRow,
    QuerySource,
    RequestContext,
    RequestFacts,
)
from token_economics_feat_rules_router import create

OPUS, SONNET, HAIKU = "claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"


class FakeBook:
    def __init__(self, models: tuple[str, ...]) -> None:
        self.models = models

    def lookup(self, provider, model, at, prompt_tokens, service_tier="standard", region=""):
        if model not in self.models:
            raise NoPriceRow(model)
        d = Decimal(1)
        return PriceRow(
            price_row_id="p", provider=provider, model=model, effective_from=datetime(2026, 1, 1, tzinfo=UTC),
            input=d, output=d, cache_read=d, cache_write_5m=d, cache_write_1h=d,
        )  # fmt: skip


def ctx(model=OPUS, turns=0, session="s1", source=QuerySource.MAIN, est=1000, provider="anthropic", team="core"):
    return RequestContext(
        request_id="r",
        ts=datetime(2026, 1, 1, tzinfo=UTC),
        key=KeyInfo(tenant="acme", team=team),
        harness="claude-code",
        provider=provider,
        identity=Identity(session_id=session, query_source=source),
        facts=RequestFacts(model=model, turns=turns, est_input_tokens=est),
    )


def feature(tmp_path, rules=None, book=None):
    rules = [{"when": {"model": OPUS}, "model": SONNET}] if rules is None else rules
    return create(FeatureEnv(state_dir=tmp_path, config={"rules": rules}, pricebook=book))


def body(model=OPUS):
    return {"model": model, "messages": [{"role": "user", "content": "hi"}]}


def test_routes_at_conversation_start_and_notes_the_rule(tmp_path):
    # Given rule 2 matches / When the conversation starts / Then the model is rewritten with a note
    f = feature(tmp_path, [{"when": {"model": "x"}, "model": HAIKU}, {"when": {"model": OPUS}, "model": SONNET}])
    r = f.rewrite(ctx(), body())
    assert r is not None
    assert r.body["model"] == SONNET
    assert r.changes == (f"model {OPUS}->{SONNET} (rule 2)",)


def test_does_not_mutate_the_input_body(tmp_path):
    # Given a body / When it is routed / Then the original is unchanged
    b = body()
    before = copy.deepcopy(b)
    feature(tmp_path).rewrite(ctx(), b)
    assert b == before


def test_first_matching_rule_wins(tmp_path):
    # Given two matching rules / When routing / Then the first one is used
    f = feature(tmp_path, [{"when": {}, "model": HAIKU}, {"when": {}, "model": SONNET}])
    r = f.rewrite(ctx(), body())
    assert r is not None and r.body["model"] == HAIKU


def test_later_turns_keep_the_routed_model(tmp_path):
    # Given a routed conversation / When turn 2 arrives with the client's original model / Then it is routed again
    f = feature(tmp_path)
    f.rewrite(ctx(turns=0), body())
    r = f.rewrite(ctx(turns=3), body())
    assert r is not None and r.body["model"] == SONNET


def test_user_model_switch_stops_routing_for_that_conversation(tmp_path):
    # Given a routed conversation / When the client sends another model / Then it is left alone from then on
    f = feature(tmp_path)
    f.rewrite(ctx(turns=0), body())
    assert f.rewrite(ctx(turns=2, model=HAIKU), body(HAIKU)) is None
    assert f.rewrite(ctx(turns=3), body()) is None


def test_no_rewrite_without_a_start_or_a_session_or_a_match(tmp_path):
    # Given mid-conversation first sight, no session id, or no match / Then nothing happens
    f = feature(tmp_path)
    assert f.rewrite(ctx(turns=4), body()) is None
    assert f.rewrite(ctx(session=""), body()) is None
    assert f.rewrite(ctx(model=HAIKU), body(HAIKU)) is None


def test_when_fields_all_must_match(tmp_path):
    # Given a rule with several conditions / When one differs / Then it does not fire
    rule = {
        "when": {"team": "core", "query_source": "main", "min_est_input_tokens": 500, "max_est_input_tokens": 2000},
        "model": SONNET,
    }
    f = feature(tmp_path, [rule])
    assert f.rewrite(ctx(), body()) is not None
    assert f.rewrite(ctx(session="a", team="other"), body()) is None
    assert f.rewrite(ctx(session="b", source=QuerySource.SUBAGENT), body()) is None
    assert f.rewrite(ctx(session="c", est=100), body()) is None
    assert f.rewrite(ctx(session="d", est=5000), body()) is None


def test_target_equal_to_current_model_is_skipped(tmp_path):
    # Given a rule targeting the model already in use / Then no rewrite
    assert feature(tmp_path, [{"when": {}, "model": OPUS}]).rewrite(ctx(), body()) is None


def test_unpriced_target_is_not_routed_to(tmp_path):
    # Given a price book without the target / Then no route; with it priced, route
    assert feature(tmp_path, book=FakeBook((OPUS,))).rewrite(ctx(), body()) is None
    assert feature(tmp_path, book=FakeBook((OPUS, SONNET))).rewrite(ctx(), body()) is not None


def test_non_anthropic_and_odd_bodies_return_none(tmp_path):
    # Given another provider or a body without a model / Then None and no exception
    f = feature(tmp_path)
    assert f.rewrite(ctx(provider="openai"), body()) is None
    assert f.rewrite(ctx(), {"messages": []}) is None
    assert f.rewrite(ctx(), {"model": 5}) is None


def test_malformed_rules_are_skipped_but_numbering_holds(tmp_path):
    # Given a bad rule 1 and a good rule 2 / Then rule 2 still fires and is numbered 2
    f = feature(tmp_path, ["junk", {"when": {"bogus": 1}, "model": HAIKU}, {"when": {}, "model": SONNET}])
    r = f.rewrite(ctx(), body())
    assert r is not None and r.changes == (f"model {OPUS}->{SONNET} (rule 3)",)
    assert f.skipped == ["rule 1", "rule 2"]


def test_state_survives_a_restart(tmp_path):
    # Given a routed conversation / When the gateway restarts / Then turn 2 is still routed
    feature(tmp_path).rewrite(ctx(turns=0), body())
    assert json.loads((tmp_path / "rules_router.json").read_text())["entries"]
    r = feature(tmp_path).rewrite(ctx(turns=2), body())
    assert r is not None and r.body["model"] == SONNET


def test_corrupt_state_file_is_tolerated(tmp_path):
    # Given garbage on disk / Then the feature starts empty
    (tmp_path / "rules_router.json").write_text("{nope")
    assert feature(tmp_path).rewrite(ctx(turns=2), body()) is None


def test_concurrent_conversations_do_not_interfere(tmp_path):
    # Given many threads each starting a conversation / Then every one is routed and remembered
    f = feature(tmp_path)
    results: dict[int, object] = {}

    def work(i: int) -> None:
        results[i] = f.rewrite(ctx(session=f"s{i}"), body())
        results[-i - 1] = f.rewrite(ctx(session=f"s{i}", turns=1), body())

    threads = [Thread(target=work, args=(i,)) for i in range(40)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert all(r is not None for r in results.values()) and len(results) == 80


def test_registered_entry_point_creates_the_feature():
    # Given the entry point / Then it loads and creates a rewriter
    (ep,) = [e for e in entry_points(group="token_economics.features") if e.name == "rules_router"]
    f = ep.load()(FeatureEnv(state_dir=Path("."), config={}))
    assert f.name == "rules_router" and hasattr(f, "rewrite")


def test_a_restarted_conversation_that_matches_no_rule_forgets_the_old_route(tmp_path):
    # Given a routed conversation, then a new one under the same key that no rule matches
    rules = {"rules": [{"when": {"team": "core"}, "model": SONNET}]}
    f = create(FeatureEnv(state_dir=tmp_path, config=rules))
    assert f.rewrite(ctx(turns=0, team="core"), {"model": OPUS, "messages": []}) is not None
    assert f.rewrite(ctx(turns=0, team="infra"), {"model": OPUS, "messages": []}) is None
    # When its later turns send opus / Then they are not routed by the old conversation's entry
    assert f.rewrite(ctx(turns=1, team="infra"), {"model": OPUS, "messages": []}) is None
