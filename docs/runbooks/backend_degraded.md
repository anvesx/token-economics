# backend_degraded

Severity: ticket. Source: services/health: backend health tracker (/_te/health backends). Owner: see `ops/alerts.json` (currently UNASSIGNED until a person is named).

State dir below is `$TOKEN_ECONOMICS_STATE_DIR`, default `~/.token-economics`.

## What it means

A provider backend failed (429 or 5xx) often enough in the last five minutes to be marked degraded. This is the provider having trouble, not the gateway, but developers will see errors.

## Who is affected

Callers using that provider.

## First checks

```bash
curl -s 127.0.0.1:8787/_te/health   # the backends section
tail -n 20 ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/rejects.jsonl
curl -s https://status.anthropic.com/api/v2/status.json | head -c 400
```

## Actions

1. Check the provider's status page.
2. If it is rate limiting (429): look at `requests_remaining` in the health output and at who is using the most (`report --days 1`).
3. Nothing in the gateway needs switching off. If an optimisation that changes requests is suspected, `uv run token-economics policy kill <feature>`.

## Confirm recovery

The backend returns to healthy in `/_te/health` within a few minutes of the provider recovering.

## Escalation

Ticket the owner; page if it lasts more than 30 minutes.

Kill switches and CLI verbs: see [README.md](README.md).
