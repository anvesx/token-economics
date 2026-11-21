"""The read-only admin API and the dashboard page. Optional services are found through entry points only."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route
from token_economics_contracts import SERVICES
from token_economics_contracts import load as _registry_load

Loader = Callable[[str, str], Any]

KEY_FIELDS = ("key_id", "tenant", "team", "caller", "created_at", "revoked_at")  # never the key or its hash
# The page is static and fetches only this origin. Nothing it renders is interpolated into markup.
PAGE_CSP = (
    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'"
)
_TAIL_BLOCK = 64 * 1024


class _NoStore(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response


def _int_param(request: Request, name: str, default: int, low: int, high: int) -> int:
    raw = request.query_params.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{name} must be an integer") from None
    return max(low, min(high, value))


def tail_jsonl(path: Path, limit: int) -> list[dict[str, Any]]:
    """The JSON objects among the last `limit` lines of `path`, oldest first; none if the file is missing."""
    if not path.is_file():
        return []
    with path.open("rb") as f:
        f.seek(0, 2)
        pos = f.tell()
        data = b""
        while pos > 0 and data.count(b"\n") <= limit:
            step = min(_TAIL_BLOCK, pos)
            pos -= step
            f.seek(pos)
            data = f.read(step) + data
    lines = data.split(b"\n")
    if pos > 0:
        lines = lines[1:]  # the first line may be cut off
    out: list[dict[str, Any]] = []
    for line in [x for x in lines if x.strip()][-limit:]:
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _plain(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, datetime):
        return obj.isoformat().replace("+00:00", "Z")  # same spelling as pydantic's JSON mode
    return obj


def _field(record: Any, name: str) -> Any:
    """A field of a key record: a dict, or an object with the field itself or inside a nested `info`."""
    if isinstance(record, dict):
        return record.get(name)
    if hasattr(record, name):
        return getattr(record, name)
    return getattr(getattr(record, "info", None), name, None)


def create_app(state_dir: Path, load: Loader = _registry_load) -> Starlette:
    """The app for one state directory. `load(group, name)` finds services; tests inject a fake one."""

    def service(name: str) -> Any | None:
        try:
            return load(SERVICES, name)
        except LookupError:
            return None

    def open_ledger() -> Any | None:
        path = state_dir / "ledger.sqlite"
        opener = service("ledger")
        return opener(str(path)) if opener is not None and path.is_file() else None

    def summary(request: Request) -> Response:
        try:
            days = _int_param(request, "days", 30, 1, 365)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
        build = service("dashboard_summary")
        if build is None:
            return JSONResponse({"error": "the insight service is not installed"}, status_code=503)
        ledger = open_ledger()
        now = datetime.now(UTC)
        try:
            rows = list(ledger.rows()) if ledger is not None else []
        finally:
            close = getattr(ledger, "close", None)
            if callable(close):
                close()
        data = build(rows, now=now, days=days).model_dump(mode="json")
        data["has_ledger"] = ledger is not None
        return JSONResponse(data)

    def budgets(request: Request) -> Response:
        factory = service("budget_status")
        if factory is None:
            return JSONResponse([])
        out = []
        for b in factory(str(state_dir)).status():
            item = _plain(b)
            item["used_share"] = str(b.used_share) if hasattr(b, "used_share") else None
            out.append(item)
        return JSONResponse(out)

    def tail(filename: str, default: int) -> Callable[[Request], Response]:
        def handler(request: Request) -> Response:
            try:
                limit = _int_param(request, "limit", default, 1, 1000)
            except ValueError as e:
                return JSONResponse({"error": str(e)}, status_code=400)
            return JSONResponse(tail_jsonl(state_dir / filename, limit))

        return handler

    def keys(request: Request) -> Response:
        factory = service("keys")
        # Opening the key store may create its file, so a state directory that does not exist is left alone.
        store = factory(str(state_dir)) if factory is not None and state_dir.is_dir() else None
        if store is None or not hasattr(store, "list"):
            return JSONResponse([])
        out = []
        for k in store.list():
            out.append({f: _plain(_field(k, f)) for f in KEY_FIELDS})
        return JSONResponse(out)

    def index(request: Request) -> Response:
        page = (files("token_economics_app_admin_api") / "static" / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(page, headers={"Content-Security-Policy": PAGE_CSP})

    routes = [
        Route("/", index, methods=["GET"]),
        Route("/api/summary", summary, methods=["GET"]),
        Route("/api/budgets", budgets, methods=["GET"]),
        Route("/api/decisions", tail("decisions.jsonl", 200), methods=["GET"]),
        Route("/api/alerts", tail("alerts.jsonl", 200), methods=["GET"]),
        Route("/api/rejects", tail("rejects.jsonl", 100), methods=["GET"]),
        Route("/api/keys", keys, methods=["GET"]),
    ]
    return Starlette(routes=routes, middleware=[Middleware(_NoStore)])
