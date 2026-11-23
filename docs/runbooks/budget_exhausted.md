# budget_exhausted

Severity: ticket. Source: features/budgets: Decision code budget_exhausted (HTTP 402). Owner: see `ops/alerts.json` (currently UNASSIGNED until a person is named).

State dir below is `$TOKEN_ECONOMICS_STATE_DIR`, default `~/.token-economics`.

## What it means

A budget (key, caller, team or tenant, per day, month or total) is spent, so the gateway refuses the request with 402. This is the budget working as designed; it only fails closed.

## Who is affected

The caller, team or tenant named in the budget scope until the window resets (UTC) or the limit is raised.

## First checks

```bash
uv run token-economics budget list
tail -n 20 ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/alerts.jsonl
uv run token-economics report --days 7   # who spent it, on which model
uv run token-economics key list
```

## Actions

1. Confirm the spend is real work, not a loop: check `report` and `detect`. A runaway session is the usual cause.
2. Raise the limit if the spend is legitimate: `uv run token-economics budget set --scope caller --match <name> --window day --usd <amount>`.
3. Or wait for the window to reset (day windows reset at 00:00 UTC; month windows on the 1st).
4. Do not remove the budget to clear the alert; that removes the cap for everyone matched.

## Confirm recovery

`uv run token-economics budget list` shows spend under the limit and a retry from the caller succeeds.

## Escalation

The owner approves any raise above the agreed ceiling. Repeated exhaustion for one caller goes to their team lead.

Kill switches and CLI verbs: see [README.md](README.md).
