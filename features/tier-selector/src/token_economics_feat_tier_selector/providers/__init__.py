"""Per-provider tier values. Gemini is listed in the layout but not built: its requests are never rewritten."""

from . import anthropic, openai

ALLOWED_BY_PROVIDER = {"anthropic": anthropic.ALLOWED, "openai": openai.ALLOWED}

__all__ = ["ALLOWED_BY_PROVIDER"]
