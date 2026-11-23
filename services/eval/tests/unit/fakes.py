import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from token_economics_contracts import Buckets
from token_economics_svc_eval import HarnessResult, SessionUsage


def git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(cwd), *args], check=True, capture_output=True
    )


@dataclass
class FakeGateway:
    base_url: str
    state_dir: Path
    stopped: bool = False

    def stop(self) -> None:
        self.stopped = True


@dataclass
class World:
    """Fake launcher, runner and cost reader sharing one record of what happened. Nothing is started or spent."""

    arm_cost: dict[str, str] = field(default_factory=lambda: {"baseline": "2.00", "cand": "1.00"})
    solves: Callable[[str, str], bool] = lambda arm, task: True
    unpriced: bool = False
    crash_on: str | None = None
    gateways: list[FakeGateway] = field(default_factory=list)
    policies: dict[str, Any] = field(default_factory=dict)
    ran: list[tuple[str, str]] = field(default_factory=list)  # (arm, task prompt)
    sessions: dict[str, str] = field(default_factory=dict)  # session id -> arm
    workspaces: list[Path] = field(default_factory=list)
    preflighted: bool = False

    # launcher
    def start(self, arm: str, arm_dir: Path, policy: Any) -> FakeGateway:
        state = arm_dir / "state"
        state.mkdir(parents=True, exist_ok=True)
        self.policies[arm] = policy
        gw = FakeGateway(f"http://fake/{arm}", state)
        self.gateways.append(gw)
        return gw

    # runner
    def preflight(self) -> None:
        self.preflighted = True

    def run(self, prompt: str, cwd: Path, base_url: str, env: Any, timeout_s: float, session_id: str) -> HarnessResult:
        arm = base_url.rsplit("/", 1)[1]
        self.ran.append((arm, prompt))
        self.workspaces.append(cwd)
        self.sessions[session_id] = arm
        if self.crash_on == prompt:
            raise RuntimeError("boom")
        if self.solves(arm, prompt):
            (cwd / "done.txt").write_text("x")
        return HarnessResult(session_id)

    # cost reader
    def read(self, state_dir: Path, session_id: str) -> SessionUsage:
        arm = self.sessions[session_id]
        cost = None if self.unpriced else Decimal(self.arm_cost[arm])
        return SessionUsage(cost, Buckets(fresh_input=10, output=5), 3, ("max_tokens",) if arm == "cand" else ())


def write_repo(root: Path, n_tasks: int = 3, seeds: int = 2, **spec_extra: Any) -> Path:
    """A temp git repo with a toy folder, a task file and a committed spec. Returns the spec path."""
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q")
    (root / "toy").mkdir()
    (root / "toy" / "README").write_text("toy")
    tasks = [
        {"id": f"t{i}", "repo": "toy", "prompt": f"p{i}", "verify": "test -f done.txt", "tags": ["lite"] if i else []}
        for i in range(n_tasks)
    ]
    (root / "tasks.json").write_text(json.dumps({"tasks": tasks}))
    spec = {
        "name": "unit",
        "tasks": "tasks.json",
        "subset": None,
        "baseline": "baseline",
        "arms": {"baseline": {"policy": {}}, "cand": {"policy": {"features": {"max_tokens": {"mode": "enforced"}}}}},
        "seeds": seeds,
        "bound": {"success_pp": 5},
        "alpha": 0.05,
        "isolation": "none",
        "n_boot": 200,
        **spec_extra,
    }
    path = root / "spec.json"
    path.write_text(json.dumps(spec))
    git(root, "add", ".")
    git(root, "commit", "-qm", "prereg")
    return path
