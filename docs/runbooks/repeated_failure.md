# repeated_failure

Severity: info. Source: features/loop-guard: Decision code repeated_failure (HTTP 429). Owner: see `ops/alerts.json` (currently UNASSIGNED until a person is named).

State dir below is `$TOKEN_ECONOMICS_STATE_DIR`, default `~/.token-economics`.

## What it means

The same tool call failed several times in a row with the same input, so the gateway refuses the next request to stop a loop that burns tokens.

## Who is affected

One developer session at a time.

## First checks

```bash
uv run token-economics policy show
uv run token-economics detect --days 1
```

## Actions

1. Normal case: the developer changes the approach, as the refusal message says.
2. If it fires on healthy work (false positive): raise the threshold with `uv run token-economics policy set loop_guard repeat_failures <n>`.
3. If it is blocking many callers: `uv run token-economics policy kill loop_guard`.

## Confirm recovery

A retry with a changed approach succeeds; `policy show` shows the guard in the intended mode.

## Escalation

Info level. Report a false-positive pattern to the owner so the threshold can be tuned.

Kill switches and CLI verbs: see [README.md](README.md).
