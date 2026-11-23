# token-economics-feat-observation-masking

Mask old tool results above a trigger, in steps that keep the cached prefix stable.

Kind: feature. Phase: P2. May import: token-economics-contracts.

Run alone: `uv run --package token-economics-feat-observation-masking pytest features/observation-masking`

## What it does

A `Feature` and `Rewriter` (`name = "observation_masking"`, `fail_closed = False`). Its `rewrite` replaces the content of old `tool_result` blocks in Anthropic Messages bodies with `[token-economics: tool result masked, N characters]`, keeping `tool_use_id`, `type` and `is_error`. Events are the `tool_result` blocks in message order, `n` in all. With `n <= min_events` nothing changes. Otherwise `boundary = ((n - keep) // step) * step` and results with index below the boundary are masked, except results of protected tools, error results, and results no longer than the marker itself. The note is counts only: `masked 20 of 31 tool results, 400000 chars`.

## Config

```json
{"min_events": 10, "keep": 5, "step": 10,
 "protect_tools": ["Read", "Edit", "MultiEdit", "Write", "NotebookEdit", "NotebookRead"]}
```

Bad values fall back to defaults. plan/06 finds masking negative at 7 or fewer events, hence the default trigger above 10.

## Prompt cache

The boundary moves only every `step` events, so between moves the masked prefix is byte-identical from one turn to the next and the provider's cache keeps hitting; only the step itself rewrites the prefix. A test proves it (turns with 15 and 16 events share the same masked prefix).

## Unverified

Not run against a live session or the eval harness. Whether masking at these defaults helps or hurts task success and cost is for the P2 eval to show.
