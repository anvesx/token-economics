# Phases: from nothing to production

Four phases. Each ends at an exit gate that must pass before the next starts. The order is measure, enforce, optimise, harden. Optimisation comes after measurement because the corpus shows savings claims from ties to 53 percent, and a saving you cannot measure is not one.

Durations assume a team of three engineers. They are estimates, not corpus findings.

| Phase | Goal | Estimate | Ships |
|---|---|---|---|
| P0 | Measure only | 4 weeks | Gateway in observe mode, ledger, price book, two adapters |
| P1 | Enforce | 4 weeks | Budgets, caps, loop guard, fallbacks, reconciliation |
| P2 | Optimise | 6 weeks | Cache planner, context guard, router, eval harness, shadow |
| P3 | Production hardening | 4 weeks | Canary, kill-switches, security, multi-tenant, runbooks |

## P0: measure only

Nothing is blocked or changed. Token Economics watches and prices.

Build:
1. Gateway proxy with virtual keys, stream tee and the five adapter functions.
2. Adapters for Claude Code (base URL) and one SDK path. Add Codex CLI next.
3. Usage normaliser with five exclusive buckets, rejecting unknown usage keys.
4. Dedupe guard: one ledger row per provider response id.
5. Append-only price book with the 30-day staleness flag.
6. Cost calculator in the order set out in `04-cost-formula.md`.
7. Ledger store with attribution (tenant, team, agent, session, prompt).
8. Spikes: LiteLLM as gateway core, Claude Code against a 402, cache loss on a model switch, subagent token multiplier.

Exit gate:
- Computed cost is within 1 percent of the vendor report for two weeks on each provider in use.
- Every request has a `cost_source` and a `price_row_id`.
- A 30-day baseline exists: mean, median and P95 spend per developer, cache hit per caller, failed-run share.
- The four spike results are written down in `09-risks-and-open-questions.md`.

## P1: enforce

Limits move outside the agent.

Build:
1. Per-key budgets with reserve-then-true-up and 402 or 429 at the gateway.
2. Budget alerts at 75, 90 and 100 percent.
3. Turn cap at P75 of each model's own baseline, with a remaining-turns reminder.
4. Loop guard that stops after the first repeated-failure signature.
5. Backend health, rate-limit tracking and fallback.
6. Reconciler against invoices and the weekly canary.
7. Dashboard: spend by tenant, caller, model, with median and P95.

Exit gate:
- A test key cannot exceed its budget by more than the measured overshoot.
- Fault injection (provider 429, timeout, stream cut) never double-counts or loses a ledger row.
- Fail-open for observation and fail-closed for budgets both demonstrated.
- No harness with `baseUrl = false` is marked as enforced.

## P2: optimise

Each optimisation ships behind its own flag, gated by the eval harness.

Build, in this order:
1. Eval harness: private task set with hard cases, an 80-task Lite subset, paired task-clustered bootstrap, a non-inferiority bound declared before each test, isolated cache per arm.
2. Cache planner: TTL from the observed reuse gap, per-caller hit monitor.
3. Context guard: schema deferral, output caps, observation masking, clearing, compaction last.
4. Router, in this order: rules, atomic classifier, best-single baseline. Static router on execution-verified labels only if it beats the baseline. Cascade only if measured acceptance beats the cost ratio.
5. Shadow runs on mirrored traffic with write isolation.

Exit gate:
- Every shipped optimisation has a paired result showing cost per successful task down, with the success bound held.
- Any optimisation that fails stays off. That counts as a pass.
- The router beats the best single model after its own overhead and cache loss, or it is not enabled.

## P3: production hardening

Build:
1. Canary rollout and one kill-switch per optimisation and tenant.
2. Auto-rollback on success below floor, cost per success above baseline interval, hit-rate drop, or billed-versus-estimate divergence.
3. Secrets handling, authorisation, retention and redaction.
4. Multi-tenant limits and the strong-share ceiling per tenant.
5. Audit log and admin API.
6. Runbooks, on-call alerts, load test, disaster recovery drill.

Exit gate:
- A rollback drill reverts a bad optimisation without a deploy.
- A load test holds the gateway latency budget set in P0.
- Security review closed. No prompt content is stored by default.
- A named owner for each alert.

## Definition of done

A phase is done when every line in its table is true and a person other than the builder has checked it. The exit gates above stay the pass-or-fail test for moving on. This section adds the evidence to show for each deliverable and the rows from `12-fix-table-50-rows.md` that the phase covers.

### P0 done: measure only

| Deliverable | Done when | Evidence |
|---|---|---|
| Gateway in observe mode | Claude Code and one SDK path send traffic through it with no change to responses | Byte-for-byte diff of responses with and without the gateway on a replayed trace |
| Ledger and price book | One ledger row per provider response id, five exclusive buckets, every row has `cost_source` and `price_row_id` | Replay of a duplicated stream produces one row |
| Cost accuracy | Computed cost is within 1 percent of the vendor report for two weeks per provider | Daily reconciliation report |
| Detectors | All 50 detectors run in alert mode on API traffic. Rows that need CLI data run from hooks and transcripts on Claude Code | Detector coverage table: 50 rows, each with a fired or not-fired count over the baseline |
| Class 0 and class 3 rows | 14 rows ship as alerts or recommendations: 7, 9, 10, 22, 26, 35, 38, 41, 44, 46, 47, 48, 49, 50 | Each alert names its owner and a recommended action |
| Spikes | Four spike results written in `09-risks-and-open-questions.md`. Every row marked `proposal` in the fix table has a spike or a reason it waits | Spike notes with a date and a result |
| Baseline | 30 days of mean, median and P95 spend per developer, cache hit per caller, failed-run share | Baseline report checked in |

### P1 done: enforce

| Deliverable | Done when | Evidence |
|---|---|---|
| Budgets and caps | A test key cannot exceed its budget by more than the measured overshoot. Turn cap sits at P75 of each model's baseline | Overshoot test log |
| Loop guard | The gateway stops after the first repeated-failure signature | Replay of a recorded failure loop |
| Class 1 guards | 3 rows ship as zero-risk guards: 15, 36, 42. Each leaves task success unchanged on the replay set | Replay result per guard, success rate before and after |
| Reliability | Fault injection never double-counts or loses a ledger row. Fail-open for observation and fail-closed for budgets both shown | Fault test report |
| Honest capability flags | No harness with `baseUrl = false` is marked as enforced | Capability matrix test |

### P2 done: optimise

| Deliverable | Done when | Evidence |
|---|---|---|
| Eval harness | Task set, paired task-clustered bootstrap, a non-inferiority bound declared before each test, an isolated cache per arm | One dry run on a known no-op change reports no difference |
| Behaviour-change fixes | 33 rows are candidates: 1 to 6, 8, 11 to 14, 16 to 21, 23 to 25, 27 to 34, 37, 39, 40, 43, 45. A row ships for a harness and version only after a paired win in cost per successful task with the success bound held | One result file per row, harness and version |
| Failed rows | A row with no win stays off and is listed as off. That counts as done | The off list with the reason for each row |
| Router | Beats the best single model after its own overhead and cache loss, or stays off | Paired result against the best-single baseline |
| Shadow runs | Mirrored traffic runs with write isolation and shows no unplanned side effects | Shadow report |

The count of shipped rows is a result, not a target. P2 is done when every candidate row has a result file, whether it won or lost.

### P3 done: production hardening

| Deliverable | Done when | Evidence |
|---|---|---|
| Canary and kill-switch | Every shipped P2 fix has a canary stage and a kill-switch per tenant | Config listing each fix with its switch |
| Auto-rollback | A bad fix reverts without a deploy when success falls below the floor, cost per success rises above the baseline interval, hit rate drops, or billed cost diverges from the estimate | Rollback drill for each trigger |
| Security | Review closed. No prompt content stored by default. Secrets and retention rules tested | Review sign-off and a storage scan |
| Scale | Load test holds the latency budget set in P0 | Load test report |
| Operations | A named owner for each alert. Runbooks and a disaster recovery drill done | Owner list and drill notes |

### Rows by phase

P0 covers 14 rows, P1 covers 3 and P2 covers 33. P3 adds no rows. It wraps each P2 fix that shipped in a canary, a kill-switch and an auto-rollback. The full table with the fix for each row is in `12-fix-table-50-rows.md`.

## Detect, measure, apply by phase

How detectors and fixes arrive per phase is in `11-detect-measure-apply.md`. P0 runs detectors in alert mode only. P1 adds zero-risk guards. P2 gates each behaviour-changing fix on a paired test per harness. P3 adds auto-canary and rollback drills.

## Dependencies

```
P0 spikes ─► P1 budgets ─► P2 eval harness ─► P2 optimisations ─► P3 canary
   │                            ▲
   └── 30-day baseline ─────────┘
```

The 30-day baseline from P0 feeds both the turn-cap threshold in P1 and the non-inferiority bounds in P2.

## What stays out until measured

- Voting, ensembles and agent teams.
- Output compressors.
- Mid-session model switching.
- Self-hosting, until utilisation is measured.
- Bandit routing.

## Code layout and papers

- Code is a Python monorepo. Each folder under `apps/`, `services/`, `features/` and `modules/` ships on its own. See [13-monorepo-layout.md](13-monorepo-layout.md). The single `src/token-economics/` tree in the phase playbook is replaced by this layout.
- Each phase ends with a paper that reports what the phase measured. Calendar and titles: [14-research-papers.md](14-research-papers.md). A paper never blocks a phase gate.
