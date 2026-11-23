import copy
from datetime import UTC, datetime
from importlib.metadata import entry_points
from pathlib import Path

from token_economics_contracts.types import FeatureEnv, KeyInfo, RequestContext, RequestFacts
from token_economics_feat_context_clearing import ContextClearing, create

M = "claude-test-1"


def ctx(provider: str = "anthropic", model: str = M) -> RequestContext:
    return RequestContext(
        request_id="r",
        ts=datetime(2026, 1, 1, tzinfo=UTC),
        key=KeyInfo(tenant="t"),
        provider=provider,
        facts=RequestFacts(model=model),
    )


def feature(config: dict | None = None) -> ContextClearing:
    return create(FeatureEnv(state_dir=Path("."), config=config or {}))


BODY = {"model": M, "messages": [{"role": "user", "content": "hi"}]}


def test_adds_context_management_with_plan_defaults():
    # Given an anthropic body and no config / When rewritten / Then the plan defaults and the beta header apply
    r = feature().rewrite(ctx(), BODY)
    assert r is not None
    assert r.body["context_management"] == {
        "edits": [
            {
                "type": "clear_tool_uses_20250919",
                "trigger": {"type": "input_tokens", "value": 35000},
                "keep": {"type": "tool_uses", "value": 5},
                "clear_at_least": {"type": "input_tokens", "value": 4000},
            }
        ]
    }
    assert r.add_headers == (("anthropic-beta", "context-management-2025-06-27"),)
    assert r.changes == ("context_management trigger=35000 keep=5 clear_at_least=4000",)
    assert r.body["messages"] == BODY["messages"]


def test_does_not_mutate_the_input_body():
    # Given a body / When rewritten / Then the original is unchanged
    body = copy.deepcopy(BODY)
    feature().rewrite(ctx(), body)
    assert body == BODY


def test_same_input_gives_same_output():
    # Given two identical calls / Then identical rewrites
    assert feature().rewrite(ctx(), BODY) == feature().rewrite(ctx(), BODY)


def test_non_anthropic_is_left_alone():
    assert feature().rewrite(ctx(provider="openai"), BODY) is None


def test_existing_context_management_is_left_alone():
    # Given a client that already sets context_management / Then no rewrite
    assert feature().rewrite(ctx(), {**BODY, "context_management": {"edits": []}}) is None


def test_exclude_tools_are_listed_when_configured():
    r = feature({"exclude_tools": ["web_fetch", 3, ""]}).rewrite(ctx(), BODY)
    assert r is not None
    assert r.body["context_management"]["edits"][0]["exclude_tools"] == ["web_fetch"]


def test_models_filter_matches_exact_ids():
    # Given a models list / Then only exact ids are rewritten
    f = feature({"models": [M]})
    assert f.rewrite(ctx(), BODY) is not None
    assert f.rewrite(ctx(model="claude-test"), BODY) is None


def test_config_overrides_and_bad_values_fall_back():
    # Given custom and invalid values
    r = feature({"trigger": 40000, "keep": 0, "clear_at_least": True, "edit_type": "x", "beta": "b"}).rewrite(
        ctx(), BODY
    )
    assert r is not None
    edit = r.body["context_management"]["edits"][0]
    # Then valid ones apply and invalid ones fall back to defaults
    assert (edit["type"], edit["trigger"]["value"], edit["keep"]["value"]) == ("x", 40000, 5)
    assert edit["clear_at_least"]["value"] == 4000
    assert r.add_headers == (("anthropic-beta", "b"),)


def test_before_and_after_do_nothing():
    f = feature()
    assert f.before(ctx()) is None
    assert f.after(ctx(), None, 200) is None


def test_entry_point_resolves_to_the_factory():
    eps = {e.name: e for e in entry_points(group="token_economics.features")}
    assert eps["context_clearing"].load() is create
