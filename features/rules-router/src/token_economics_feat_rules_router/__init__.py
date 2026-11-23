"""Route a session to a model by rules, at session start, and keep it there."""

from .rules_router import RulesRouter, create

__all__ = ["RulesRouter", "create"]
