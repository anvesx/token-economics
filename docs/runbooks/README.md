# Runbooks

One runbook per alert in `ops/alerts.json`. `uv run python tools/check_alerts.py` fails when an alert has no runbook, or when the code emits a refusal or alert with no entry. Add `--require-owners` for the P3 gate: a named person per alert (every owner is `UNASSIGNED` today; the plan owner must name them).

| Alert | Severity | What it is |
|---|---|---|
| [gateway_down](gateway_down.md) | page | The gateway does not answer on its port. |
| [budget_exhausted](budget_exhausted.md) | ticket | A budget (key, caller, team or tenant, per day, month or total) is spent, so the gateway refuses the request with 402. |
| [budget_threshold](budget_threshold.md) | info | A budget crossed a warning line (default 75%, 90%, 100%) or blocked a request. |
| [unpriced_model](unpriced_model.md) | ticket | A request names a model with no price row in force, so its worst-case cost cannot be capped, and budgets are set to refuse such requests (`unpriced: block`). |
| [turn_cap_reached](turn_cap_reached.md) | info | A conversation reached the configured turn cap for its model, so the next request is refused with 429. |
| [repeated_failure](repeated_failure.md) | info | The same tool call failed several times in a row with the same input, so the gateway refuses the next request to stop a loop that burns tokens. |
| [compaction_limit](compaction_limit.md) | info | A session was compacted so many times that the guard refuses more requests; each compaction rewrites the cache and loses detail. |
| [policy_unavailable](policy_unavailable.md) | page | A feature that fails closed (budgets) raised an error in enforced mode, so the gateway refused the request with 503 rather than let spend go uncapped. |
| [feature_error](feature_error.md) | ticket | A policy feature raised an exception. |
| [key_revoked](key_revoked.md) | info | A request used a virtual key that was revoked, so the gateway refuses it with 401. |
| [strong_share_exceeded](strong_share_exceeded.md) | ticket | A tenant's share of calls (or spend) on strong models is over `max_share` in the last `window_hours`, so strong-model requests are refused with 429 (when `downgrade_to` is unset) or rewritten to a cheaper model at conversation start. |
| [strong_share](strong_share.md) | info | A tenant's strong-model share reached `alert_at` (default 90% of `max_share`). |
| [spend_anomaly](spend_anomaly.md) | page | A caller's spend today is far above their own trailing baseline (robust z-score on daily spend), or one session alone spent over `session_usd`. |
| [cache_hit_rate](cache_hit_rate.md) | ticket | A caller's cache hit rate over the recent window fell below the configured `alert_below`. |
| [rollback](rollback.md) | page | A feature was switched off automatically because success fell below the floor, cost per success rose above the baseline interval, the hit rate dropped, or billed cost diverged from the estimate. |
| [shadow_spend_cap](shadow_spend_cap.md) | ticket | Shadow runs (a mirrored session sent through a candidate policy) spent their `max_usd_per_day` cap, so sampling stops until 00:00 UTC. |
| [stale_price_rows](stale_price_rows.md) | ticket | Price rows are unverified for more than 30 days, or end within 30 days. |
| [reconciliation_divergence](reconciliation_divergence.md) | ticket | The vendor's billed cost differs from the gateway's estimate by more than the agreed margin (1 percent target). |
| [backend_degraded](backend_degraded.md) | ticket | A provider backend failed (429 or 5xx) often enough in the last five minutes to be marked degraded. |

## Commands used in every runbook

```bash
curl -s 127.0.0.1:8787/_te/health        # gateway up? policy problems? backend health
curl -s 127.0.0.1:8787/_te/stats         # rows written, duplicates, rejects since start
uv run token-economics policy show      # every feature and its mode
uv run token-economics policy kills     # kill switches in force (P3)
uv run token-economics policy kill <feature> [--tenant <t>]   # stop one optimisation now (P3)
uv run token-economics policy mode <feature> off|advisory|enforced
uv run token-economics budget list
uv run token-economics key list
uv run token-economics report --days 1
uv run token-economics-gateway --port 8787   # restart
```

`policy kill <feature> [--tenant T] [--reason R]`, `policy unkill <feature> [--tenant T]` and `policy kills` write and read `kill.json`; the gateway re-reads it on the next request, so no restart or deploy is needed. `policy canary <feature> --share S` and `--off` manage canaries; `rollout check` runs the auto-rollback check by hand.

Every alert, kill and key change is also in the audit log: `sqlite3 $STATE/tenancy.sqlite "select ts, actor, action, subject from audit order by ts desc limit 20"`.

Related: [load test](../ops/load-test.md), [disaster recovery](../ops/disaster-recovery.md).
