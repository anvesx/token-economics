# R7: Paper novelty check for 14 candidate Tally papers

Date: 2026-11-10. Method: web search (standard mode) then WebFetch of each cited page. Every URL below was opened. Where a fetch returned only the abstract, the verdict rests on the abstract and I say so. "Not found" means no academic or primary source turned up after 2 to 4 searches.

Corpus check: I grepped `research/`, `plan/12b-source-coverage.md` and `plan/_research/` for each arXiv ID. All items below are NEW to the corpus except where marked "in corpus". 2604.22750 appears in `plan/model/model.json` and is the C:023 paper named in 12b. Evan Miller 2411.00640 is in corpus (059.txt). Cost-of-Pass, Rerouting LLM Routers, MTRouter, Analyzing and Mitigating Cost-Inefficient Behaviors and BATS (C:131) are in corpus and are not re-reported as new.

## Summary table

| # | Candidate | Closest prior work (opened) | Verdict | Why |
|---|---|---|---|---|
| 1 | CPS accounting standard | Weinberger and Hozez, Prompt-Induced Waste, 2608.01347 (2026); Weinberger and Hozez, Token Reduction Is Not Cost Reduction, 2607.12161 (2026); Ni et al., GitTaskBench alpha metric, 2508.18993 (2025) | PARTLY | Two 2026 papers already define efficiency as cost per successful task and recommend it as the headline metric; nobody has written the accounting rules (what counts as cost, failure handling, retries, cache, cross-vendor). |
| 2 | Five exclusive token buckets across 5 vendors | CrewAI issue 6768 (2026); LiteLLM cost-discrepancy doc; Tian Pan blog (2026-06-03) | OPEN (academically) | Only bug reports and practitioner notes exist; no paper formalises exclusive buckets or audits the five usage schemas. |
| 3 | Cost decomposition by harness | Bai et al., How Do AI Agents Spend Your Money, 2604.22750 (2026, in corpus); Eden AI / Systima, Claude Code vs OpenCode 33K gap (2026); Fan et al., Empirical Study of Harness Design, 2609.20804 (2026) | PARTLY | Token and phase breakdown exists for one harness family; a logging-proxy test splits prompt vs tools for two harnesses; nothing gives billed-dollar decomposition across 3+ production harnesses. |
| 4 | Reserve-then-true-up gateway budgets, overshoot | Token Budgets: 63 incidents, 2606.04056 (2026); Portkey coding-agent docs; agentgateway v1.3.0 | PARTLY | The 63-incident paper measures overshoot and reservation overhead (4-6x static, 2.11x adaptive) but in-process, not at a gateway; vendors claim hard limits with no mechanics published. |
| 5 | Visible budgets vs gateway caps | Hariri, Coding agents ignore their own budgets, Ramp Labs (2026-04-21); Lin et al., BAGEN, 2606.00198 (2026); BATS (C:131, in corpus) | PARTLY | Visible budget alone had no effect in one single-harness test and agents are over-optimistic; no head-to-head against an enforced cap exists. |
| 6 | Paired, task-clustered eval with cache isolation and non-inferiority | Weinberger and Hozez 2607.12161; Kotrys and Migdal, Quesma RTK (2026-09-11); Bjarnason et al., On Randomness in Agentic Evals, 2602.07150 (2026) | PARTLY | Paired designs and repeat runs exist, and Quesma runs 5x repeats; cache isolation between arms and non-inferiority margins are not stated in any of them. |
| 7 | Cache TTL planning from reuse-gap histograms | Lumer et al., Don't Break the Cache, 2601.06007 (2026); Li et al., Continuum, 2511.02230 (2025); LiteLLM Auto Router prompt-caching doc | OPEN | Continuum does TTL for self-hosted KV; Lumer does not analyse TTL or gaps; blogs only restate the 1.25x/2x/0.1x arithmetic. No measured 5m vs 1h planner found. |
| 8 | Router vs best single model after overhead and cache loss | LiteLLM Auto Router prompt-caching doc (2026); vLLM Semantic Router, Session-Aware Agentic Routing (2026-06-02); Son et al., SWE-Router, 2607.00053 (2026) | PARTLY | Vendors report cache-aware savings vs caching-alone baselines, but self-reported and simulated; SWE-Router and TwinRouterBench abstracts do not state they charge overhead or cache loss. |
| 9 | Same compressor +48% on one harness, -12% on another | PointFive, Token reduction is not cost reduction (2026-08-06); Dasein, Code-Compression Bench (2026-07-04); Quesma RTK (2026-09-11) | COVERED (headline) / PARTLY (harness angle) | The direction of the finding is already published three times; Quesma already shows the same tool -5% on Claude Code and +5% on OpenCode. Your 48% vs -12% pair would need to be a controlled two-harness replication. |
| 10 | Retry and iteration caps | Kiecker et al., Is Three the Magic Number, 2607.05197 (2026); Meir et al., Reset and Discard, 2601.21522 (2026); Bjarnason et al. 2602.07150 | PARTLY | The 3-4 round knee is published for repair loops with cheap models; not for full coding-agent sessions priced in dollars with cache, nor as a stop rule at a gateway. |
| 11 | Router attack surface, strong-model share ceilings | Tang et al., Route to Rome, 2604.15022 (2026); Zhang et al., RerouteGuard, 2601.21380 (2026); Rerouting LLM Routers (in corpus) | PARTLY | Attacks and detectors are published (up to 100% ASR on some routers); a billing-side cap on strong-model share as the defence is not studied in the abstracts. |
| 12 | Gateway traffic vs CLI transcripts for waste detection | Zhu et al., RedundancyBench, 2605.29893 (2026); metermaidai, Agent Waste Index (HF forum, 2026-09-17); Eden AI / Systima proxy method (2026) | OPEN | All detectors run on trajectories; none compares what a gateway can see vs what a transcript shows. |
| 13 | Stale prices, price-book lifecycle, invoice canaries | LiteLLM cost-discrepancy doc; Tian Pan blog (2026-06-03) | OPEN | Vendor docs name stale price maps as a cause; no study, no lifecycle design, no canary method. |
| 14 | Tally system paper | agentgateway v1.3.0 (Agentic AI Foundation, 2026-07); Portkey coding-agent docs; Switchcraft 2605.07112 (2026); vLLM SAAR (2026) | PARTLY | Gateways with per-tool spend and hard limits exist as products; no paper joins accounting, budgets, routing and optimisation measurement across harnesses and CLI backends. |

## Per-candidate detail

### 1. Cost per successful task as an accounting standard
- Weinberger and Hozez (PointFive), "Prompt-Induced Waste in Coding Agents: Reasoning, Effort, Harness Design, and End-to-End Cost", arXiv 2608.01347, Aug 2026 (v6 Sep 2026). https://arxiv.org/abs/2608.01347 . States efficiency is cost per successful task; token and cache counts are "not sufficient optimization targets". Preregistered, two harnesses (abstract-level read).
- Weinberger and Hozez, "Token Reduction Is Not Cost Reduction", arXiv 2607.12161, Jul 2026 (v5 Aug 2026). https://arxiv.org/abs/2607.12161 . Recommends cost per successful task including cache behaviour and correctness.
- Ni et al., "GitTaskBench", arXiv 2508.18993, Aug 2025. https://arxiv.org/abs/2508.18993 . Alpha metric combining success, token cost and developer salary. Formula not on the abstract page.
- In corpus: Cost-of-Pass (economic framework).
- Verdict PARTLY. The metric name is no longer novel. The standard is: a definition of numerator (billed cost incl. failed attempts, retries, router and judge cost), denominator (verified success), censoring, and vendor-neutral billing.
- Sharper title: "Cost per Successful Task, Specified: Numerator, Denominator and Failure Handling for Billed Coding-Agent Spend".

### 2. Five exclusive token buckets
- CrewAI issue 6768, "Anthropic total_tokens omits cache read/write tokens, undercounting cost", opened 2026-08-01. https://github.com/crewAIInc/crewAI/issues/6768 . Repro: 17 reported vs about 4,526 billed.
- LiteLLM, "Debugging a cost discrepancy". https://docs.litellm.ai/docs/troubleshoot/cost_discrepancy . Notes OpenAI cache reads are inside input and Anthropic's are separate; flags categories off by more than about 10%.
- Tian Pan, "The Token Count Your Client Estimated And Your Provider Invoiced", 2026-06-03. https://tianpan.co/blog/2026/06/03/the-token-count-your-client-estimated-and-your-provider-invoiced . Treats `usage` as the ledger. No cache-bucket coverage.
- OpenTelemetry GenAI conventions: the page I opened has moved to https://github.com/open-telemetry/semantic-conventions-genai ; I did not read the attribute definitions, so I make no claim about them. Check before writing.
- Not found: any paper that audits five vendors' usage schemas. Verdict OPEN. This is more a spec plus conformance suite than a research paper; pair it with candidate 13 or 1.

### 3. Cost decomposition by harness
- Bai et al., "How Do AI Agents Spend Your Money? Analyzing and Predicting Token Consumption in Agentic Coding Tasks", arXiv 2604.22750, Apr 2026. https://arxiv.org/abs/2604.22750 . 8 LLMs, SWE-bench Verified, input tokens dominate, 30x run-to-run spread. One harness setup; no harness comparison. In corpus.
- Eden AI (Samy Melaine) reporting Systima AI, "Claude Code vs OpenCode: The 33K-Token Overhead Gap", updated 2026-10-20. https://www.edenai.co/post/claude-code-vs-opencode-the-33k-token-overhead-gap . Logging proxy, same model. First turn about 32.8K vs 6.9K tokens; the page contradicts itself on tool-definition tokens (8,500 in a table vs about 24,000 in text) and does not quantify history. Treat as a blog, not a measurement.
- Fan et al., "An Empirical Study of Harness Design for Coding Agents", arXiv 2609.20804, Sep 2026. https://arxiv.org/abs/2609.20804 . Varies planning, action space and context management, 176 matched settings. No dollar decomposition on the abstract page.
- Verdict PARTLY. Open space: four-component split (base prompt, tool schemas, history, tool output) in billed dollars with cache buckets, for Claude Code, Codex, Aider and an SDK agent.
- Sharper title: "Where the Billed Dollar Goes: A Four-Component Cost Decomposition of Three Production Coding Harnesses".

### 4. Reserve-then-true-up hard budgets at a gateway
- "Token Budgets: An Empirical Catalog of 63 LLM-Agent Budget-Overrun Incidents, with an Affine-Typed Rust Mitigation as a Case Study", arXiv 2606.04056, 2026 (authors not on the page I read). https://arxiv.org/abs/2606.04056 . In-process crate; under asyncio multi-agent delegation a plain counter overshoots 30/30; static over-reservation 4-6x, adaptive 2.11x. Abstract does not say soft vs hard.
- Portkey, coding-agent docs. https://portkey.ai/docs/aigw/product/coding-agent.md . "Hard spend limits per developer, team, or workspace"; no reserve or true-up mechanics stated.
- Agentgateway v1.3.0, Agentic AI Foundation (adapted from Sebastian Maniak, 2026-06-17). https://aaif.io/blog/agentgateway-v1-3-0-llm-consumption-reimagined . Per-tool spend analytics, hard quotas; no reserve or true-up.
- Verdict PARTLY. Reservation overhead and overshoot are measured in-process; the gateway version with the soft-budget overshoot size (what harness-side or post-hoc budgets let through) is open.
- Sharper title: "How Much Does a Soft Budget Leak? Overshoot of Post-Hoc vs Reserve-and-True-Up Caps on Coding-Agent Traffic".

### 5. Do visible budgets help
- Hariri (Ramp Labs), "Coding agents ignore their own budgets", 2026-04-21. https://labs.ramp.com/research/coding-agents-ignore-spend/ . GPT-5.4 in mini-swe-agent, 50K-token budget on SWE-bench Verified. Live counter never mentioned across 14,000+ messages; no change in success, spend or turns. `request_more_budget` tool never called in 5,000+ turns; forced approve/stop chose approve 97% (default-approve) and 79% (neutral). Single harness, single model, no gateway-cap arm.
- Lin et al., "BAGEN: Are LLM Agents Budget-Aware?", arXiv 2606.00198, May 2026. https://arxiv.org/abs/2606.00198 . Budget-awareness correlates weakly with capability (r=0.35); agents are over-optimistic; early stopping saves 28-64% of tokens on failed runs at a 1.6-4.2 point success cost. Trained stop signal, not a visible-reminder arm (abstract-level).
- In corpus: BATS / Budget Tracker (C:131), which reports awareness helps.
- Verdict PARTLY. Evidence conflicts (BATS positive, Ramp null). A randomised gateway-cap vs visible-reminder arm across harnesses (Codex has a reminder setting per a secondary blog I did not verify) is open.
- Sharper title: "Telling the Agent vs Stopping the Agent: Visible Budget Reminders vs Gateway Caps on Coding-Agent Spend".

### 6. Paired, task-clustered evaluation of cost optimisations
- Weinberger and Hozez 2607.12161 (above). Paired comparison vs unmodified baseline, 103 tasks, 7 repos, 3 models, 2,908 runs (PointFive blog, https://www.pointfive.co/blog/token-reduction-is-not-cost-reduction ). Cache isolation not described on either page I read.
- Kotrys and Migdal (Quesma), "RTK reports huge token savings, but our cost benchmarks disagree", 2026-09-11. https://quesma.com/blog/does-rtk-make-ai-coding-cheaper/ . Terminal-Bench 2.1, 5 runs per arm per task, 1,740 attempts, over $1,500 spend. No non-inferiority bound.
- Bjarnason, Silva, Monperrus, "On Randomness in Agentic Evals", arXiv 2602.07150, Feb 2026. https://arxiv.org/abs/2602.07150 . Single-run pass@1 moves 2.2-6.0 points; recommends repeated runs and power analysis.
- Miller, "Adding Error Bars to Evals", arXiv 2411.00640 (in corpus): clustered SEs and paired differences.
- Dasein Code-Compression Bench: states one cache-aware price table but does not say whether cache is isolated between arms. https://raw.githack.com/daseinlabs/code-compression-bench/master/FACT-VS-FICTION.md
- Verdict PARTLY. Components exist; the combination (paired by task, clustered by repo, cache isolated per arm, non-inferiority margin on success, superiority on cost) is not stated by any of them. Strongest candidate to publish as a methods paper.

### 7. Cache TTL planning from reuse-gap histograms
- Lumer et al., "Don't Break the Cache: An Evaluation of Prompt Caching for Long-Horizon Agentic Tasks", arXiv 2601.06007, Jan 2026. https://arxiv.org/abs/2601.06007 . 3 providers, 500+ sessions, 41-80% cost cut, TTFT 13-31%. Abstract has no TTL or reuse-gap analysis.
- Li et al., "Continuum", arXiv 2511.02230, Nov 2025 (v7 Sep 2026). https://arxiv.org/abs/2511.02230 . Self-hosted KV TTL set from predicted tool-call time. Not provider API prompt caching.
- LiteLLM, Auto Router "Prompt Caching". https://docs.litellm.ai/docs/auto_router/prompt_caching . Reports 97.4% of 4,684 switch-backs found cache warm at 5 min and 99.3% at 1 h (vendor, self-reported). Closest thing to a measured reuse-gap statistic.
- Practitioner posts claim Anthropic changed the default TTL from 1 h to 5 min in March 2026; I could not confirm this on an official page and I did not open those posts. Do not cite.
- Verdict OPEN. Sharper title: "5 Minutes or 1 Hour? Planning Prompt-Cache TTL from Measured Reuse-Gap Distributions of Coding-Agent Sessions".

### 8. Does a router beat the best single model after overhead and cache loss
- LiteLLM Auto Router doc (above): router plus caching vs caching alone cheaper by 37.4% on 95 real agent sessions (8,174 calls), 46% on DevGPT simulation, 44-50% on TwinRouterBench static track; router with caching off about 4x worse. Vendor-reported. Baseline is caching alone on one model, which is the comparison you want.
- Liu et al. (vLLM Semantic Router Team), "Session-Aware Agentic Routing: Continuity-Aware Model Selection for Long-Horizon LLM Agents", 2026-06-02. https://vllm.ai/blog/2026-06-02-session-aware-agentic-routing . 21,600 turns: per-turn routing 9,709 switches, 3,836 unsafe, 0% estimated saving; SAAR 78.71% estimated saving. Costs are estimates, not billing; the baseline is a per-turn router, not a single model.
- Son et al., "SWE-Router", arXiv 2607.00053, Jun 2026. https://arxiv.org/abs/2607.00053 . Compares to the stronger model of a pair, not best single model at matched cost; overhead and cache loss not stated on the abstract page.
- TwinRouterBench, arXiv 2605.18859, 2026 (authors not retrieved). https://arxiv.org/abs/2605.18859 . Step-level routing scored on realised API spend; abstract does not say cache loss is modelled.
- Fireworks AI, "Model Routing for LLMs: What 18 Models Show on DeepSWE", 2026-09-21. https://fireworks.ai/blog/llm-model-routing-deepswe . Oracle 97.6% at $1.88 vs best single 74.1% at $6.52; hindsight oracle, no overhead or cache charge stated.
- Also: Agarwal et al., "Switchcraft", arXiv 2605.07112 (v2 Oct 2026), 78.3% accuracy at 59% lower cost than best single model; abstract silent on cache. https://arxiv.org/abs/2605.07112 ; Madeyski, "Triage", arXiv 2604.07494. https://arxiv.org/abs/2604.07494 . JFrog's "Why Model Routing Backfires" (2026-07-23) has no original measurements (https://jfrog.com/blog/why-model-routing-backfires); do not cite it for numbers.
- In corpus: RouterBench, MTRouter, Router-R1 and the router set.
- Verdict PARTLY. Not yet done independently: billed-dollar comparison on real harness traffic, router and judge cost charged, cache loss measured, against best single model including its cache.

### 9. Harness-specific savings of the same compressor
- PointFive, "Token reduction is not cost reduction", blog 2026-08-06 (upd. 2026-09-17). https://www.pointfive.co/blog/token-reduction-is-not-cost-reduction . Headroom +48.4% pooled billed cost; RTK-ML -38.4% tool-output tokens but +6.8% cost; RTK -2.7% (CI crosses zero). Claude Code only. Note: your "+48%" matches this number for Headroom on Claude Code; check that you are not re-deriving their figure. PointFive sells cost tooling.
- Dasein, "Fact vs fiction: compression vendor claims, measured", Claude Code + Sonnet 4.6, 100 SWE-bench Verified, 2026-07-04. https://raw.githack.com/daseinlabs/code-compression-bench/master/FACT-VS-FICTION.md . RTK +13%, Headroom +44%, Parsec -39%. Dasein-sponsored.
- Quesma, 2026-09-11 (above). RTK: Claude Code with Fable 5.0 -5% bill (+1% avg per-task, no clear difference), OpenCode with DeepSeek V4 Pro +5% bill (+17% avg per-task). This is a same-tool, two-harness comparison already.
- Verdict COVERED for "token reduction is not cost reduction"; PARTLY for the harness-dependence claim (Quesma and Dasein cover two harnesses with different models). Open: same model, three or more harnesses, cache-isolated, with a mechanism (extra turns, cache-prefix breakage).
- Sharper title: "Same Compressor, Same Model, Different Harness: Why Output Compression Moves Billed Cost in Opposite Directions".

### 10. Retry and iteration caps
- Kiecker et al., "Is Three the Magic Number? An Empirical Evaluation of LLM-Based Repair Loops", arXiv 2607.05197, Jul 2026. https://arxiv.org/abs/2607.05197 . Most gain in the first 3-4 repair rounds; recommends reporting repair budget as a variable. Code generation, test generation, translation with low-cost LLMs; not agentic sessions.
- Meir et al., "More Bang for the Buck... Reset and Discard (ReD)", arXiv 2601.21522, Jan 2026 (v3 Sep 2026). https://arxiv.org/abs/2601.21522 . Coverage@cost with diminishing returns; HumanEval, GSM8K, MMLU-Pro.
- Bjarnason et al. 2602.07150: run-to-run variance 2.2-6.0 points affects any cap-tuning claim.
- Verdict PARTLY. Sharper title: "When Does Another Attempt Stop Paying? Dollar-Denominated Stopping Rules for Coding-Agent Retries and Step Caps".

### 11. Router attack surface and strong-model share ceilings
- Tang et al., "Route to Rome Attack: Directing LLM Routers to Expensive Models via Adversarial Suffix Optimization", arXiv 2604.15022, Apr 2026 (ACL 2026). https://arxiv.org/abs/2604.15022 . Surrogate router plus suffix; raises expensive-model routing on open and commercial routers. No numbers, caps or defences on the abstract page.
- Zhang et al., "RerouteGuard: Understanding and Mitigating Adversarial Risks for LLM Routing", arXiv 2601.21380, Jan 2026. https://arxiv.org/abs/2601.21380 . Cost escalation, quality hijack, safety bypass; embedding detector over 99% detection.
- In corpus: "Rerouting LLM Routers" (control-plane integrity, confounder gadgets).
- Verdict PARTLY. Prior work attacks and filters inputs; a ceiling on strong-model share enforced by the control plane (so an attack costs at most X) is a different defence and not found. Sharper title: "Bounding the Bill, Not Detecting the Prompt: Strong-Model Share Ceilings as a Router Defence".

### 12. Detect, measure, apply: gateway vs transcripts
- Zhu et al., "Redundant or Necessary? A Benchmark for Detecting Redundant Steps in Agent Trajectories" (RedundancyBench), arXiv 2605.29893, May 2026 (v2 Oct 2026). https://arxiv.org/abs/2605.29893 . 1,920 trajectories, 3,613 step labels; hard even for Claude-Opus-5.
- metermaidai, "Agent Waste Index", Hugging Face forum, 2026-09-17. https://discuss.huggingface.co/t/agent-waste-index-what-341-054-public-coding-agent-runs-wasted/180539 . 341,054 public runs; loops, blind retries, oversized tool output; commenters note long runs may be hard tasks, not waste. Forum post, not a paper.
- Systima via Eden AI (above): logging-proxy method.
- Verdict OPEN. No source compares what a wire-level gateway can detect versus what a CLI transcript shows (the 12-detect-measure-apply split). Not found: any paper on this comparison.

### 13. Stale prices and invoice canaries
- LiteLLM cost-discrepancy doc (above): says a stale model-price map is one of three causes of mismatch.
- Search results from Langfuse, Datadog and a dev.to post say stale pricing and non-exclusive buckets cause drift; one practitioner post says no measured distribution of tracked-vs-invoice drift exists. I did not open these pages.
- Not found: any paper, measurement, or design for price-book versioning or canaries. Verdict OPEN. Low academic weight; better as an engineering note or a section of 1 or 2.

### 14. System paper
- Agentgateway v1.3.0 and Portkey (above): product-level gateways with per-tool spend and hard limits.
- Switchcraft (Microsoft-affiliated authors per the page list) and SAAR (vLLM) cover routing only.
- Not found: an academic system paper for a harness-agnostic cost control plane over API and CLI backends. Verdict PARTLY (products exist). Publish last, citing results from 1, 3, 4, 6, 8.

## Notes and caveats
- Several "papers" are vendor blogs with commercial interests (PointFive, Dasein, Fireworks, LiteLLM, Eden AI, Portkey). Cite them as vendor reports.
- Fetch depth: for most arXiv items I read the abstract page only. Claims about full-text content (cache isolation, overhead charging) are "not stated on the abstract page", not "absent from the paper". Read full texts of 2607.12161, 2608.01347, 2607.00053, 2605.18859 and 2606.04056 before final positioning.
- Dates in this environment run to Nov 2026; arXiv IDs 2604 to 2609 are 2026 submissions.
- Not opened, so not cited: AI Agents That Matter (2407.01502), TwinRouterBench authors, Anthropic and OpenAI official caching docs, the dev.to TTL posts.

## Suggested priority
1. Paper 6 (methods, strongest gap), 2. Paper 7 (clearest OPEN), 3. Paper 8 and 4 (partly covered, sharper angles above), 4. Paper 12 and 13 (open but thin; fold into 1 or 2), 5. Paper 9 only as a controlled replication, 6. Paper 1 should be written fast since 2607.12161 and 2608.01347 are already claiming the metric.
