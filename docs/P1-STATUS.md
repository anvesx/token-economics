# P1 status: working core

Branch `feat/p1-working-core`, 2026-11-21. P1 is "enforce": limits move outside the agent.
First pass, built on a P0 that has not met its own exit gate. **The P1 exit gate is not met.** Every enforcement
feature is off unless `policy.json` switches it on.

## What runs today
- Policy engine in the gateway: features run before dispatch, each `off`, `advisory` or `enforced`; `policy.json` is
  re-read when it changes. Decisions are logged to `decisions.jsonl` (metadata only).
- Budgets per key, caller, team or tenant; day, month or total windows; reserve the worst case, true up to the real
  cost; alerts at 75, 90 and 100 percent in `alerts.jsonl`; 402 at the gateway when spent.
- Turn cap and loop guard.
- Virtual keys hashed at rest, revocable (401 within about a second), append-only audit log.
- Backend health and rate-limit tracking, shown at `/_te/health`.
- Dashboard: `token-economics-admin` (http://127.0.0.1:8788): spend by caller, model and tenant with median and P95,
  budgets, decisions, alerts. Read-only, no login, localhost only.
- CLI: `key issue|list|revoke`, `budget set|list|remove`, `policy show|mode|set`.
- Checks passing locally: ruff, mypy --strict, 281 tests (24 end to end on real local ports), 37 tool tests,
  layering (24 contracts), surface, 18 packages each installing and passing alone.
- Tried once with real Claude Code: a one-cent budget refused `claude -p "hi"` in 2 to 4 seconds with the budget
  message; after raising it, the reply came through and the budget showed the true cost.

## Exit gate (PHASES.md)
| Gate line | Status |
|---|---|
| A test key cannot exceed its budget by more than the measured overshoot | Shown on fixtures: 50 parallel requests against $1, overshoot 0. **Not measured on real traffic**, where the body-size token estimate may be low |
| Fault injection (429, timeout, stream cut) never double-counts or loses a row | Shown on the fake provider: 429, 500, cut stream, timeout, repeated response id. Gateway restart mid-stream not tested |
| Fail-open for observation and fail-closed for budgets both demonstrated | Shown (broken budget config refuses with 503; advisory lets traffic through; broken ledger does not affect responses) |
| No harness with `baseUrl = false` is marked as enforced | Holds in the contract suite. All three adapters have `base_url` true, so the false case is only tested on the rule itself |

## Cards (playbook P1, 20 cards)
| Card | Status |
|---|---|
| per-key budget with reserve then true-up | Done |
| return 402 or 429 at the gateway when over budget | Done (402 by default, configurable) |
| alerts at 75, 90 and 100 percent | Written to `alerts.jsonl` and shown on the dashboard. Nothing sends them anywhere |
| overshoot stays inside the measured bound | Test done on fixtures |
| turn cap at P75 of each model baseline, with a remaining-turns reminder | Cap done, but the number is set by hand: `p75_caps()` exists and nothing feeds it a baseline. Reminder not built (it would change the request) |
| loop guard stops at the first repeated-failure signature | Done for Claude Code and SDK. "Redirect, then stop": redirect not built. Not for Codex |
| backend health and rate-limit tracking | Done, in memory. Rate-limit header names are from documentation, unverified |
| fallback route when a backend fails | Not built |
| provider 429, timeout and stream cut never double-count or lose a row | Done on the fake provider |
| fail-open for observation, fail-closed for budgets | Done |
| capability flags | Done |
| fix rows 15, 36, 42 (zero-risk guards) | **Not built: waiting on the row-numbering decision.** Hermes retired row 15 and narrowed row 42 |
| invoice comparison and weekly canary | Not built (needs the provider's usage and cost API) |
| dashboard: spend by tenant, caller and model with median and P95 | Done as a local read-only page |
| papers T3, T4, T5 | Not started |
| gate(P1) | Not met |

## Not built from the P1 package list
`features/max-tokens`, `features/headless-runner`, `services/reconciler`, `apps/worker`; in `services/tenancy`: roles,
policy-as-code store, secrets vault, second approver, key rotation; admin write API (changes go through the CLI).

## Things a reviewer should know
- **The reservation is large.** It assumes the whole prompt is written to the 1-hour cache and every `max_tokens`
  output token is used. Claude Code sends a big `max_tokens`: "hi" on Sonnet 5.5 reserved about $1.60 for a call that
  cost $0.05. A budget must leave that much headroom, and parallel requests each hold it until they finish.
- **Budgets count API list prices**, including for subscription logins that pay nothing per token.
- **Unpriced models are refused** when a budget applies (`"unpriced": "allow"` changes that). All OpenAI models are
  unpriced today.
- **A request with no key matches no wildcard budget**, and unknown keys are still let through as tenant "unknown".
  There is no "require a key" switch yet, so a developer can drop the header to escape a budget.
- **Only model calls an adapter recognises are policed.** Other paths pass through.
- **Policy is JSON** (`policy.json`), not the YAML the plan names.
- P0 keys in `keys.json` are imported into the hashed store on first start and the plaintext file is scrubbed.
