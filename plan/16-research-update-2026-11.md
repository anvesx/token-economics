# Research update, November 2026

This update covers papers dated 2026-09-01 or later. Every date was checked on the arXiv page (v1 submission date). The corpus was pruned at the same time: 49 papers with no cost, price or routing angle were deleted, and 18 new papers were added (research/INDEX.md). Four of the 18 (a later pass) cover latent and KV-cache compression of tool output.

## Bottom line

No paper proves a best-possible technique for token cost. Every result in range is empirical and some conflict. Three findings are consistent and change the plan:

1. **Cache reads are the largest cost line, and token savings do not equal cost savings.** CliffCompaction reports cache reads at 78% of an uncompacted bill (search snippet; the abstract does not state it). Beyond Token Savings (about 35,000 runs) found that policies using a third of the tokens ran 20 to 80% slower.
2. **Cheap, deterministic controls have the best evidence.** Rule-based elision beat LLM summarisation across 176 matched settings. A black-box controller that prunes tools and stops failure loops cut token cost 18.4 to 30.9% on Claude Code, Codex and Copilot CLI.
3. **A single run is not a measurement.** Run-to-run variation exceeded the gap between agents in a 584-run study, and cost differed over 20x between two agents on one model.

## New papers and what they change

| Paper | Date | Key number | Plan change |
|---|---|---|---|
| AgentRouter (2609.22951) | 2026-09-19 | A 12M-parameter step classifier cuts cost 72% at 97.3% quality, under 5 ms per step | Step-level routing fits in the proxy. Keep it in "Ship second". Report savings per solved task, not per quality retained. |
| COMPASS (2610.27822) | 2026-10-20 | DeepSWE 78.1% at $215 against 74.1% at $500 for the best single model | Evidence that routing beats the best single model on both axes. Count the router's own cost in the arm. |
| Pathwise-Budgeted Routing (2611.05835) | 2026-11-04 | Solves over 2x as many tasks at the tightest budgets | Model the heavy tail of response cost when setting hard per-session caps. |
| Chance-Constrained Routing (2610.22695) | 2026-10-15 | Sublinear cost regret with a high-probability quality guarantee | Template for the "third" online-routing stage. No savings evidence yet. |
| SCRouter (2610.18566) | 2026-10-13 | 38,869 queries over 144 model-budget pairs | Quality-only routing can pick insecure pairs. Add a security condition to the router policy. |
| Which Model for Which Role? (2610.26676) | 2026-10-19 | Recovers most of the Pareto frontier at about 10% of exhaustive evaluation cost | Assign models per agent role (planner, coder, reviewer) with a sampled search, not a full grid. |
| PISA ensemble routing (2611.10193) | 2026-11-06 | Cost down about 36% in distribution against the strongest ensemble baselines | Ensembles are a competitor to routers at equal cost. Test before ruling them out. |
| MultiTurnRoute (2611.10848) | 2026-11-07 | CoR cuts normalised cost by up to 20.3% | Multi-turn routing benchmark. Chat traces only; adapt to coding traces. |
| TokenEconomizer (2610.22732) | 2026-10-15 | Token cost down 18.4 to 30.9% at comparable success | Closest match to this gateway: black-box, harness-agnostic, tool pruning plus loop interruption. Validates the context guard and loop guard. |
| CliffCompaction (2609.26779) | 2026-09-22 | Up to 50% cost cut under a bounded context | Compaction default becomes drop-only: truncate or drop, never rewrite, never re-compact. Time it against the cache. |
| Harness design study (2609.20804) | 2026-09-17 | 176 matched settings; elision beats summarisation | Prefer rule-based elision to LLM summarisation. Tag every request with harness, tool set and context strategy. |
| Beyond Token Savings (2609.32961) | 2026-09-26 | Fewer tokens did not reliably mean cheaper or faster | Judge every compression control on billed cost and latency per solved task. |
| Total Cost of Agency (2609.23790) | 2026-09-20 | Memory injection is 13.6% of optimisable cost, 27.6% at depth 6 | Meter injected context per agent and per depth in the ledger. |
| Identical Runs, Different Results (2609.33812) | 2026-09-27 | Cost differed over 20x on the same model, mostly from caching | Store per-run cost distributions. Capture cache read and write tokens separately. Never publish a single-run figure. |
| DeltaSelect (2609.19607) | 2026-09-17 | 13 evaluations for $27.86; adopted configuration 58.1% cheaper | Paired A/B on a fixed small task subset. Report the p-value with the cost delta. |

## Latent compression: agents that skip reading tool output as text

Four papers train or build a way for the agent to take tool output as latent (soft) tokens or compressed KV entries instead of text. All four need access to model internals, so they work only on self-hosted open-weight models. A hosted API such as Claude or OpenAI's models accepts text and cannot take injected embeddings.

| Paper | Date | Key number | Limit |
|---|---|---|---|
| Coca-Cola, "Tools Need Not Speak in Text" (2611.06500) | 2026-11-04 | Tool observations compress into latent tokens injected into the agent's input embeddings. Token use down 70.01 to 89.24%, runtime down 24.45 to 55.97%, accuracy up. | 4 web-search QA benchmarks, Qwen3.5 and GLM open models. Not coding agents. Needs a trained compressor and a frozen open agent. |
| ASTC (2610.41291) | 2026-10-30 | Training-free. Up to 50.68% fewer attention pairs at equal or better accuracy. Reusable KV caches. | Needs a hybrid GDN-attention model. Attention pairs are compute, not billed cost. |
| LOHA with ACD (2609.31430) | 2026-09-25 | Old observations become soft tokens, the last K stay text. K=3 cuts context per call 43 to 57% on SWE-bench Verified. | Resolve rate fell: 12.1 and 21.8% against 14.5 and 27.5% for the uncompressed bases. 4B models. |
| ActKV (2609.31395) | 2026-09-25 | Keeps 98.53% of full-KV accuracy with 25.98% of peak KV memory. 3.97x token throughput. | Serving-side. Needs control of the inference engine. |

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
| 04-cost-formula.md | Add effective-dated price rows and the 12-hour cache write multiplier. Add a break-even rule per prefix: reuses needed before a 2.5x write pays off. |
| 05-policy-router-budgets.md | Add per-step routing evidence (AgentRouter), the heavy-tail budget model, a security condition on routing, and per-role Pareto assignment. |
| 06-context-guard.md | Make drop-only compaction the default. Prefer rule-based elision to LLM summarisation. Add latent compression as a self-hosted-only candidate. |
| 07-observability-eval-rollout.md | Require per-run cost distributions, paired bootstrap with multiple-comparison correction, a metered-calls-per-task field, and a rule that no compression control ships on token count alone. |
| 09-risks-and-open-questions.md | Record that no proven best-possible technique exists, and that several vendor numbers rest on third-party pages. |
| 14-research-papers.md | Cite the new papers in the matching paper outlines. |

## What this search did not find

- No September-or-later paper on thinking-budget or reasoning-effort selection.
- No official vendor announcement of a new cost-cutting orchestrator. Bifrost and Context Gateway show no new cost feature in the window.
- No formal bound for prompt-cache eviction or agent context management. The only formal result found, a Θ(n) competitive ratio for online KV-cache scheduling (2608.16944), is dated 2026-08-14.
- No paper on billing reconciliation or on cost-of-pass as a formal metric.

## Excluded on date

An Empirical Cost Attribution of Context-Compression Gateways (2609.22114) has a September ID but was submitted 2026-08-19. Token Reduction Is Not Cost Reduction (2607.12161) and Prompt-Induced Waste in Coding Agents (2608.01347) are July and August. All three stay in the corpus as earlier evidence that the plan already cites.
