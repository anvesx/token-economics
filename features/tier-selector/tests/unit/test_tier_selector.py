import copy
from datetime import UTC, datetime
from importlib.metadata import entry_points
from pathlib import Path

from token_economics_contracts.types import FeatureEnv, Identity, KeyInfo, QuerySource, RequestContext, RequestFacts
from token_economics_feat_tier_selector import create

SONNET = "claude-sonnet-5-5"


def ctx(provider="openai", team="batch", source=QuerySource.MAIN, model=SONNET):
    return RequestContext(
        request_id="r",
        ts=datetime(2026, 1, 1, tzinfo=UTC),
        key=KeyInfo(tenant="acme", team=team, caller="ci"),
        harness="claude-code",
        provider=provider,
        identity=Identity(query_source=source),
        facts=RequestFacts(model=model),
    )


def feature(rules, **extra):
    return create(FeatureEnv(state_dir=Path("."), config={"rules": rules, **extra}))


FLEX = [{"when": {"team": "batch"}, "service_tier": "flex"}]


def test_entry_point_is_registered():
    assert any(e.name == "tier_selector" for e in entry_points(group="token_economics.features"))


def test_matching_rule_sets_the_tier_and_notes_the_rule():
    # Given a rule for the batch team / When an OpenAI request from it arrives / Then service_tier is flex
    body = {"model": SONNET, "messages": []}
    original = copy.deepcopy(body)
    out = feature(FLEX).rewrite(ctx(), body)
    assert out is not None
    assert out.body["service_tier"] == "flex"
    assert out.changes == ("service_tier -> flex (rule 1)",)
    assert body == original


def test_first_match_wins():
    # Given two matching rules / When a request arrives / Then the first decides, numbered from 1
    rules = [{"when": {"team": "other"}, "service_tier": "priority"}, *FLEX, {"when": {}, "service_tier": "auto"}]
    out = feature(rules).rewrite(ctx(), {})
    assert out is not None and out.changes == ("service_tier -> flex (rule 2)",)


def test_no_matching_rule_leaves_the_request_alone():
    assert feature(FLEX).rewrite(ctx(team="core"), {}) is None


def test_value_not_allowed_for_the_provider_is_not_applied():
    # Given flex is not an Anthropic value / When an Anthropic request matches / Then nothing changes
    assert feature(FLEX).rewrite(ctx(provider="anthropic"), {}) is None


def test_anthropic_standard_only_is_applied():
    rules = [{"when": {"query_source": "main"}, "service_tier": "standard_only"}]
    out = feature(rules).rewrite(ctx(provider="anthropic"), {})
    assert out is not None and out.body["service_tier"] == "standard_only"


def test_unsupported_provider_is_never_rewritten():
    assert feature(FLEX).rewrite(ctx(provider="gemini"), {}) is None


def test_request_that_sets_a_tier_is_left_alone_unless_override():
    # Given the client chose a tier / When no override / Then untouched; with override it is replaced
    body = {"service_tier": "priority"}
    assert feature(FLEX).rewrite(ctx(), body) is None
    out = feature(FLEX, override=True).rewrite(ctx(), body)
    assert out is not None and out.body["service_tier"] == "flex"


def test_override_with_the_same_tier_is_no_change():
    assert feature(FLEX, override=True).rewrite(ctx(), {"service_tier": "flex"}) is None


def test_exact_match_only_and_unknown_when_key_never_matches():
    assert feature([{"when": {"team": "bat"}, "service_tier": "flex"}]).rewrite(ctx(), {}) is None
    assert feature([{"when": {"colour": "x"}, "service_tier": "flex"}]).rewrite(ctx(), {}) is None


def test_malformed_config_does_not_raise_and_keeps_rule_numbers():
    rules = ["junk", {"when": {"team": "batch"}, "service_tier": "flex"}, {"when": 3}]
    out = feature(rules).rewrite(ctx(), {})
    assert out is not None and out.changes == ("service_tier -> flex (rule 2)",)
    assert create(FeatureEnv(state_dir=Path("."), config={"rules": 5})).rewrite(ctx(), {}) is None


def test_non_dict_body_values_do_not_raise():
    assert feature(FLEX).rewrite(ctx(), {"service_tier": None}) is not None
