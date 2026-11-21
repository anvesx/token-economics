from datetime import UTC, datetime
from importlib.metadata import entry_points
from pathlib import Path

from token_economics_contracts.types import FeatureEnv, KeyInfo, RequestContext, RequestFacts
from token_economics_feat_loop_guard import create


def ctx(repeats: int) -> RequestContext:
    return RequestContext(
        request_id="r",
        ts=datetime(2026, 1, 1, tzinfo=UTC),
        key=KeyInfo(tenant="t"),
        facts=RequestFacts(trailing_repeat_failures=repeats, last_failure_signature="abc"),
    )


def feature(config: dict | None = None):
    return create(FeatureEnv(state_dir=Path("."), config=config or {}))


def test_allows_when_not_configured_and_no_repeats():
    # Given the default config / When nothing or one failure has happened / Then it is allowed
    assert feature().before(ctx(0)) is None
    assert feature().before(ctx(1)) is None


def test_default_threshold_blocks_the_first_repeat():
    # Given the default of 2 / When the same call has failed twice / Then it is refused
    d = feature().before(ctx(2))
    assert d is not None
    assert (d.allow, d.feature, d.status, d.code) == (False, "loop_guard", 429, "repeated_failure")
    assert d.message == (
        "Loop guard: the same tool call has failed 2 times in a row with the same input. "
        "Change the approach before retrying."
    )


def test_configured_threshold_is_respected_at_the_boundary():
    # Given a threshold of 3 / Then 2 passes, 3 and 4 are refused
    f = feature({"repeat_failures": 3})
    assert f.before(ctx(2)) is None
    assert f.before(ctx(3)) is not None
    assert f.before(ctx(4)) is not None


def test_invalid_threshold_falls_back_to_the_default():
    # Given nonsense config / Then the default of 2 applies
    for bad in (0, -1, "x", True, None):
        assert feature({"repeat_failures": bad}).before(ctx(2)) is not None
        assert feature({"repeat_failures": bad}).before(ctx(1)) is None


def test_after_does_nothing():
    assert feature().after(ctx(0), None, 200) is None


def test_entry_point_resolves_to_the_factory():
    # Given the installed package / When the group is read / Then loop_guard loads to create
    eps = {e.name: e for e in entry_points(group="token_economics.features")}
    assert eps["loop_guard"].load() is create
    assert feature().name == "loop_guard"
