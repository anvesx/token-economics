# token-economics-feat-strong-share

Cap each tenant's share of strong-model calls and alert on drift. Kind: feature. Phase: P3.
May import: token-economics-contracts.

Run alone: `uv run --package token-economics-feat-strong-share pytest features/strong-share`

## What it does

Plan/05 "Strong-model ceiling" and plan/08 "Router attack": an adversarial prefix pushed routing to the strong model
73-100% of the time. This feature counts, per tenant, the calls (or spend) that went to a strong model over a rolling
window and acts when the share is over the cap.

- `after()` records each ledger row: tenant, hour, strong or not, cost. Counts are kept hourly, numbers only.
- `before()`: tenant over `max_share`, request's model is strong, `downgrade_to` is null: refuse with 429
  `strong_share_exceeded`.
- `rewrite()`: same condition with `downgrade_to` set: swap the model, note `model X->Y (strong share 0.62 > 0.50)`.
  Only at a conversation start (`facts.turns == 0`). A mid-session switch would break the prompt cache, so
  **mid-session requests are left alone** (they are counted, so the share still reflects them).
- One alert per tenant per UTC day in `alerts.jsonl` (`kind: "strong_share"`) when the share reaches `alert_at`.
- Nothing acts, and no alert fires, before `min_calls` calls are in the window.

## Config (the feature's section of `policy.json`)

| key | default | meaning |
|---|---|---|
| `strong_models` | none (required) | exact model ids; empty or missing makes the feature inert |
| `max_share` | 0.5 | cap, 0 to 1 |
| `measure` | `"calls"` | `"calls"` or `"cost"` (share of spend; rows without a price count as $0) |
| `window_hours` | 24 | rolling window, 1 to 2160 |
| `min_calls` | 50 | calls in the window before it acts |
| `downgrade_to` | null | model id to rewrite to instead of refusing |
| `alert_at` | `max_share` x 0.9 | share at which the daily alert fires |

State: `strong_share.json` in the state dir (atomic, written at most every 30 s and at once on an alert; a corrupt
file reads as empty). Fails open: a check that raises lets the request through.

## Unverified

- Defaults (0.5 share, 50 calls) are not tuned against real traffic.
- With `measure: "cost"`, the share depends on the ledger's cost estimates being priced.
