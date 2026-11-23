# rollback

Severity: page. Source: services/rollout: auto-rollback event (kill.json, audit log). Owner: see `ops/alerts.json` (currently UNASSIGNED until a person is named).

> The emitting package and CLI verbs were still being built when this runbook was written. Confirm them with `uv run token-economics policy --help`.

State dir below is `$TOKEN_ECONOMICS_STATE_DIR`, default `~/.token-economics`.

## What it means

A feature was switched off automatically because success fell below the floor, cost per success rose above the baseline interval, the hit rate dropped, or billed cost diverged from the estimate. Built in P3; the alert name is reserved here.

## Who is affected

Callers in the rolled-back feature's tenant and canary.

## First checks

```bash
uv run token-economics policy kills
cat ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/kill.json
sqlite3 ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/tenancy.sqlite "select ts, actor, action, subject, detail from audit order by ts desc limit 20"
uv run token-economics policy show
```

## Actions

1. Read the trigger in the audit entry. The feature is already off for the tenant: confirm with `policy kills`.
2. Do not turn it back on until the owner has looked at the evidence (shadow pairs under `shadow/`, `uv run token-economics report`).
3. To re-enable after a fix: remove the kill (`uv run token-economics policy unkill <feature>`), then step through advisory before enforced.

## Confirm recovery

`policy kills` lists the feature, and the trigger metric returns to its normal range in the next report.

## Escalation

Page the alert owner in `ops/alerts.json`. If there is no answer in 15 minutes, go to the plan owner. The rollback is the system working; the question is why the feature was bad.

Kill switches and CLI verbs: see [README.md](README.md).
