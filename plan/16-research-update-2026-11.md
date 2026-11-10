# Research update, November 2026

This update covers papers dated 2026-09-01 or later. Every date was checked on the arXiv page (v1 submission date). The corpus was pruned at the same time: 49 papers with no cost, price or routing angle were deleted. 19 papers from the window are now in the corpus: 15 on routing, context and measurement, and 4 on latent and key-value (KV) cache compression. We then read all 19 in full text, not at abstract level, and corrected the figures below (research/INDEX.md).

## Bottom line

No paper proves a best-possible technique for token cost. Every result in range is empirical and some conflict. Four findings are consistent and change the plan:

1. **Cache reads can be the largest cost line, and token savings do not equal cost savings.** CliffCompaction's Table 7 puts cache reads at 78% of an uncompacted bill (GLM 5.1 on Terminal-Bench, idealised cache model). Beyond Token Savings found Qwen running 20 to 80% slower on Terminal-Bench under token-saving policies, while SWE-bench latency stayed flat.
2. **Cheap, deterministic controls have the better evidence, with caveats.** TokenEconomizer's tool pruning, loop interruption and micro-skills cut cache-aware cost 18.4 to 30.9% on SWE-Bench, from the harness side. The harness design study found elision and summarisation about equal in accuracy, with a staged mix cheapest.
3. **A single run is not a measurement.** Run-to-run spread exceeded the gap between agents in one 312-run study (584 runs across three studies). Cost differed 22.5x between two agents on one model, from a rate card, mostly following cache share.
4. **Headline numbers shrank on full-text reading.** All 19 papers were read end to end by seven reader agents. Most savings are single-benchmark, simulated or token-based, so re-measure before quoting any of them.

## New papers and what they change

| Paper | Date | Key number, with its qualifier | Plan change |
|---|---|---|---|
| AgentRouter (2609.22951) | 2026-09-19 | A 12M-parameter step classifier cut cost 71.8% at 97.3% of the quality, in 4.7 ms per step on an A100 graphics processing unit. | Step-level routing fits in the proxy. Keep it in "Ship second". The baseline is GPT-4o, not a frontier coding model. Four templated domains, code is weakest (63.8%), no cache pricing, no confidence intervals. Replicate on our own traces. |
| COMPASS (2610.27822) | 2026-10-20 | DeepSWE 78.1% at $215, against 74.1% at $500 for the best single model. | The $215 excludes router inference and needs the 28-configuration pool (18 configurations give 63.9% at $474). Confidence intervals are wide, and on FrontierSWE no router beat the best constant. Count the router's own cost in the arm. |
| Pathwise-Budgeted Routing (2611.05835) | 2026-11-04 | Solves over 2x as many tasks only at the tightest budget ($0.025): 216.2 against 100.8 on MATH500, 85.0 against 29.8 on GPQA. At the largest budgets the gap is 2.6 and 4.6 tasks. | Model the heavy tail of response cost when you set hard per-session caps. Untested on agentic or cached workloads. |
| Chance-Constrained Routing (2610.22695) | 2026-10-15 | Sublinear cost regret with a quality guarantee that holds with high probability. | The guarantee is asymptotic and needs a known-safe fallback model. The experiments shrink the confidence radius by 0.005, so they do not run the proven algorithm, and the real-model test is 100 queries with simulated satisfaction. Template for the "third" stage only. No savings evidence. |
| SCRouter (2610.18566) | 2026-10-13 | 38,869 in-domain queries (plus 2,753 out-of-distribution) over 144 model-budget actions, which is 12 models times 12 budgets. The gain is mostly on security (+32.9 points, against +3.5 on utility). Cost is tokens times a fixed price table. | Quality-only routing can pick insecure pairs. Add a security condition to the router policy. Out of distribution the gain shrinks, and the probe misclassifies about a quarter of unseen security queries. |
| Which Model for Which Role? (2610.26676) | 2026-10-19 | A substantial fraction of the Pareto frontier at about 10% of exhaustive evaluation cost, and most of it by 30%. Recall on HotpotQA is 0.58 at 10% and 0.74 at 30%. | Assign models per agent role (planner, coder, reviewer) with a sampled search, not a full grid. Evidence is offline replay on question-answering, math and SQL tasks, not coding agents. |
| PISA ensemble routing (2611.10193) | 2026-11-06 | Cost down about 36% in distribution and 25% out of distribution. That is 84 against 132 and 292 against 387 (units of 0.0001 dollars per query) at a hand-picked setting, for +0.60 and +0.48 points of accuracy. | A fixed single model often matches or beats adaptive ensembling (Table 5). Keep ensembles off for agent loops until a measured cost-per-success gain exists. |
| MultiTurnRoute (2611.10848) | 2026-11-07 | A 20.3% drop in simulated normalised cost against Bao on WildChat (16.7% on LMSYS), assuming an 80% cache discount and no eviction. The only billed-dollar result is 19.7% on a separate 3-family pool. | Multi-turn routing built on chat traces only. Adapt it to coding traces before quoting it. |
| TokenEconomizer (2610.22732) | 2026-10-15 | Cache-aware cost down 18.4 to 30.9%, Pass@1 change of -1.0 to +2.6 points, on 277 SWE-Bench tasks with 3 seeds. Three mechanisms: tool pruning, loop interruption and micro-skills. It costs more for the first six tasks or so. | Closest match to this gateway, but it runs on the harness side, not as a gateway-only black box. It learns from grader success labels through a language-model proposer plus regex detectors. Supports the context guard and loop guard. Replicate before quoting. |
| CliffCompaction (2609.26779) | 2026-09-22 | Cache reads are 78% of the uncompacted bill (Table 7: GLM 5.1 on Terminal-Bench, idealised cache model). Up to 50% cost cut, but real Kimi savings on SWE-bench are about 0%. | Drop-only is the authors' own stance, but their Table 6 shows summarisation and a sliding window close or better on some benchmarks. Keep compaction a last resort, and test drop-only against the other two on our traces. |
| Harness design study (2609.20804) | 2026-09-17 | 176 settings (22 models, 4 harness variants, 2 benchmarks). Elision-only and summarisation-only reach similar accuracy, and summarisation is often cheaper (550B model at 32K on SWE-bench Verified: $1.25 against $2.57). Staged elision then summarisation wins on cost. | Do not claim elision beats summarisation. Prefer the staged mix and tag every request with harness, tool set and context strategy. Most of the study needs control of the harness. |
| Beyond Token Savings (2609.32961) | 2026-09-26 | 65 policies, 3 models, 3 repeats per cell, nearly 35,000 runs. The 20 to 80% slowdown is Qwen on Terminal-Bench only. SWE-bench latency was 0.79 to 1.0x. Costs are an input-only estimate with an assumed 0.1x cache price. | Judge every compression control on billed cost and latency per solved task. This study did not bill spend either. |
| Total Cost of Agency (2609.23790) | 2026-09-20 | 13.6% is injection over injection plus inference at the mid tier, uncached (11.8% of the full bill). 27.6% is depth 6. The workload is a synthetic 4-node enterprise workflow, not a coding agent. | Meter injected context per agent and per depth in the ledger. Do not quote the percentages for coding traffic. |
| Identical Runs, Different Results (2609.33812) | 2026-09-27 | 584 runs is 116 + 312 + 156 across three studies. Run-to-run spread exceeded the gap between agents in Study 2 only (312 runs, one machine-learning task). The over-20x cost gap is $0.08 against $1.86 (22.5x) on one model, 3 runs each, from a rate card. | Store per-run cost distributions. Capture cache read and write tokens separately. Never publish a single-run figure. About 9x of the gap follows cache share. The cause of the cache failure is untested. |
| DeltaSelect (2609.19607) | 2026-09-17 | 13 evaluations for $27.86. The 58.1% cheaper result is one run per configuration on 8 tasks. The score gain is not significant (p=0.326), and bare Luna at medium effort beat the adopted configuration on both score and cost. | Use it as a method for cheap paired A/B on a fixed task subset, not as a result. Report the p-value with the cost delta. |

## What the full text changed

- **Headline numbers narrowed.** Most come from one benchmark, a simulation or a token count. Only two narrow results are in billed dollars (MultiTurnRoute 19.7%, DeltaSelect $27.86 for 13 evaluations), and neither covers a coding agent in production.
- **One claim reversed.** The harness study does not show that elision beats summarisation. The two reach similar accuracy and summarisation is often cheaper. A staged mix is cheapest.
- **One claim reclassified.** TokenEconomizer is a harness-side tool with three mechanisms, not a gateway-only black box. It costs more for roughly the first six tasks.
- **Latent savings shrink end to end.** LOHA cuts context per call 43 to 57% but whole-trajectory decoder input only about 8%, and plain masking matches its resolve rate on Qwen3. Every latent method needs open weights.
- **Cost-of-agency and variance figures are narrow.** 13.6% and 27.6% are from a synthetic enterprise workflow. The variance-over-gap result is one study of 312 runs on one task.

## Latent compression: agents that skip reading tool output as text

Four papers train or build a way for the agent to take tool output as latent (soft) tokens or compressed KV entries instead of text. All four need access to model internals, so they work only on self-hosted open-weight models. A hosted API such as Claude or OpenAI's models accepts text and cannot take injected embeddings.

| Paper | Date | Key number, with its qualifier | Limit |
|---|---|---|---|
| Coca-Cola, "Tools Need Not Speak in Text" (2611.06500) | 2026-11-04 | Tool observations compress into latent tokens injected into the agent's input embeddings. Tokens fell 70.01 to 89.24% and runtime fell 24.45 to 55.97%. Accuracy rose only against the vanilla baseline, with no variance or evaluation sizes. | Self-host only: needs embeddings and gradients, and one compressor trained per agent. Tested on 4 web-search question-answering benchmarks with Qwen3.5 and GLM, not coding. |
| ASTC (2610.41291) | 2026-10-30 | 50.68% fewer attention pairs is the best case (OfficeBench, -1.05 points of accuracy). AppWorld gives 19.30% fewer pairs, and its accuracy gain is about 2 tasks. | "Training-free" still needs a calibrated reader per model and tuned thresholds, plus a hybrid GDN-attention model. Pairs are analytical compute counts, not billed cost. |
| LOHA with ACD (2609.31430) | 2026-09-25 | Old observations become soft tokens and the last K stay text. K=3 cuts context per call 43% and 57%. Whole-trajectory decoder input falls only about 8% on Qwen3 (1.65M to 1.51M tokens), because calls rise from 37.9 to 60.9. | Resolve rate fell: 12.1 and 21.8% against 14.5 and 27.5% for the uncompressed bases. Plain masking matches it on Qwen3 (12.2%). The 1.9x throughput is against its own weakened agent, about 1.09x against the base. |
| ActKV (2609.31395) | 2026-09-25 | 98.53% accuracy at 25.98% of peak KV memory is the mean of ALFWorld and WebShop with the adaptive budget (HotpotQA-Web: 96.81% at 35.08%). Token throughput 3.97x, task throughput 3.58x. | Needs custom vLLM kernels, so self-host only. Measured on one GPU, offline, on two open models. Not tested on coding. Absolute accuracies and intervals are not stated. |

What it means here:

1. **API backends: no change.** The gateway cannot inject latents. Text-level elision (TokenEconomizer, CliffCompaction) stays the default.
2. **Self-hosted backends: a P3 candidate.** If we serve open models, a latent compressor in front of web-search tools is the highest-saving item found. Test it on our own traces first.
3. **Judge on cost, not tokens.** Every figure above is tokens, compute or memory. Beyond Token Savings (2609.32961) shows token cuts can still raise bills.
4. **Earlier context, before the date window:** CoACT (2607.02911, text-level, next-action preserving), TokenPilot (2606.17016, cache-stable compaction), What Does Context Compression Cost an Agent? (2608.16370, dropped state is re-fetched) and LatentPress (2609.01507, 2026-09-01). They agree with the plan: a compression control must keep the prompt prefix stable and be priced after re-fetch cost.

## Price and billing changes to load into the price book

Rows marked "vendor page" were read on the vendor's own page on 2026-11-10. The rest come from third-party reports. Confirm those against the vendor page before they go live. The price book already requires dated, expiring entries (04-cost-formula.md).

| Change | Effective | Source |
|---|---|---|
| Anthropic cache-read multiplier is per model: 0.025x on Fable 5.1 and 5.2, 0.05x on Opus 5.5 and Sonnet 5.5, 0.1x elsewhere. Sonnet 5.5 reads at $0.10 per M tokens, Opus 5.5 at $0.20. | 2026-10-07 for Sonnet 5.5 | Vendor page; MIXED News for the date |
| Haiku 5.5 prices each request by length: over 100K tokens, input rises from $0.10 to $0.50 and output from $0.50 to $2.50, even on a cache hit. | 2026-10-07 | Vendor page |
| Sonnet 5 stays at $2 input and $10 output. The planned rise to $3 and $15 on 2026-09-01 was cancelled. | 2026-09-01 | Vendor page |
| Claude 4.7 and later tokenise about 30% more tokens for the same text. `inference_geo: "us"` adds 1.1x to every token category. | Current | Vendor page |
| OpenAI adds a cache-write charge on GPT-6 and 6.1 models, and an optional 12-hour cache. The write multiplier conflicts: 1.25x of input on a third-party price sheet (Sol: $2 input, $2.50 write), 2.5x in an OpenAI changelog snippet. | 2026-10-20 | Conflict. Read OpenAI's own page before use. |
| Gemini 4 Argon: input $2 to $4, output $10 to $20, cache $0.10 to $0.20 per M tokens. | 2026-12-01 | Vendor page |
| Gemini 3.8 Flash and 3.6 Flash rates double (input $0.75 to $1.50, output $3.75 to $7.50). Cache storage $0.50 to $1.00 per hour. | 2027-01-01 | Vendor page; Yahoo Finance |
| Grok 4.7 doubles every rate for the whole request at 200K prompt tokens and above (input $2 to $4, output $6 to $12). | Current | Vendor page |

Three rules follow. Price entries carry an effective date, so a historical cost-per-success trend is restated across a cutover. Prompt length is a price input: Haiku 5.5 and Grok 4.7 have a cliff at 100K and 200K tokens. Client-side cost displays can lag the real price (Claude Code 2.1.295 priced Sonnet 5.5 cache reads at $0.20 until 2.1.296), so reconcile against the provider's usage and cost API.

## Orchestrators, gateways and agent CLIs since September

No new research paper describes an orchestrator. The changes are in products. Dates come from vendor pages and changelogs, read 2026-11-10.

| Product | Date | What changed | What it means here |
|---|---|---|---|
| LiteLLM Auto Router benchmark | 2026-09-11 | 25 SWE-bench Verified tasks, one attempt each. The router solved 23 for $11.15 ($0.48 per solved task). Always-Opus 5 solved 23 for $20.27. | Cost fell 45% at the same score. The sample is tiny and vendor-run. Replicate before quoting. |
| LiteLLM Switchyard router | 2026-11-06 | Routes each turn by tool history (failures, retries, recovery), not prompt text. No cost numbers published. | Tool-trajectory signals are a cheap routing input for agent traffic. |
| LiteLLM cost accounting redesign | 2026-10-31 | Design post: usage meter, cost compiler, budget enforcer. Reservations are separate from settled spend. | Matches the reserve-then-settle flow in 05-policy-router-budgets.md. A design, not a shipped feature. |
| LiteLLM v1.107.0 | 2026-10-21 | Release reported compromised. Releases later moved to Tuesdays, with an LTS line on 1.108. | Pin gateway dependencies. Do not use v1.107.0. Details were not read. |
| OpenRouter routing rebuild | 2026-10-28 | Default scores cost, speed and reliability, not cheapest-first. | Weigh latency and error cost next to price. Figures came from a snippet. |
| OpenRouter Auto Code router | 2026-11-06 | Picks model and reasoning effort per request. | Effort is a routing dimension. |
| Claude Code 2.1.316 to 2.1.319 | 2026-10-31 to 2026-11-06 | Pooled group budgets, a per-developer cost report API, `/usage` spend behind a gateway, subagent effort variable. | The native gateway now enforces budgets. Integrate with it. |
| Codex CLI 0.166.0 | 2026-10-29 | Rollout budgets can be advisory, with optional enforcement. | Expose advisory and enforced modes. |

## Which model for which job

No peer-reviewed result gives a rule. Two leaderboards and Anthropic's own guidance agree on the shape. Treat the numbers as leads, not facts: one leaderboard page has no date, and the other is a secondary source.

- Anthropic's models page tiers the family: Haiku 5.5 for classification and routing, Sonnet 5.5 for most work, Opus 5.5 as the default for most workloads, Fable 5.2 for long-horizon agent work.
- On the Snorkel SWE-bench CLI board, cost per task spans $1.44 (GPT-6.1 Sol, 9.8% pass at 1) to $118.64 (Opus 5, 14.0%). Opus 5.5 scores 16.6% at $15.87. Dividing cost by pass rate, Opus 5.5 is about $96 per solved task and GPT-6.1 Sol about $15. The page is undated.
- On Terminal-Bench 4.0 (Morph's page, updated 2026-10-06), Opus 5.5 scored 64.8% at $14.30 per task and Sonnet 5.5 scored 61.8% at $22.22. The mid-priced model cost more.
- Effort changes both score and cost, so route on model and effort together.

## Changes to the plan


| File | Change |
|---|---|
| 04-cost-formula.md | Add effective-dated price rows and the 12-hour cache write multiplier. Add a break-even rule per prefix: the reuses needed before a 2.5x write pays off. |
| 05-policy-router-budgets.md | Add per-step routing evidence (AgentRouter) with its qualifiers, the heavy-tail budget model, a security condition on routing, per-role Pareto assignment, and the COMPASS pool-size and router-cost caveats. |
| 06-context-guard.md | Keep compaction a last resort and test drop-only against summarisation and a sliding window. Use a staged elision-then-summarisation mix, not elision alone. Add latent compression as a self-hosted-only candidate, and note TokenEconomizer is harness-side. |
| 07-observability-eval-rollout.md | Require per-run cost distributions, a paired bootstrap with multiple-comparison correction, a metered-calls-per-task field, and the single-study scope of the variance result. Add a rule that no compression control ships on token count alone. |
| 09-risks-and-open-questions.md | Record that no proven best-possible technique exists, that several vendor numbers rest on third-party pages, and that September to November figures were narrowed by full-text reading. |
| 14-research-papers.md | Cite the new papers in the matching paper outlines, with the qualifiers found in full text. |

## What this search did not find

- No September-or-later paper on thinking-budget or reasoning-effort selection.
- No official vendor announcement of a new cost-cutting orchestrator. Bifrost and Context Gateway show no new cost feature in the window.
- No formal bound for prompt-cache eviction or agent context management. The only formal result found, a Θ(n) competitive ratio for online KV-cache scheduling (2608.16944), is dated 2026-08-14.
- No paper on billing reconciliation or on cost-of-pass as a formal metric.

## Excluded on date

An Empirical Cost Attribution of Context-Compression Gateways (2609.22114) has a September ID but was submitted 2026-08-19. Token Reduction Is Not Cost Reduction (2607.12161) and Prompt-Induced Waste in Coding Agents (2608.01347) are July and August. All three stay in the corpus as earlier evidence that the plan already cites.
