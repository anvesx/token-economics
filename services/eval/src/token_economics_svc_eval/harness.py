"""The EvalHarness the gateway tooling finds as SERVICES "eval"."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from token_economics_contracts import Attempt

from . import analysis
from .parts import ClaudeCodeRunner, CostReader, GatewayLauncher, HarnessRunner, LedgerCostReader, SubprocessLauncher
from .runner import EvalRunner
from .spec import SpecError


class Harness:
    def __init__(
        self,
        launcher: GatewayLauncher | None = None,
        runner: HarnessRunner | None = None,
        costs: CostReader | None = None,
    ) -> None:
        self._launcher = launcher or SubprocessLauncher()
        self._runner = runner  # default is built per spec, from its harness and harness_args
        self._costs = costs or LedgerCostReader()

    def run(self, spec: Path, out_dir: Path | None = None, allow_dirty: bool = False) -> Path:
        runner = self._runner
        if runner is None:
            data = json.loads(Path(spec).read_text())
            if data.get("harness", "claude_code") != "claude_code":
                raise SpecError(f"no runner for harness {data.get('harness')!r}; only claude_code is built")
            runner = ClaudeCodeRunner(data.get("harness_args") or ())
        return EvalRunner(self._launcher, runner, self._costs).run(Path(spec), out_dir, allow_dirty)

    def analyse(self, attempts: Sequence[Attempt], spec: Mapping[str, Any]) -> dict[str, Any]:
        return analysis.analyse(attempts, spec)

    def selftest(self, seed: int = 0) -> dict[str, Any]:
        return analysis.selftest(seed)


def create() -> Harness:
    """SERVICES "eval": the harness wired with the real gateway launcher, Claude Code runner and ledger reader."""
    return Harness()
