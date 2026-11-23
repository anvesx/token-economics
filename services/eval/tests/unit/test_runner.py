import json
from pathlib import Path

import pytest
from fakes import World, git, write_repo
from token_economics_svc_eval import (
    EvalRunner,
    HarnessConfigError,
    PreregistrationError,
    read_attempts,
)


def _runner(w: World, **kw: object) -> EvalRunner:
    return EvalRunner(w, w, w, **kw)  # type: ignore[arg-type]


def test_a_spec_that_is_not_tracked_by_git_is_refused(tmp_path: Path, world: World) -> None:
    # Given a spec file that exists but was never committed
    spec = write_repo(tmp_path / "r")
    new = spec.with_name("new.json")
    new.write_text(spec.read_text())
    # When it is run without allow_dirty Then the run is refused before any gateway starts
    with pytest.raises(PreregistrationError, match="not tracked"):
        _runner(world).run(new, tmp_path / "out")
    assert world.gateways == []


def test_a_spec_with_uncommitted_changes_is_refused_unless_allowed_and_then_marked(
    tmp_path: Path, world: World
) -> None:
    # Given a committed spec edited afterwards
    spec = write_repo(tmp_path / "r", seeds=1)
    spec.write_text(spec.read_text().replace('"alpha": 0.05', '"alpha": 0.01'))
    with pytest.raises(PreregistrationError, match="uncommitted"):
        _runner(world).run(spec, tmp_path / "out")
    # When allowed
    out = _runner(world).run(spec, tmp_path / "out", allow_dirty=True)
    # Then the meta and the report say it was not preregistered
    assert json.loads((out / "meta.json").read_text())["preregistered"] is False
    assert "Not preregistered" in (out / "REPORT.md").read_text()


def test_a_run_writes_the_result_folder_and_stops_every_gateway(tmp_path: Path, world: World) -> None:
    # Given a committed spec with 3 tasks, 2 arms, 2 seeds
    spec = write_repo(tmp_path / "r")
    # When it runs
    out = _runner(world).run(spec, tmp_path / "out")
    # Then every (task, arm, seed) has one attempt with the ledger cost, and the files exist
    attempts = read_attempts(out / "attempts.jsonl")
    assert len(attempts) == 12 and all(a.success and a.calls == 3 for a in attempts)
    assert {a.cost_usd for a in attempts if a.arm == "cand"} == {attempts[0].cost_usd.__class__("1.00")}
    assert all(a.fired == ("max_tokens",) for a in attempts if a.arm == "cand")
    meta = json.loads((out / "meta.json").read_text())
    assert meta["preregistered"] is True and len(meta["spec_sha256"]) == 64 and meta["finished"]
    assert json.loads((out / "spec.json").read_text())["name"] == "unit"
    result = json.loads((out / "result.json").read_text())
    assert result["comparisons"]["cand"]["ratio"] == 0.5
    assert "Eval report: unit" in (out / "REPORT.md").read_text()
    # And each arm got its own policy, all gateways were stopped, and workspaces are gone
    assert world.policies["cand"]["features"]["max_tokens"]["mode"] == "enforced"
    assert world.gateways and all(g.stopped for g in world.gateways)
    assert world.workspaces and not any(p.exists() for p in world.workspaces)


def test_no_prompt_text_is_stored_in_any_output(tmp_path: Path, world: World) -> None:
    out = _runner(world).run(write_repo(tmp_path / "r", seeds=1), tmp_path / "out")
    for path in out.rglob("*"):
        if path.is_file() and path.name != "spec.json":
            assert b'"prompt"' not in path.read_bytes() and b'"p1"' not in path.read_bytes(), path


def test_a_rerun_into_the_same_folder_skips_attempts_already_present(tmp_path: Path, world: World) -> None:
    # Given a finished run
    spec = write_repo(tmp_path / "r", seeds=1)
    out = _runner(world).run(spec, tmp_path / "out")
    first = len(world.ran)
    # When the same folder is run again
    _runner(world).run(spec, out)
    # Then nothing is run twice
    assert len(world.ran) == first and len(read_attempts(out / "attempts.jsonl")) == 6


def test_a_failed_verify_is_a_failure_whose_cost_still_counts(tmp_path: Path, world: World) -> None:
    world.solves = lambda arm, prompt: arm == "baseline"
    out = _runner(world).run(write_repo(tmp_path / "r", seeds=1), tmp_path / "out")
    cand = [a for a in read_attempts(out / "attempts.jsonl") if a.arm == "cand"]
    assert all(not a.success and a.cost_usd == 1 for a in cand)
    assert json.loads((out / "result.json").read_text())["arms"]["cand"]["failed_waste_share"] == 1.0


def test_an_unpriced_session_is_an_error_and_not_a_success(tmp_path: Path, world: World) -> None:
    world.unpriced = True
    out = _runner(world).run(write_repo(tmp_path / "r", seeds=1), tmp_path / "out")
    assert all(a.error == "unpriced" and not a.success for a in read_attempts(out / "attempts.jsonl"))


def test_gateways_are_stopped_when_a_run_crashes(tmp_path: Path, world: World) -> None:
    world.crash_on = "p1"
    with pytest.raises(RuntimeError, match="boom"):
        _runner(world).run(write_repo(tmp_path / "r"), tmp_path / "out")
    assert world.gateways and all(g.stopped for g in world.gateways)


def test_a_task_waits_for_the_spacing_before_running_in_a_second_arm(tmp_path: Path, world: World) -> None:
    # Given spacing 330 s and a clock that moves 10 s per reading
    now = [0.0]
    waits: list[float] = []

    def clock() -> float:
        now[0] += 10
        return now[0]

    def sleep(s: float) -> None:
        waits.append(s)
        now[0] += s

    spec = write_repo(tmp_path / "r", n_tasks=1, seeds=1, isolation="spacing", spacing_s=330)
    # When one task runs in both arms
    _runner(world, clock=clock, sleep=sleep).run(spec, tmp_path / "out")
    # Then the second arm waited until 330 s after the first
    assert len(waits) == 1 and 300 < waits[0] <= 330


def test_the_order_is_the_same_for_the_same_seed(tmp_path: Path) -> None:
    a, b = World(), World()
    _runner(a).run(write_repo(tmp_path / "a", n_tasks=5, seeds=2), tmp_path / "oa")
    _runner(b).run(write_repo(tmp_path / "b", n_tasks=5, seeds=2), tmp_path / "ob")
    assert a.ran == b.ran


def test_the_subset_runs_only_tagged_tasks(tmp_path: Path, world: World) -> None:
    spec = write_repo(tmp_path / "r", n_tasks=4, seeds=1, subset="lite")
    out = _runner(world).run(spec, tmp_path / "out")
    assert {a.task_id for a in read_attempts(out / "attempts.jsonl")} == {"t1", "t2", "t3"}


def test_an_arm_env_that_names_a_missing_variable_stops_the_run_before_any_spend(
    tmp_path: Path, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("NOPE_EFFORT", raising=False)
    spec = write_repo(tmp_path / "r")
    data = json.loads(spec.read_text())
    data["arms"]["cand"]["env"] = {"CLAUDE_CODE_EFFORT": "NOPE_EFFORT"}
    spec.write_text(json.dumps(data))
    git(spec.parent, "commit", "-qam", "env")
    with pytest.raises(HarnessConfigError, match="NOPE_EFFORT"):
        _runner(world).run(spec, tmp_path / "out")
    assert world.ran == []


def test_a_git_task_repo_gets_a_detached_worktree_that_is_removed(tmp_path: Path, world: World) -> None:
    # Given a task whose repo is itself a git repo, at a given ref
    task_repo = tmp_path / "taskrepo"
    task_repo.mkdir()
    git(task_repo, "init", "-q")
    (task_repo / "f.txt").write_text("1")
    git(task_repo, "add", ".")
    git(task_repo, "commit", "-qm", "one")
    spec = write_repo(tmp_path / "r", n_tasks=1, seeds=1)
    (spec.parent / "tasks.json").write_text(
        json.dumps({"tasks": [{"id": "g", "repo": str(task_repo), "ref": "HEAD", "prompt": "pg", "verify": "true"}]})
    )
    git(spec.parent, "commit", "-qam", "tasks")
    # When run Then the attempt succeeds and no worktree is left registered
    out = _runner(world).run(spec, tmp_path / "out")
    assert all(a.error == "" for a in read_attempts(out / "attempts.jsonl"))
    assert not (task_repo / ".git" / "worktrees").exists() or not list((task_repo / ".git" / "worktrees").iterdir())
