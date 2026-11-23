# unpriced_model

Severity: ticket. Source: features/budgets: Decision code unpriced_model. Owner: see `ops/alerts.json` (currently UNASSIGNED until a person is named).

State dir below is `$TOKEN_ECONOMICS_STATE_DIR`, default `~/.token-economics`.

## What it means

A request names a model with no price row in force, so its worst-case cost cannot be capped, and budgets are set to refuse such requests (`unpriced: block`). Model ids match exactly.

## Who is affected

Callers who use that model under a budget.

## First checks

```bash
uv run token-economics prices
uv run token-economics prices --stale
uv run token-economics policy show
tail -n 20 ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/decisions.jsonl
```

## Actions

1. Check the model id is spelled as the provider sends it (exact match; a date suffix counts).
2. Add a price row for it. The price book is append-only: a price change is a new row, never an edit (see docs/P0-STATUS.md).
3. As a stopgap only, allow unpriced models in the budgets section of `policy.json` (`"unpriced": "allow"`) with the owner's agreement; spend on that model is then uncapped.

## Confirm recovery

`uv run token-economics prices` lists the model with a non-stale row and a retry succeeds.

## Escalation

The plan owner decides whether an unpriced model may run without a cap.

Kill switches and CLI verbs: see [README.md](README.md).
