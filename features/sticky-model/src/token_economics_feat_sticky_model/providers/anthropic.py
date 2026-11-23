"""Anthropic Messages bodies: the model is the top-level `model` string. Gemini, OpenAI and xAI are not built."""

from __future__ import annotations

from typing import Any

PROVIDER = "anthropic"


def model_of(body: dict[str, Any]) -> str | None:
    model = body.get("model")
    return model if isinstance(model, str) and model else None


def with_model(body: dict[str, Any], model: str) -> dict[str, Any]:
    """A copy of `body` naming `model`; the input is never changed."""
    return {**body, "model": model}
