# token-economics-feat-loop-guard

Stop at the first repeated-failure signature.

Kind: feature. Phase: P1. May import: token-economics-contracts.

Run alone: `uv run --package token-economics-feat-loop-guard pytest features/loop-guard`

## What it does

A `Feature` (`name = "loop_guard"`, `fail_closed = False`) registered as `loop_guard` under the entry-point group `token_economics.features`. Before dispatch, if `ctx.facts.trailing_repeat_failures >= repeat_failures` it refuses with status 429, code `repeated_failure`. The adapter's `facts()` counts how many of the latest tool results in a row failed with the same signature (hash of tool name and input).

## Config

```json
{"repeat_failures": 2}
```

Default 2: the first repeat of the same failing call. A value that is not an integer of at least 1 falls back to 2.

## Not built

The "redirect, then stop" redirect step. This version only stops.
