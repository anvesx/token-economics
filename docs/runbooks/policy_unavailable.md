# policy_unavailable

Severity: page. Source: services/policy: Decision code policy_unavailable (HTTP 503). Owner: see `ops/alerts.json` (currently UNASSIGNED until a person is named).

State dir below is `$TOKEN_ECONOMICS_STATE_DIR`, default `~/.token-economics`.

## What it means

A feature that fails closed (budgets) raised an error in enforced mode, so the gateway refused the request with 503 rather than let spend go uncapped. This is the only fail-closed path.

## Who is affected

Every request that the failing feature would check, which can mean the whole tenant.

## First checks

```bash
curl -s 127.0.0.1:8787/_te/health   # look at policy_problems
tail -n 30 ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/decisions.jsonl   # find outcome=blocked, code feature_error
ls -la ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/budgets.sqlite*; df -h ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}
uv run token-economics budget list   # fails the same way if the budget store is broken
```

## Actions

1. Find the failing feature in the decisions log and its `detail` (exception type).
2. Common causes: `budgets.sqlite` locked or corrupt, disk full, unreadable `policy.json`. Fix the cause and the next request recovers (no restart needed unless the file is corrupt).
3. If the budget store is corrupt, restore it from the last backup (docs/ops/disaster-recovery.md) after stopping the gateway.
4. Last resort, with the plan owner's sign-off: `uv run token-economics policy mode budgets advisory` stops the refusals but removes the spend cap. Put it back to `enforced` once fixed.

## Confirm recovery

`curl -s 127.0.0.1:8787/_te/health` shows empty `policy_problems`, `budget list` works, and a request through the gateway is allowed.

## Escalation

Page the alert owner in `ops/alerts.json`. If there is no answer in 15 minutes, go to the plan owner. Treat any time spent in advisory mode for budgets as an incident.

Kill switches and CLI verbs: see [README.md](README.md).
