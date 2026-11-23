# strong_share

Severity: info. Source: features/strong-share: alert kind strong_share (alerts.jsonl, early warning at alert_at). Owner: see `ops/alerts.json` (currently UNASSIGNED until a person is named).

State dir below is `$TOKEN_ECONOMICS_STATE_DIR`, default `~/.token-economics`.

## What it means

A tenant's strong-model share reached `alert_at` (default 90% of `max_share`). One alert per tenant per UTC day. Nothing is refused yet.

## Who is affected

The tenant named in the alert, who may hit `strong_share_exceeded` soon.

## First checks

```bash
tail -n 20 ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/alerts.jsonl
uv run token-economics policy show
uv run token-economics report --days 1
```

## Actions

1. Tell the tenant's owner, and check for a runaway session on a strong model.
2. Raise `max_share` if the work is legitimate (see `strong_share_exceeded`).

## Confirm recovery

No further `strong_share` alert for the tenant next day, or the ceiling is raised.

## Escalation

Info level: no page.

Kill switches and CLI verbs: see [README.md](README.md).
