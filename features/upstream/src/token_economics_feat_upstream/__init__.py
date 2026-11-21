"""Send the request upstream unchanged: one file per provider."""

from .providers.anthropic import SECRET_HEADERS as SECRET_HEADERS
from .providers.anthropic import UPSTREAM as ANTHROPIC
from .providers.anthropic import AnthropicUpstream
from .providers.openai import UPSTREAM as OPENAI
from .providers.openai import OpenAIUpstream

__all__ = ["ANTHROPIC", "OPENAI", "SECRET_HEADERS", "AnthropicUpstream", "OpenAIUpstream"]
