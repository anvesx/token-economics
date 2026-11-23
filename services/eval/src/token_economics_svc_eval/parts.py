"""The injectable parts of the runner. Tests use fakes; the real ones start processes and spend money."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from token_economics_contracts import SERVICES, Buckets, load


class HarnessConfigError(RuntimeError):
    """The harness would not send its calls through the arm gateway, so a run would measure nothing."""


# ---------------------------------------------------------------- gateway per arm


class RunningGateway(Protocol):
    base_url: str
    state_dir: Path

    def stop(self) -> None: ...


class GatewayLauncher(Protocol):
    def start(self, arm: str, arm_dir: Path, policy: Mapping[str, object]) -> RunningGateway:
        """Start a gateway for one arm with its own state directory under `arm_dir` and the arm's policy."""
        ...


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _tool(name: str) -> str:
    """An installed console script: on PATH, or next to this interpreter (a venv that is not activated)."""
    found = shutil.which(name) or shutil.which(name, path=str(Path(sys.executable).parent))
    if not found:
        raise HarnessConfigError(f"{name} is not installed; run `uv sync --all-packages`")
    return found


@dataclass
class _Process:
    base_url: str
    state_dir: Path
    proc: subprocess.Popen[bytes]

    def stop(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()


class SubprocessLauncher:
    """Per arm: `token-economics init` on a fresh state directory, the arm's policy.json, then the real gateway."""

    def __init__(self, health_timeout_s: float = 30.0) -> None:
        self._health_timeout_s = health_timeout_s

    def start(self, arm: str, arm_dir: Path, policy: Mapping[str, object]) -> RunningGateway:
        state = arm_dir / "state"
        state.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "TOKEN_ECONOMICS_STATE_DIR": str(state)}
        subprocess.run([_tool("token-economics"), "init"], env=env, check=True, capture_output=True, timeout=60)
        (state / "policy.json").write_text(json.dumps(dict(policy), indent=2) + "\n")
        port = _free_port()
        proc = subprocess.Popen(
            [_tool("token-economics-gateway"), "--port", str(port)],
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        running = _Process(f"http://127.0.0.1:{port}", state, proc)
        try:
            self._wait_healthy(running)
        except BaseException:
            running.stop()
            raise
        return running

    def _wait_healthy(self, gw: _Process) -> None:
        deadline = time.monotonic() + self._health_timeout_s
        while time.monotonic() < deadline:
            if gw.proc.poll() is not None:
                raise HarnessConfigError(f"the gateway for {gw.state_dir} exited with code {gw.proc.returncode}")
            try:
                with urllib.request.urlopen(f"{gw.base_url}/_te/health", timeout=2) as r:
                    if r.status == 200:
                        return
            except (urllib.error.URLError, OSError):
                time.sleep(0.2)
        raise HarnessConfigError(f"the gateway at {gw.base_url} was not healthy after {self._health_timeout_s:.0f}s")


# ---------------------------------------------------------------- the harness under test


@dataclass(frozen=True)
class HarnessResult:
    session_id: str = ""
    error: str = ""  # "timeout", "exit_<code>", ...; empty when the harness finished


class HarnessRunner(Protocol):
    def preflight(self) -> None:
        """Raise HarnessConfigError when calls would skip the arm gateway. Called once, before any spend."""
        ...

    def run(
        self, prompt: str, cwd: Path, base_url: str, env: Mapping[str, str], timeout_s: float, session_id: str
    ) -> HarnessResult: ...


class ClaudeCodeRunner:
    """`claude -p <prompt> --output-format json`. stdin is closed: otherwise the script text leaks into the prompt."""

    def __init__(self, extra_args: Sequence[str] = (), settings_path: Path | None = None, command: str = "claude"):
        self._extra = list(extra_args)
        self._settings = settings_path or Path("~/.claude/settings.json").expanduser()
        self._command = command

    def preflight(self) -> None:
        try:
            pinned = json.loads(self._settings.read_text()).get("env", {}).get("ANTHROPIC_BASE_URL")
        except (OSError, ValueError, AttributeError):
            return
        if pinned:
            raise HarnessConfigError(
                f"{self._settings} sets env.ANTHROPIC_BASE_URL, which overrides the shell variable: calls would skip "
                "the arm gateway and cost nothing in its ledger. Remove it for the run."
            )

    def run(
        self, prompt: str, cwd: Path, base_url: str, env: Mapping[str, str], timeout_s: float, session_id: str
    ) -> HarnessResult:
        cmd = [self._command, "-p", prompt, "--output-format", "json", "--session-id", session_id, *self._extra]
        try:
            done = subprocess.run(
                cmd,
                cwd=cwd,
                env={**os.environ, **env, "ANTHROPIC_BASE_URL": base_url},
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            return HarnessResult(session_id, "timeout")
        except OSError as exc:
            return HarnessResult(session_id, f"cannot_start_{type(exc).__name__}")
        reported = session_id
        try:
            out = json.loads(done.stdout)
            reported = str(out.get("session_id") or session_id)  # only the id is kept; the reply text is dropped
        except (ValueError, AttributeError):
            pass
        return HarnessResult(reported, f"exit_{done.returncode}" if done.returncode else "")


def new_session_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------- workspace and verify


@contextmanager
def workspace(repo: str, ref: str | None) -> Iterator[Path]:
    """A fresh copy of the task repo, removed afterwards: a git worktree for a git repo, else a plain copy."""
    src = Path(repo)
    parent = Path(tempfile.mkdtemp(prefix="te-eval-"))
    target = parent / "ws"
    is_git = (src / ".git").exists()
    try:
        if is_git:
            subprocess.run(
                ["git", "-C", str(src), "worktree", "add", "--detach", str(target), ref or "HEAD"],
                check=True,
                capture_output=True,
            )
        else:
            shutil.copytree(src, target, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
        yield target
    finally:
        if is_git:
            subprocess.run(["git", "-C", str(src), "worktree", "remove", "--force", str(target)], capture_output=True)
            subprocess.run(["git", "-C", str(src), "worktree", "prune"], capture_output=True)
        shutil.rmtree(parent, ignore_errors=True)


def run_verify(command: str, cwd: Path, timeout_s: float) -> bool:
    try:
        done = subprocess.run(
            command, shell=True, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout_s
        )
    except subprocess.TimeoutExpired:
        return False
    return done.returncode == 0


# ---------------------------------------------------------------- cost from the arm's own ledger


@dataclass(frozen=True)
class SessionUsage:
    cost_usd: Decimal | None  # None when a call in the session had no price row
    buckets: Buckets
    calls: int
    fired: tuple[str, ...]


class CostReader(Protocol):
    def read(self, state_dir: Path, session_id: str) -> SessionUsage: ...


class LedgerCostReader:
    """Sum the arm ledger's rows for one session; `fired` comes from the arm's decisions.jsonl."""

    def __init__(self, wait_s: float = 5.0) -> None:
        self._wait_s = wait_s  # the gateway writes a row once a response finishes, which can trail the client

    def read(self, state_dir: Path, session_id: str) -> SessionUsage:
        deadline = time.monotonic() + self._wait_s
        while True:
            usage = self._once(state_dir, session_id)
            if usage.calls or time.monotonic() >= deadline:
                return usage
            time.sleep(0.5)

    def _once(self, state_dir: Path, session_id: str) -> SessionUsage:
        path = state_dir / "ledger.sqlite"
        rows = (
            [r for r in load(SERVICES, "ledger")(str(path)).rows() if r.session_id == session_id]
            if path.exists()
            else []
        )
        parts = {k: sum(getattr(r.buckets, k) for r in rows) for k in Buckets.model_fields}
        priced = [r.cost_estimate_usd for r in rows]
        cost = None if any(c is None for c in priced) else sum((c for c in priced if c is not None), Decimal(0))
        return SessionUsage(cost, Buckets(**parts), len(rows), self._fired(state_dir / "decisions.jsonl", session_id))

    @staticmethod
    def _fired(path: Path, session_id: str) -> tuple[str, ...]:
        names: list[str] = []
        try:
            lines = path.read_text().splitlines()
        except OSError:
            return ()
        for line in lines:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("action") == "rewritten" and d.get("session_id") == session_id and d["feature"] not in names:
                names.append(str(d["feature"]))
        return tuple(names)
