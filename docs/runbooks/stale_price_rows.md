# stale_price_rows

Severity: ticket. Source: modules/pricebook-core: 30-day staleness flag (prices --stale). Owner: see `ops/alerts.json` (currently UNASSIGNED until a person is named).

> No scheduled job emits this alert today (recorded as a gap in the report).

State dir below is `$TOKEN_ECONOMICS_STATE_DIR`, default `~/.token-economics`.

## What it means

Price rows are unverified for more than 30 days, or end within 30 days. Costs are still computed from them but may be wrong, and the 1 percent cost-accuracy gate depends on them. Today every seed row is unverified.

## Who is affected

Every cost figure and budget that uses those models.

## First checks

```bash
uv run token-economics prices --stale
uv run token-economics prices
```

## Actions

1. Compare each stale row with the vendor price page.
2. If correct: append a new row that records the new verification date. If wrong: append a corrected row from the date it changed. Never edit or delete a row.
3. Models with no row are refused when budgets are set to block unpriced models (see `unpriced_model`).

## Confirm recovery

`uv run token-economics prices --stale` lists nothing.

## Escalation

Ticket the owner; this should be a weekly check.

Kill switches and CLI verbs: see [README.md](README.md).
