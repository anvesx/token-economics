# spend_anomaly

Severity: page. Source: features/anomaly: alert kind spend_anomaly, and Decision code spend_anomaly (HTTP 429) when block is on. Owner: see `ops/alerts.json` (currently UNASSIGNED until a person is named).

State dir below is `$TOKEN_ECONOMICS_STATE_DIR`, default `~/.token-economics`.

## What it means

A caller's spend today is far above their own trailing baseline (robust z-score on daily spend), or one session alone spent over `session_usd`. Causes: a runaway agent, a leaked key, or a wrong price row. With `block` true the caller is also refused with 429 `spend_anomaly` for the rest of the UTC day.

## Who is affected

The caller in the alert; the whole budget if it is a leaked key.

## First checks

```bash
tail -n 20 ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/alerts.jsonl
uv run token-economics report --days 1
uv run token-economics key list
uv run token-economics budget list
uv run token-economics detect --days 1
```

## Actions

1. Find the caller, session and model driving the spend (`report`, `detect`).
2. If it is a runaway or leaked key: revoke it now (`uv run token-economics key revoke <key_id>`).
3. If the alert is a false positive for a known burst, tune it: `uv run token-economics policy set anomaly k <n>` or `min_usd`; to stop alerts and refusals: `uv run token-economics policy kill anomaly`.
4. Cap the damage while you look: set a low day budget for that caller (`uv run token-economics budget set --scope caller --match <name> --window day --usd <amount>`).
5. If a price row is wrong, compare `uv run token-economics prices` with the vendor price page and add a corrected row (append-only).

## Confirm recovery

Spend per hour in `report` is back to baseline and no new `spend_anomaly` lines appear.

## Escalation

Page the alert owner in `ops/alerts.json`. If there is no answer in 15 minutes, go to the plan owner. Tell security if a key leaked.

Kill switches and CLI verbs: see [README.md](README.md).
