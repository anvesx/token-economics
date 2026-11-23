# reconciliation_divergence

Severity: ticket. Source: services/eval / P3 auto-rollback: billed cost vs gateway estimate. Owner: see `ops/alerts.json` (currently UNASSIGNED until a person is named).

> No code emits this alert today (recorded as a gap in the report).

State dir below is `$TOKEN_ECONOMICS_STATE_DIR`, default `~/.token-economics`.

## What it means

The vendor's billed cost differs from the gateway's estimate by more than the agreed margin (1 percent target). Either a price row is wrong, a usage field is unmapped, or the gateway is missing traffic.

## Who is affected

Every cost report and budget, until the cause is found.

## First checks

```bash
uv run token-economics prices --stale
uv run token-economics report --days 7
tail -n 20 ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/rejects.jsonl   # responses that produced no ledger row
curl -s 127.0.0.1:8787/_te/health | head -c 600
```

## Actions

1. Compare per model and per day: which model drifts?
2. Check for stale or wrong price rows first (most common), then for rejects (unknown usage keys), then for traffic that bypasses the gateway.
3. Fix by appending a corrected price row. Past ledger rows are not edited; the bill is reconciled in reports.

## Confirm recovery

The next reconciliation is within the margin for every model.

## Escalation

Ticket the owner. Escalate to the plan owner if the gap is over 5 percent.

Kill switches and CLI verbs: see [README.md](README.md).
