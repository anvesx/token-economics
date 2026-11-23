import copy
from datetime import UTC, datetime
from importlib.metadata import entry_points
from pathlib import Path

from token_economics_contracts.types import FeatureEnv, KeyInfo, RequestContext
from token_economics_feat_output_cap import OutputCap, create

# 100 tokens x 1 char per token = 100 characters allowed, so tests stay small.
SMALL = {"limit_tokens": 100, "chars_per_token": 1}


def ctx(provider: str = "anthropic") -> RequestContext:
    return RequestContext(
        request_id="r", ts=datetime(2026, 1, 1, tzinfo=UTC), key=KeyInfo(tenant="t"), provider=provider
    )


def feature(config: dict | None = None) -> OutputCap:
    return create(FeatureEnv(state_dir=Path("."), config=SMALL if config is None else config))


def turn(tool: str, content, tid: str = "t1", **result_extra) -> list[dict]:
    return [
        {"role": "assistant", "content": [{"type": "tool_use", "id": tid, "name": tool, "input": {}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid, "content": content, **result_extra}]},
    ]


def body(messages: list[dict]) -> dict:
    return {"model": "m", "max_tokens": 10, "messages": messages}


def result_content(out_body: dict, msg_index: int = 1):
    return out_body["messages"][msg_index]["content"][0]["content"]


BIG = "a" * 1000


def test_caps_an_oversized_string_result_keeping_head_and_tail():
    # Given a 1000 char Bash result and a 100 char allowance / When rewritten
    out = feature().rewrite(ctx(), body(turn("Bash", "H" * 500 + "T" * 500)))
    # Then 70 head chars, a marker for 900 removed chars, and 30 tail chars remain
    assert out is not None
    assert result_content(out.body) == (
        "H" * 70 + "\n[token-economics: 900 characters removed from this tool result]\n" + "T" * 30
    )
    assert out.changes == ("capped 1 tool results, 900 chars removed",)


def test_caps_text_blocks_and_leaves_images_alone():
    # Given a result of an image block and an oversized text block
    image = {"type": "image", "source": {"type": "base64", "data": "x" * 5000}}
    out = feature().rewrite(ctx(), body(turn("Bash", [image, {"type": "text", "text": BIG}])))
    # Then the image is untouched and the text is capped
    assert out is not None
    blocks = result_content(out.body)
    assert blocks[0] == image
    assert "900 characters removed" in blocks[1]["text"]


def test_small_results_are_left_alone():
    assert feature().rewrite(ctx(), body(turn("Bash", "a" * 100))) is None


def test_protected_tools_are_never_capped():
    # Given file reads and edits, which are edit anchors
    for tool in ("Read", "Edit", "MultiEdit", "Write", "NotebookEdit", "NotebookRead"):
        assert feature().rewrite(ctx(), body(turn(tool, BIG))) is None


def test_protect_tools_config_replaces_the_default_list():
    f = feature({**SMALL, "protect_tools": ["Bash"]})
    assert f.rewrite(ctx(), body(turn("Bash", BIG))) is None
    assert f.rewrite(ctx(), body(turn("Read", BIG))) is not None


def test_error_results_are_never_capped():
    assert feature().rewrite(ctx(), body(turn("Bash", BIG, is_error=True))) is None


def test_results_with_tracebacks_and_failures_are_never_capped():
    # Given large outputs containing protected patterns
    texts = [
        "Traceback (most recent call last):\n" + BIG,
        BIG + '\n  File "x.py", line 3, in f\n',
        BIG + "\n    at Object.run (/app/a.js:10:5)\n",
        BIG + "\npanic: boom\n",
        BIG + "\nerror[E0308]: mismatched types\n",
        BIG + "\ntests/test_a.py::t FAILED\n",
        BIG + "\nAssertionError: x\n",
    ]
    for t in texts:
        assert feature().rewrite(ctx(), body(turn("Bash", t))) is None, t[-40:]
        assert feature().rewrite(ctx(), body(turn("Bash", [{"type": "text", "text": t}]))) is None


def test_unknown_tool_id_is_treated_as_unprotected():
    msgs = turn("Read", BIG, tid="t1")
    msgs[1]["content"][0]["tool_use_id"] = "other"
    assert feature().rewrite(ctx(), body(msgs)) is not None


def test_counts_several_results_across_turns():
    msgs = turn("Bash", BIG, "a") + turn("Grep", BIG, "b")
    out = feature().rewrite(ctx(), body(msgs))
    assert out is not None
    assert out.changes == ("capped 2 tool results, 1800 chars removed",)


def test_non_anthropic_is_left_alone():
    assert feature().rewrite(ctx("openai"), body(turn("Bash", BIG))) is None


def test_odd_bodies_return_none():
    f = feature()
    assert f.rewrite(ctx(), {}) is None
    assert f.rewrite(ctx(), {"messages": "x"}) is None
    assert (
        f.rewrite(ctx(), {"messages": [None, 3, {"content": 4}, {"role": "user", "content": [1, "x", None]}]}) is None
    )
    assert f.rewrite(ctx(), body([{"role": "user", "content": [{"type": "tool_result", "content": None}]}])) is None


def test_does_not_mutate_the_input_and_is_deterministic():
    # Given a body / When rewritten on two successive turns with the same history / Then the capped part is identical
    b = body(turn("Bash", BIG))
    before = copy.deepcopy(b)
    f = feature()
    first = f.rewrite(ctx(), b)
    assert b == before
    later = body([*b["messages"], {"role": "user", "content": "next"}])
    second = f.rewrite(ctx(), later)
    assert first is not None and second is not None
    assert second.body["messages"][:2] == first.body["messages"]


def test_defaults_and_bad_config_fall_back():
    # Given nonsense values / Then the 25000 x 4 default applies: 100k chars pass, 100001 are capped
    f = create(
        FeatureEnv(
            state_dir=Path("."),
            config={
                "limit_tokens": "x",
                "chars_per_token": -1,
                "head_share": 7,
                "protect_tools": "Bash",
                "protect_patterns": [1],
            },
        )
    )
    assert f.rewrite(ctx(), body(turn("Bash", "a" * 100_000))) is None
    out = f.rewrite(ctx(), body(turn("Bash", "a" * 100_001)))
    assert out is not None and "1 characters removed" in result_content(out.body)
    assert result_content(out.body).startswith("a" * 70_000 + "\n[")


def test_invalid_regex_is_dropped():
    f = feature({**SMALL, "protect_patterns": ["(", "KEEP"]})
    assert f.rewrite(ctx(), body(turn("Bash", BIG + "KEEP"))) is None
    assert f.rewrite(ctx(), body(turn("Bash", BIG))) is not None


def test_before_and_after_do_nothing():
    f = feature()
    assert f.before(ctx()) is None
    assert f.after(ctx(), None, 200) is None


def test_entry_point_resolves_to_the_factory():
    eps = {e.name: e for e in entry_points(group="token_economics.features")}
    assert eps["output_cap"].load() is create
    assert create(FeatureEnv(state_dir=Path("."))).name == "output_cap"
