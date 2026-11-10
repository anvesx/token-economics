# Policy engine: budgets, run control, routing, tiers

The policy engine decides before dispatch. It runs inside the gateway, so a developer cannot switch it off. Ids: `A:nnn` API corpus, `C:nnn` CLI corpus.

## Request flow

1. Resolve key to tenant, team and agent.
2. Check the budget. Reserve the worst-case cost: `input_tokens × in_rate + max_tokens × out_rate`.
3. Apply run control: turn cap, loop guard, session stickiness.
4. Apply routing and tier selection.
5. Apply the cache plan.
6. Dispatch. On completion, replace the reservation with the true cost.

## Budgets

| Rule | Detail | Source |
|---|---|---|
| Enforce outside the agent | Agents never referenced a budget in 14,000+ messages and called `request_more_budget` zero times | C:136 |
| Hard cap at the gateway | Return 402 or 429 when exhausted | A:234, C:001 |
| Price every path | Unpriced models and BYOK escape budgets. A "0 cents" row means price unknown. | A:242, A:245 |
| Treat eventually consistent limits as soft | Add an explicit overshoot margin. Size is not in the corpus. | A:191 |
| Alerts at 75, 90, 100 percent | Size budgets near P95, not the mean | A:213, C:116, C:054 |
| Stack windows | For example 10 dollars a day and 100 a month | C:060 |

## Run control

| Control | Rule | Source |
|---|---|---|
| Turn cap | Start at the 75th percentile of that model's own baseline turns. Never start at the 25th. Add a remaining-turns reminder. | C:025 |
| Loop guard | Detect the first repeated-failure signature. Redirect, then stop. 51 percent of spend fell after it. | C:028 |
| Stickiness | One model and provider per session. About 15 requests per minute per prefix on OpenAI. | A:192, A:228, A:230 |
| Switch cost | Switch mid-session only if the saving exceeds the cache rewrite at the incoming model. Log the reason. | A:192, C:030, A:204, C:055 |
| Cache keys | Treat model, effort, fast mode and tool set as cache keys. Change them only at session start or a priced boundary. | C:055, C:086, A:204, A:282 |

Turn cap evidence (C:025, 100 tasks, caching off, single run): at P75 Sonnet cost fell 23.62 percent while solve rate went 75 to 71. Gemini fell 68.28 percent, solve rate 63 to 65. GPT-4.1 fell 38.43 percent, solve rate 62 to 57. At P25 Gemini dropped to 26 percent with 63 empty patches.

## Routing ladder

| Stage | Technique | Condition |
|---|---|---|
| Ship first | Best-single-model baseline, per-key budgets, turn caps, loop guard, stickiness | No training data needed |
| Ship first | Rules plus an atomic yes/no classifier at session start. Escalate on a verifiable failure. | Re-check against blind labels. One classifier fell from 0.742 to 0.60 (A:018). |
| Ship first | Change effort before changing model | Check effort invalidation per provider |
| Ship second | Static step-level router on execution-verified labels | Balanced labels. C:030 had no confidence intervals. Rerun on own work. |
| Ship second | Step-level router that reads tool history (failures, retries, recovery) as well as prompt text | AgentRouter reports −72% cost at 97.3% quality with a 12M-parameter model under 5 ms (2609.22951). LiteLLM Switchyard routes on tool history, no cost data. Replicate on own traces. |
| Ship second | Per-role model assignment (planner, coder, reviewer) from a sampled Pareto search | About 10% of exhaustive evaluation cost (2610.26676) |
| Ship second | Cascade where a cheap verifier exists | Measured acceptance must beat c1/c2. A single model wins above a $0.10 error price (A:123). |
| Ship second | Probe-run cost prediction | One probe cut median error from 161 to 36 percent. Use a 1.9x multiplier. (C:027) |
| Third | Online budgeted routing, bandits, chance-constrained routing | Needs ground truth. Single sources (2610.22695, 2611.05835). Use the heavy-tailed response cost model when setting hard per-session caps. |
| Third | Security-conditioned routing | Quality-only routing can pick an insecure model-budget pair (2610.18566). Add a security condition once P3 starts. |
| Never | Prompt-only budgets, a frontier LLM as router, a router trained on one dominant model's logs, preference labels without gold samples, sum log-prob deferral, mid-session switching without cache-loss pricing, a large model pool | A:019, A:001, A:013, A:022, A:006, C:136, C:030 |

Router results are reported against the best single model and an oracle, in dollars per solved task, with real cache read and write costs (A:006, A:002, A:001). Savings against a random router are not savings.

Since September 2026: COMPASS reports DeepSWE 78.1% at $215 against 74.1% at $500 for the best single model (2610.27822). LiteLLM's vendor test solved 23 of 25 tasks for $11.15 against $20.27 for always-Opus (small, one attempt). Both still need replication on own traffic. Route on model and effort together: OpenRouter's Auto Code router does, and Claude Code exposes a subagent effort variable. Prompt length is a price input: Haiku 5.5 and Grok 4.7 reprice at 100K and 200K tokens (see 04-cost-formula.md). Also meter hard budgets in two modes, advisory and enforced, as Codex CLI 0.166.0 does, and match Claude Code's pooled group budgets.

## Strong-model ceiling

A short adversarial prefix pushed routing to the strong model 73 to 100 percent of the time in white-box tests, and raised cost over 8x on 72 queries (A:010). Token Economics caps each tenant's strong-model share and alerts on drift.

## Tier and cache selection

| Workload | Lever | Condition |
|---|---|---|
| Offline bulk | Batch, or flex if synchronous | 24 hour window acceptable. Check stacking. |
| Repeated long prefix | Cache before tier | Prefix meets minimum and reads repay the write |
| Latency or service-level agreement (SLA) | Priority or fast | Pay 1.75 to 2x only if the SLA binds |
| Steady known load | Reserved or provisioned | Above about 40 percent of on-demand |
| Narrow, verifiable, high volume | Small or fine-tuned model | Eval parity on the slice |

Cache planner: choose 5 minute or 1 hour cache lifetime, or time to live (TTL), from the observed reuse gap. A blanket 1 hour TTL made one bill 8.6 percent worse (C:051, C:052, C:055). Judge hit rate per caller, not per account: a 77 percent account rate hid cron runs near 0 percent (C:052). A miss is more than 5 percent and at least 2,000 tokens reprocessed (C:076).

Anthropic cache read costs 0.1x input on most models, so a hit pays off after about one read at the 5 minute TTL.

## Log per request

caller, model, effort, prefix size, cache read and write, turns, outcome, router reason, router latency and router cost (C:026, C:052, A:192).

## Experiments before trusting a router

1. Replay the same task set through best single, each router and an oracle. Report dollars per solved task with 95 percent intervals over at least 5 seeds.
2. Measure the billed cost of a forced mid-session switch against staying, at several prefix sizes. Not in the corpus.
3. Run on real multi-turn interactive sessions, not single-shot benchmarks. Not in the corpus.
4. Measure router latency and failure on a live loop, with fail-open verified.
5. Sweep the error price from $0.01 to $1.00 for each cascade pair.
6. Test budget enforcement: no cap, harness cap at P75, prompt-only cap, caching on.
7. Audit router labels for class balance and agreement with blind labels.
8. Test held-out repos and an adversarial prefix; measure the strong-model share shift.
