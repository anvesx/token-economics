"""The preregistered spec and the task file (plan/07). Plain dataclasses: a bad file fails with a clear message."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class SpecError(ValueError):
    """A spec or task file that cannot be run."""


@dataclass(frozen=True)
class ArmSpec:
    name: str
    policy: dict[str, Any]
    env: dict[str, str] = field(default_factory=dict)  # variable to set -> name of the variable to copy it from


@dataclass(frozen=True)
class EvalSpec:
    name: str
    tasks: str
    baseline: str
    arms: tuple[ArmSpec, ...]
    subset: str | None = None
    seeds: int = 3
    bound_pp: float = 5.0
    alpha: float = 0.05
    harness: str = "claude_code"
    harness_args: tuple[str, ...] = ()
    isolation: str = "spacing"
    spacing_s: float = 330.0
    n_boot: int = 10_000
    timeout_s: float = 1800.0
    cluster: str = "task"

    @property
    def candidates(self) -> list[str]:
        return [a.name for a in self.arms if a.name != self.baseline]


def parse_spec(data: Mapping[str, Any]) -> EvalSpec:
    for key in ("name", "tasks", "baseline", "arms"):
        if key not in data:
            raise SpecError(f"spec has no {key!r}")
    raw_arms = data["arms"]
    if not isinstance(raw_arms, dict) or data["baseline"] not in raw_arms:
        raise SpecError("spec 'arms' must be an object that contains the baseline arm")
    if len(raw_arms) < 2:
        raise SpecError("spec needs the baseline and at least one candidate arm")
    arms = tuple(
        ArmSpec(str(n), dict(a.get("policy") or {}), {str(k): str(v) for k, v in (a.get("env") or {}).items()})
        for n, a in raw_arms.items()
    )
    isolation = str(data.get("isolation", "spacing"))
    cluster = str(data.get("cluster", "task"))
    if isolation not in ("spacing", "none"):
        raise SpecError("isolation must be 'spacing' or 'none'")
    if cluster not in ("task", "repo"):
        raise SpecError("cluster must be 'task' or 'repo'")
    bound = data.get("bound") or {}
    if "success_pp" not in bound:
        raise SpecError("spec must declare bound.success_pp before the run")
    return EvalSpec(
        name=str(data["name"]),
        tasks=str(data["tasks"]),
        baseline=str(data["baseline"]),
        arms=arms,
        subset=data.get("subset"),
        seeds=int(data.get("seeds", 3)),
        bound_pp=float(bound["success_pp"]),
        alpha=float(data.get("alpha", 0.05)),
        harness=str(data.get("harness", "claude_code")),
        harness_args=tuple(str(x) for x in data.get("harness_args") or ()),
        isolation=isolation,
        spacing_s=float(data.get("spacing_s", 330)),
        n_boot=int(data.get("n_boot", 10_000)),
        timeout_s=float(data.get("timeout_s", 1800)),
        cluster=cluster,
    )


@dataclass(frozen=True)
class Task:
    id: str
    repo: str
    prompt: str
    verify: str
    ref: str | None = None
    tags: tuple[str, ...] = ()
    timeout_s: float | None = None


def load_tasks(path: Path, root: Path, subset: str | None = None) -> list[Task]:
    """Tasks from `path`; a relative `repo` is resolved against `root`. `subset` keeps tasks carrying that tag."""
    try:
        raw = json.loads(path.read_text())["tasks"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SpecError(f"cannot read task file {path}: {exc}") from exc
    tasks, seen = [], set()
    for t in raw:
        for key in ("id", "repo", "prompt", "verify"):
            if key not in t:
                raise SpecError(f"task {t.get('id', '?')} has no {key!r}")
        if t["id"] in seen:
            raise SpecError(f"duplicate task id {t['id']!r}")
        seen.add(t["id"])
        repo = Path(t["repo"])
        tasks.append(
            Task(
                id=str(t["id"]),
                repo=str(repo if repo.is_absolute() else (root / repo).resolve()),
                prompt=str(t["prompt"]),
                verify=str(t["verify"]),
                ref=t.get("ref"),
                tags=tuple(t.get("tags") or ()),
                timeout_s=float(t["timeout_s"]) if t.get("timeout_s") else None,
            )
        )
    if subset:
        tasks = [t for t in tasks if subset in t.tags]
    if not tasks:
        raise SpecError("no tasks to run")
    return tasks
