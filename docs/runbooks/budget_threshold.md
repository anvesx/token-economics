# budget_threshold

Severity: info. Source: features/budgets: alerts.jsonl record (threshold 0.75, 0.9, 1 or blocked). Owner: see `ops/alerts.json` (currently UNASSIGNED until a person is named).

State dir below is `$TOKEN_ECONOMICS_STATE_DIR`, default `~/.token-economics`.

## What it means

A budget crossed a warning line (default 75%, 90%, 100%) or blocked a request. One line is written per budget slot and line per window. Nothing is refused yet unless the threshold is `blocked`.

## Who is affected

The caller, team or tenant in `scope`, who may be refused soon.

## First checks

```bash
tail -n 20 ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/alerts.jsonl
uv run token-economics budget list
uv run token-economics report --days 1
```

## Actions

1. At 0.75 and 0.9: tell the owner of the budget; check for a loop (`uv run token-economics detect`).
2. Raise the limit before it blocks if the work is legitimate: `uv run token-economics budget set --scope <scope> --match <name> --window <win> --usd <amount>`.
3. At `blocked`, follow the `budget_exhausted` runbook.

## Confirm recovery

`budget list` shows the used share falling after a reset or rising more slowly after the fix.

## Escalation

Info level: no page. Escalate to the owner at 0.9 for a tenant-wide budget.

Kill switches and CLI verbs: see [README.md](README.md).
