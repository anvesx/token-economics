# ADR 0004: canaries by session, kill switches in a file, rollback by comparing canary with control

Status: proposed (2026-11-23).

## Decision
1. **Kill switches live in `kill.json`, beside `policy.json`**, not inside it. People (CLI, admin API) and the
   auto-rollback job write it through one writer (`services/rollout/kill.py`: file lock, atomic replace, audit). The
   policy engine re-reads it when it changes, so a kill takes effect on the next request with no deploy. A killed
   feature leaves the request byte for byte as the client sent it (tested end to end).
2. **A broken `kill.json` is never overwritten** by a writer, and the engine treats it as "no kills" and logs it.
   The rollback job reports it and takes no action.
3. **Per-tenant modes and canaries are part of a feature's policy section** (`tenants`, `canary`), read by the engine,
   never passed to the feature. The order per request: killed → off; else the tenant's mode, else the section's;
   then the canary slice.
4. **A canary covers whole sessions**: `canary_slot(session_id, feature) < share` (contracts). Mid-session changes
   break the prompt cache, so a session is either in or out for its whole life. Different features draw different
   slices. The rollback job recomputes the same function to split canary from control.
5. **Rollback compares canary sessions with control sessions of the same tenants**, on ledger rows. Cost fires when
   the bootstrap interval of the difference in mean session cost lies above zero (both samples' noise counted);
   errors need a margin and a significant two-proportion test; success only with an outcomes file; cache hit by a
   margin; billing divergence (from a reconciliation file) kills every canaried feature. p95 latency is not checked:
   the ledger records no latency.
6. **Admin API fails closed off localhost**: it refuses to listen on another address without `--require-auth`. Once
   any admin token exists, every `/api` route needs one; revoking the last token does not reopen it.

## Why
- PHASES P3: one kill switch per optimisation and tenant, auto-rollback without a deploy, drills per trigger.
- Comparing a canary's mean with the control's interval alone fires on about a third of healthy 5% canaries, which a
  job running every few minutes would turn into a steady stream of false kills.

## Consequences and open points
- The rollback job runs repeatedly over a sliding window, so false alarms accumulate over days; thresholds in
  `rollout.json` are DevX placeholders until P2 measures real variance.
- Success has no production signal yet; `outcomes.jsonl` (from CI or hooks) and `reconciliation.jsonl` (from the
  reconciler, not built) are formats waiting for writers.
- Retention trims metadata logs only. Ledger retention conflicts with the append-only rule: a decision for the owner.
