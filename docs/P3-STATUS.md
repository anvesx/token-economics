# P3 status: working core

Branch `feat/p3-working-core` (on top of `feat/p2-working-core`), 2026-11-23. P3 is "harden". First pass. **The P3
exit gate is not met**: there are no shipped P2 optimisations to wrap, the security review is not done by a second
person, and alerts have no named owners. Decisions: `docs/adr/0004`.

## What runs today
- Kill switch per feature and tenant (`kill.json`; `token-economics policy kill|unkill|kills`; admin API
  `/api/kills`). Hot-reloaded; a killed feature sends the client's original bytes.
- Per-tenant modes and session canaries in `policy.json` (`policy canary <feature> --share S [--tenants a,b]`).
- Auto-rollback (`token-economics rollout check`, `token-economics-worker`): cost, errors, success (with
  `outcomes.jsonl`), cache hit, billing (with `reconciliation.jsonl`). One drill per trigger plus an end-to-end drill on
  a real gateway: after the check, the next request reaches the provider unchanged, no deploy.
- Admin API roles (viewer, operator, admin) on bearer tokens hashed at rest; second approver for policy and
  price-book changes; audit of every change; refuses to listen off localhost without `--require-auth`.
- Retention of metadata logs per tenant (`retention.json`); never the ledger, price book or audit log.
- Features: `strong_share` (per-tenant strong-model ceiling: refuse, or downgrade at session start), `anomaly` (spend
  per caller against its median and MAD), `tier_selector` (service tier by rule).
- Ops: `tools/loadtest.py`, `tools/backup.py` (backup, verify, restore) with a DR drill test, `ops/alerts.json` and
  one runbook per alert in `docs/runbooks/`, `tools/check_alerts.py` in CI.
- Security test: provider keys, OAuth tokens, virtual keys and prompt text sent through the real gateway (with a
  rewrite and shadow on) appear in no file of the state dir.
- Checks: ruff, mypy --strict, 635 tests, 53 tool tests, layering (45 contracts), surface, every package passes alone
  (extractable).

## Exit gate (PHASES.md)
| Gate line | Status |
|---|---|
| A rollback drill reverts a bad optimisation without a deploy | Shown on the fake provider, one drill per trigger. Not on real traffic |
| A load test holds the gateway latency budget set in P0 | No budget was set in P0. Measured added p95 TTFB 3-6 ms at concurrency 5 on one machine; proposed budget 15 ms (`docs/ops/load-test.md`), **owner to confirm** |
| Security review closed; no prompt content stored by default | Storage scan passes. **Review by a second person not done** |
| A named owner for each alert | **Not met**: 19 alerts, all `UNASSIGNED` in `ops/alerts.json` |

## Not built
- Reconciler and its weekly canary (needs the provider's usage and cost API key): the billing trigger has no input.
- A writer for `outcomes.jsonl` (task success in production).
- Secrets manager integration and key rotation schedules; TLS; brute-force limits on the admin API.
- Health-checked gateway bypass; fallback route (P1 items still open).
- Latency recorded per request, so the p95 latency rollback trigger cannot run.
- Papers T10-T13, T14 outline; tag v1.0.0.

## Things a reviewer should know
- The load test runs gateway, fake provider and client in one Python process; at concurrency 50 the numbers are the
  harness queueing, not the gateway. Rerun with the gateway in its own process before trusting a budget.
- Rollback thresholds (`rollout.json`) are placeholders. Repeated checks accumulate false alarms; keep levels strict.
- Retention can lose a log line appended in the instant of its file replace (the gateway takes no lock it can share).
- A policy change approved through the admin API is written before its approval row commits; a crash between the two
  leaves the new policy without the approval record.
- `strong_share` refuses mid-session strong-model calls once a tenant is over its share when no downgrade is set.
- The backup tool was run read-only once against the real `~/.token-economics` by the builder (3 ledger rows, 12 price
  rows, 2 keys verified); nothing there was changed.
