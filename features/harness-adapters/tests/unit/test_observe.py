from pathlib import Path

import pytest
from token_economics_feat_harness_adapters.providers.claude_code import ADAPTER as CLAUDE_CODE
from token_economics_feat_harness_adapters.providers.codex import ADAPTER as CODEX
from token_economics_feat_harness_adapters.providers.sdk import ADAPTER as SDK

FIX = Path(__file__).parent.parent / "fixtures"
SSE = {"content-type": "text/event-stream", "request-id": "req_1"}
JSON = {"content-type": "application/json", "request-id": "req_1"}


def read(name: str) -> bytes:
    return (FIX / name).read_bytes()


@pytest.mark.parametrize("adapter", [CLAUDE_CODE, SDK], ids=lambda a: a.name)
def test_stream_final_output_tokens_replace_the_message_start_placeholder(adapter):
    # Given an SSE stream with placeholder output_tokens 1 and a final message_delta of 42
    # When observed
    obs = adapter.observe(200, SSE, read("anthropic_stream.sse"))
    # Then the usage shows 42 and keeps the other counts and unknown keys raw
    assert obs is not None
    assert obs.provider == "anthropic"
    assert (obs.response_id, obs.model, obs.request_id) == ("msg_test1", "claude-test-1", "req_1")
    assert obs.usage["output_tokens"] == 42
    assert obs.usage["cache_read_input_tokens"] == 100
    assert obs.usage["future_key"] == 7


def test_crlf_stream_gives_the_same_observation():
    # Given the same stream with CRLF line endings / When observed / Then it equals the LF result
    assert CLAUDE_CODE.observe(200, SSE, read("anthropic_stream_crlf.sse")) == CLAUDE_CODE.observe(
        200, SSE, read("anthropic_stream.sse")
    )


def test_cut_stream_still_yields_the_message_start_observation():
    # Given a stream cut before any message_delta / When observed / Then message_start's usage is used
    obs = CLAUDE_CODE.observe(200, SSE, read("anthropic_stream_cut.sse"))
    assert obs is not None
    assert obs.usage["output_tokens"] == 1


def test_error_event_without_message_start_gives_none():
    # Given a stream holding only an error event / When observed / Then None
    assert CLAUDE_CODE.observe(200, SSE, read("anthropic_error_only.sse")) is None


def test_error_event_after_message_start_keeps_the_partial_usage():
    # Given a stream that errors after message_start / When observed / Then the partial usage is reported
    obs = CLAUDE_CODE.observe(200, SSE, read("anthropic_stream_error.sse"))
    assert obs is not None
    assert obs.usage["output_tokens"] == 1


def test_non_stream_json_message_is_observed_with_tier_speed_and_geo():
    # Given a non-stream JSON message / When observed
    obs = SDK.observe(200, JSON, read("anthropic_message.json"))
    # Then ids and usage pass through and tier, speed and geo are copied
    assert obs is not None
    assert obs.response_id == "msg_test2"
    assert obs.usage["mystery"] == {"a": 1}
    assert (obs.service_tier, obs.speed, obs.inference_geo) == ("priority", "fast", "us")


def test_service_tier_defaults_to_standard():
    # Given a stream whose usage has no service_tier / When observed / Then "standard"
    body = b'event: message_start\ndata: {"message":{"id":"m","model":"x","usage":{"input_tokens":1}}}\n\n'
    obs = CLAUDE_CODE.observe(200, SSE, body)
    assert obs is not None and obs.service_tier == "standard"


@pytest.mark.parametrize("status", [400, 429, 500, 529])
def test_error_status_gives_none(status):
    # Given a non-2xx status / When observed / Then None even with a usable body
    assert CLAUDE_CODE.observe(status, JSON, read("anthropic_message.json")) is None
    assert CODEX.observe(status, JSON, read("responses.json")) is None


@pytest.mark.parametrize("body", [b"", b"   ", b"not json", b"[]", b'{"id":"m","model":"x"}', b"\xff\xfe"])
def test_empty_garbled_or_usageless_bodies_give_none(body):
    # Given bodies with nothing usable / When observed / Then None and no exception
    for adapter in (CLAUDE_CODE, SDK, CODEX):
        assert adapter.observe(200, JSON, body) is None
        assert adapter.observe(200, SSE, body) is None


def test_responses_stream_uses_the_completed_event():
    # Given a Responses SSE stream / When observed by Codex
    headers = {"content-type": "text/event-stream", "x-request-id": "req_o"}
    obs = CODEX.observe(200, headers, read("responses_stream.sse"))
    # Then the completed event's id, model, tier and raw usage are returned
    assert obs is not None
    assert obs.provider == "openai"
    assert (obs.response_id, obs.model, obs.service_tier, obs.request_id) == ("resp_1", "gpt-test", "flex", "req_o")
    assert obs.usage["input_tokens_details"] == {"cached_tokens": 8}
    assert obs.usage["output_tokens_details"] == {"reasoning_tokens": 2}


def test_responses_json_is_observed_and_unknown_keys_survive():
    # Given a non-stream Responses body / When observed / Then usage is raw
    obs = CODEX.observe(200, JSON, read("responses.json"))
    assert obs is not None
    assert obs.response_id == "resp_2"
    assert obs.usage["new_key"] == 1


def test_responses_stream_without_completion_gives_none():
    # Given a stream cut before response.completed / When observed / Then None
    assert CODEX.observe(200, SSE, read("responses_stream.sse").split(b"event: response.completed")[0]) is None
