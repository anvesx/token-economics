import json

import pytest
from token_economics_contracts.types import RequestFacts
from token_economics_feat_harness_adapters.providers.claude_code import ADAPTER as CLAUDE_CODE
from token_economics_feat_harness_adapters.providers.codex import ADAPTER as CODEX
from token_economics_feat_harness_adapters.providers.sdk import ADAPTER as SDK

SECRET = "SECRET-PROMPT-TEXT-xyz"
ANTHROPIC = [CLAUDE_CODE, SDK]


def call(i: str, cmd: str = "pytest") -> dict:
    return {
        "role": "assistant",
        "content": [
            {"type": "text", "text": SECRET},
            {"type": "tool_use", "id": i, "name": "Bash", "input": {"command": cmd, "b": 1}},
        ],
    }


def result(i: str, error: bool) -> dict:
    return {
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": i, "is_error": error, "content": SECRET}],
    }


def body(messages: list) -> bytes:
    return json.dumps({"model": "claude-test-1", "max_tokens": 64, "stream": True, "messages": messages}).encode()


@pytest.mark.parametrize("adapter", ANTHROPIC, ids=lambda a: a.name)
def test_facts_reads_model_max_tokens_stream_turns_and_size(adapter):
    # Given a body with two assistant messages
    raw = body([{"role": "user", "content": "hi"}, call("a"), result("a", False), call("b")])
    # When facts are read
    f = adapter.facts({}, raw)
    # Then the numbers match and the size estimate is len // 3
    assert (f.model, f.max_tokens, f.stream, f.turns) == ("claude-test-1", 64, True, 2)
    assert f.est_input_tokens == len(raw) // 3


@pytest.mark.parametrize("adapter", ANTHROPIC, ids=lambda a: a.name)
@pytest.mark.parametrize("n", [1, 2, 3])
def test_same_failing_call_n_times_in_a_row_counts_n(adapter, n):
    # Given the same call failing n times in a row
    msgs = []
    for i in range(n):
        msgs += [call(f"t{i}"), result(f"t{i}", True)]
    # When facts are read
    f = adapter.facts({}, body(msgs))
    # Then the run length is n and the signature is set
    assert f.trailing_repeat_failures == n
    assert len(f.last_failure_signature) == 16


@pytest.mark.parametrize("adapter", ANTHROPIC, ids=lambda a: a.name)
def test_a_success_in_between_resets_the_run(adapter):
    # Given fail, fail, success, fail of the same call
    msgs = [call("a"), result("a", True), call("b"), result("b", False), call("c"), result("c", True)]
    # When / Then only the last failure counts
    assert adapter.facts({}, body(msgs)).trailing_repeat_failures == 1


@pytest.mark.parametrize("adapter", ANTHROPIC, ids=lambda a: a.name)
def test_a_different_failing_call_resets_the_run(adapter):
    # Given the same call twice, then a different call failing
    msgs = [call("a"), result("a", True), call("b"), result("b", True), call("c", "ls"), result("c", True)]
    # When facts are read
    f = adapter.facts({}, body(msgs))
    # Then the run is 1 and the signature is the different call's
    assert f.trailing_repeat_failures == 1
    assert f.last_failure_signature != adapter.facts({}, body(msgs[:4])).last_failure_signature


@pytest.mark.parametrize("adapter", ANTHROPIC, ids=lambda a: a.name)
def test_most_recent_result_succeeding_gives_zero_repeats_but_keeps_last_signature(adapter):
    # Given a failure followed by a success
    f = adapter.facts({}, body([call("a"), result("a", True), call("b"), result("b", False)]))
    # Then the run is 0
    assert f.trailing_repeat_failures == 0
    assert f.last_failure_signature != ""


@pytest.mark.parametrize("adapter", ANTHROPIC, ids=lambda a: a.name)
def test_string_content_is_handled(adapter):
    # Given messages whose content is plain strings
    f = adapter.facts({}, body([{"role": "user", "content": "x"}, {"role": "assistant", "content": "y"}]))
    # Then turns count and there are no failures
    assert (f.turns, f.trailing_repeat_failures, f.last_failure_signature) == (1, 0, "")


@pytest.mark.parametrize("adapter", [CLAUDE_CODE, SDK, CODEX], ids=lambda a: a.name)
@pytest.mark.parametrize(
    "raw", [b"", b"not json", b"[1,2]", b'{"messages": 5, "model": 3, "max_tokens": "x"}', b"\xff\xfe"]
)
def test_garbage_body_gives_default_facts(adapter, raw):
    # Given a body that is not a valid request / When facts are read / Then it does not raise
    f = adapter.facts({}, raw)
    assert isinstance(f, RequestFacts)
    assert (f.turns, f.trailing_repeat_failures, f.model, f.max_tokens) == (0, 0, "", None)


@pytest.mark.parametrize("adapter", ANTHROPIC, ids=lambda a: a.name)
def test_no_prompt_or_tool_text_is_in_the_facts(adapter):
    # Given a conversation full of text
    f = adapter.facts({}, body([call("a"), result("a", True)]))
    # When serialised / Then none of the text is there
    dumped = f.model_dump_json()
    assert SECRET not in dumped
    assert "pytest" not in dumped


def test_codex_facts_read_the_responses_body_and_leave_turns_and_failures_empty():
    # Given a Responses API body
    raw = json.dumps({"model": "gpt-test", "max_output_tokens": 100, "stream": True, "input": SECRET}).encode()
    # When facts are read
    f = CODEX.facts({}, raw)
    # Then only the supported fields are set
    assert (f.model, f.max_tokens, f.stream, f.turns) == ("gpt-test", 100, True, 0)
    assert f.est_input_tokens == len(raw) // 3
    assert (f.last_failure_signature, f.trailing_repeat_failures) == ("", 0)
    assert SECRET not in f.model_dump_json()
