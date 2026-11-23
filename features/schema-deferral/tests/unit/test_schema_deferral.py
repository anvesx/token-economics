import copy
from datetime import UTC, datetime
from importlib.metadata import entry_points
from pathlib import Path

from token_economics_contracts.types import FeatureEnv, Identity, KeyInfo, RequestContext, RequestFacts
from token_economics_feat_schema_deferral import SchemaDeferral, create


def ctx(provider: str = "anthropic", est: int = 0, session: str = "") -> RequestContext:
    return RequestContext(
        request_id="r",
        ts=datetime(2026, 1, 1, tzinfo=UTC),
        key=KeyInfo(tenant="t"),
        provider=provider,
        identity=Identity(session_id=session),
        facts=RequestFacts(model="m", est_input_tokens=est),
    )


def feature(config: dict | None = None) -> SchemaDeferral:
    return create(FeatureEnv(state_dir=Path("."), config=config or {}))


def tool(name: str, **extra) -> dict:
    return {"name": name, "description": "d", "input_schema": {"type": "object"}, **extra}


def body(n: int, core: bool = True) -> dict:
    tools = ([tool("Bash"), tool("Read")] if core else []) + [tool(f"mcp__x__t{i}") for i in range(n)]
    return {"model": "m", "tools": tools, "messages": []}


def test_defers_non_core_tools_above_the_count_and_adds_search_tool():
    # Given 22 tools (2 core) / When rewritten / Then 20 are deferred, core kept, search tool appended
    b = body(20)
    r = feature({"min_tools": 21}).rewrite(ctx(), b)
    assert r is not None
    tools = r.body["tools"]
    assert [t.get("defer_loading") for t in tools[:2]] == [None, None]
    assert all(t["defer_loading"] is True for t in tools[2:22])
    assert tools[-1] == {"type": "tool_search_tool_regex_20251119", "name": "tool_search_tool_regex"}
    assert len(tools) == 23
    assert r.changes == ("deferred 20 of 22 tools",)
    assert r.add_headers == (("anthropic-beta", "advanced-tool-use-2025-11-20"),)


def test_few_tools_and_small_share_do_nothing():
    # Given 5 tools and a large context / Then no rewrite
    assert feature().rewrite(ctx(est=1_000_000), body(3)) is None


def test_fires_on_schema_share_of_context():
    # Given few tools but schemas are over 10 percent of the estimated context
    b = body(3)
    assert feature().rewrite(ctx(est=100), b) is not None


def test_unknown_context_size_does_not_trigger_the_share_rule():
    assert feature().rewrite(ctx(est=0), body(3)) is None


def test_does_not_mutate_the_input_body():
    b = body(25)
    before = copy.deepcopy(b)
    feature().rewrite(ctx(), b)
    assert b == before


def test_same_tool_list_gives_same_output():
    b = body(25)
    assert feature().rewrite(ctx(), b) == feature().rewrite(ctx(), b)


def test_non_anthropic_and_odd_bodies_are_left_alone():
    f = feature()
    assert f.rewrite(ctx(provider="openai"), body(25)) is None
    assert f.rewrite(ctx(), {"messages": []}) is None
    assert f.rewrite(ctx(), {"tools": "x"}) is None
    assert f.rewrite(ctx(), {"tools": ["x"]}) is None
    assert f.rewrite(ctx(), {"tools": []}) is None


def test_harness_managed_tool_search_is_respected():
    # Given a tool already deferred, or a search tool present / Then nothing changes
    b = body(25)
    b["tools"][5] = tool("a", defer_loading=True)
    assert feature().rewrite(ctx(), b) is None
    c = body(25)
    c["tools"].append({"type": "tool_search_tool_bm25_20251119", "name": "s"})
    assert feature().rewrite(ctx(), c) is None


def test_server_tools_are_never_deferred():
    b = body(25)
    b["tools"].append({"type": "web_search_20250305", "name": "web_search"})
    r = feature().rewrite(ctx(), b)
    assert r is not None
    assert "defer_loading" not in r.body["tools"][-2]


def test_nothing_deferred_when_every_tool_is_kept():
    b = {"tools": [tool(f"T{i}") for i in range(25)]}
    assert feature({"keep": [f"T{i}" for i in range(25)]}).rewrite(ctx(), b) is None


def test_no_rewrite_when_deferral_would_leave_no_loaded_tool():
    # Given only non-kept tools / Then all would be deferred, so nothing is done
    assert feature().rewrite(ctx(), body(25, core=False)) is None


def test_config_overrides_and_bad_values_fall_back():
    f = feature(
        {
            "min_tools": "x",
            "min_share": 5,
            "keep": ["mcp__x__t0"],
            "search_tool": {"type": "s", "name": "n"},
            "beta": "b",
        }
    )
    r = f.rewrite(ctx(), body(25))
    assert r is not None
    assert r.body["tools"][-1] == {"type": "s", "name": "n"}
    assert r.add_headers == (("anthropic-beta", "b"),)
    assert r.body["tools"][2].get("defer_loading") is None  # mcp__x__t0 kept
    assert r.body["tools"][0]["defer_loading"] is True  # Bash no longer kept


def test_before_and_after_do_nothing():
    f = feature()
    assert f.before(ctx()) is None
    assert f.after(ctx(), None, 200) is None


def test_entry_point_resolves_to_the_factory():
    eps = {e.name: e for e in entry_points(group="token_economics.features")}
    assert eps["schema_deferral"].load() is create


def test_a_session_that_deferred_keeps_deferring_as_its_context_grows():
    # Given a session whose schemas were over 10 percent of its small early context
    f, b = feature(), body(3)
    first = f.rewrite(ctx(est=100, session="s1"), b)
    # When the same session has grown so the share rule alone would no longer fire
    later = f.rewrite(ctx(est=1_000_000, session="s1"), b)
    # Then it still defers the same way (a changed tool list would lose the cached prefix), but other sessions do not
    assert first is not None and later is not None and later.body == first.body
    assert f.rewrite(ctx(est=1_000_000, session="s2"), b) is None
