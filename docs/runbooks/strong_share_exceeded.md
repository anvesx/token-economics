# strong_share_exceeded

Severity: ticket. Source: features/strong-share: Decision code strong_share_exceeded (HTTP 429). Owner: see `ops/alerts.json` (currently UNASSIGNED until a person is named).

State dir below is `$TOKEN_ECONOMICS_STATE_DIR`, default `~/.token-economics`.

## What it means

A tenant's share of calls (or spend) on strong models is over `max_share` in the last `window_hours`, so strong-model requests are refused with 429 (when `downgrade_to` is unset) or rewritten to a cheaper model at conversation start.

## Who is affected

The tenant over its ceiling; developers there see 429 on strong models.

## First checks

```bash
uv run token-economics policy show
uv run token-economics report --days 7   # spend by model
tail -n 20 ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/alerts.jsonl
cat ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/strong_share.json | head -c 600
```

## Actions

1. Check whether the tenant legitimately needs more strong-model work (a launch, a migration).
2. Raise the ceiling: `uv run token-economics policy set strong_share max_share <0..1>`; or set `downgrade_to` to a cheaper model id so requests are rewritten instead of refused.
3. If it is refusing work wrongly: `uv run token-economics policy kill strong_share --tenant <tenant>` (or `policy mode strong_share off`).

## Confirm recovery

`policy show` shows the new ceiling, the tenant's share in `strong_share.json` falls under it as the window rolls, and a strong-model request succeeds.

## Escalation

The plan owner approves permanent ceiling changes.

Kill switches and CLI verbs: see [README.md](README.md).
