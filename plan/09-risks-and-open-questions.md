# Risks and open questions

## What the corpus does not contain

Token Economics cannot be specified from evidence on these. Each needs a measurement in the phase shown.

| Gap | Why it matters | Resolve in |
|---|---|---|
| Cache loss when switching model mid-session | Decides whether session-level routing pays | P0 measurement, P2 router |
| Claude Code behaviour on a 402 from a gateway | Decides how budget exhaustion is signalled | P0 spike |
| Size of soft-budget overshoot | Sets reservation headroom | P1 |
| A measured subagent or agent-team token multiplier | The 7x figure is quoted from docs that do not state it | P0 measurement |
| Shadow, canary and staged-rollout results from production | Rollout thresholds are placeholders | P1 to P3 |
| Sample-size and power formulas, minimum test duration | Eval length is a guess | P2, fit on our own pilot |
| Anomaly-detection method | Corpus has only 75, 90 and 100 percent budget alerts | P1 |
| Reconciliation tolerance | Canary target of 1 percent is a proposal | P0 |
| Default GPU utilisation | Self-host rule needs it | P3, only if self-hosting |
| Acceptable quality-loss margin | A business call, not a research result | P2 |

## Evidence risks

1. All 423 sources and 411 notes are model-written. A note can misstate its paper.
2. Six extraction agents read the notes plus corpus text. None read every paper first-hand.
3. Codex produced 24 of 93 notes before its usage limit. Its share is missing.
4. Many figures are vendor or author claims on their own product.
5. Some pages and model names are future-dated or unverifiable (Fable 5.1, GPT-6.1, Gemini 4 Argon).
6. Plan figures expire quickly. Weekly caps doubled in May 2026, and a promo ended on 31 May 2026.

7. No paper dated September 2026 or later proves a best-possible technique for token cost. Results are empirical and several conflict (16-research-update-2026-11.md).
8. Vendor price changes in the update rest on third-party pages in part. The OpenAI cache-write multiplier conflicts (1.25x against 2.5x). Verify on vendor pages before billing on them.
9. Two public model leaderboards used for "which model" guidance are secondary or undated. Treat them as leads.
10. 49 off-topic papers were removed on 2026-11-10 and 18 added. Counts of 423 sources elsewhere in the plan predate this change.
11. Latent-compression results (2611.06500, 2610.41291, 2609.31430) come from open 4B to 35B models on QA or SWE-bench tasks. None was tested on a hosted API or measured in billed cost.

## Unresolved conflicts

Each conflict gets an explicit Token Economics default, labelled DevX proposal until measured.

| Conflict | Sources | Token Economics default |
|---|---|---|
| Visible budget helps or does nothing | helps C:131, C:025; no effect C:136 | Enforce caps outside the agent. Keep a reminder only with turn caps. |
| Voting and ensembles | 0 percent benefit A:122; Self-MoA best A:032 | Off. Needs a measured cost-per-success gain. |
| Compaction | neutral C:122; adds cost A:224, C:130, C:133 | Last resort only. |
| Routers beat the best single model | papers yes; LLMRouterBench no (A:006, A:046) | Ship a best-single baseline first. Router must beat it after overhead. |
| Main cost driver | input C:023; output C:027; harness base C:024 | Measure per workload before choosing a lever. |
| Output compressors | savings flip by harness: +48 percent on Claude Code, -12.49 percent on Codex | Off by default. |
| Gemini cache discount | 75 percent A:121; 90 percent A:280 | Take the newer row, flag the older. |
| Self-host crossover | $3 per hour gives 72M tokens per day; $5.49 gives about 132M | Use measured GPU rate. |

## Product risks

| Risk | Mitigation |
|---|---|
| A harness stops honouring the base URL | Capability flags degrade control to observation. Contract tests per adapter on each harness release. |
| OAuth passthrough breaks | `oauthPassthrough` flag. Fall back to API key mode. |
| Gateway adds latency or becomes a single point of failure | Fail open for observation. Health-checked bypass for reads. Budgets fail closed. |
| An optimisation saves tokens but costs money | Gate on cost per successful task, never on token counts. |
| Quality drops unseen | Non-inferiority bound declared before the test, auto-rollback on breach. |
| Stale prices misbill | Expiry flags, billing block, weekly canary against invoices. |
| Prompt content leaks via logs | No content stored by default. Retention and redaction rules in the Security group. |
