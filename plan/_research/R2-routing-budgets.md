# R2 Routing, cascades, model selection, budget policy

Id prefix: A### = research/ notes; C### = research-cli-agents/ notes (the two id spaces overlap). Tags: [measured] [self-reported] [price-list] [illustrative]. "Not in corpus" means no source states it.

## 1. Facts to build on

### 1.1 Routers: gains are real but smaller and noisier than headlines
- RouteLLM (A001) [self-reported]: MF router needs 13.4% strong calls for 50% of the strong/weak gap on MT Bench vs 49% random; 95% of GPT-4 quality; 3.66x saving vs random. MMLU 1.41x, GSM8K 1.49x. Savings are vs a random router, not vs always-weak. Arena-only training was near random on MMLU/GSM8K until ~1,500 gold samples (<2% of data) were added. Router cost at most 0.4% of GPT-4 generation; $3.32 per M requests for MF.
- RouterBench (A002) [self-reported]: 405,467 samples, 11 models. Predictive routers did not consistently beat the convex hull of single models. Cascade AIQ collapses once judge error exceeds 0.2. Oracle MMLU 0.957 at $0.297 vs GPT-4 0.828 at $4.086.
- LLMRouterBench (A006) [self-reported, near-independent]: 33 models, 10 routers, 5 seeds. Most routers nearly tie. Best: up to +4% accuracy and 31.7% cost cut vs best single model. OpenRouter -24.7% vs GPT-5. Failure case: queries that few models solve (accuracy 23-25% when at most 3 experts are right, 11.9% of queries). Embedding backbone barely matters (22.7M vs 7B). Recommends a Best Single baseline and a cheap k-means router.
- RouterArena (A046) [self-reported, list prices]: GPT-5 74.0% at $14.02/1K queries; MIRT-BERT 66.9% at $0.15; Azure-Router 68.1% at $0.54; RouteLLM 47.0%; RouterDC 32.0%; oracle 90.89%. Router latency 11.1-546.8 ms. Robustness to perturbation spans 100% (RouteLLM) to 35% (vLLM-SR).
- AWS tokenomics (A051) [self-reported]: task routing on 21 tasks, -44.7% cost, -4.8% mean quality, with a quality floor of 65.
- Gemini classifier (A052) [self-reported, 50 tasks, single run]: classifier plus Flash-Lite escalation scored 50/50, same as Flash LOW alone. A regex heuristic lost 23.2 points held-out. Atomic yes/no questions work; one broad question collapses.
- s1 classifier (A018) [vendor]: 7 heads, 14 ms CPU; routing agreement 0.742 own test set, 0.60 on blind Opus labels (n=100).
- PORT (A007) [self-reported]: online routing under token budgets; 75.99-84.66% of offline optimum; needs ground truth; no caching model. Label bias (A013): fix with 100-1,000 gold samples.
- Zen Router (A019) [self-reported]: one-model logs gave a majority-class router (2 of 24 models emitted); needs balanced counterfactual labels.
- Router attack (A010) [measured by attackers]: a short gadget upgrades routing to the strong model 73-100% (white-box); OpenRouter cost on 72 queries rose from $0.03 to $0.25 (over 8x). Perplexity filters bypassable. Defence named: per-tenant quotas on strong-model use.

### 1.2 Routers on agent work (CLI side)
- TwinRouterBench (C030) [self-reported]: static router trained on 970 execution-verified step labels: $25.66 vs unrouted Opus $54.73 (-53.1%), 75/100 vs 74/100 resolved (locked 100 SWE-bench instances, no CIs). Opus 4.6 prompted as router flagged only 7/147 verified-high steps and failed all 40 trajectories. Mid-trajectory switches must be priced at the incoming tier's cache-write rate. Median prefix about 5,300 tokens.
- MTRouter (A008) [self-reported]: turn-level, 6 models over 20x cost range; ScienceWorld 53.8 at $5.7 vs GPT-5 48.4 at $13.9 (-58.7%); HLE -43.4%. Training data cost about $1,620. Retains the same model after an error 90.2% / 80.9% of the time. Cache loss on switch noted, not measured.
- Unified cascade routing (C029) [self-reported]: 1-4% AUC over routing or cascading alone; routing on noisy ex-ante estimates gains about 1%; threshold cascade fails with binary feedback; test pass/fail is a post-hoc signal.
- ACRouter (C032) [self-reported]: perf/$ 3.79 vs 1.29 always-Opus in distribution; static classifiers 8.93-21.43% OOD; bandits 49.82%/46.43%.
- LLMRouter (C033) [self-reported]: +14.6% relative over best fixed model; multi-turn routers weak (Router-R1 22.30).
- RLM-Cascade proxy (C031) [self-reported, 125 requests]: -45.8%; tool-bearing requests go to Opus; 70-80% of Claude Code turns are tool selection so only 20-30% are eligible; draft accepted 88.8%; break-even skip rate 13.3%; TTFT 2.1x worse; one cost inversion.

### 1.3 Cascades and error price
- FrugalGPT (A021) [self-reported, March 2023 prices]: 59.2-98.3% cheaper at matched accuracy; judge and fall-through calls must be budgeted.
- Deferral score (A022): sum log-prob is length-biased; use min-quantile of token probabilities. Needs logprobs.
- Conformal cascade (A028) [self-reported]: 2 tiers, multiple choice, N=16 samples per tier, n >= 200 calibration. Cost ratio 1:2.7 gives break-even acceptance 0.37; guard rail is Always-Strong if acceptance < 1/r. Tier-1 acceptance ranges 0% to 95.6%. Sampling overhead not priced.
- Economic evaluation (A123) [self-reported]: reward = -(cost + latency + error + abstain prices). A single big model beats cascades above a $0.10 error price at zero latency price. Reasoning wins above an error price of $0.20 (body) or $0.01 (abstract). Reasoning models cost 10-100x per query.

### 1.4 Vendor routers and gateways
- Copilot Auto (A155) 10% and Kiro Auto (A162) about 23% are [vendor claims] with no baseline. Azure (A149): session affinity does not guarantee cache hits. Bedrock (A158): no numbers.
- Cloudflare (A189, A191, A192): dynamic routes with budget-limit nodes; spend limits are eventually consistent so bursts overshoot; Auto Router switches only when benefit exceeds cache-loss cost, keyed by session id, with a routing-reason header.
- OpenRouter Auto (A228/A230): default policy cost more per task than the old one (MMLU Pro $140.93 vs $393.34 in one direction; SWE-Atlas Max $1,325 vs $205.52 in the other); MMLU Pro accuracy 85.2% vs 86.6%. Prefers changing effort over switching model; session_id stickiness. Provider routing (A227/A229): Routing Cost algorithm +6.0% cost per request for -16.9% TTFT p50, 46% fewer 429s, switchback on 24M requests.
- Vercel (A245, A246): accept threshold 0.85 is a placeholder; budgets are soft caps (HTTP 402); BYOK uncounted. Portkey (A242): unpriced models escape budgets. Langfuse (A234): gateway budgets cannot be bypassed like hooks.

### 1.5 Cache loss on switch (the cost a router must price)
- Changing model, effort, fast mode, or tool set invalidates the cache: A204 (OpenAI cache diagnostics: model_changed, tools_changed, reasoning_effort_changed), C055, A282 (top-level effort change invalidates; per-message effort in beta), C086 (turning fast mode on mid-conversation charges full fast uncached input for the whole context). A052: keep long agent turns on one model.
- Prices [price-list, Claude docs]: 5-minute write 1.25x, 1-hour write 2x, read 0.1x on most models (C052; 0.05x on Opus 5.5 at $4/MTok input: write $5.00, read $0.20). Subagents do not read the parent cache unless forked (C052, C055).
- Measured cost of a model switch on a real agent loop: not in corpus.

### 1.6 Budgets, turn caps, early stopping, prediction
- Ramp (C136) [measured by Ramp]: budget never referenced in 14,000+ messages; request_more_budget called 0 times; an approver agent accuracy 49-67%; advice swings approval (20% vs 84%). Enforce externally.
- Turn caps (C025) [self-reported, caching disabled, single run, 100 tasks]: cap at 75th percentile of baseline turns: Sonnet -23.62% cost (75 to 71% solve), Gemini -68.28% (63 to 65%), GPT-4.1 -38.43% (62 to 57%). 25th percentile: Gemini 26% solve with 63 empty patches. Dynamic 25 to 50 vs fixed 50: -5.95% to -24.30%. Per-model baselines differ.
- TokenEconomizer (C028) [self-reported]: -18.4 to -30.9% including controller overhead; 10 failed runs = 17% of tasks, 32% of spend; 51% of spend after first repeated failure; loop guard redirects before terminating.
- Budget Tracker (C131) [self-reported]: budget 10 matches ReAct at budget 100 (12.8% vs 12.6%), 31.3% lower cost. C132: more budget does not help a capability-limited agent.
- Probe prediction (C027) [self-reported, Kimi K3]: no probe median error 161%; 1 probe ($0.11) 36%; 3 probes 29%; 10 probes 25%; a 1.9x multiplier covers 90%. Run-to-run geometric SD x1.34; identical runs differ up to 30x. Output was 2.7% of tokens but 51.1% of dollars at 96.3% cache hit.

## 2. Decision table

| Order | Technique | Evidence | Condition |
|---|---|---|---|
| Ship first | Best-single-model baseline, per-key hard budgets, turn caps, loop guard, per-session stickiness | A006, A002, C025, C028, C136, A052 | Needed before any router; no training data required |
| Ship first | Rules plus atomic yes/no classifier at session start or at tier boundaries; escalate on verifiable failure | A052, A018, A245, C031 | Re-measure against blind labels (A018 fell 0.742 to 0.60) |
| Ship first | Effort or per-message effort change in preference to model switch | A228, A282 | Check effort invalidation per provider (C055) |
| Ship second | Step-level static router trained on execution-verified counterfactual labels | C030 (-53.1%, 75 vs 74), A019 | Needs balanced labels; C030 has no CIs; rerun on own workload |
| Ship second | Cascade where a cheap post-hoc verifier exists (tests, schema) and measured acceptance exceeds c1/c2 | C029, C031, A028, A123 | Cascade loses above a $0.10 error price (A123) |
| Ship second | Probe-run cost prediction for budget sizing | C027 | One probe cuts median error 161% to 36% |
| Third | Online budgeted routing (PORT-style duals) | A007 | Needs ground truth; no caching model |
| Third | Bandits for drift | C032 (49.82% OOD vs 8.93-21.43% static) | Single source |
| Never | Prompt-only budget self-limits | C136 | Budget ignored 14,000+ times |
| Never | Frontier LLM prompted as router | C030 (failed 40/40), A228 default policy cost more | |
| Never | Router trained on logs from one dominant model | A019 | |
| Never | Preference-only labels without gold set | A001, A013 | Need 100-1,000 gold |
| Never | Sum log-prob deferral score | A022 | Use min-quantile or a post-hoc score |
| Never | Mid-session switching without cache-loss pricing | A192, C030, C055 | |
| Never | Large model pool | A006 | Curate a small complementary pool |
| Never | Spend counted only after the fact, or unpriced models | A191, A242, A245 | |

## 3. Inputs and features per request

Evidence-backed:
- Session id, turn index, and current model (stickiness, A192, A228, A230).
- Cached prefix size and time since last write (to price a switch; C030, C052, A192). Cached-token fraction: see rule 5.
- Needs_tools, needs_vision, needs_long_context, stakes, difficulty, follow_up (A018). Tool-bearing request flag: route to the strong tier (C031).
- Tool/step type in the agent loop (C030 step-level labels; A008 history embedding truncated at 8,192 tokens).
- Previous outcome signals: test pass/fail, repeated failure count, empty patch (C029, C028, C025).
- Per-model price table including cache read/write and output multipliers (A231, C052); output tokens drive dollars at high hit rates (C027).
- Remaining budget on the key/session (A007, A246).


Feature set validated on interactive CLI sessions: not in corpus.

## 4. Rules the system MUST enforce

1. Every router result is reported against Best Single and against an oracle on the same data, in dollars per solved task. Evidence: A006, A002, A001 (savings vs random is not a saving), C026.
2. Budgets are enforced outside the agent, at a gateway or harness, in hard-cap mode. Evidence: C136, A234, C062.
3. Budget counting must price every model and every path, and treat any eventually consistent limit as a soft cap with an explicit overshoot margin. Evidence: A191, A242, A245 (BYOK not counted).
4. Cap per-task turns at a per-model percentile of baseline turns (start at the 75th, never at the 25th), with an explicit reminder to the agent and a fallback when the cap hits. Evidence: C025.
5. Switch models mid-session only if expected saving exceeds cache-rewrite cost of the incoming model, and log the reason. Evidence: A192, C030, A204, C055. Default to staying put after an error (A008: retained 90.2%/80.9%).
6. Treat effort, fast mode, tool set, and model as cache keys: change them only at session start or priced boundaries. Evidence: C055, C086, A204, A282.
7. Per-tenant ceiling on strong-model share, with drift alerts. Evidence: A010.
8. Loop guard: detect repeated failure and redirect or stop; log spend after first repeated failure. Evidence: C028 (51% of spend after it), A246.
9. Route tool-bearing and verifiable-check-failed requests to a strong tier. Evidence: C031, A245.
10. Do not use a deferral score without length normalisation. Evidence: A022.
11. Router training labels come from execution-verified counterfactual outcomes with class balance; preference labels are debiased with 100-1,000 gold samples. Evidence: C030, A019, A013, A001.
12. Router quality is checked on blind labels and out-of-distribution tasks before rollout; static classifiers dropped to 8.93-21.43% OOD. Evidence: A018, C032, A052 (regex -23.2 points).
13. Cascade is enabled for a pair only when measured tier-1 acceptance exceeds c1/c2, with an Always-Strong fallback. Evidence: A028, C031 (break-even skip 13.3%), A123.
14. Budget size per task uses a probe-based prediction with a 1.9x multiplier, not agent self-estimates. Evidence: C027, C110.
15. Log per request: caller, model, effort, prefix size, cache read/write, turns, outcome, router reason, router latency and cost. Evidence: C026, C052, A192.

## 5. Conflicts and how to resolve them

1. Routers tie or lose (A006, A045, A046 for RouteLLM and RouterDC) vs large savings (A001, A003, A008, C030). Likely cause: baselines (random vs best single), cost basis (calls vs dollars, list vs cached) and workload. Resolve by experiment E1.
2. Cascades save 43-98% (A021, A028) vs a single big model wins above $0.10 error price (A123). Resolve by E5 with the product's real error price.
3. Budgets help (C025, C131) vs budgets ignored (C136). Reconcile: C025 and C131 enforce the cap in the harness; C136 relied on the model. Verify with E6.
5. A123 error price break-even $0.01 (abstract) vs $0.20 (body). Take neither; measure.
6. TwinRouterBench -53.1% (C030) vs RLM-Cascade -45.8% (C031, 125 requests) vs unified cascade only +1% when estimates are noisy (C029). Different baselines and sample sizes.

## 6. Experiments required before trusting any router saving

E1. Replay harness: replay the same agent task set through (a) Best Single, (b) each candidate router, (c) an oracle built from execution-verified results; report billed dollars per solved task with real cache read/write, plus 95% CIs over at least 5 seeds (A006 used 5 seeds; C030 had none). A sample size is not in corpus; choose it from the CI width on a pilot.
E2. Cache-switch cost: measure billed cost of a forced mid-session model switch vs staying, at several prefix sizes (C030's median is 5,300 tokens) and time gaps. Not in corpus.
E3. Interactive CLI session test: run the router on real multi-turn sessions, not single-shot benchmarks. Not in corpus.
E4. Router overhead on a live loop: latency (TTFT 2.1x worse in C031), router cost, and failures, with fail-open verified.
E5. Error-price sweep: for each cascade pair, plot net cost against error price $0.01 to $1.00 and find the crossover with a single strong model (A123).
E6. Budget enforcement A/B: no cap, harness cap at 75th percentile, prompt-only cap; with caching on; report solve rate, cost, empty-patch rate (C025, C136).
E7. Label audit: class balance of router labels, and agreement with blind labels from an independent strong model (A019, A018, A013).
E8. OOD and adversarial: held-out repos/task types and a confounder-gadget test; measure strong-model share shift (C032, A010).

