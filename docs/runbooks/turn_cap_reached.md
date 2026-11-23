# turn_cap_reached

Severity: info. Source: features/turn-cap: Decision code turn_cap_reached (HTTP 429). Owner: see `ops/alerts.json` (currently UNASSIGNED until a person is named).

State dir below is `$TOKEN_ECONOMICS_STATE_DIR`, default `~/.token-economics`.

## What it means

A conversation reached the configured turn cap for its model, so the next request is refused with 429. The developer should start a fresh session.

## Who is affected

One developer session at a time.

## First checks

```bash
uv run token-economics policy show
uv run token-economics report --days 1
```

## Actions

1. Normal case: the developer starts a new session. No action.
2. If many callers hit it: the cap is too low. Raise it with `uv run token-economics policy set turn_cap default <n>` (or the per-model cap).
3. If it is blocking real work and cannot be tuned quickly: `uv run token-economics policy kill turn_cap`.

## Confirm recovery

`uv run token-economics policy show` shows the new cap; a retry in the same session succeeds.

## Escalation

Info level. Tell the owner if more than a handful of callers are affected in a day.

Kill switches and CLI verbs: see [README.md](README.md).
