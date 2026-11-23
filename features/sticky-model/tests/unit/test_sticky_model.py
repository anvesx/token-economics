import copy
import json
from datetime import UTC, datetime
from importlib.metadata import entry_points
from pathlib import Path
from threading import Thread

from token_economics_contracts.types import FeatureEnv, Identity, KeyInfo, QuerySource, RequestContext, RequestFacts
from token_economics_feat_sticky_model import create

OPUS, HAIKU = "claude-opus-5-5", "claude-haiku-5-5"


def ctx(turns=0, session="s1", source=QuerySource.MAIN, provider="anthropic", agent=""):
    return RequestContext(
        request_id="r",
        ts=datetime(2026, 1, 1, tzinfo=UTC),
        key=KeyInfo(tenant="acme"),
        provider=provider,
        identity=Identity(session_id=session, query_source=source, agent=agent),
        facts=RequestFacts(turns=turns),
    )


def feature(tmp_path):
    return create(FeatureEnv(state_dir=tmp_path))


def body(model):
    return {"model": model, "messages": [{"role": "user", "content": "hi"}]}


def test_first_model_is_pinned_and_a_later_change_is_undone(tmp_path):
    # Given the first request pinned opus / When a later request names haiku / Then it is rewritten back with a note
    f = feature(tmp_path)
    assert f.rewrite(ctx(0), body(OPUS)) is None
    r = f.rewrite(ctx(2), body(HAIKU))
    assert r is not None
    assert r.body["model"] == OPUS
    assert r.changes == (f"model {HAIKU}->{OPUS} (pinned for session)",)


def test_does_not_mutate_the_input_body(tmp_path):
    # Given a pinned conversation / When a changed body is rewritten / Then the original is untouched
    f = feature(tmp_path)
    f.rewrite(ctx(0), body(OPUS))
    b = body(HAIKU)
    before = copy.deepcopy(b)
    f.rewrite(ctx(1), b)
    assert b == before


def test_same_model_is_left_alone(tmp_path):
    # Given a pinned model / When it repeats / Then None
    f = feature(tmp_path)
    f.rewrite(ctx(0), body(OPUS))
    assert f.rewrite(ctx(1), body(OPUS)) is None


def test_auxiliary_requests_are_ignored_and_do_not_pin(tmp_path):
    # Given title generation on haiku / Then it neither pins nor is rewritten, and the main model is unaffected
    f = feature(tmp_path)
    f.rewrite(ctx(0), body(OPUS))
    assert f.rewrite(ctx(1, source=QuerySource.AUXILIARY), body(HAIKU)) is None
    assert f.rewrite(ctx(0, source=QuerySource.AUXILIARY), body(HAIKU)) is None
    assert f.rewrite(ctx(2, source=QuerySource.AUXILIARY), body(OPUS)) is None


def test_conversations_are_pinned_separately_by_session_agent_and_source(tmp_path):
    # Given a main and a subagent conversation / Then each keeps its own pin
    f = feature(tmp_path)
    f.rewrite(ctx(0), body(OPUS))
    assert f.rewrite(ctx(0, source=QuerySource.SUBAGENT, agent="a"), body(HAIKU)) is None
    assert f.rewrite(ctx(1, source=QuerySource.SUBAGENT, agent="a"), body(HAIKU)) is None
    assert f.rewrite(ctx(1, session="other"), body(HAIKU)) is None


def test_no_session_id_means_no_state(tmp_path):
    # Given no session id / Then nothing is pinned or rewritten
    f = feature(tmp_path)
    assert f.rewrite(ctx(0, session=""), body(OPUS)) is None
    assert f.rewrite(ctx(1, session=""), body(HAIKU)) is None


def test_a_conversation_first_seen_mid_way_pins_what_it_sees(tmp_path):
    # Given a gateway that missed turn 0 / Then the first model seen is pinned
    f = feature(tmp_path)
    assert f.rewrite(ctx(5), body(OPUS)) is None
    assert f.rewrite(ctx(6), body(HAIKU)) is not None


def test_non_anthropic_and_odd_bodies_return_none(tmp_path):
    # Given another provider or a body without a model / Then None
    f = feature(tmp_path)
    assert f.rewrite(ctx(0, provider="openai"), body(OPUS)) is None
    assert f.rewrite(ctx(0), {"messages": []}) is None


def test_pin_survives_a_restart(tmp_path):
    # Given a pin written to disk / When the gateway restarts / Then the pin still holds
    feature(tmp_path).rewrite(ctx(0), body(OPUS))
    assert json.loads((tmp_path / "sticky_model.json").read_text())["entries"]
    r = feature(tmp_path).rewrite(ctx(3), body(HAIKU))
    assert r is not None and r.body["model"] == OPUS


def test_corrupt_state_file_is_tolerated(tmp_path):
    # Given garbage on disk / Then the feature starts empty and pins afresh
    (tmp_path / "sticky_model.json").write_text("not json")
    f = feature(tmp_path)
    assert f.rewrite(ctx(1), body(OPUS)) is None
    assert f.rewrite(ctx(2), body(HAIKU)) is not None


def test_concurrent_requests_keep_one_pin(tmp_path):
    # Given many threads racing on one conversation / Then exactly one model wins and every other is rewritten to it
    f = feature(tmp_path)
    out = []

    def work(i: int) -> None:
        out.append((f.rewrite(ctx(1), body(OPUS if i % 2 else HAIKU)), i))

    threads = [Thread(target=work, args=(i,)) for i in range(40)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    rewritten = {r.body["model"] for r, _ in out if r is not None}
    assert len(rewritten) == 1


def test_registered_entry_point_creates_the_feature():
    # Given the entry point / Then it loads and creates a rewriter
    (ep,) = [e for e in entry_points(group="token_economics.features") if e.name == "sticky_model"]
    f = ep.load()(FeatureEnv(state_dir=Path(".")))
    assert f.name == "sticky_model" and hasattr(f, "rewrite")
