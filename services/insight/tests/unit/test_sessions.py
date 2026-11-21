from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from token_economics_svc_insight import SessionViews


def views(transcripts: Path, tmp_path: Path, **kw: Any) -> SessionViews:
    return SessionViews(transcripts, tmp_path / "state", **kw)


def test_overview_lists_every_session_with_cost_tokens_and_task_count(transcripts: Path, tmp_path: Path) -> None:
    # Given a small transcript tree  # When the overview is built
    data = views(transcripts, tmp_path).overview(days=36500)
    # Then each session has its numbers, and the session costs add up to the total
    assert data["sessions"] and "details" not in data
    for s in data["sessions"]:
        assert s["task_count"] >= 1 and s["calls"] >= 1 and s["cost_usd"] >= 0 and s["split_by"] == "heuristic"
        assert set(s["tokens"]) == {"fresh_input", "cache_read", "cache_write", "output"}
    assert abs(sum(s["cost_usd"] for s in data["sessions"]) - data["total_usd"]) < 1e-4
    assert abs(sum(x["usd"] for x in data["spend_by_token_type"]) - data["total_usd"]) < 1e-4
    assert len(data["retired"]) == 7 and len(data["categories"]) == 43


def test_a_session_is_split_into_tasks_whose_costs_add_up_and_each_says_why(transcripts: Path, tmp_path: Path) -> None:
    v = views(transcripts, tmp_path)
    for summary in v.overview(days=36500)["sessions"]:
        s = v.session(summary["id"], days=36500)
        assert s is not None and len(s["tasks"]) == summary["task_count"]
        assert s["tasks"][0]["how"] == "start" and all(t["how_text"] for t in s["tasks"])
        assert abs(sum(t["cost_usd"] for t in s["tasks"]) - s["cost_usd"]) < 1e-4
        assert v.session(summary["short"], days=36500)["id"] == summary["id"]  # type: ignore[index]
    assert v.session("nope-nope", days=36500) is None


def test_leaks_found_in_a_session_appear_on_that_session(transcripts: Path, tmp_path: Path) -> None:
    v = views(transcripts, tmp_path)
    data = v.overview(days=36500)
    fired = {c["row"] for c in data["categories"] if c["count"]}
    on_sessions = {leak["row"] for s in data["sessions"] for leak in v.session(s["id"], days=36500)["leaks"]}  # type: ignore[index]
    assert fired and fired == on_sessions


def test_cached_labels_from_the_plugin_are_reused_and_nothing_else_is_written(
    transcripts: Path, tmp_path: Path
) -> None:
    # Given a labels cache left by the Hermes plugin (hashes and labels only)
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    (plugin / "prompt_checks.json").write_text(json.dumps({"abc": {"labels": []}}))
    v = views(transcripts, tmp_path, seed_labels_from=plugin)
    v.overview(days=36500)
    # Then it is copied once, and the state directory holds nothing but that cache
    assert sorted(p.name for p in (tmp_path / "state").iterdir()) == ["prompt_checks.json"]


def test_an_empty_tree_gives_an_empty_overview(tmp_path: Path) -> None:
    data = views(tmp_path / "none", tmp_path).overview()
    assert data["sessions"] == [] and data["total_usd"] == 0 and data["categories"] == []
