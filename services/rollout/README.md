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
