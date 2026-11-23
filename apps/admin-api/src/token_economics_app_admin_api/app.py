"""The admin API and the dashboard page. Optional services are found through entry points only.

Authentication: once any admin token exists (or with `require_auth`), every `/api` route needs
`Authorization: Bearer <admin token>` and a role that is high enough: viewer reads, operator also changes kill
switches, admin also proposes and decides changes and manages admin tokens. With no tokens the app is the local
read-only dashboard and every write route is refused.
"""

from __future__ import annotations

import inspect
import json
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
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
_ROLES = ("viewer", "operator", "admin")  # lowest first
_FORBIDDEN = ("vk-", "sk-ant", "adm-")  # text that looks like a key or token is never accepted into a write


class _Refused(Exception):
    """A request body the write routes will not accept."""


class _Unavailable(Exception):
    """A service the route needs is not installed."""


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


def create_app(
    state_dir: Path,
    load: Loader = _registry_load,
    transcripts_root: Path | None = None,
    prompt_check: bool = False,
    require_auth: bool = False,
) -> Starlette:
    """The app for one state directory. `load(group, name)` finds services; tests inject a fake one.

    The session views read Claude Code transcripts (default `~/.claude/projects`). Their service object is built once,
    on first use, because an analysis is slow and the service caches it.
    """
    transcripts = transcripts_root if transcripts_root is not None else Path("~/.claude/projects").expanduser()
    views_lock = threading.Lock()
    views_box: list[Any] = []

    def service(name: str) -> Any | None:
        try:
            return load(SERVICES, name)
        except LookupError:
            return None

    def session_views() -> Any | None:
        with views_lock:
            if not views_box:
                factory = service("session_views")
                if factory is None:
                    return None
                views_box.append(factory(str(transcripts), str(state_dir / "detectors"), prompt_check))
            return views_box[0]

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

    def overview(request: Request) -> Response:
        try:
            days = _int_param(request, "days", 30, 1, 365)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
        views = session_views()
        if views is None:
            return JSONResponse({"error": "the insight service is not installed"}, status_code=503)
        return JSONResponse(views.overview(days))

    def session_detail(request: Request) -> Response:
        try:
            days = _int_param(request, "days", 30, 1, 365)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
        views = session_views()
        if views is None:
            return JSONResponse({"error": "the insight service is not installed"}, status_code=503)
        found = views.session(request.path_params["session_id"], days)
        if found is None:
            return JSONResponse({"error": "session not found in this period"}, status_code=404)
        return JSONResponse(found)

    def task_detail(request: Request) -> Response:
        try:
            days = _int_param(request, "days", 30, 1, 365)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
        raw = request.path_params["n"]
        if not raw.isascii() or not raw.isdigit() or int(raw) < 1:
            return JSONResponse({"error": "task not found in this period"}, status_code=404)
        views = session_views()
        if views is None:
            return JSONResponse({"error": "the insight service is not installed"}, status_code=503)
        found = views.task(request.path_params["session_id"], int(raw), days)
        if found is None:
            return JSONResponse({"error": "task not found in this period"}, status_code=404)
        return JSONResponse(found)

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

    cache_lock = threading.Lock()
    cached: dict[str, Any] = {}

    def store(name: str) -> Any | None:
        """A service object built once per name. Building one may create files, so only when the state dir exists."""
        with cache_lock:
            if name not in cached:
                factory = service(name)
                if factory is None or not state_dir.is_dir():
                    return None
                cached[name] = factory(str(state_dir))
            return cached[name]

    def auth_store() -> Any | None:
        if not require_auth and not (state_dir / "tenancy.sqlite").is_file():
            return None  # no token database yet: do not create one just to look
        return store("admin_auth")

    def guard(role: str, handler: Callable[[Request], Any], *, write: bool = False) -> Callable[[Request], Any]:
        """Check the bearer token and role, then run the handler. A refusal never echoes what was presented."""

        async def wrapper(request: Request) -> Response:
            auth = auth_store()
            enforced = require_auth or (auth is not None and auth.has_tokens())
            if not enforced:
                if write:
                    return JSONResponse({"error": "write routes need admin tokens; none exist yet"}, status_code=403)
            else:
                if auth is None:
                    return JSONResponse({"error": "authentication is required but unavailable"}, status_code=503)
                scheme, _, presented = request.headers.get("authorization", "").partition(" ")
                who = auth.resolve(presented.strip()) if scheme.lower() == "bearer" else None
                if who is None:
                    return JSONResponse(
                        {"error": "a valid admin token is required"},
                        status_code=401,
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                if _ROLES.index(who.role) < _ROLES.index(role):
                    return JSONResponse({"error": f"this needs the {role} role"}, status_code=403)
                request.state.admin = who
            if inspect.iscoroutinefunction(handler):
                return await handler(request)  # type: ignore[no-any-return]
            return await run_in_threadpool(handler, request)

        return wrapper

    def actor(request: Request) -> str:
        return f"admin:{request.state.admin.name}"

    async def body_of(request: Request) -> dict[str, Any]:
        try:
            data = await request.json()
        except ValueError:
            raise _Refused("the body must be a JSON object") from None
        if not isinstance(data, dict):
            raise _Refused("the body must be a JSON object")
        return data

    def text_field(data: dict[str, Any], name: str, default: str | None = None, limit: int = 200) -> str:
        value = data.get(name, default)
        if not isinstance(value, str) or (default is None and not value.strip()) or len(value) > limit:
            raise _Refused(f"{name} must be a text value of at most {limit} characters")
        if any(bad in value for bad in _FORBIDDEN):
            raise _Refused(f"{name} looks like a key or token and was refused")
        return value

    def refusal(e: Exception) -> Response:
        status = getattr(e, "status", None)  # ChangeError from the tenancy service carries its HTTP status
        if isinstance(e, _Refused):
            return JSONResponse({"error": str(e)}, status_code=400)
        if isinstance(status, int):
            return JSONResponse({"error": str(e)}, status_code=status)
        raise e

    def need(name: str) -> Any:
        found = store(name)
        if found is None:
            raise _Unavailable(name)
        return found

    def unavailable(e: _Unavailable) -> Response:
        return JSONResponse({"error": f"the {e} service is not installed"}, status_code=503)

    def kills_list(request: Request) -> Response:
        try:
            switches = need("kill")
        except _Unavailable as e:
            return unavailable(e)
        return JSONResponse([_plain(k) for k in switches.list()])

    async def kills_add(request: Request) -> Response:
        try:
            data = await body_of(request)
            feature, tenant = text_field(data, "feature"), text_field(data, "tenant", "*")
            reason = text_field(data, "reason", "", 500)
            changed = need("kill").add(feature, tenant, reason, actor(request))
        except _Unavailable as e:
            return unavailable(e)
        except _Refused as e:
            return refusal(e)
        return JSONResponse({"changed": bool(changed)})

    async def kills_remove(request: Request) -> Response:
        try:
            data = await body_of(request)
            feature, tenant = text_field(data, "feature"), text_field(data, "tenant", "*")
            changed = need("kill").remove(feature, tenant, actor(request))
        except _Unavailable as e:
            return unavailable(e)
        except _Refused as e:
            return refusal(e)
        return JSONResponse({"changed": bool(changed)})

    def audit_list(request: Request) -> Response:
        try:
            limit = _int_param(request, "limit", 200, 1, 1000)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
        log = store("audit")
        return JSONResponse([_plain(x) for x in log.entries()[-limit:]] if log is not None else [])

    def changes_list(request: Request) -> Response:
        try:
            changes = need("changes")
        except _Unavailable as e:
            return unavailable(e)
        return JSONResponse([_plain(c) for c in changes.list()])

    async def change_propose(request: Request) -> Response:
        try:
            data = await body_of(request)
            payload = data.get("payload")
            if not isinstance(payload, dict):
                raise _Refused("payload must be a JSON object")
            made = need("changes").propose(text_field(data, "kind"), payload, request.state.admin.name)
        except _Unavailable as e:
            return unavailable(e)
        except Exception as e:
            return refusal(e)
        return JSONResponse({"change_id": made}, status_code=201)

    def decide(verb: str) -> Callable[[Request], Response]:
        def handler(request: Request) -> Response:
            try:
                done = getattr(need("changes"), verb)(request.path_params["change_id"], request.state.admin.name)
            except _Unavailable as e:
                return unavailable(e)
            except Exception as e:
                return refusal(e)
            return JSONResponse(_plain(done))

        return handler

    def tokens_list(request: Request) -> Response:
        try:
            auth = need("admin_auth")
        except _Unavailable as e:
            return unavailable(e)
        return JSONResponse([_plain(t) for t in auth.list()])

    async def token_issue(request: Request) -> Response:
        try:
            data = await body_of(request)
            plaintext, token_id = need("admin_auth").issue(
                text_field(data, "name"), text_field(data, "role"), actor=actor(request)
            )
        except _Unavailable as e:
            return unavailable(e)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
        except _Refused as e:
            return refusal(e)
        return JSONResponse({"token": plaintext, "token_id": token_id}, status_code=201)  # shown once, never stored

    def token_revoke(request: Request) -> Response:
        try:
            done = need("admin_auth").revoke(request.path_params["token_id"], actor=actor(request))
        except _Unavailable as e:
            return unavailable(e)
        return JSONResponse({"revoked": bool(done)})

    def index(request: Request) -> Response:
        page = (files("token_economics_app_admin_api") / "static" / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(page, headers={"Content-Security-Policy": PAGE_CSP})

    def api(path: str, handler: Callable[[Request], Any], methods: list[str], role: str = "viewer") -> Route:
        return Route(path, guard(role, handler, write=methods != ["GET"]), methods=methods)

    routes = [
        Route("/", index, methods=["GET"]),
        api("/api/summary", summary, ["GET"]),
        api("/api/overview", overview, ["GET"]),
        api("/api/sessions/{session_id}", session_detail, ["GET"]),
        api("/api/sessions/{session_id}/tasks/{n}", task_detail, ["GET"]),
        api("/api/budgets", budgets, ["GET"]),
        api("/api/decisions", tail("decisions.jsonl", 200), ["GET"]),
        api("/api/alerts", tail("alerts.jsonl", 200), ["GET"]),
        api("/api/rejects", tail("rejects.jsonl", 100), ["GET"]),
        api("/api/keys", keys, ["GET"]),
        api("/api/kills", kills_list, ["GET"]),
        api("/api/kills", kills_add, ["POST"], "operator"),
        api("/api/kills", kills_remove, ["DELETE"], "operator"),
        api("/api/audit", audit_list, ["GET"]),
        api("/api/changes", changes_list, ["GET"]),
        api("/api/changes", change_propose, ["POST"], "admin"),
        api("/api/changes/{change_id}/approve", decide("approve"), ["POST"], "admin"),
        api("/api/changes/{change_id}/reject", decide("reject"), ["POST"], "admin"),
        api("/api/admin-tokens", tokens_list, ["GET"], "admin"),
        api("/api/admin-tokens", token_issue, ["POST"], "admin"),
        api("/api/admin-tokens/{token_id}", token_revoke, ["DELETE"], "admin"),
    ]
    return Starlette(routes=routes, middleware=[Middleware(_NoStore)])
