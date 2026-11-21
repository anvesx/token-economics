import pytest
from token_economics_feat_upstream.providers.anthropic import SECRET_HEADERS, AnthropicUpstream
from token_economics_feat_upstream.providers.openai import OpenAIUpstream


def test_default_base_urls():
    # Given no env and no argument / When constructed / Then the public API hosts are used
    assert AnthropicUpstream().base_url == "https://api.anthropic.com"
    assert OpenAIUpstream().base_url == "https://api.openai.com"


def test_env_overrides_default_and_argument_overrides_env(monkeypatch):
    # Given an env override / When constructed with and without an argument / Then argument wins, env beats default
    monkeypatch.setenv("TOKEN_ECONOMICS_UPSTREAM_ANTHROPIC", "http://env.local/")
    monkeypatch.setenv("TOKEN_ECONOMICS_UPSTREAM_OPENAI", "http://env-openai.local")
    assert AnthropicUpstream().base_url == "http://env.local"
    assert AnthropicUpstream("http://arg.local").base_url == "http://arg.local"
    assert OpenAIUpstream().base_url == "http://env-openai.local"


def test_env_is_read_at_construction(monkeypatch):
    # Given an object built before the env was set / When env changes later / Then it keeps its value
    up = AnthropicUpstream()
    monkeypatch.setenv("TOKEN_ECONOMICS_UPSTREAM_ANTHROPIC", "http://late.local")
    assert up.base_url == "https://api.anthropic.com"


@pytest.mark.parametrize(
    ("path", "query", "expected"),
    [
        ("/v1/messages", "", "https://api.anthropic.com/v1/messages"),
        ("v1/messages", "beta=true", "https://api.anthropic.com/v1/messages?beta=true"),
    ],
)
def test_url_joins_path_and_query(path, query, expected):
    # Given a path and query / When building the URL / Then base, path and query are joined once
    assert AnthropicUpstream().url(path, query) == expected


def test_forward_headers_keeps_everything_but_hop_by_hop_and_virtual_key():
    # Given a request with auth, betas and hop-by-hop headers
    headers = {
        "Host": "gateway",
        "Content-Length": "12",
        "Connection": "keep-alive",
        "Keep-Alive": "5",
        "Transfer-Encoding": "chunked",
        "TE": "trailers",
        "Upgrade": "h2c",
        "Proxy-Authorization": "x",
        "Proxy-Connection": "keep-alive",
        "X-Token-Economics-Key": "vk-1",
        "Authorization": "Bearer sk-ant-oat01-abc",
        "x-api-key": "k",
        "anthropic-beta": "oauth-2025-04-20,prompt-caching",
        "Anthropic-Version": "2023-06-01",
        "Accept-Encoding": "gzip",
    }
    # When forwarded
    out = AnthropicUpstream().forward_headers(headers)
    # Then only the safe ones remain, names and values untouched
    assert out == {
        "Authorization": "Bearer sk-ant-oat01-abc",
        "x-api-key": "k",
        "anthropic-beta": "oauth-2025-04-20,prompt-caching",
        "Anthropic-Version": "2023-06-01",
        "Accept-Encoding": "gzip",
    }


def test_forward_headers_keeps_two_anthropic_beta_values():
    # Given two separate anthropic-beta entries (a combined value as one header)
    out = OpenAIUpstream().forward_headers({"anthropic-beta": "a-1,b-2", "authorization": "Bearer t"})
    # Then the value is intact
    assert out["anthropic-beta"] == "a-1,b-2"
    assert out["authorization"] == "Bearer t"


def test_secret_headers_are_lowercase_names():
    # Given the secret list / Then it covers credentials and the virtual key
    assert {"authorization", "x-api-key", "x-token-economics-key", "cookie", "proxy-authorization"} == SECRET_HEADERS
