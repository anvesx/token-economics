import json
from importlib.metadata import entry_points

from token_economics_contracts.registry import ADAPTERS
from token_economics_contracts.types import QuerySource
from token_economics_feat_harness_adapters.providers.claude_code import ADAPTER as CLAUDE_CODE
from token_economics_feat_harness_adapters.providers.codex import ADAPTER as CODEX
from token_economics_feat_harness_adapters.providers.sdk import ADAPTER as SDK

SID = "123e4567-e89b-12d3-a456-426614174000"


def test_entry_points_resolve_to_the_adapter_objects():
    # Given the installed entry points / When loaded / Then each is the module-level ADAPTER
    found = {ep.name: ep.load() for ep in entry_points(group=ADAPTERS)}
    assert found["claude_code"] is CLAUDE_CODE
    assert found["sdk"] is SDK
    assert found["codex"] is CODEX


def test_capabilities_follow_the_matrix():
    # Given the matrix in plan/02 / Then the flags match
    assert CLAUDE_CODE.capabilities.model_dump() == {
        "base_url": True, "oauth_passthrough": True, "hooks_blocking": True, "otel": True,
        "budget_flag": True, "headless": True, "model_rewrite": False, "transcript_path": True,
    }  # fmt: skip
    on = {k for k, v in CODEX.capabilities.model_dump().items() if v}
    assert on == {"base_url", "otel", "headless", "transcript_path"}
    assert {k for k, v in SDK.capabilities.model_dump().items() if v} == {"base_url"}


def test_route_settings():
    # Given a gateway url and key / When routed / Then each harness gets its settings
    assert CLAUDE_CODE.route("http://gw:1", "vk") == {
        "ANTHROPIC_BASE_URL": "http://gw:1",
        "ANTHROPIC_CUSTOM_HEADERS": "x-token-economics-key: vk",
    }
    assert SDK.route("http://gw:1", "vk") == {"ANTHROPIC_BASE_URL": "http://gw:1", "TOKEN_ECONOMICS_KEY": "vk"}
    assert CODEX.route("http://gw:1", "vk") == {
        "model_providers.token-economics.base_url": "http://gw:1/v1",
        "model_providers.token-economics.wire_api": "responses",
        "model_provider": "token-economics",
    }


def test_matches_claude_code_needs_cli_user_agent_but_sdk_does_not():
    # Given the same Messages request with and without a claude-cli agent
    cli = {"User-Agent": "Claude-CLI/2.0 (external)"}
    assert CLAUDE_CODE.matches("POST", "/v1/messages", cli)
    assert not CLAUDE_CODE.matches("POST", "/v1/messages", {"user-agent": "anthropic-python/1"})
    assert not CLAUDE_CODE.matches("GET", "/v1/messages", cli)
    assert SDK.matches("POST", "/v1/messages", {"user-agent": "anthropic-python/1"})
    assert not SDK.matches("POST", "/v1/models", {})


def test_matches_codex_on_responses_path():
    # Given Responses paths / Then POST to .../responses matches
    assert CODEX.matches("POST", "/v1/responses", {})
    assert CODEX.matches("POST", "/responses", {})
    assert not CODEX.matches("POST", "/v1/messages", {})
    assert not CODEX.matches("GET", "/v1/responses", {})


def test_claude_code_session_comes_from_header_first():
    # Given both a header and body metadata / When identified / Then the header wins
    body = json.dumps({"metadata": {"user_id": f"user_x_account_y_session_{SID}"}}).encode()
    ident = CLAUDE_CODE.identify({"X-Claude-Code-Session-Id": "hdr-1"}, body)
    assert ident.session_id == "hdr-1"


def test_claude_code_session_from_metadata_string_and_json_string():
    # Given the two user_id shapes / When identified / Then the session id is extracted from both
    plain = json.dumps({"metadata": {"user_id": f"user_abc_account__session_{SID}"}}).encode()
    nested = json.dumps({"metadata": {"user_id": json.dumps({"session_id": SID, "device_id": "d"})}}).encode()
    assert CLAUDE_CODE.identify({}, plain).session_id == SID
    assert CLAUDE_CODE.identify({}, nested).session_id == SID
    assert SDK.identify({}, nested).session_id == SID


def test_claude_code_auth_mode_and_query_source():
    # Given different credentials / When identified / Then auth_mode and query_source are derived
    assert CLAUDE_CODE.identify({"authorization": "Bearer sk-ant-oat01-x"}, b"").auth_mode == "oauth"
    assert CLAUDE_CODE.identify({"x-api-key": "k"}, b"").auth_mode == "api_key"
    assert CLAUDE_CODE.identify({"authorization": "Bearer other"}, b"").auth_mode == "api_key"
    assert CLAUDE_CODE.identify({}, b"").auth_mode == "unknown"
    assert CLAUDE_CODE.identify({}, b"").query_source is QuerySource.MAIN
    assert CLAUDE_CODE.identify({"x-claude-code-agent-id": "a"}, b"").query_source is QuerySource.SUBAGENT


def test_codex_session_from_headers():
    # Given Codex headers / When identified / Then session_id, else conversation_id, else empty
    assert CODEX.identify({"session_id": "s1"}, b"").session_id == "s1"
    assert CODEX.identify({"Conversation_Id": "c1"}, b"").session_id == "c1"
    assert CODEX.identify({}, b"{").session_id == ""


def test_identify_never_raises_on_odd_bodies():
    # Given odd bodies / When identified / Then empty identities
    for body in (b"", b"[]", b'{"metadata": 3}', b'{"metadata":{"user_id":5}}', b"\xff"):
        assert CLAUDE_CODE.identify({}, body).session_id == ""
        assert SDK.identify({}, body).session_id == ""


def test_cap_maps_policy_for_claude_code_only():
    # Given a policy / When capped / Then Claude Code gets flags, the others nothing
    policy = {"budget_usd": 5, "max_turns": 20}
    assert CLAUDE_CODE.cap(policy) == {"--max-budget-usd": "5", "--max-turns": "20"}
    assert CLAUDE_CODE.cap({}) == {}
    assert CODEX.cap(policy) == {}
    assert SDK.cap(policy) == {}
