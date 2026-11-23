"""The run loop: arms and tasks shuffled per seed, spaced apart, one Attempt appended per finished attempt."""

from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import time
from collections.abc import Callable
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from token_economics_contracts import Attempt, Buckets

from .analysis import analyse_attempts
from .parts import (
    CostReader,
    GatewayLauncher,
    HarnessConfigError,
    HarnessRunner,
    RunningGateway,
    new_session_id,
    run_verify,
    workspace,
)
from .report import report_markdown
from .spec import EvalSpec, Task, load_tasks, parse_spec


class PreregistrationError(RuntimeError):
    """The spec is not committed, so its bound was not declared before the run."""


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)


def check_preregistered(spec_path: Path) -> tuple[bool, str]:
    """(True, "") when the spec is tracked by git with no uncommitted changes; else (False, why)."""
    if _git(spec_path.parent, "ls-files", "--error-unmatch", spec_path.name).returncode != 0:
        return False, f"{spec_path} is not tracked by git"
    if _git(spec_path.parent, "status", "--porcelain", "--", spec_path.name).stdout.strip():
        return False, f"{spec_path} has uncommitted changes"
    return True, ""


def repo_root(spec_path: Path) -> Path:
    top = _git(spec_path.parent, "rev-parse", "--show-toplevel")
    return Path(top.stdout.strip()) if top.returncode == 0 and top.stdout.strip() else spec_path.parent


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_attempts(path: Path) -> list[Attempt]:
    if not path.exists():
        return []
    return [Attempt.model_validate_json(line) for line in path.read_text().splitlines() if line.strip()]


@dataclass
class EvalRunner:
    launcher: GatewayLauncher
    runner: HarnessRunner
    costs: CostReader
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep

    def run(self, spec_path: Path, out_dir: Path | None = None, allow_dirty: bool = False) -> Path:
        spec_path = spec_path.resolve()
        preregistered, why = check_preregistered(spec_path)
        if not preregistered and not allow_dirty:
            raise PreregistrationError(
                f"{why}. Commit the spec so the success bound is fixed before the run, or pass --allow-dirty "
                "(the result is then marked as not preregistered)."
            )
        raw = json.loads(spec_path.read_text())
        spec = parse_spec(raw)
        root = repo_root(spec_path)
        task_file = (root / spec.tasks).resolve()
        tasks = load_tasks(task_file, root, spec.subset)
        env_by_arm = self._arm_env(spec)
        self.runner.preflight()

        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        out = (out_dir or root / "evals" / "results" / spec.name / stamp).resolve()
        out.mkdir(parents=True, exist_ok=True)
        (out / "spec.json").write_text(json.dumps(raw, indent=2) + "\n")
        meta_path = out / "meta.json"
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        meta |= {
            "spec_sha256": _sha256(spec_path),
            "tasks_sha256": _sha256(task_file),
            "git_commit": _git(spec_path.parent, "rev-parse", "HEAD").stdout.strip(),
            "preregistered": preregistered,
            "started": meta.get("started") or datetime.now(UTC).isoformat(),
            "finished": None,
        }
        meta_path.write_text(json.dumps(meta, indent=2) + "\n")

        attempts_path = out / "attempts.jsonl"
        with ExitStack() as stack:
            gateways: dict[str, RunningGateway] = {}
            for arm in spec.arms:
                gw = self.launcher.start(arm.name, out / "arms" / arm.name, arm.policy)
                stack.callback(gw.stop)  # always stopped, even when a later arm fails to start
                gateways[arm.name] = gw
            self._loop(spec, tasks, gateways, env_by_arm, attempts_path)

        attempts = read_attempts(attempts_path)
        result = analyse_attempts(attempts, spec)
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        (out / "REPORT.md").write_text(report_markdown(result, preregistered=preregistered))
        meta["finished"] = datetime.now(UTC).isoformat()
        meta_path.write_text(json.dumps(meta, indent=2) + "\n")
        return out

    @staticmethod
    def _arm_env(spec: EvalSpec) -> dict[str, dict[str, str]]:
        """Resolve each arm's env: it names the variables to copy, never values. A missing one stops the run."""
        out: dict[str, dict[str, str]] = {}
        for arm in spec.arms:
            out[arm.name] = {}
            for var, source in arm.env.items():
                if source not in os.environ:
                    raise HarnessConfigError(f"arm {arm.name!r} copies {var} from ${source}, which is not set")
                out[arm.name][var] = os.environ[source]
        return out

    def _loop(
        self,
        spec: EvalSpec,
        tasks: list[Task],
        gateways: dict[str, RunningGateway],
        env_by_arm: dict[str, dict[str, str]],
        attempts_path: Path,
    ) -> None:
        done = {(a.task_id, a.arm, a.seed) for a in read_attempts(attempts_path)}  # a re-run resumes
        last_ran: dict[str, tuple[str, float]] = {}
        for seed in range(spec.seeds):
            rng = random.Random(seed)
            arm_order = [a.name for a in spec.arms]
            task_order = list(tasks)
            rng.shuffle(arm_order)
            rng.shuffle(task_order)
            for arm in arm_order:
                for task in task_order:
                    if (task.id, arm, seed) in done:
                        continue
                    if spec.isolation == "spacing" and task.id in last_ran and last_ran[task.id][0] != arm:
                        wait = spec.spacing_s - (self.clock() - last_ran[task.id][1])
                        if wait > 0:
                            self.sleep(wait)  # provider cache from the other arm must expire first
                    attempt = self._attempt(spec, task, arm, seed, gateways[arm], env_by_arm[arm])
                    last_ran[task.id] = (arm, self.clock())
                    with attempts_path.open("a") as f:
                        f.write(attempt.model_dump_json() + "\n")

    def _attempt(
        self, spec: EvalSpec, task: Task, arm: str, seed: int, gw: RunningGateway, env: dict[str, str]
    ) -> Attempt:
        started = self.clock()
        timeout = task.timeout_s or spec.timeout_s
        sid, error, verified = new_session_id(), "", False
        try:
            with workspace(task.repo, task.ref) as ws:
                res = self.runner.run(task.prompt, ws, gw.base_url, env, timeout, sid)
                sid, error = res.session_id or sid, res.error
                if not error:
                    verified = run_verify(task.verify, ws, timeout)
        except (OSError, subprocess.CalledProcessError) as exc:
            error = f"workspace_{type(exc).__name__}"
        usage = self.costs.read(gw.state_dir, sid)
        if not error and usage.calls == 0:
            error = "no_ledger_rows"
        if not error and usage.cost_usd is None:
            error = "unpriced"
        return Attempt(
            task_id=task.id,
            arm=arm,
            seed=seed,
            success=verified and not error,
            cost_usd=usage.cost_usd or Decimal(0),
            repo=task.repo,
            calls=usage.calls,
            buckets=usage.buckets if usage.calls else Buckets(),
            duration_s=max(0.0, self.clock() - started),
            session_id=sid,
            fired=usage.fired,
            error=error,
        )
