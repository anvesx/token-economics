import copy
from datetime import UTC, datetime
from importlib.metadata import entry_points
from pathlib import Path

from token_economics_contracts.types import FeatureEnv, KeyInfo, RequestContext
from token_economics_feat_observation_masking import ObservationMasking, create

PAYLOAD = "x" * 200
MASKED = "[token-economics: tool result masked, 200 characters]"


def ctx(provider: str = "anthropic") -> RequestContext:
    return RequestContext(
        request_id="r", ts=datetime(2026, 1, 1, tzinfo=UTC), key=KeyInfo(tenant="t"), provider=provider
    )


def feature(config: dict | None = None) -> ObservationMasking:
    return create(FeatureEnv(state_dir=Path("."), config=config or {}))


def conversation(n: int, tool: str = "Bash", **result_extra) -> list[dict]:
    msgs: list[dict] = [{"role": "user", "content": "do the thing"}]
    for i in range(n):
        msgs.append({"role": "assistant", "content": [{"type": "tool_use", "id": f"t{i}", "name": tool, "input": {}}]})
        msgs.append(
            {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": f"t{i}", "content": PAYLOAD, **result_extra}],
            }
        )
    return msgs


def body(messages: list[dict]) -> dict:
    return {"model": "m", "max_tokens": 10, "messages": messages}


def results(b: dict) -> list[dict]:
    return [
        blk
        for m in b["messages"]
        if isinstance(m["content"], list)
        for blk in m["content"]
        if blk["type"] == "tool_result"
    ]


def masked_flags(b: dict) -> list[bool]:
    return [r["content"] != PAYLOAD for r in results(b)]


def test_no_change_at_or_below_min_events():
    # Given 10 tool results (the default trigger) / Then nothing is masked
    assert feature().rewrite(ctx(), body(conversation(10))) is None
    assert feature().rewrite(ctx(), body(conversation(3))) is None


def test_masks_old_results_in_steps_above_the_trigger():
    # Given 15 events: boundary = ((15-5)//10)*10 = 10 / Then the first 10 are masked and the last 5 are kept
    out = feature().rewrite(ctx(), body(conversation(15)))
    assert out is not None
    assert masked_flags(out.body) == [True] * 10 + [False] * 5
    assert results(out.body)[0] == {"type": "tool_result", "tool_use_id": "t0", "content": MASKED}
    assert out.changes == ("masked 10 of 15 tool results, 2000 chars",)


def test_no_mask_when_boundary_is_zero():
    # Given 14 events: (14-5)//10 = 0
    assert feature().rewrite(ctx(), body(conversation(14))) is None


def test_prefix_is_byte_identical_while_the_boundary_has_not_moved():
    # Given the same history on turn k (15 events) and turn k+1 (16 events), both with boundary 10
    f = feature()
    k = f.rewrite(ctx(), body(conversation(15)))
    k1 = f.rewrite(ctx(), body(conversation(16)))
    assert k is not None and k1 is not None
    # Then every message of turn k is unchanged in turn k+1, up to the new turn
    assert k1.body["messages"][: len(k.body["messages"])] == k.body["messages"]
    # And the boundary only moves at 25 events
    assert masked_flags(f.rewrite(ctx(), body(conversation(24))).body).count(True) == 10  # type: ignore[union-attr]
    assert masked_flags(f.rewrite(ctx(), body(conversation(25))).body).count(True) == 20  # type: ignore[union-attr]


def test_masked_results_stay_masked_on_every_later_turn():
    # Given masking at 25 events / When the history grows by one / Then earlier masked results are identical
    f = feature()
    a = f.rewrite(ctx(), body(conversation(25)))
    b = f.rewrite(ctx(), body(conversation(26)))
    assert a is not None and b is not None
    assert b.body["messages"][: len(a.body["messages"])] == a.body["messages"]


def test_protected_tools_and_errors_are_never_masked():
    assert feature().rewrite(ctx(), body(conversation(15, tool="Read"))) is None
    assert feature().rewrite(ctx(), body(conversation(15, is_error=True))) is None


def test_protect_tools_config_replaces_the_default_list():
    assert feature({"protect_tools": ["Bash"]}).rewrite(ctx(), body(conversation(15))) is None
    assert feature({"protect_tools": ["Bash"]}).rewrite(ctx(), body(conversation(15, tool="Read"))) is not None


def test_tool_result_with_list_content_is_masked_and_keeps_its_ids():
    msgs = conversation(15)
    msgs[2]["content"][0]["content"] = [{"type": "text", "text": PAYLOAD}]
    out = feature().rewrite(ctx(), body(msgs))
    assert out is not None
    assert results(out.body)[0] == {"type": "tool_result", "tool_use_id": "t0", "content": MASKED}


def test_results_shorter_than_the_marker_are_left_alone():
    msgs = conversation(15)
    for m in msgs:
        if m["role"] == "user" and isinstance(m["content"], list):
            m["content"][0]["content"] = "ok"
    assert feature().rewrite(ctx(), body(msgs)) is None


def test_custom_min_keep_and_step():
    # Given min 2, keep 1, step 2 / When 5 events: boundary = ((5-1)//2)*2 = 4
    out = feature({"min_events": 2, "keep": 1, "step": 2}).rewrite(ctx(), body(conversation(5)))
    assert out is not None and masked_flags(out.body) == [True] * 4 + [False]


def test_bad_config_falls_back_to_defaults():
    f = feature({"min_events": -1, "keep": "x", "step": 0, "protect_tools": 5})
    assert (f.min_events, f.keep, f.step) == (10, 5, 10)


def test_non_anthropic_is_left_alone():
    assert feature().rewrite(ctx("openai"), body(conversation(30))) is None


def test_odd_bodies_return_none():
    f = feature({"min_events": 0})
    assert f.rewrite(ctx(), {}) is None
    assert f.rewrite(ctx(), {"messages": "x"}) is None
    assert (
        f.rewrite(ctx(), {"messages": [None, 3, {"content": 4}, {"role": "user", "content": [1, "x", None]}]}) is None
    )


def test_does_not_mutate_the_input_and_is_deterministic():
    b = body(conversation(15))
    before = copy.deepcopy(b)
    f = feature()
    x, y = f.rewrite(ctx(), b), f.rewrite(ctx(), b)
    assert b == before
    assert x is not None and y is not None and x.body == y.body


def test_before_and_after_do_nothing():
    f = feature()
    assert f.before(ctx()) is None
    assert f.after(ctx(), None, 200) is None


def test_entry_point_resolves_to_the_factory():
    eps = {e.name: e for e in entry_points(group="token_economics.features")}
    assert eps["observation_masking"].load() is create
    assert create(FeatureEnv(state_dir=Path("."))).name == "observation_masking"
