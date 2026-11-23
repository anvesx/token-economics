# token-economics-svc-rollout

Shadow runs on mirrored traffic with write isolation; later canary, kill-switch and rollback.

Kind: service. Phase: P2. May import: token-economics-contracts, token-economics-stats.

Run alone: `uv run --package token-economics-svc-rollout pytest services/rollout`

## Shadow

`open_shadow(state_dir)` returns a `ShadowSampler` (registered as the service `shadow`). The gateway asks
`sample(ctx)`; when it says yes, it sends a mirror of the request through the candidate policy
(`<state_dir>/shadow/policy.json`) and reports both sides with `record(ctx, side, row, status)`.

Config `<state_dir>/shadow/shadow.json`, re-read when it changes; a missing file means disabled:

```json
{"enabled": false, "share": 0.0, "tenants": [], "harnesses": [], "max_usd_per_day": "5.00"}
```

Empty lists mean all. Sampling is deterministic per conversation (sha256 of the session id, or of the request id when
there is none), so a whole session is mirrored or none of it. Once today's (UTC) shadow spend reaches
`max_usd_per_day`, sampling stops until the next day. Shadow roughly doubles spend for the sampled share, so keep
`share` small and the cap low.

Both sides append metadata (ids, model, status, cost, bucket totals; no prompt or response text) to
`<state_dir>/shadow/pairs.jsonl`. `report()` joins them on request id: pairs, unmatched per side, total / per-model /
median / P95 cost per side, shadow-over-primary cost ratio over matched pairs, shadow errors where the primary
succeeded, and today's spend against the cap.

### What shadow can and cannot tell you

- A mirrored single request is a one-step shadow. The candidate never runs its own tool loop, so shadow measures
  per-call cost and errors, not whether the task succeeds. Task success comes from the eval harness.
- Write isolation: the shadow row goes to a separate ledger (`<state_dir>/shadow/ledger.sqlite`), never touches a
  budget, and the response is discarded, never returned to the client.
- Spend: sampled by `share` and capped per day by `max_usd_per_day`.
- Nothing here raises into the request path: a broken config means disabled, a failed write is dropped.

## Auto-rollback

`open_rollback(state_dir)` returns a `RollbackChecker` (service `rollback`; the worker and `token-economics rollout check`
call `check()`). For every feature in `policy.json` with a `canary` that is not already killed, it takes the last
`window_hours` of ledger rows and splits the sessions: canary (`canary_slot(session, feature) < share`, tenant listed
if the canary lists tenants, tenant mode not off) against control (the other sessions of the same tenants). Rows
without a session id are ignored. A trigger needs at least `min_sessions` sessions per side, else "insufficient data"
and no action.

| trigger | fires when |
|---|---|
| `cost` | mean cost per session in the canary is above the upper end of the control's seeded 95% bootstrap interval |
| `errors` | share of non-2xx rows in the canary is above the control's plus `error_margin` (success proxy) |
| `success` | only with `outcomes.jsonl` (`{"session_id", "success"}`): canary rate below control minus `success_drop_pp` |
| `cache_hit` | canary cache_read over prompt tokens below the control's minus `hit_drop` |
| `billing` | only with `reconciliation.jsonl` (`{"date", "provider", "billed_usd", "estimated_usd"}`): the latest line is off by more than `billing_tolerance`; every canaried feature is killed |

p95 latency is not checked: the ledger has no latency, and `check()` says so in each result. The thresholds are DevX
proposals in `<state>/rollout.json` (all optional): `window_hours` 24, `min_sessions` 30, `error_margin` 0.02,
`success_drop_pp` 5, `hit_drop` 0.10, `billing_tolerance` 0.05, `level` 0.95, `n_boot` 1000, `seed` 0.

A breach calls the kill switch (`by = "rollback:<trigger>"`, reason holds the numbers), appends a line to
`rollbacks.jsonl` and an alert (`kind: "rollback"`) to `alerts.jsonl`. A second check finds the feature killed and does
nothing. `check()` returns one dict per canaried feature (`status`, `sessions`, `triggers`, `action`: none, killed,
already_killed or error, `problems`) and never raises on unreadable files; it reports them. A broken `kill.json` is
never overwritten. The drills: one unit test per trigger, and `tests/integration/test_rollback.py` reverts a rewrite on
a real gateway.
