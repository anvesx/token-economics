"""Eval harness: preregistered specs, isolated arms, attempts and paired verdicts on cost per successful task."""

from .harness import Harness, create
from .parts import (
    ClaudeCodeRunner,
    CostReader,
    GatewayLauncher,
    HarnessConfigError,
    HarnessResult,
    HarnessRunner,
    LedgerCostReader,
    RunningGateway,
    SessionUsage,
    SubprocessLauncher,
)
from .report import report_markdown
from .runner import EvalRunner, PreregistrationError, check_preregistered, read_attempts
from .spec import ArmSpec, EvalSpec, SpecError, Task, load_tasks, parse_spec

__all__ = [
    "ArmSpec",
    "ClaudeCodeRunner",
    "CostReader",
    "EvalRunner",
    "EvalSpec",
    "GatewayLauncher",
    "Harness",
    "HarnessConfigError",
    "HarnessResult",
    "HarnessRunner",
    "LedgerCostReader",
    "PreregistrationError",
    "RunningGateway",
    "SessionUsage",
    "SpecError",
    "SubprocessLauncher",
    "Task",
    "check_preregistered",
    "create",
    "load_tasks",
    "parse_spec",
    "read_attempts",
    "report_markdown",
]
