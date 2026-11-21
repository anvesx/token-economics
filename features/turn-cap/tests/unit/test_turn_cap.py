from datetime import UTC, datetime
from importlib.metadata import entry_points
from pathlib import Path

from token_economics_contracts.types import FeatureEnv, KeyInfo, RequestContext, RequestFacts
from token_economics_feat_turn_cap import TurnCap, create, p75_caps

M = "claude-test-1"


def ctx(turns: int, model: str = M) -> RequestContext:
    return RequestContext(
        request_id="r",
        ts=datetime(2026, 1, 1, tzinfo=UTC),
        key=KeyInfo(tenant="t"),
        facts=RequestFacts(model=model, turns=turns),
    )


def feature(config: dict) -> TurnCap:
    return create(FeatureEnv(state_dir=Path("."), config=config))


def test_allows_when_not_configured():
    # Given no caps and no default / When any conversation arrives / Then it is allowed
    assert feature({}).before(ctx(10_000)) is None


def test_allows_a_model_with_no_cap_and_no_default():
    # Given a cap for another model only
    assert feature({"caps": {"other": 5}, "default": None}).before(ctx(100)) is None


def test_blocks_at_the_cap_and_allows_one_below():
    # Given a cap of 10 / When turns are 9 and 10 / Then 9 passes and 10 is refused
    f = feature({"caps": {M: 10}})
    assert f.before(ctx(9)) is None
    d = f.before(ctx(10))
    assert d is not None
    assert (d.allow, d.feature, d.status, d.code) == (False, "turn_cap", 429, "turn_cap_reached")
    assert d.message == (
        f"Turn cap reached: this conversation has 10 turns and the cap for {M} is 10. "
        "Start a new session or ask an admin to raise the cap."
    )


def test_default_applies_to_models_without_their_own_cap():
    # Given a default of 5 and a specific cap of 50
    f = feature({"caps": {M: 50}, "default": 5})
    # Then the other model uses the default and this one its own
    assert f.before(ctx(5, "other")) is not None
    assert f.before(ctx(5)) is None


def test_model_ids_match_exactly():
    # Given a cap for the full id / When the request carries a prefix of it / Then no cap applies
    assert feature({"caps": {M: 1}}).before(ctx(5, "claude-test")) is None


def test_after_does_nothing():
    assert feature({}).after(ctx(1), None, 200) is None


def test_p75_uses_nearest_rank():
    # Given 20 samples 1..20 / Then rank ceil(15) = 15th value
    assert p75_caps({"m": list(range(20, 0, -1))}) == {"m": 15}
    # Given 21 samples / Then rank ceil(15.75) = 16
    assert p75_caps({"m": list(range(1, 22))}) == {"m": 16}


def test_p75_leaves_out_models_with_fewer_than_20_samples():
    # Given 19 and 20 samples
    out = p75_caps({"few": [1] * 19, "enough": [4] * 20})
    # Then only the model with 20 gets a cap
    assert out == {"enough": 4}


def test_entry_point_resolves_to_the_factory():
    # Given the installed package / When the group is read / Then turn_cap loads to create
    eps = {e.name: e for e in entry_points(group="token_economics.features")}
    assert eps["turn_cap"].load() is create
    assert create(FeatureEnv(state_dir=Path("."))).name == "turn_cap"
