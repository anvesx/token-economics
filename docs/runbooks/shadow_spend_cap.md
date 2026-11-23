# shadow_spend_cap

Severity: ticket. Source: services/rollout/shadow.py: daily shadow spend cap. Owner: see `ops/alerts.json` (currently UNASSIGNED until a person is named).

> No code emits this alert today (recorded as a gap in the report).

State dir below is `$TOKEN_ECONOMICS_STATE_DIR`, default `~/.token-economics`.

## What it means

Shadow runs (a mirrored session sent through a candidate policy) spent their `max_usd_per_day` cap, so sampling stops until 00:00 UTC. Real traffic is not affected. Today sampling stops silently; there is no emitter yet, so check the shadow report.

## Who is affected

Nobody directly. The evidence for the candidate feature gets thinner.

## First checks

```bash
cat ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/shadow/shadow.json
uv run token-economics report --days 1
ls -la ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/shadow/
```

## Actions

1. Check the spend is what you expected for the sample `share`.
2. Raise `max_usd_per_day` in `${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/shadow/shadow.json`, or lower `share`, or set `enabled` to false.
3. Do not delete files under `shadow/`; the ledger there is append-only.

## Confirm recovery

The shadow report shows new pairs the next day, and spend stays under the cap.

## Escalation

Ticket the owner of the feature under test.

Kill switches and CLI verbs: see [README.md](README.md).
