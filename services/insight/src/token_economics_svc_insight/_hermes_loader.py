"""Import the vendored hermes modules without changing them and without leaving them importable.

The vendored files are flat scripts that import each other by bare name (`import leak_extra`), and
`leak_config` reads CC_METRICS_DIR when it is imported to decide where its config and cache live.
So for each state directory this loader:

  1. puts the `hermes/` folder first on sys.path and sets CC_METRICS_DIR to the state directory,
  2. imports the modules under their bare names,
  3. removes those names from sys.modules again and restores sys.path and the environment.

The returned modules keep working because they hold references to each other. Each state directory
gets its own set of modules (the setting is read once at import), cached for the life of the process.

This is the one place where untyped legacy code enters this package: everything on `HermesModules`
is `Any`. Keep other code from reaching into the vendored modules except through `detectors.py`.
"""

from __future__ import annotations

import importlib
import os
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

HERMES_DIR = Path(__file__).resolve().parent / "hermes"
_NAMES = ("leak_config", "leak_extra", "leak_categories", "prompt_check", "leak_report")
_ENV = "CC_METRICS_DIR"

_lock = threading.RLock()
_cache: dict[Path, HermesModules] = {}


@dataclass(frozen=True)
class HermesModules:
    """The vendored modules, untyped on purpose (they are legacy code we do not annotate)."""

    leak_report: Any
    leak_extra: Any
    leak_categories: Any
    leak_config: Any
    prompt_check: Any
    state_dir: Path


def load_hermes(state_dir: Path) -> HermesModules:
    """The vendored modules bound to `state_dir` (created if missing). Nothing is read from ~/.claude/metrics."""
    key = Path(state_dir).resolve()
    with _lock:
        if key not in _cache:
            key.mkdir(parents=True, exist_ok=True)
            _cache[key] = _import(key)
        return _cache[key]


def _import(state_dir: Path) -> HermesModules:
    saved_path = list(sys.path)
    saved_env = os.environ.get(_ENV)
    shadowed: dict[str, ModuleType] = {n: sys.modules.pop(n) for n in _NAMES if n in sys.modules}
    try:
        sys.path.insert(0, str(HERMES_DIR))
        os.environ[_ENV] = str(state_dir)
        loaded: dict[str, Any] = {n: importlib.import_module(n) for n in _NAMES}
    finally:
        sys.path[:] = saved_path
        if saved_env is None:
            os.environ.pop(_ENV, None)
        else:
            os.environ[_ENV] = saved_env
        for n in _NAMES:
            sys.modules.pop(n, None)
        sys.modules.update(shadowed)
    mods = HermesModules(state_dir=state_dir, **loaded)
    if Path(mods.leak_config.METRICS_DIR).resolve() != state_dir:  # pragma: no cover - guards the isolation promise
        raise RuntimeError(f"vendored leak_config is not bound to {state_dir}: {mods.leak_config.METRICS_DIR}")
    return mods
