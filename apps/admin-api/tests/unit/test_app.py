from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import count
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("httpx", reason="Starlette's TestClient needs httpx (the `test` extra)")

from starlette.testclient import TestClient  # noqa: E402
from token_economics_app_admin_api import create_app  # noqa: E402
from token_economics_contracts import SERVICES, Buckets, BudgetStatus, CostSource, LedgerRow, load  # noqa: E402

_ids = count(1)


def _installed() -> bool:
    try:
        load(SERVICES, "ledger")
        load(SERVICES, "dashboard_summary")
    except LookupError:
        return False
    return True


# The ledger and insight services are the `test` extra; a bare install of this package skips what needs them.
needs_services = pytest.mark.skipif(not _installed(), reason="ledger and insight services are not installed")
ENDPOINTS = ["/api/summary", "/api/budgets", "/api/decisions", "/api/alerts", "/api/rejects", "/api/keys"]
INJECTION = '<img src=x onerror=alert(1)>"</script>'


def write_rows(state: Path, rows: list[LedgerRow]) -> None:
    ledger = load(SERVICES, "ledger")(str(state / "ledger.sqlite"))
    for r in rows:
        assert ledger.write(r)
    ledger.close()


def row(ago_days: int, cost: str | None, *, caller: str = "ann", model: str = "m1", **buckets: int) -> LedgerRow:
    ts = datetime.now(UTC) - timedelta(days=ago_days, minutes=1)
    return LedgerRow(
        provider="anthropic",
        response_id=f"r{next(_ids)}",
        ts=ts,
        tenant="acme",
        caller=caller,
        harness="claude-code",
        session_id="s1",
        model=model,
        buckets=Buckets(**buckets),
        cost_estimate_usd=None if cost is None else Decimal(cost),
        cost_source=CostSource.GATEWAY,
        price_row_id="" if cost is None else "p1",
    )


def client(state: Path, loader: Callable[[str, str], Any] | None = None) -> TestClient:
    return TestClient(create_app(state, loader) if loader else create_app(state))


@needs_services
def test_empty_state_dir_every_endpoint_is_200_with_empty_data(tmp_path: Path) -> None:
    # Given a state dir with nothing in it
    c = client(tmp_path)
    # When / Then
    for path in ENDPOINTS:
        assert c.get(path).status_code == 200, path
    s = c.get("/api/summary").json()
    assert (s["requests"], s["spend_usd"], s["has_ledger"], len(s["by_day"])) == (0, "0", False, 30)
    for path in ENDPOINTS[1:]:
        assert c.get(path).json() == []
    assert not (tmp_path / "ledger.sqlite").exists()  # never created


@needs_services
def test_summary_numbers_match_a_ledger_written_through_the_real_service(tmp_path: Path) -> None:
    # Given three rows today and yesterday, one unpriced, one outside a 7-day window
    write_rows(
        tmp_path,
        [
            row(0, "1.50", fresh_input=100, cache_read=300, output=10),
            row(1, "0.50", caller="bob", model="m2", fresh_input=100, output=5),
            row(1, None, fresh_input=1),
            row(20, "9"),
        ],
    )
    c = client(tmp_path)
    # When
    week = c.get("/api/summary?days=7").json()
    month = c.get("/api/summary?days=30").json()
    # Then
    assert week["has_ledger"] is True
    assert (week["requests"], week["unpriced_requests"], week["spend_usd"]) == (3, 1, "2.00")
    assert month["spend_usd"] == "11.00" and len(week["by_day"]) == 7
    assert [g["name"] for g in week["by_caller"]] == ["ann", "bob"]
    assert week["by_caller"][0]["share_of_spend"] == "0.7500" and week["tokens"]["cache_read"] == 300


@needs_services
def test_bad_days_is_a_400_and_big_values_are_clamped(tmp_path: Path) -> None:
    c = client(tmp_path)
    assert c.get("/api/summary?days=abc").status_code == 400
    assert len(c.get("/api/summary?days=9999").json()["by_day"]) == 365
    assert c.get("/api/decisions?limit=x").status_code == 400


def test_jsonl_endpoints_tail_and_skip_bad_lines(tmp_path: Path) -> None:
    # Given a decisions file of 300 lines with two bad ones and a non-object, and a missing alerts file
    lines = [json.dumps({"n": i, "action": "blocked"}) for i in range(300)]
    lines[298] = "{not json"
    lines[297] = "[1, 2]"
    (tmp_path / "decisions.jsonl").write_text("\n".join(lines) + "\n\n")
    (tmp_path / "rejects.jsonl").write_text(json.dumps({"n": 1}) + "\n" + json.dumps({"n": 2}))  # no final newline
    c = client(tmp_path)
    # When / Then the last 200 lines, oldest first, minus the unusable ones
    got = c.get("/api/decisions").json()
    assert [d["n"] for d in got] == [i for i in range(100, 300) if i not in (297, 298)]
    assert [d["n"] for d in c.get("/api/decisions?limit=3").json()] == [299]
    assert [d["n"] for d in c.get("/api/rejects").json()] == [1, 2]
    assert c.get("/api/alerts").json() == []


def fake_loader(**services: Any) -> Callable[[str, str], Any]:
    def loader(group: str, name: str) -> Any:
        if name in services:
            return services[name]
        if name in ("ledger", "dashboard_summary"):
            return load(group, name)
        raise LookupError(name)

    return loader


class _Budgets:
    def __init__(self, state: str) -> None:
        self.state = state

    def status(self) -> list[BudgetStatus]:
        return [
            BudgetStatus(
                scope="tenant:acme",
                window="day",
                limit_usd=Decimal(10),
                spent_usd=Decimal(6),
                reserved_usd=Decimal(2),
                period_start=datetime(2026, 11, 1, tzinfo=UTC),
            )
        ]


class _Keys:
    def __init__(self, state: str) -> None:
        self.state = state

    def list(self) -> list[dict[str, Any]]:
        return [
            {
                "key_id": "k1",
                "tenant": "acme",
                "team": "t",
                "caller": "ann",
                "created_at": datetime(2026, 11, 1, tzinfo=UTC),
                "revoked_at": None,
                "key": "vk-SECRET",
                "hash": "abc",
            }
        ]


@needs_services
def test_budgets_and_keys_come_from_injected_services_and_keys_never_leak_secrets(tmp_path: Path) -> None:
    # Given fake budget and key services
    c = client(tmp_path, fake_loader(budget_status=_Budgets, keys=_Keys))
    # When
    budgets = c.get("/api/budgets").json()
    keys = c.get("/api/keys").json()
    # Then
    assert budgets[0]["scope"] == "tenant:acme" and budgets[0]["used_share"] == "0.8"
    assert budgets[0]["spent_usd"] == "6" and budgets[0]["reserved_usd"] == "2"
    assert keys == [
        {
            "key_id": "k1",
            "tenant": "acme",
            "team": "t",
            "caller": "ann",
            "created_at": "2026-11-01T00:00:00Z",
            "revoked_at": None,
        }
    ]
    assert "SECRET" not in c.get("/api/keys").text


class _Info:
    tenant, team, caller = "acme", "t", "ann"


class _Record:
    """The shape services/tenancy returns: identity fields nested under `info`, no plaintext, no hash."""

    key_id = "k2"
    info = _Info()
    created_at = datetime(2026, 11, 2, tzinfo=UTC)
    revoked_at = datetime(2026, 11, 3, tzinfo=UTC)


class _RecordKeys:
    def __init__(self, state: str) -> None:
        self.state = state

    def list(self) -> list[_Record]:
        return [_Record()]


def test_keys_accept_records_with_a_nested_info(tmp_path: Path) -> None:
    # Given a key store returning records like the tenancy service's
    c = client(tmp_path, fake_loader(keys=_RecordKeys))
    # Then
    assert c.get("/api/keys").json() == [
        {
            "key_id": "k2",
            "tenant": "acme",
            "team": "t",
            "caller": "ann",
            "created_at": "2026-11-02T00:00:00Z",
            "revoked_at": "2026-11-03T00:00:00Z",
        }
    ]


def test_missing_services_degrade_to_empty_or_503(tmp_path: Path) -> None:
    # Given a loader that knows nothing
    def nothing(group: str, name: str) -> Any:
        raise LookupError(name)

    c = client(tmp_path, nothing)
    # Then
    assert c.get("/api/budgets").json() == [] and c.get("/api/keys").json() == []
    assert c.get("/api/summary").status_code == 503
    # And a ledger file with no ledger service still gives an empty summary
    (tmp_path / "ledger.sqlite").write_bytes(b"")
    assert client(tmp_path, fake_loader()).get("/api/summary").json()["requests"] == 0


@needs_services
def test_page_is_static_self_contained_and_never_interpolates_server_data(tmp_path: Path) -> None:
    # Given a caller name that is an HTML/JS injection string
    write_rows(tmp_path, [row(0, "1", caller=INJECTION, output=1)])
    c = client(tmp_path)
    # When
    page = c.get("/")
    api = c.get("/api/summary")
    # Then the JSON carries the string as data, the page does not contain it, and the page is the same each time
    assert api.json()["by_caller"][0]["name"] == INJECTION
    assert page.status_code == 200 and page.headers["content-type"].startswith("text/html")
    assert INJECTION not in page.text and "alert(1)" not in page.text
    assert page.text == client(tmp_path / "other").get("/").text
    assert "Costs are estimates at price-book rates" in page.text
    # And it makes no external requests and never builds markup from data
    assert not re.search(r"https?://", page.text)
    assert "innerHTML" not in page.text and "document.write" not in page.text and "eval(" not in page.text
    assert "default-src 'none'" in page.headers["content-security-policy"]


@needs_services
def test_responses_are_no_store_and_only_get_is_allowed(tmp_path: Path) -> None:
    c = client(tmp_path)
    for path in ["/", *ENDPOINTS, "/nope"]:
        assert c.get(path).headers["cache-control"] == "no-store", path
    for path in ["/", *ENDPOINTS]:
        for method in ("post", "put", "delete", "patch"):
            assert getattr(c, method)(path).status_code == 405, (method, path)


@needs_services
@pytest.mark.parametrize("path", ENDPOINTS)
def test_every_endpoint_returns_json(path: str, tmp_path: Path) -> None:
    assert client(tmp_path).get(path).headers["content-type"].startswith("application/json")


# ---- session views: the transcript-backed overview and session detail

SESSION = {
    "id": "abcdef1234567890",
    "short": "abcdef12",
    "project": "demo",
    "title": INJECTION,
    "started": "2026-11-20T10:00:00Z",
    "duration_s": 600,
    "task_count": 1,
    "calls": 3,
    "cost_usd": 1.5,
    "leak_usd": 0.5,
    "top_leak": {"row": 3, "name": "Re-read", "usd": 0.5},
    "split_by": "heuristic",
    "tasks": [{"n": 1, "title": "t", "how_text": "first prompt of the session", "cost_usd": 1.5}],
    "leaks": [],
}
OVERVIEW = {
    "days": 30,
    "total_usd": 1.5,
    "sessions": [{k: v for k, v in SESSION.items() if k not in ("tasks", "leaks")}],
    "categories": [],
    "retired": [],
    "spend_by_token_type": [{"name": "output", "usd": 1.5}],
    "spend_by_model": [],
    "spend_by_project": [],
}


TASK = {
    "n": 1,
    "title": INJECTION,
    "session": {"id": SESSION["id"], "title": INJECTION, "task_count": 1},
    "share_of_session": 1.0,
    "timeline": [],
}


class _Views:
    made: list[tuple[str, str, bool]] = []

    def __init__(self, transcripts: str, state: str, prompt_check: bool) -> None:
        _Views.made.append((transcripts, state, prompt_check))
        self.asked: list[int] = []

    def overview(self, days: int) -> dict[str, Any]:
        self.asked.append(days)
        return {**OVERVIEW, "days": days}

    def session(self, session_id: str, days: int) -> dict[str, Any] | None:
        return SESSION if SESSION["id"].startswith(session_id) else None

    def task(self, session_id: str, n: int, days: int) -> dict[str, Any] | None:
        self.asked.append(days)
        return {**TASK, "days": days} if SESSION["id"].startswith(session_id) and n == 1 else None


def views_client(tmp_path: Path, **kwargs: Any) -> TestClient:
    _Views.made = []
    return TestClient(create_app(tmp_path, fake_loader(session_views=_Views), **kwargs))


def test_overview_and_session_come_from_the_session_views_service(tmp_path: Path) -> None:
    # Given a fake session_views service
    c = views_client(tmp_path)
    # When / Then
    assert c.get("/api/overview?days=7").json() == {**OVERVIEW, "days": 7}
    assert c.get("/api/overview").json()["days"] == 30
    assert c.get(f"/api/sessions/{SESSION['id']}").json()["title"] == INJECTION
    missing = c.get("/api/sessions/nope")
    assert missing.status_code == 404 and "error" in missing.json()


def test_task_endpoint_returns_the_task_and_404s_for_unknown_or_non_numeric(tmp_path: Path) -> None:
    # Given a fake session_views service with one task
    c = views_client(tmp_path)
    base = f"/api/sessions/{SESSION['id']}/tasks"
    # When / Then
    got = c.get(f"{base}/1?days=7").json()
    assert got["title"] == INJECTION and got["days"] == 7
    assert c.get("/api/sessions/abcdef12/tasks/1").status_code == 200
    for bad in ("2", "0", "-1", "abc", "1.5", "%CE%A3"):
        r = c.get(f"{base}/{bad}")
        assert r.status_code == 404 and "error" in r.json(), bad
    assert c.get("/api/sessions/nope/tasks/1").status_code == 404
    assert c.get(f"{base}/1?days=x").status_code == 400
    assert c.get(f"{base}/1").headers["cache-control"] == "no-store"
    assert c.post(f"{base}/1").status_code == 405


def test_task_endpoint_without_the_insight_service_is_503(tmp_path: Path) -> None:
    def nothing(group: str, name: str) -> Any:
        raise LookupError(name)

    assert TestClient(create_app(tmp_path, nothing)).get("/api/sessions/abcdef12/tasks/1").status_code == 503


def test_session_views_service_is_built_once_with_the_paths_and_flag(tmp_path: Path) -> None:
    # Given an app with explicit transcripts and prompt check on
    c = views_client(tmp_path, transcripts_root=tmp_path / "t", prompt_check=True)
    # When several requests are made
    for _ in range(3):
        c.get("/api/overview")
        c.get("/api/sessions/abcdef12")
    # Then the factory ran once, with the transcripts, the detectors directory and the flag
    assert _Views.made == [(str(tmp_path / "t"), str(tmp_path / "detectors"), True)]


def test_session_views_defaults_to_claude_projects_and_no_prompt_check(tmp_path: Path) -> None:
    views_client(tmp_path).get("/api/overview")
    assert _Views.made == [(str(Path("~/.claude/projects").expanduser()), str(tmp_path / "detectors"), False)]


def test_session_views_validate_days_and_missing_service_is_503(tmp_path: Path) -> None:
    c = views_client(tmp_path)
    assert c.get("/api/overview?days=abc").status_code == 400
    assert c.get("/api/sessions/abcdef12?days=x").status_code == 400

    def nothing(group: str, name: str) -> Any:
        raise LookupError(name)

    bare = TestClient(create_app(tmp_path, nothing))
    assert bare.get("/api/overview").status_code == 503
    assert bare.get("/api/sessions/abcdef12").status_code == 503
    assert "error" in bare.get("/api/overview").json()
    assert views_client(tmp_path).post("/api/overview").status_code == 405


def test_page_has_the_views_no_external_urls_and_no_innerhtml(tmp_path: Path) -> None:
    # Given the page as served (it needs no service)
    page = client(tmp_path, fake_loader()).get("/").text
    # Then it has every view, the footer, no external URL and never assigns markup
    for text in (
        '["overview"',
        '["sessions"',
        '["categories"',
        '["gateway"',
        "#session/",
        "#task/",
        "renderTask",
        "Call timeline",
        "/tasks/",
        "/api/overview",
        "/api/sessions/",
    ):
        assert text in page
    assert "Titles are read from your own transcripts" in page
    assert not re.search(r"https?://", page)
    assert not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(", page)


def test_page_script_is_valid_javascript(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    page = client(tmp_path, fake_loader()).get("/").text
    script = page.split("<script>", 1)[1].split("</script>", 1)[0]
    path = tmp_path / "page.js"
    path.write_text(script)
    done = subprocess.run([node, "--check", str(path)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
