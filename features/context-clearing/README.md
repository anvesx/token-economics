# token-economics-feat-context-clearing

Ask the provider to clear old tool uses server-side (context management).

Kind: feature. Phase: P2. May import: token-economics-contracts.

Run alone: `uv run --package token-economics-feat-context-clearing pytest features/context-clearing`

## What it does

A `Feature` and `Rewriter` (`name = "context_clearing"`, `fail_closed = False`) registered as `context_clearing`. For an Anthropic Messages body it adds `context_management` with one edit and the beta header, so the provider drops old tool results once the prompt passes the trigger. It does nothing for other providers, for a body that already has `context_management`, or (when `models` is set) for other model ids. `before` and `after` do nothing. The rewrite copies the body and never mutates the input; the same input gives the same output.

## Config

```json
{"trigger": 35000, "keep": 5, "clear_at_least": 4000, "exclude_tools": [],
 "edit_type": "clear_tool_uses_20250919", "beta": "context-management-2025-06-27", "models": []}
```

- `trigger`: prompt tokens at which clearing starts (plan: 30-40k).
- `keep`: most recent tool uses left intact.
- `clear_at_least`: tokens a clear must free to be worth it (plan: 3-5k), because a clear invalidates the cached prefix.
- `exclude_tools`: tools whose results cannot be re-fetched; never cleared.
- `models`: exact model ids; empty means all.

Invalid values fall back to the default. Decisions log notes are numbers only.

## Cache interaction

Clearing rewrites the prefix at the point it fires, so that turn pays a cache write. `clear_at_least` keeps it from firing for small gains.

## Unverified

Every API name here is a configurable guess from the plan and has not been checked against the live API: the edit type, the beta header value, and the field names. Claude Code over a subscription login may not accept the beta header at all. Verify before enabling in `enforced`.
