"""Cap oversized tool results before they are sent, never cutting tracebacks or edit anchors."""

from .output_cap import DEFAULT_PROTECT_PATTERNS, DEFAULT_PROTECT_TOOLS, OutputCap, create

__all__ = ["DEFAULT_PROTECT_PATTERNS", "DEFAULT_PROTECT_TOOLS", "OutputCap", "create"]
