# token-economics-feat-max-tokens

Hard cap on max_tokens per model.

Kind: feature. Phase: P1. May import: token-economics-contracts.

Run alone: `uv run --package token-economics-feat-max-tokens pytest features/max-tokens`

## What it does

A `Feature` and `Rewriter` (`name = "max_tokens"`, `fail_closed = False`) registered as `max_tokens`. Its `rewrite` lowers the Anthropic Messages `max_tokens` to the cap for the body's exact model id (else `default`). It never raises the value and leaves a body without an integer `max_tokens` alone. With `thinking: {"type": "enabled", "budget_tokens": B}` and a cap at or below `B` it does not rewrite, because the API requires `max_tokens > budget_tokens`. The note is metadata only, e.g. `max_tokens 64000->8192`. Other providers are left alone.

## Config

```json
{"default": null, "caps": {"<exact model id>": 8192}}
```

Model ids match exactly. Non-positive or non-integer values are ignored (no cap). Off by default, like every feature.

## Prompt cache

`max_tokens` is not part of the cached prefix on Anthropic, so lowering it does not invalidate the cache. The same body always gives the same output.

## Unverified

Not run against the live API. A lower cap can truncate a long answer (`stop_reason: max_tokens`); pick caps from the baseline's output-token distribution.
