from pathlib import Path

from token_economics_feat_harness_adapters.providers.claude_code import ADAPTER as CLAUDE_CODE
from token_economics_feat_harness_adapters.providers.codex import ADAPTER as CODEX
from token_economics_feat_harness_adapters.providers.sdk import ADAPTER as SDK

FIX = Path(__file__).parent.parent / "fixtures"


def test_repeated_message_id_gives_one_observation_with_the_last_usage():
    # Given a transcript where msg_a streams over two lines, plus bad, synthetic and usage-less lines
    # When replayed
    obs = list(CLAUDE_CODE.replay(FIX / "transcript.jsonl"))
    # Then one observation per id in first-seen order, msg_a with its last usage
    assert [o.response_id for o in obs] == ["msg_a", "msg_d"]
    assert obs[0].usage["output_tokens"] == 77
    assert obs[0].speed == "standard"
    assert obs[1].inference_geo == "global"
    assert all(o.provider == "anthropic" for o in obs)


def test_missing_transcript_gives_nothing():
    # Given a path that does not exist / When replayed / Then empty, no exception
    assert list(CLAUDE_CODE.replay(FIX / "nope.jsonl")) == []


def test_codex_and_sdk_replay_are_not_built_yet():
    # Given the two adapters without a transcript reader / When replayed / Then empty
    assert list(CODEX.replay(FIX / "transcript.jsonl")) == []
    assert list(SDK.replay(FIX / "transcript.jsonl")) == []
