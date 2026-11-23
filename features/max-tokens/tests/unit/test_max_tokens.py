import copy
from datetime import UTC, datetime
from importlib.metadata import entry_points
from pathlib import Path

from token_economics_contracts.types import FeatureEnv, KeyInfo, RequestContext
from token_economics_feat_max_tokens import MaxTokens, create

M = "claude-test-1"


def ctx(provider: str = "anthropic") -> RequestContext:
    return RequestContext(
        request_id="r", ts=datetime(2026, 1, 1, tzinfo=UTC), key=KeyInfo(tenant="t"), provider=provider
    )


def feature(config: dict) -> MaxTokens:
    return create(FeatureEnv(state_dir=Path("."), config=config))


def body(**extra) -> dict:
    return {"model": M, "max_tokens": 64000, "messages": [], **extra}


def test_lowers_max_tokens_to_the_model_cap():
    # Given a cap of 8192 for the model / When a body asks for 64000 / Then it is lowered and noted
    out = feature({"caps": {M: 8192}}).rewrite(ctx(), body())
    assert out is not None
    assert out.body["max_tokens"] == 8192
    assert out.changes == ("max_tokens 64000->8192",)


def test_default_applies_to_models_without_their_own_cap():
    f = feature({"caps": {"other": 100}, "default": 4096})
    out = f.rewrite(ctx(), body())
    assert out is not None and out.body["max_tokens"] == 4096


def test_never_raises_max_tokens():
    # Given a cap above the request's value / Then nothing changes
    assert feature({"caps": {M: 100000}}).rewrite(ctx(), body()) is None
    assert feature({"caps": {M: 64000}}).rewrite(ctx(), body()) is None


def test_model_ids_match_exactly():
    assert feature({"caps": {"claude-test": 10}}).rewrite(ctx(), body()) is None


def test_body_without_integer_max_tokens_is_left_alone():
    f = feature({"default": 10})
    assert f.rewrite(ctx(), {"model": M}) is None
    assert f.rewrite(ctx(), {"model": M, "max_tokens": "64000"}) is None
    assert f.rewrite(ctx(), {"model": M, "max_tokens": True}) is None
    assert f.rewrite(ctx(), {"max_tokens": 5000}) is None


def test_does_not_rewrite_when_cap_would_not_exceed_the_thinking_budget():
    # Given enabled thinking with budget 10000 / When the cap is 8192 / Then the API would reject it, so skip
    f = feature({"caps": {M: 8192}})
    thinking = {"type": "enabled", "budget_tokens": 10000}
    assert f.rewrite(ctx(), body(thinking=thinking)) is None
    # And a cap equal to the budget is also unsafe
    assert feature({"caps": {M: 10000}}).rewrite(ctx(), body(thinking=thinking)) is None


def test_rewrites_when_cap_exceeds_the_thinking_budget_or_thinking_is_off():
    f = feature({"caps": {M: 12000}})
    out = f.rewrite(ctx(), body(thinking={"type": "enabled", "budget_tokens": 10000}))
    assert out is not None and out.body["max_tokens"] == 12000
    out = feature({"caps": {M: 100}}).rewrite(ctx(), body(thinking={"type": "disabled"}))
    assert out is not None and out.body["max_tokens"] == 100


def test_non_anthropic_is_left_alone():
    assert feature({"default": 10}).rewrite(ctx("openai"), body()) is None


def test_does_not_mutate_the_input_and_is_deterministic():
    # Given a body / When rewritten twice / Then the input is untouched and outputs are equal
    b = body(thinking={"type": "disabled"})
    before = copy.deepcopy(b)
    f = feature({"default": 10})
    a, c = f.rewrite(ctx(), b), f.rewrite(ctx(), b)
    assert b == before
    assert a is not None and c is not None and a.body == c.body
    assert a.body is not b


def test_bad_config_values_fall_back_to_no_cap():
    f = feature({"caps": {M: "big", "x": -1, "y": True}, "default": 0})
    assert f.rewrite(ctx(), body()) is None
    assert feature({"caps": [1, 2], "default": "no"}).rewrite(ctx(), body()) is None


def test_before_and_after_do_nothing():
    f = feature({})
    assert f.before(ctx()) is None
    assert f.after(ctx(), None, 200) is None


def test_entry_point_resolves_to_the_factory():
    eps = {e.name: e for e in entry_points(group="token_economics.features")}
    assert eps["max_tokens"].load() is create
    assert create(FeatureEnv(state_dir=Path("."))).name == "max_tokens"
