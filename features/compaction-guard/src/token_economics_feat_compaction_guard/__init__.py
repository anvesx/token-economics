"""Count compactions per session and recommend a restart at the third."""

from .compaction_guard import CompactionGuard, create

__all__ = ["CompactionGuard", "create"]
