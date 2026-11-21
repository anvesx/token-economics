"""The request path: a pass-through proxy in observe mode.

Requests go upstream unchanged and responses come back byte for byte. A copy of each response is handed to the observer
after the last byte has been sent, so the client is never delayed and nothing is blocked (P0: measure only).
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator, Mapping
from typing import Any

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route
from token_economics_contracts import (
    ADAPTERS,
    NORMALISERS,
    SERVICES,
    UPSTREAMS,
    Adapter,
    Identity,
    Upstream,
    load,
    load_all,
)

from .observer import Observer
from .settings import KEY_HEADER, UNKNOWN, Settings, load_keys

HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "transfer-encoding",
        "te",
        "trailer",
        "upgrade",
        "proxy-authenticate",
        "proxy-authorization",
        "proxy-connection",
    }
)
ADAPTER_ORDER = ("claude_code", "codex", "sdk")  # most specific first; "sdk" is the fallback for the Messages API
METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


def build_observer(settings: Settings) -> Observer:
    """Compose the accounting path from whatever is registered under the entry-point groups."""
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    return Observer(
        ledger=load(SERVICES, "ledger")(str(settings.ledger_path)),
        pricebook=load(SERVICES, "pricebook")(str(settings.pricebook_path)),
        calculator=load(SERVICES, "cost")(),
        deduper=load(SERVICES, "dedupe")(),
        normalisers=load_all(NORMALISERS),
        rejects_path=settings.rejects_path,
    )


def create_app(
    settings: Settings | None = None,
    *,
    observer: Observer | None = None,
    adapters: Mapping[str, Adapter] | None = None,
    upstreams: Mapping[str, Upstream] | None = None,
    client: httpx.AsyncClient | None = None,
) -> Starlette:
    settings = settings or Settings()
    observer = observer or build_observer(settings)
    registered = dict(adapters) if adapters is not None else load_all(ADAPTERS)
    ordered = [registered[n] for n in ADAPTER_ORDER if n in registered]
    ordered += [a for n, a in registered.items() if n not in ADAPTER_ORDER]
    ups = dict(upstreams) if upstreams is not None else load_all(UPSTREAMS)
    keys = load_keys(settings.keys_path)
    http = client or httpx.AsyncClient(
        timeout=httpx.Timeout(settings.upstream_timeout_s, connect=30.0), follow_redirects=False
    )
    pending: set[asyncio.Task[None]] = set()

    def pick_upstream(adapter: Adapter | None, path: str) -> Upstream | None:
        if adapter is not None and adapter.provider in ups:
            return ups[adapter.provider]
        openai_path = path.rstrip("/").endswith(("/responses", "/chat/completions")) or "/responses/" in path
        return ups.get("openai" if openai_path else "anthropic") or next(iter(ups.values()), None)

    async def proxy(request: Request) -> Response:
        path, query = request.url.path, request.url.query
        raw_headers = [(k.decode("latin-1"), v.decode("latin-1")) for k, v in request.headers.raw]
        headers = dict(request.headers)  # lower-case names; repeated headers joined
        body = await request.body()
        adapter = next((a for a in ordered if a.matches(request.method, path, headers)), None)
        upstream = pick_upstream(adapter, path)
        if upstream is None:
            return JSONResponse({"error": "token-economics gateway: no upstream registered"}, status_code=502)
        observer.stats["requests"] += 1

        # Send every header upstream as it arrived (order, casing, repeats), minus hop-by-hop and the virtual key.
        allowed = {name.lower() for name in upstream.forward_headers(headers)}
        out_headers = [(k, v) for k, v in raw_headers if k.lower() in allowed]
        req = http.build_request(request.method, upstream.url(path, query), headers=out_headers, content=body)
        sent = {k.lower() for k, _ in out_headers} | {"host", "content-length", "transfer-encoding"}
        for name in [n for n in req.headers if n.lower() not in sent]:
            del req.headers[name]  # httpx defaults (accept, accept-encoding, user-agent) the client did not send
        try:
            resp = await http.send(req, stream=True)
        except httpx.HTTPError as exc:
            observer.stats["upstream_errors"] += 1
            return JSONResponse(
                {"error": f"token-economics gateway: upstream unreachable ({type(exc).__name__})"}, status_code=502
            )

        key = keys.get(headers.get(KEY_HEADER, ""), UNKNOWN)
        identity = adapter.identify(headers, body) if adapter is not None else Identity()
        resp_headers = dict(resp.headers)
        chunks: list[bytes] = []
        size = 0

        async def tee() -> AsyncIterator[bytes]:
            nonlocal size
            complete = False
            try:
                async for chunk in resp.aiter_raw():
                    if size <= settings.max_observed_bytes:
                        chunks.append(chunk)
                    size += len(chunk)
                    yield chunk
                complete = True
            finally:
                await resp.aclose()
                if adapter is not None and size <= settings.max_observed_bytes and (complete or chunks):
                    captured = b"".join(chunks)
                    task = asyncio.create_task(
                        asyncio.to_thread(
                            observer.record, adapter, key, identity, resp.status_code, resp_headers, captured
                        )
                    )
                    pending.add(task)
                    task.add_done_callback(pending.discard)
                elif adapter is not None:
                    observer.stats["too_large"] += 1

        passthrough = [(k, v) for k, v in resp.headers.raw if k.decode("latin-1").lower() not in HOP_BY_HOP]
        out = StreamingResponse(tee(), status_code=resp.status_code)
        out.raw_headers = passthrough
        return out

    async def health(_: Request) -> Response:
        return JSONResponse(
            {"status": "ok", "mode": "observe", "adapters": [a.name for a in ordered], "upstreams": sorted(ups)}
        )

    async def stats(_: Request) -> Response:
        return JSONResponse(dict(observer.stats))

    async def drain() -> None:
        """Wait for observations still running (shutdown, and tests)."""
        while pending:
            await asyncio.gather(*list(pending), return_exceptions=True)

    @contextlib.asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        yield
        await drain()
        if client is None:
            await http.aclose()

    app = Starlette(
        routes=[
            Route("/_te/health", health),
            Route("/_te/stats", stats),
            Route("/{path:path}", proxy, methods=METHODS),
        ],
        lifespan=lifespan,
    )
    app.state.observer, app.state.drain, app.state.settings = observer, drain, settings
    return app


def app_factory() -> Any:
    """For `uvicorn --factory token_economics_app_gateway.app:app_factory`."""
    return create_app()
