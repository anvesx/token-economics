"""End-to-end replay through apps/gateway (P0 gate `replay`, and the evidence lines of PHASES.md "P0 done")."""

from __future__ import annotations

import json
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import pytest
from token_economics_app_gateway import Settings, create_app
from token_economics_contracts import CostSource
from token_economics_feat_upstream.providers.anthropic import AnthropicUpstream
from token_economics_redaction import scan_for_content
from token_economics_svc_ledger import SqliteLedger

PROMPT = "prompt-text-that-must-never-be-stored"
REPLY = "reply-text-that-must-never-be-stored"
HEADERS = [
    ("user-agent", "claude-cli/2.1.330 (external, cli)"),
    ("x-api-key", "sk-ant-api-secret-value"),
    ("anthropic-version", "2023-06-01"),
    ("anthropic-beta", "beta-one"),
    ("anthropic-beta", "beta-two"),
    ("content-type", "application/json"),
    ("x-claude-code-session-id", "sess-123"),
    ("x-token-economics-key", "vk-dev-1"),
]


def body(scenario: str = "stream", message_id: str = "msg_fixture_1") -> bytes:
    return json.dumps(
        {
            "model": "claude-opus-5-5",
            "stream": True,
            "scenario": scenario,
            "message_id": message_id,
            "messages": [{"role": "user", "content": PROMPT}],
        }
    ).encode()


def post(
    base: str, content: bytes, headers: list[tuple[str, str]] = HEADERS
) -> tuple[int, list[tuple[str, str]], bytes]:
    """POST and return status, response headers and the RAW body bytes (no decompression)."""
    with (
        httpx.Client(timeout=30) as client,
        client.stream("POST", f"{base}/v1/messages?beta=true", content=content, headers=headers) as resp,
    ):
        raw = b"".join(resp.iter_raw())
        return resp.status_code, [(k.lower(), v) for k, v in resp.headers.multi_items()], raw


def ledger_rows(rig: Any) -> list[Any]:
    return list(SqliteLedger(rig.settings.ledger_path).rows())


def test_replayed_trace_returns_byte_identical_responses(rig: Any) -> None:
    # Given a recorded stream served by the provider
    # When the same request goes straight to the provider and through the gateway
    direct = post(rig.upstream_url, body())
    through = post(rig.gateway_url, body())
    # Then status, headers and body bytes are the same
    assert through[0] == direct[0] == 200
    assert through[2] == direct[2]
    assert sorted(through[1]) == sorted(direct[1])


def test_request_reaches_the_provider_unchanged_except_for_the_virtual_key(rig: Any) -> None:
    # When a request passes through the gateway
    post(rig.gateway_url, body())
    seen = rig.provider.requests[-1]
    names = [k.lower() for k, _ in seen["headers"]]
    # Then the body, path and query are untouched and every header arrives, repeated ones included
    assert seen["body"] == body() and seen["path"] == "/v1/messages" and seen["query"] == "beta=true"
    assert [v for k, v in seen["headers"] if k.lower() == "anthropic-beta"] == ["beta-one", "beta-two"]
    assert dict(seen["headers"])["x-api-key"] == "sk-ant-api-secret-value"
    # And the gateway's own key is not sent upstream, and no header was added
    assert "x-token-economics-key" not in names
    sent = {k for k, _ in HEADERS} - {"x-token-economics-key"}
    assert set(names) - sent <= {"host", "content-length", "accept", "accept-encoding", "connection"}
    assert "user-agent" in names and dict(seen["headers"])["user-agent"].startswith("claude-cli")


def test_one_priced_ledger_row_per_response_with_cost_source_and_price_row_id(rig: Any) -> None:
    # Given a response with 12 fresh, 50,000 cache-read, 1,000 five-minute and 2,000 one-hour write tokens, 420 output
    post(rig.gateway_url, body())
    assert rig.wait_idle("rows").get("rows") == 1
    (row,) = ledger_rows(rig)
    # Then the five buckets are exclusive and the final output count replaced the placeholder
    b = row.buckets
    assert (b.fresh_input, b.cache_read, b.cache_write_5m, b.cache_write_1h, b.output) == (
        12,
        50_000,
        1_000,
        2_000,
        420,
    )
    # And the cost follows the seed row for claude-opus-5-5: $4 in, $20 out, read 0.05x, writes 1.25x and 2x
    expected = (
        12 * Decimal(4) + 50_000 * Decimal("0.2") + 1_000 * Decimal(5) + 2_000 * Decimal(8) + 420 * Decimal(20)
    ) / 1_000_000
    assert row.cost_estimate_usd == expected
    assert row.cost_source is CostSource.GATEWAY and row.price_row_id.startswith("anthropic:claude-opus-5-5:")
    # And it is attributed to the key's tenant and the request's session
    assert (row.tenant, row.team, row.caller, row.harness, row.session_id) == (
        "devx",
        "platform",
        "dhruv",
        "claude_code",
        "sess-123",
    )
    assert row.response_id == "msg_fixture_1" and row.request_id == "req_fixture_1" and row.auth_mode == "api_key"


def test_duplicate_stream_writes_one_ledger_row(rig: Any) -> None:
    # Given a recorded stream the provider delivered twice
    # When both copies pass through the gateway
    post(rig.gateway_url, body())
    post(rig.gateway_url, body())
    stats = rig.wait_idle("duplicates")
    # Then the ledger holds one row for that response id
    assert stats.get("rows") == 1 and stats.get("duplicates") == 1
    assert SqliteLedger(rig.settings.ledger_path).count("msg_fixture_1") == 1


def test_stream_is_teed_without_delaying_the_client(rig: Any) -> None:
    # Given a provider that pauses between chunks
    rig.provider.chunk_delay_s = 0.3
    start = time.monotonic()
    with (
        httpx.Client(timeout=30) as client,
        client.stream("POST", f"{rig.gateway_url}/v1/messages", content=body(), headers=HEADERS) as resp,
    ):
        chunks = resp.iter_raw()
        next(chunks)
        first = time.monotonic() - start
        for _ in chunks:
            pass
        total = time.monotonic() - start
    # Then the first bytes arrive long before the stream ends
    assert first < 0.3 < total


def test_no_prompt_or_response_text_is_stored(rig: Any) -> None:
    # Given requests and responses that carry recognisable text and a secret key
    post(rig.gateway_url, body())
    post(rig.gateway_url, body("unknown_key", "msg_fixture_2"))
    rig.wait_idle("unknown_usage_key")
    # When everything the gateway wrote is scanned  # Then none of it is on disk
    hits = scan_for_content([rig.settings.state_dir], [PROMPT, REPLY, "sk-ant-api-secret-value"])
    assert hits == []


def test_unknown_usage_key_is_rejected_and_the_response_is_untouched(rig: Any) -> None:
    # Given a response whose usage carries a key the normaliser does not know
    direct = post(rig.upstream_url, body("unknown_key", "msg_fixture_3"))
    through = post(rig.gateway_url, body("unknown_key", "msg_fixture_3"))
    stats = rig.wait_idle("unknown_usage_key")
    # Then the client still gets the same bytes, no ledger row is written, and the reject names the key
    assert through[2] == direct[2] and stats.get("unknown_usage_key") == 1 and not stats.get("rows")
    reject = json.loads(rig.settings.rejects_path.read_text().splitlines()[-1])
    assert reject["reason"] == "unknown_usage_key" and reject["keys"] == ["brand_new_token_field"]


def test_compressed_json_response_is_observed_and_priced_with_the_region_multiplier(rig: Any) -> None:
    # Given a gzip-compressed, non-streamed response from the US region
    direct = post(rig.upstream_url, body("gzip_json", "msg_fixture_gz"))
    through = post(rig.gateway_url, body("gzip_json", "msg_fixture_gz"))
    rig.wait_idle("rows")
    (row,) = ledger_rows(rig)
    # Then the compressed bytes pass through untouched and the row is priced at 1.1x
    assert through[2] == direct[2] and dict(through[1])["content-encoding"] == "gzip"
    assert row.model == "claude-sonnet-5-5" and row.inference_geo == "us"
    assert row.cost_estimate_usd == (1000 * Decimal(2) + 100 * Decimal(10)) * Decimal("1.1") / 1_000_000


def test_provider_error_passes_through_and_writes_no_row(rig: Any) -> None:
    direct = post(rig.upstream_url, body("overloaded"))
    through = post(rig.gateway_url, body("overloaded"))
    stats = rig.wait_idle("no_usage")
    assert through[0] == direct[0] == 529 and through[2] == direct[2] and not stats.get("rows")


def test_observation_fails_open_when_the_ledger_is_broken(rig: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given a ledger that cannot be written
    def broken(_: object) -> bool:
        raise OSError("disk full")

    monkeypatch.setattr(rig.app.state.observer.ledger, "write", broken)
    # When a request passes through
    direct = post(rig.upstream_url, body(message_id="msg_fixture_9"))
    through = post(rig.gateway_url, body(message_id="msg_fixture_9"))
    stats = rig.wait_idle("observer_errors")
    # Then the client is unaffected and the failure is counted
    assert through[0] == 200 and through[2] == direct[2] and stats.get("observer_errors") == 1


def test_unknown_virtual_key_is_observed_not_blocked(rig: Any) -> None:
    # P0 blocks nothing: a request with no known key still goes through and is attributed to "unknown"
    headers = [h for h in HEADERS if h[0] != "x-token-economics-key"]
    assert post(rig.gateway_url, body(message_id="msg_fixture_nokey"), headers)[0] == 200
    rig.wait_idle("rows")
    assert ledger_rows(rig)[0].tenant == "unknown"


def test_unreachable_provider_returns_a_gateway_error(tmp_path: Path, serve: Any, unused_url: str) -> None:
    app = create_app(Settings(state_dir=tmp_path), upstreams={"anthropic": AnthropicUpstream(base_url=unused_url)})
    with serve(app) as gw:
        status, _, raw = post(gw.url, body())
    assert status == 502 and b"upstream unreachable" in raw
