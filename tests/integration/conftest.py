"""Real sockets: a fake provider and the gateway, each on its own port, so streaming and bytes are tested for real."""

from __future__ import annotations

import asyncio
import contextlib
import gzip
import json
import socket
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.routing import Route
from token_economics_app_gateway import Settings, create_app
from token_economics_feat_upstream.providers.anthropic import AnthropicUpstream
from token_economics_feat_upstream.providers.openai import OpenAIUpstream

USAGE_START = {
    "input_tokens": 12,
    "cache_creation_input_tokens": 3000,
    "cache_read_input_tokens": 50_000,
    "cache_creation": {"ephemeral_5m_input_tokens": 1000, "ephemeral_1h_input_tokens": 2000},
    "output_tokens": 1,
    "service_tier": "standard",
    "inference_geo": "global",
    "speed": "standard",
}
FINAL_OUTPUT = 420
REPLY_TEXT = "reply-text-that-must-never-be-stored"


def sse(event: str, data: dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n".encode()


def stream_chunks(message_id: str, model: str = "claude-opus-5-5", usage: dict[str, Any] | None = None) -> list[bytes]:
    start = {
        "type": "message_start",
        "message": {
            "id": message_id,
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": [],
            "usage": usage or USAGE_START,
        },
    }
    return [
        sse("message_start", start),
        sse("ping", {"type": "ping"}),
        sse(
            "content_block_delta",
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": REPLY_TEXT}},
        ),
        sse(
            "message_delta",
            {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": FINAL_OUTPUT}},
        ),
        sse("message_stop", {"type": "message_stop"}),
    ]


@dataclass
class FakeProvider:
    """Records what it received and answers the way the request body's `scenario` asks."""

    requests: list[dict[str, Any]] = field(default_factory=list)
    chunk_delay_s: float = 0.0

    async def messages(self, request: Request) -> Response:
        body = await request.body()
        self.requests.append(
            {
                "headers": [(k.decode(), v.decode()) for k, v in request.headers.raw],
                "body": body,
                "path": request.url.path,
                "query": request.url.query,
            }
        )
        spec = json.loads(body)
        scenario, message_id = spec.get("scenario", "stream"), spec.get("message_id", "msg_fixture_1")
        if scenario == "overloaded":
            return Response(
                b'{"type":"error","error":{"type":"overloaded_error"}}', status_code=529, media_type="application/json"
            )
        if scenario == "rate_limited":
            return Response(
                b'{"type":"error","error":{"type":"rate_limit_error","message":"slow down"}}',
                status_code=429,
                media_type="application/json",
                headers={"retry-after": "30"},
            )
        if scenario == "server_error":
            return Response(b'{"type":"error","error":{"type":"api_error"}}', status_code=500)
        if scenario == "slow":
            await asyncio.sleep(3)
        if scenario == "cut":

            async def cut_iter() -> Any:
                yield stream_chunks(message_id)[0]
                await asyncio.sleep(0.05)
                raise RuntimeError("provider dropped the connection")

            return StreamingResponse(cut_iter(), media_type="text/event-stream")
        if scenario == "gzip_json":
            payload = json.dumps(
                {
                    "id": message_id,
                    "type": "message",
                    "role": "assistant",
                    "model": "claude-sonnet-5-5",
                    "content": [{"type": "text", "text": REPLY_TEXT}],
                    "usage": {
                        "input_tokens": 1000,
                        "output_tokens": 100,
                        "service_tier": "standard",
                        "inference_geo": "us",
                    },
                }
            ).encode()
            return Response(
                gzip.compress(payload),
                media_type="application/json",
                headers={"content-encoding": "gzip", "request-id": "req_fixture_gz"},
            )
        usage = {**USAGE_START, "brand_new_token_field": 9} if scenario == "unknown_key" else None

        async def body_iter() -> Any:
            for chunk in stream_chunks(message_id, usage=usage):
                yield chunk
                if self.chunk_delay_s:
                    await asyncio.sleep(self.chunk_delay_s)

        return StreamingResponse(
            body_iter(),
            media_type="text/event-stream",
            headers={"request-id": "req_fixture_1", "x-upstream-only": "kept"},
        )

    def app(self) -> Starlette:
        return Starlette(routes=[Route("/v1/messages", self.messages, methods=["POST"])])


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class Served:
    """An ASGI app on a real port, in a background thread."""

    def __init__(self, app: Any) -> None:
        self.port = free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        self._server = uvicorn.Server(
            uvicorn.Config(
                app, host="127.0.0.1", port=self.port, log_level="error", server_header=False, date_header=False
            )
        )
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    def __enter__(self) -> Served:
        self._thread.start()
        deadline = time.time() + 10
        while not self._server.started and time.time() < deadline:
            time.sleep(0.01)
        assert self._server.started, "server did not start"
        return self

    def __exit__(self, *_: object) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=10)


@dataclass
class Rig:
    provider: FakeProvider
    upstream_url: str
    gateway_url: str
    settings: Settings
    app: Any

    def wait_idle(self, expect: str = "", timeout: float = 10.0) -> dict[str, int]:
        """Wait until the gateway's observer has counted `expect` (observations run after the response is sent)."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            stats = dict(self.app.state.observer.stats)
            if not expect or stats.get(expect):
                return stats
            time.sleep(0.02)
        return dict(self.app.state.observer.stats)


@pytest.fixture
def rig_factory(tmp_path: Path) -> Iterator[Any]:
    """Build a rig with a given policy file and settings. Keys: vk-dev-1 (dhruv), vk-dev-2 (asha)."""
    stack = contextlib.ExitStack()

    def make(policy: dict[str, Any] | None = None, **settings_kw: Any) -> Rig:
        provider = FakeProvider()
        state = tmp_path / f"state{len(list(tmp_path.iterdir()))}"
        state.mkdir()
        keys = {
            "vk-dev-1": {"tenant": "devx", "team": "platform", "caller": "dhruv"},
            "vk-dev-2": {"tenant": "devx", "team": "platform", "caller": "asha"},
        }
        (state / "keys.json").write_text(json.dumps(keys))
        if policy is not None:
            (state / "policy.json").write_text(json.dumps(policy))
        settings = Settings(state_dir=state, **settings_kw)
        up = stack.enter_context(Served(provider.app()))
        app = create_app(
            settings,
            upstreams={"anthropic": AnthropicUpstream(base_url=up.url), "openai": OpenAIUpstream(base_url=up.url)},
        )
        gw = stack.enter_context(Served(app))
        return Rig(provider, up.url, gw.url, settings, app)

    with stack:
        yield make


@pytest.fixture
def rig(rig_factory: Any) -> Rig:
    return rig_factory()  # type: ignore[no-any-return]


@pytest.fixture
def serve() -> type[Served]:
    """The server helper, for tests that build their own gateway."""
    return Served


@pytest.fixture
def unused_url() -> str:
    return f"http://127.0.0.1:{free_port()}"
