"""The request path: a pass-through proxy in observe mode.

Requests go upstream unchanged unless an enforced policy feature rewrites them (P2), and responses come back byte for
byte. A copy of each response is handed to the observer
after the last byte has been sent, so the client is never delayed and nothing is blocked (P0: measure only).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import uuid
from collections.abc import AsyncIterator, Mapping
from datetime import UTC, datetime
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
    Decision,
    HealthTracker,
    Identity,
    KeyResolver,
    PolicyEngine,
    RequestContext,
    RequestFacts,
    ResolvedKey,
    RewrittenRequest,
    ShadowSampler,
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


ERROR_TYPES = {401: "authentication_error", 402: "billing_error", 403: "permission_error", 429: "rate_limit_error"}


def optional(name: str, *args: Any) -> Any:
    """A registered service, or None when its package is not installed (P0 runs without the P1 packages)."""
    try:
        return load(SERVICES, name)(*args)
    except LookupError:
        return None


def optional_quiet(name: str, *args: Any) -> Any:
    """Like `optional`, but any failure to build the service means it is absent (shadow runs are never required)."""
    try:
        return load(SERVICES, name)(*args)
    except Exception:
        return None


def build_shadow_observer(settings: Settings, primary: Observer) -> Observer:
    """Write isolation for shadow runs: its own ledger, dedupe and rejects under `<state>/shadow/`."""
    folder = settings.state_dir / "shadow"
    folder.mkdir(parents=True, exist_ok=True)
    return Observer(
        ledger=load(SERVICES, "ledger")(str(folder / "ledger.sqlite")),
        pricebook=primary.pricebook,
        calculator=primary.calculator,
        deduper=load(SERVICES, "dedupe")(),
        normalisers=primary.normalisers,
        rejects_path=folder / "rejects.jsonl",
    )


class LegacyKeys:
    """P0 key file: used only when the tenancy service is not installed."""

    def __init__(self, settings: Settings) -> None:
        self._keys = load_keys(settings.keys_path)

    def resolve(self, presented: str) -> ResolvedKey:
        if not presented:
            return ResolvedKey(info=UNKNOWN, status="none")
        info = self._keys.get(presented)
        return ResolvedKey(info=info, status="active") if info else ResolvedKey(info=UNKNOWN, status="unknown")


def refusal(provider: str, decision: Decision) -> Response:
    """A blocked request, in the error shape the harness's provider uses, so the harness shows the message."""
    kind = ERROR_TYPES.get(decision.status, "api_error")
    if provider == "openai":
        payload: dict[str, Any] = {"error": {"message": decision.message, "type": kind, "code": decision.code}}
    else:
        payload = {"type": "error", "error": {"type": kind, "message": decision.message}}
    headers = {"x-token-economics-blocked": decision.code or "blocked", "x-should-retry": "false"}
    return Response(json.dumps(payload), status_code=decision.status, media_type="application/json", headers=headers)


def create_app(
    settings: Settings | None = None,
    *,
    observer: Observer | None = None,
    adapters: Mapping[str, Adapter] | None = None,
    upstreams: Mapping[str, Upstream] | None = None,
    client: httpx.AsyncClient | None = None,
    policy: PolicyEngine | None = None,
    keys: KeyResolver | None = None,
    health: HealthTracker | None = None,
    shadow: ShadowSampler | None = None,
    shadow_policy: PolicyEngine | None = None,
    shadow_observer: Observer | None = None,
) -> Starlette:
    settings = settings or Settings()
    observer = observer or build_observer(settings)
    state = str(settings.state_dir)
    engine: PolicyEngine | None = policy or optional("policy", state, observer.pricebook, observer.calculator)
    resolver: KeyResolver = keys or optional("keys", state) or LegacyKeys(settings)
    tracker: HealthTracker | None = health or optional("health")
    audit = optional("audit", state)
    # Shadow runs (P2): off unless the rollout service is installed and its config enables sampling.
    sampler: ShadowSampler | None = shadow or optional_quiet("shadow", state)
    shadow_engine: PolicyEngine | None = None
    shadow_obs: Observer | None = None
    if sampler is not None:
        shadow_dir = str(settings.state_dir / "shadow")
        shadow_engine = shadow_policy or optional_quiet("policy", shadow_dir, observer.pricebook, observer.calculator)
        try:
            shadow_obs = shadow_observer or build_shadow_observer(settings, observer)
        except Exception:
            sampler = None
    registered = dict(adapters) if adapters is not None else load_all(ADAPTERS)
    ordered = [registered[n] for n in ADAPTER_ORDER if n in registered]
    ordered += [a for n, a in registered.items() if n not in ADAPTER_ORDER]
    ups = dict(upstreams) if upstreams is not None else load_all(UPSTREAMS)
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

        # Who is asking. A revoked key is refused; a missing or unknown key is still observed as tenant "unknown".
        resolved = resolver.resolve(headers.get(KEY_HEADER, ""))
        provider = adapter.provider if adapter is not None else upstream.provider
        if resolved.status == "revoked":
            observer.stats["revoked_key"] += 1
            if audit is not None:
                with contextlib.suppress(Exception):
                    audit.record("revoked_key_refused", resolved.key_id, {"harness": adapter.name if adapter else ""})
            revoked = Decision(
                allow=False,
                status=401,
                code="key_revoked",
                message="Token Economics: this virtual key has been revoked.",
            )
            return refusal(provider, revoked)
        key = resolved.info
        identity = adapter.identify(headers, body) if adapter is not None else Identity()

        # Policy runs before dispatch, only for model calls an adapter understands. With no policy file it does nothing.
        ctx: RequestContext | None = None
        if engine is not None and adapter is not None:
            ctx = RequestContext(
                request_id=uuid.uuid4().hex,
                ts=datetime.now(UTC),
                key_id=resolved.key_id,
                key=key,
                harness=adapter.name,
                provider=provider,
                identity=identity,
                facts=_facts(adapter, headers, body),
            )
            decision = await asyncio.to_thread(engine.before, ctx)
            if not decision.allow:
                observer.stats["blocked"] += 1
                return refusal(provider, decision)

        mirror = False
        if ctx is not None and sampler is not None:
            try:
                mirror = bool(sampler.sample(ctx))
            except Exception:
                mirror = False

        # P2: features may rewrite an allowed request (caps, masking, routing). Never a compressed body; any failure
        # sends the original bytes, so a broken optimisation costs a saving, never a request.
        send, extra_headers = body, []
        rewrite = getattr(engine, "rewrite", None)
        if ctx is not None and rewrite is not None and "content-encoding" not in headers:
            try:
                changed = await asyncio.to_thread(rewrite, ctx, body)
            except Exception:
                changed = None
                observer.stats["rewrite_errors"] += 1
            if changed is not None:
                send, extra_headers = changed.body, list(changed.add_headers)
                observer.stats["rewritten"] += 1

        def settle(row: Any, status: int) -> None:
            if ctx is not None and engine is not None:
                engine.after(ctx, row, status)
            if mirror and ctx is not None and sampler is not None:
                with contextlib.suppress(Exception):
                    sampler.record(ctx, "primary", row, status)

        # Send every header upstream as it arrived (order, casing, repeats), minus hop-by-hop and the virtual key.
        allowed = {name.lower() for name in upstream.forward_headers(headers)}
        client_headers = [(k, v) for k, v in raw_headers if k.lower() in allowed]

        def build(content: bytes, extra: list[tuple[str, str]]) -> httpx.Request:
            out_headers = client_headers
            if content is not body:  # httpx sets the length of the new body
                out_headers = [(k, v) for k, v in client_headers if k.lower() != "content-length"] + extra
            req = http.build_request(request.method, upstream.url(path, query), headers=out_headers, content=content)
            sent = {k.lower() for k, _ in out_headers} | {"host", "content-length", "transfer-encoding"}
            for name in [n for n in req.headers if n.lower() not in sent]:
                del req.headers[name]  # httpx defaults (accept, accept-encoding, user-agent) the client did not send
            return req

        async def run_mirror() -> None:
            """Send the request again through the candidate policy; its response goes to the shadow ledger only."""
            assert ctx is not None and sampler is not None and shadow_obs is not None and adapter is not None
            row, status = None, 599
            try:
                changed: RewrittenRequest | None = None
                if shadow_engine is not None and "content-encoding" not in headers:
                    changed = await asyncio.to_thread(shadow_engine.rewrite, ctx, body)
                content = changed.body if changed is not None else bytes(body)  # a copy, so build() drops the length
                mresp = await http.send(build(content, list(changed.add_headers) if changed else []), stream=True)
                try:
                    captured = b"".join([c async for c in mresp.aiter_raw()])
                finally:
                    await mresp.aclose()
                status = mresp.status_code
                row = await asyncio.to_thread(
                    shadow_obs.record, adapter, key, identity, status, dict(mresp.headers), captured
                )
                observer.stats["shadow_sent"] += 1
            except Exception:
                observer.stats["shadow_errors"] += 1
            with contextlib.suppress(Exception):
                await asyncio.to_thread(sampler.record, ctx, "shadow", row, status)
            if shadow_engine is not None:
                with contextlib.suppress(Exception):
                    await asyncio.to_thread(shadow_engine.after, ctx, row, status)

        req = build(send, extra_headers)
        try:
            resp = await http.send(req, stream=True)
        except httpx.HTTPError as exc:
            observer.stats["upstream_errors"] += 1
            await asyncio.to_thread(settle, None, 502)
            return JSONResponse(
                {"error": f"token-economics gateway: upstream unreachable ({type(exc).__name__})"}, status_code=502
            )

        if mirror:
            mtask = asyncio.create_task(run_mirror())
            pending.add(mtask)
            mtask.add_done_callback(pending.discard)

        resp_headers = dict(resp.headers)
        if tracker is not None:
            with contextlib.suppress(Exception):
                tracker.record(provider, resp.status_code, resp_headers)

        def observe_and_settle(captured: bytes | None) -> None:
            row = None
            if captured is not None and adapter is not None:
                row = observer.record(adapter, key, identity, resp.status_code, resp_headers, captured)
            settle(row, resp.status_code)

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
                observable = adapter is not None and size <= settings.max_observed_bytes and (complete or chunks)
                if adapter is not None and not observable:
                    observer.stats["too_large"] += 1
                if observable or ctx is not None:
                    captured = b"".join(chunks) if observable else None
                    task = asyncio.create_task(asyncio.to_thread(observe_and_settle, captured))
                    pending.add(task)
                    task.add_done_callback(pending.discard)

        passthrough = [(k, v) for k, v in resp.headers.raw if k.decode("latin-1").lower() not in HOP_BY_HOP]
        out = StreamingResponse(tee(), status_code=resp.status_code)
        out.raw_headers = passthrough
        return out

    async def health_view(_: Request) -> Response:
        return JSONResponse(
            {
                "status": "ok",
                "adapters": [a.name for a in ordered],
                "upstreams": sorted(ups),
                "policy": getattr(engine, "modes", dict)() if engine is not None else {},
                "policy_problems": list(getattr(engine, "problems", [])),
                "backends": tracker.snapshot() if tracker is not None else {},
            }
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
            Route("/_te/health", health_view),
            Route("/_te/stats", stats),
            Route("/{path:path}", proxy, methods=METHODS),
        ],
        lifespan=lifespan,
    )
    app.state.observer, app.state.drain, app.state.settings = observer, drain, settings
    return app


def _facts(adapter: Adapter, headers: Mapping[str, str], body: bytes) -> RequestFacts:
    try:
        return adapter.facts(headers, body)
    except Exception:
        return RequestFacts()


def app_factory() -> Any:
    """For `uvicorn --factory token_economics_app_gateway.app:app_factory`."""
    return create_app()
