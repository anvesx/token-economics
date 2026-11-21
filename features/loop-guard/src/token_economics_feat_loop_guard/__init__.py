"""Stop at the first repeated-failure signature."""

from .loop_guard import LoopGuard, create

__all__ = ["LoopGuard", "create"]
