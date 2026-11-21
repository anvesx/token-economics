import pytest
from token_economics_contracts import Buckets, UnknownUsageKey
from token_economics_metering.providers.anthropic import NORMALISER as anthropic
from token_economics_metering.providers.openai import NORMALISER as openai

REAL_ANTHROPIC = {  # key set seen in Claude Code responses
    "input_tokens": 2,
    "cache_creation_input_tokens": 718,
    "cache_read_input_tokens": 0,
    "output_tokens": 67,
    "output_tokens_details": {"thinking_tokens": 0},
    "server_tool_use": {"web_search_requests": 0, "web_fetch_requests": 0},
    "service_tier": "standard",
    "cache_creation": {"ephemeral_1h_input_tokens": 718, "ephemeral_5m_input_tokens": 0},
    "inference_geo": "global",
    "iterations": [],
    "speed": "standard",
    "fallback_credit": None,
}


def test_anthropic_usage_becomes_five_exclusive_buckets() -> None:
    # Given a real-shaped Anthropic usage object with a 1-hour cache write
    # When it is normalised
    b = anthropic.normalise(REAL_ANTHROPIC)
    # Then input excludes cache, and the write lands in the 1-hour bucket only
    assert b == Buckets(fresh_input=2, cache_write_1h=718, output=67)


def test_anthropic_write_without_a_recorded_lifetime_is_a_5_minute_write() -> None:
    b = anthropic.normalise({"input_tokens": 10, "cache_creation_input_tokens": 100, "output_tokens": 1})
    assert (b.cache_write_5m, b.cache_write_1h) == (100, 0)


def test_unknown_usage_key_is_rejected() -> None:
    # Given a gateway in the path added a key the normaliser does not know
    # When the usage is normalised  # Then it is rejected, not guessed
    with pytest.raises(UnknownUsageKey) as err:
        anthropic.normalise({**REAL_ANTHROPIC, "cache_write_tokens": 5})
    assert err.value.keys == ["cache_write_tokens"]
    with pytest.raises(UnknownUsageKey):
        anthropic.normalise({"input_tokens": 1, "cache_creation": {"ephemeral_12h_input_tokens": 9}})
    with pytest.raises(UnknownUsageKey):
        openai.normalise({"input_tokens": 1, "output_tokens": 1, "cache_write_tokens": 3})


def test_openai_prompt_tokens_include_cached_so_fresh_is_the_difference() -> None:
    # Given the example in plan/03: 17,903 prompt tokens with 17,817 cached
    usage = {
        "prompt_tokens": 17_903,
        "completion_tokens": 10,
        "total_tokens": 17_913,
        "prompt_tokens_details": {"cached_tokens": 17_817},
    }
    # Then 86 are fresh
    assert openai.normalise(usage) == Buckets(fresh_input=86, cache_read=17_817, output=10)


def test_reasoning_tokens_are_never_added_to_output_twice() -> None:
    # Given 1,186 output tokens that already include 1,024 reasoning tokens (plan/03)
    usage = {"input_tokens": 50, "output_tokens": 1_186, "output_tokens_details": {"reasoning_tokens": 1_024}}
    assert openai.normalise(usage).output == 1_186


def test_inconsistent_counts_are_an_error_not_a_guess() -> None:
    with pytest.raises(ValueError):
        openai.normalise({"input_tokens": 5, "output_tokens": 1, "input_tokens_details": {"cached_tokens": 9}})
    with pytest.raises(ValueError):
        anthropic.normalise({"input_tokens": -1})
    with pytest.raises(ValueError):
        anthropic.normalise(
            {
                "cache_creation_input_tokens": 10,
                "cache_creation": {"ephemeral_5m_input_tokens": 8, "ephemeral_1h_input_tokens": 8},
            }
        )
