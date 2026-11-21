"""Connect a harness to the gateway: one file per harness, five functions each."""

from .providers.claude_code import ADAPTER as CLAUDE_CODE
from .providers.claude_code import ClaudeCodeAdapter
from .providers.codex import ADAPTER as CODEX
from .providers.codex import CodexAdapter
from .providers.sdk import ADAPTER as SDK
from .providers.sdk import SdkAdapter

__all__ = ["CLAUDE_CODE", "CODEX", "SDK", "ClaudeCodeAdapter", "CodexAdapter", "SdkAdapter"]
