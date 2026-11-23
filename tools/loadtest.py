"""Load test: how much latency does the gateway add, and does it lose or double any ledger row?

    uv run python tools/loadtest.py [--requests 2000] [--concurrency 50] [--stream] [--policy policy.json]
                                    [--out report.json] [--budget-ms P95]

Starts a fake provider (fixed delay, optional streamed chunks) and the real gateway on free local ports with a
scratch state dir. The same load goes straight to the provider, then through the gateway. Added latency is
gateway minus direct at p50, p95 and p99, for time to first byte (TTFB) and for the total. After the run the ledger
must hold exactly one row per successful gateway request. Exits 1 when that fails or when added p95 TTFB is over
`--budget-ms`.

Everything shares one process and one core pool, so the load generator competes with the gateway: numbers are an
upper bound on added latency, not a production figure.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import socket
import sqlite3
import statistics
import sys
import tempfile
import threading
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

KEY = "vk-load-1"
MODEL = "claude-opus-5-5"
USAGE = {
    "input_tokens": 12,
    "cache_creation_input_tokens": 300,
    "cache_read_input_tokens": 5000,
    "cache_creation": {"ephemeral_5m_input_tokens": 100, "ephemeral_1h_input_tokens": 200},
    "output_tokens": 1,
    "service_tier": "standard",
    "inference_geo": "global",
    "speed": "standard",
}


def _sse(event: str, data: dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n".encode()


def stream_events(message_id: str, deltas: int) -> list[bytes]:
    start = {"id": message_id, "type": "message", "role": "assistant", "model": MODEL, "content": [], "usage": USAGE}
    delta = {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "x"}}
    return [
        _sse("message_start", {"type": "message_start", "message": start}),
        *[_sse("content_block_delta", delta) for _ in range(deltas)],
        _sse(
            "message_delta",
            {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 42}},
        ),
        _sse("message_stop", {"type": "message_stop"}),
    ]


def provider_app(delay_s: float, chunks: int, chunk_delay_s: float) -> Starlette:
    """A fake Anthropic: waits `delay_s`, then answers (JSON, or `chunks` SSE deltas `chunk_delay_s` apart)."""

    async def messages(request: Request) -> Response:
        spec = json.loads(await request.body())
        message_id = spec["message_id"]
        if delay_s:
            await asyncio.sleep(delay_s)
        if not spec.get("stream"):
            body = {
                "id": message_id,
                "type": "message",
                "role": "assistant",
                "model": MODEL,
                "content": [{"type": "text", "text": "ok"}],
                "usage": {**USAGE, "output_tokens": 42},
            }
            return JSONResponse(body)

        async def events() -> Any:
            for event in stream_events(message_id, chunks):
                yield event
                if chunk_delay_s:
                    await asyncio.sleep(chunk_delay_s)

        return StreamingResponse(events(), media_type="text/event-stream")

    return Starlette(routes=[Route("/v1/messages", messages, methods=["POST"])])


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class Served:
    """An ASGI app on a real local port, in a background thread."""

    def __init__(self, app: Any) -> None:
        self.port = _free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        self._server = uvicorn.Server(
            uvicorn.Config(
                app, host="127.0.0.1", port=self.port, log_level="error", server_header=False, date_header=False
            )
        )
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    def __enter__(self) -> Served:
        self._thread.start()
        deadline = time.time() + 15
        while not self._server.started and time.time() < deadline:
            time.sleep(0.01)
        if not self._server.started:
            raise RuntimeError("server did not start")
        return self

    def __exit__(self, *_: object) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=10)


def percentile(values: Sequence[float], q: float) -> float:
    """Nearest-rank percentile, `q` in 0..100. 0.0 for no values."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, -(-len(ordered) * q // 100))  # ceil
    return ordered[int(rank) - 1]


def summarise(ttfb: Sequence[float], total: Sequence[float]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for name, values in (("ttfb_ms", ttfb), ("total_ms", total)):
        out[name] = {
            "p50": percentile(values, 50),
            "p95": percentile(values, 95),
            "p99": percentile(values, 99),
            "mean": statistics.fmean(values) if values else 0.0,
        }
    return out


async def _send(client: httpx.AsyncClient, base: str, stream: bool, message_id: str) -> tuple[float, float, bool]:
    """One request. Returns (ttfb_ms, total_ms, ok). TTFB is the first body chunk."""
    payload = json.dumps(
        {
            "model": MODEL,
            "stream": stream,
            "message_id": message_id,
            "messages": [{"role": "user", "content": "load test"}],
        }
    ).encode()
    headers = {
        "x-api-key": "sk-ant-load-test",
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "x-token-economics-key": KEY,
        "x-claude-code-session-id": "load-session",
    }
    start = time.perf_counter()
    first: float | None = None
    try:
        async with client.stream("POST", f"{base}/v1/messages", content=payload, headers=headers) as resp:
            async for _ in resp.aiter_raw():
                if first is None:
                    first = time.perf_counter()
            ok = resp.status_code == 200
    except httpx.HTTPError:
        return 0.0, 0.0, False
    end = time.perf_counter()
    return ((first or end) - start) * 1000, (end - start) * 1000, ok


async def drive(base: str, requests: int, concurrency: int, stream: bool, prefix: str) -> dict[str, Any]:
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    sem = asyncio.Semaphore(concurrency)
    results: list[tuple[float, float, bool]] = []

    async with httpx.AsyncClient(timeout=60, limits=limits) as client:

        async def one(i: int) -> None:
            async with sem:
                results.append(await _send(client, base, stream, f"msg_{prefix}_{i}"))

        t0 = time.perf_counter()
        await asyncio.gather(*(one(i) for i in range(requests)))
        wall = time.perf_counter() - t0
    good = [r for r in results if r[2]]
    return {
        "requests": requests,
        "ok": len(good),
        "errors": requests - len(good),
        "throughput_rps": len(good) / wall if wall else 0.0,
        "wall_s": wall,
        **summarise([r[0] for r in good], [r[1] for r in good]),
    }


def ledger_counts(db: Path) -> tuple[int, int]:
    """(rows, distinct response ids) in the ledger."""
    con = sqlite3.connect(db)
    try:
        return con.execute("SELECT COUNT(*), COUNT(DISTINCT provider || response_id) FROM ledger").fetchone()  # type: ignore[no-any-return]
    finally:
        con.close()


def run_load(
    requests: int = 2000,
    concurrency: int = 50,
    stream: bool = False,
    policy: Path | None = None,
    delay_ms: float = 20.0,
    chunks: int = 5,
    chunk_delay_ms: float = 2.0,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Run the whole comparison and return the report."""
    from token_economics_app_gateway import Settings, create_app
    from token_economics_feat_upstream.providers.anthropic import AnthropicUpstream

    with tempfile.TemporaryDirectory(prefix="te-loadtest-") as tmp:
        state = state_dir or Path(tmp)
        state.mkdir(parents=True, exist_ok=True)
        (state / "keys.json").write_text(json.dumps({KEY: {"tenant": "load", "team": "t", "caller": "loadtest"}}))
        if policy is not None:
            (state / "policy.json").write_text(policy.read_text())
        settings = Settings(state_dir=state)
        with Served(provider_app(delay_ms / 1000, chunks, chunk_delay_ms / 1000)) as provider:
            app = create_app(settings, upstreams={"anthropic": AnthropicUpstream(base_url=provider.url)})
            with Served(app) as gateway:

                async def go() -> tuple[dict[str, Any], dict[str, Any]]:
                    warm = min(100, requests)
                    await drive(provider.url, warm, concurrency, stream, "warm_d")
                    await drive(gateway.url, warm, concurrency, stream, "warm_g")
                    direct = await drive(provider.url, requests, concurrency, stream, "d")
                    via = await drive(gateway.url, requests, concurrency, stream, "g")
                    return direct, via

                warm_rows = min(100, requests)
                direct, via = asyncio.run(go())
                expected = via["ok"] + warm_rows  # the warm-up through the gateway writes rows too
                deadline = time.time() + 60
                rows, distinct = ledger_counts(settings.ledger_path)
                while rows < expected and time.time() < deadline:
                    time.sleep(0.2)
                    rows, distinct = ledger_counts(settings.ledger_path)
        added = {m: {p: via[m][p] - direct[m][p] for p in ("p50", "p95", "p99")} for m in ("ttfb_ms", "total_ms")}
        return {
            "config": {
                "requests": requests,
                "concurrency": concurrency,
                "stream": stream,
                "policy": str(policy) if policy else None,
                "provider_delay_ms": delay_ms,
                "stream_chunks": chunks if stream else 0,
                "chunk_delay_ms": chunk_delay_ms if stream else 0,
            },
            "direct": direct,
            "gateway": via,
            "added": added,
            "ledger": {
                "expected_rows": expected,
                "rows": rows,
                "distinct_response_ids": distinct,
                "consistent": rows == expected and distinct == rows,
            },
        }


def verdict(report: dict[str, Any], budget_ms: float | None) -> list[str]:
    """Problems that should fail the run. Empty means pass."""
    problems = []
    if report["gateway"]["errors"]:
        problems.append(f"{report['gateway']['errors']} gateway requests failed")
    led = report["ledger"]
    if not led["consistent"]:
        problems.append(
            f"ledger rows {led['rows']} (distinct {led['distinct_response_ids']}) != expected {led['expected_rows']}"
        )
    p95 = report["added"]["ttfb_ms"]["p95"]
    if budget_ms is not None and p95 > budget_ms:
        problems.append(f"added p95 TTFB {p95:.1f} ms is over the budget of {budget_ms:.1f} ms")
    return problems


def render(report: dict[str, Any]) -> str:
    c, a = report["config"], report["added"]
    lines = [
        f"requests={c['requests']} concurrency={c['concurrency']} stream={c['stream']} "
        f"provider_delay={c['provider_delay_ms']}ms",
        "",
        "| ms | direct p50 | direct p95 | direct p99 | gateway p50 | gateway p95 | gateway p99 "
        "| added p50 | added p95 | added p99 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for m in ("ttfb_ms", "total_ms"):
        d, g = report["direct"][m], report["gateway"][m]
        lines.append(
            f"| {m[:-3]} | "
            + " | ".join(f"{x:.1f}" for x in (d["p50"], d["p95"], d["p99"], g["p50"], g["p95"], g["p99"]))
            + " | "
            + " | ".join(f"{a[m][p]:.1f}" for p in ("p50", "p95", "p99"))
            + " |"
        )
    led = report["ledger"]
    lines += [
        "",
        f"throughput: direct {report['direct']['throughput_rps']:.0f} rps, "
        f"gateway {report['gateway']['throughput_rps']:.0f} rps",
        f"errors: direct {report['direct']['errors']}, gateway {report['gateway']['errors']}",
        f"ledger rows {led['rows']} (distinct {led['distinct_response_ids']}), expected {led['expected_rows']}: "
        f"{'ok' if led['consistent'] else 'MISMATCH'}",
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0] if __doc__ else None)
    p.add_argument("--requests", type=int, default=2000)
    p.add_argument("--concurrency", type=int, default=50)
    p.add_argument("--stream", action="store_true", help="use streamed (SSE) responses")
    p.add_argument("--policy", type=Path, help="a policy.json to run the gateway with")
    p.add_argument("--out", type=Path, help="write the report as JSON")
    p.add_argument("--budget-ms", type=float, help="exit 1 when added p95 TTFB is over this")
    p.add_argument("--delay-ms", type=float, default=20.0, help="fixed provider delay before the first byte")
    p.add_argument("--chunks", type=int, default=5, help="streamed deltas per response")
    p.add_argument("--chunk-delay-ms", type=float, default=2.0)
    a = p.parse_args(argv)
    report = run_load(a.requests, a.concurrency, a.stream, a.policy, a.delay_ms, a.chunks, a.chunk_delay_ms)
    print(render(report))
    if a.out:
        a.out.write_text(json.dumps(report, indent=2))
    problems = verdict(report, a.budget_ms)
    for line in problems:
        print(f"FAIL: {line}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
