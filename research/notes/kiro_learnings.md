# Kiro Learnings — LLM Token Economics

Synthesis of ~90 sources in `notes/kiro/`. Source ids in brackets refer to the note numbers.

## 1. The 15 most important lessons

1. **Token prices are in sustained exponential decline, but unevenly by tier.** Input prices fell ~600× from GPT-3 $60/M (Jun 2020) to Gemini 2.0 Flash $0.10/M (Feb 2025); economy-tier half-life is 1.10 yr, mid-tier 1.55 yr, flagship 3.59 yr (flagship barely fits exponential decay, R²=0.031) [061]. GPT-4-class fell from $30/$60 to $2.50/$10 in 16 months (~90% cut) [134]. Default to economy/mid models to capture most of this deflation, and treat flagship pricing as temporary.

2. **Optimize cost-per-successful-task, not cost-per-token.** The governing metric is dollars per correct answer, which combines price and success rate [052][122]. On BrowseComp, GPT-5.6 Luna hit 84.04% at $1.33 vs GPT-5.5's 84.36% at $33.27 three months earlier [207]; frontier cost-of-pass on MATH-500 halved every ~2.6 months and AIME-2024 every 7.1 months [122]. Match task type to the cheapest-per-correct-answer model family rather than the cheapest sticker price.

3. **Prompt caching is the single largest practical cost lever for repeated context.** Reported reductions: up to 90% cost and 85% latency on long prompts (Anthropic) [068][070]; Gemini implicit caching gives a flat 75% discount on cached prefixes [121]; Claude cache reads cost 0.1× base input [199][283]; OpenAI up to 80% latency on >10K-token prompts [203]; Fireworks 50% cached-input with cache-hit rates up to 99.6% on long agent sessions [257][260]. Structure prompts static-prefix-first, variable content last.

4. **Caching only works if the prefix is byte-identical — one volatile token at the top destroys it.** Putting the current time at the top of a system prompt dropped cache reuse from 87% to 3% and raised the cost of the same 30-message chat 2.2–2.9× [224]. Pin timestamps/request-ids to the end of the latest user message; keep tools, images, and thinking config stable [199][203][257]; and pass a stable session key so requests land on the replica holding the cache [221][231][256].

5. **Batch APIs give a flat ~50% discount for latency-tolerant work, across every major provider.** 50% off with 24-hour turnaround on OpenAI [111], Azure OpenAI [150 (Flex, synchronous) / 152 (Batch)], Amazon Bedrock [159][160], Anthropic Messages Batches [219], and Fireworks [259]; Together AI up to 50% [276]. Caching discounts stack on top of the batch discount [219][256]. Route evals, bulk classification, embedding, and document processing here.

6. **Routers rarely beat a well-chosen single model under fair evaluation — benchmark Best-Single first.** On a 400K-instance, 33-model benchmark most routers performed nearly identically, and commercial OpenRouter scored −24.7% PerfGain vs the Best-Single baseline (GPT-5); top routers gained only up to +4% accuracy and 31.7% cost reduction [006]. Real router methods still lag their oracle potential badly [045]. Gains, when real, mostly come from coarse domain routing, so curate a small high-complementarity pool rather than scaling the pool [006].

7. **Where routing does pay, it is cheap-classifier-in-front routing on a mixed pool, not a big-LLM judge.** A near-free structured classifier escalating only flagged-complex tasks solved 50/50 where Flash-Lite alone missed 6/25 hard tasks [052]; a 1.5B generative router matched/beat proprietary models at policy matching at 51±12 ms vs ~1450 ms [011]; vendor auto-routers claim ~10% (GitHub Copilot) [155] and ~23% (Kiro Auto vs always-Sonnet-4) [162] credit savings. A pool of 3–10 mostly-weak models with a capable router can beat a strong single model [045].

8. **Small/fine-tuned models can replace most agentic subtasks at 10–30× lower cost.** For repetitive, format-constrained agent steps, ~40–70% of a typical agent's LLM calls are SLM-replaceable (MetaGPT ~60%, Open Operator ~40%, Cradle ~70%), with 7B serving 10–30× cheaper than a 70–175B model [041]. Phi-4-Mini 3.8B matches 2×-larger models on math/coding via GQA + small LoRAs [156]. Route extraction/classification/routing to small models and reserve flagships for open reasoning [207][282].

9. **Speculative decoding is a near-free 2–3× latency win, but it decays on long outputs.** Lossless 2–3× speedup with identical output distribution and no retraining; pick a draft model ~100× smaller, tune γ from acceptance rate α [132]; distilling the draft adds ~20% more (up to 8× vs no-spec baseline) [025]. But acceptance length collapses toward ~1.1 beyond ~20K tokens; Test-Time Speculation restores it (up to +72% acceptance, 1.71–1.83× throughput) by adapting the draft online for free from the verification pass [027].

10. **KV-cache memory, not FLOPs, bounds serving cost — pack and pool it.** PagedAttention/vLLM cut KV waste (prior systems used only 20.4–38.2% of KV memory for real tokens) for 2–4× throughput at equal latency, more with shared prefixes (up to 3.58×) [073]. NVIDIA Dynamo's disaggregated prefill/decode + KV-aware routing claims up to 30× on DeepSeek-R1 671B [164]; segment-level pooling (TokenLake) 2.6× [076]; Databricks autoscaling on a cost-derived "model unit" saved >80% GPU vs static provisioning [185].

11. **Large reasoning models overthink, especially on easy questions — cap the reasoning budget.** LRMs burn large token budgets reflecting after already reaching the correct answer; Qwq-plus averaged 5,738 tokens (3,092 in reflection) vs Claude-3.7-Sonnet under 1,000, at comparable accuracy [093]. Prompt-side fixes: Constrained-CoT cut computation with maintained/improved accuracy [103], Chain of Unconscious Thought ~47.6% fewer tokens at ~2.8 pp accuracy cost [090]. Use effort levels (Claude low→max; drop from high to medium when overthinking) and budget forcing/early-exit [282][270][131][030].

12. **For long-context QA, retrieve-and-order beats dumping the full context — cheaper AND better.** Order-Preserving RAG scored 44.43 F1 on En.QA using only 16K retrieved tokens vs 34.32 F1 feeding the full 128K context to the same Llama-3.1-70B; answer quality follows an inverted-U in chunk count [118]. Task-agnostic prompt compression (LLMLingua-2, a small encoder) is 3–6× faster at 2–5× compression with near-parity [081]; attention-guided RAG pruning reaches up to 6.3× compression [088].

13. **Demand is largely price-inelastic — reliability and quality win, not the lowest token price.** Across >100T OpenRouter tokens, a 10% price drop produced only ~0.5–0.7% more usage; median cost was $0.73/1M, reasoning models exceeded 50% of usage, and open-weight models reached ~1/3 [226]. The market is not commoditized: build model-agnostic stacks and optimize cost-per-outcome, since cheap-but-unreliable models fail to win integration [226].

14. **Output tokens are the expensive ones — price and architect around that.** Output is billed ~3–5× input because generation is sequential/autoregressive while input encoding is parallelizable [134][133]; long-output requests, not long-input ones, dominate real serving cost [185]. This is also why Batch and flat per-token linear pricing (no volume discounts) are the constrained-efficient benchmark [134][064]; providers extract margin through subscriptions/credit tiers, not the token meter.

15. **Measure before optimizing — most cost surprises are measurement errors.** Track-attribute-control-optimize, in that order; record each call once with mutually-exclusive token buckets, because OpenAI-style `prompt_tokens` includes cached tokens while Anthropic `input_tokens` excludes them (inclusive counts silently double-count cache reads) [233]. Tiered pricing (e.g. Claude Sonnet 4.5 / Gemini 2.5 Pro charge more above 200K input) must be modeled explicitly [233][270]. Attribute spend per developer/repo/task and enforce budgets at a gateway, noting spend limits are soft caps that can overshoot [234][215][056][191][245][242].

## 2. Where sources disagree or numbers conflict

- **Does routing actually save money?** RouterEval frames routing as a powerful "model-level scaling up" where 3–10 candidates beat a strong single model [045], and GraphRouter/CSCR/FLARE/MODEL-SAT all report large savings [004][020][009][017]. But LLMRouterBench, re-evaluating 10 routers fairly over 400K instances, finds most routers nearly tie each other and several (including commercial OpenRouter, −24.7%) fail to beat Best-Single [006]. The academic self-reported wins and the independent benchmark conflict; [006] and [045] both agree real routers sit far below their oracle.

- **Headline reduction of Chain of Unconscious Thought is internally inconsistent.** The same paper reports both 47.62% and 20.51% token reduction depending on comparison/aggregation, and the method fails entirely on QwQ-32B [090].

- **"Up to" caching/tool numbers vs realistic averages.** Anthropic advertises token-efficient tool use "up to 70%" but the realistic early-user average is 14% [068][070]; caching's "up to 90% / 85%" are best-case for long prompts only [068][203]. For short, single-use prompts caching can cost *more* — GPT-5.6+ charges 1.25× for a cache write with no offsetting read [231].

- **Cache-read discount magnitude varies by provider and model.** Reads are 0.1× input on Anthropic/DeepSeek/Qwen, ~0.2–0.25× on Grok/Moonshot/Gemini/Z.AI, 0.25–0.5× on OpenAI/Groq, and as low as 0.025–0.05× on specific Claude models [199][231]; "cached ~10% of input" [175] vs "~1/4 of input" [224][225] are both true but model-specific.

- **Compaction: help or hidden cost?** Anthropic presents compaction as a core long-horizon technique [084][270][207], but a Grok cookbook measured 3 compactions costing 1.4–3.3¢ each while removing only 600–900 tokens, and the turn after each compaction missed the cache — net more expensive for short chats [224].

- **Ensembling more models/agents.** "More Agents Is All You Need" claims performance scales with agent count [033], while Self-MoA shows repeated samples from the single strongest model beat mixing models by 6.6 pts and at half the forward passes [032]; cost-of-pass found majority voting delivered 0% economic benefit [122]. Direct conflict on whether diversity or proposer quality matters.

- **US–China cost gap.** Training-cost gap cited as 63× (GPT-4.5 $340M vs DeepSeek-V3 $5.4M) and compute gap 115×, yet the per-FLOP cost difference is statistically insignificant (Welch t=1.25, p=0.228) [061] — the headline gap and the normalized gap tell opposite stories.

- **Speculative decoding durability.** [132] and [025] report stable 2–3× (and up to 8×) speedups; [027] shows those static speedups collapse to ~1.1× acceptance beyond ~20K output tokens unless adapted online. [274] separately found speculative decoding gave only marginal speedup for gpt-oss-20b→120b because active-param counts (3B vs 5B) are too close.

## 3. Hype vs measured

**Measured / independently credible:**
- vLLM PagedAttention 2–4× throughput — academic (SOSP'23) but independently and widely adopted; an independent reimplementation confirmed speculative decoding at 2–2.5× on Chinchilla 70B [073][132].
- GPTQ 3–4 bit at 3.25–4.5× generation speedup with ≤0.03 perplexity loss, ~4 GPU-hours for 175B — reproducible, open [108].
- LLMRouterBench's "routers barely beat Best-Single" — large (400K instances, 33 models), fair, cross-model, the strongest counter-hype result in the corpus [006].
- OpenRouter's 100T-token usage study — large-scale empirical, though single-platform and co-authored by the platform operator + a16z [226].
- GDPval-AA on Claude Opus 4.6 was run independently by Artificial Analysis; the rest of that launch's figures are partner testimonials [270].

**Hype / self-reported / best-case — discount accordingly:**
- Every vendor "up to X%" headline: Anthropic caching 90% / tools 70% (true average 14%) [068][070]; OpenAI 80% latency [203]; Helicone "cut spend by 90%" with no controlled study [236]; Fireworks "up to 4× vs vLLM," 99.6% cache, $4M→$800K customer quote [260]; NVIDIA Dynamo "up to 30×" (explicitly projected, one model/hardware/workload) [164].
- Vendor router savings with no benchmark or quality-parity evidence: GitHub Copilot Auto ~10% [155], Kiro Auto ~23% vs Sonnet-4 [162].
- Almost all routing/compression/reasoning-budget papers are self-reported by their authors on academic benchmarks (GSM8K, MMLU, MATH, LongBench), not production traffic [004][009][017][020][081][088][090][103][131] — and several may be partly contaminated in pretraining, giving an optimistic frontier [122].
- "Small Language Models are the Future of Agentic AI" is an explicit NVIDIA position paper; the 40–70% replaceable-call figures are authors' estimates, not measured, and NVIDIA sells edge/inference systems [041].
- OpenAI's GPT-5-Codex "93.7% fewer tokens" and GPT-5.6 cost figures are internal employee traffic / customer testimonials, not independent [055][207].
- Many docs/pricing pages are forward-dated (2026) with placeholder/future model names (gpt-6-luna, Opus 5.5, etc.), so treat specific prices as point-in-time snapshots [111][150][152][199][219][282][283].
- Several "cost" figures are proxies, not dollars: CSCR/EmbedLLM use parameter count as a cost proxy [020]; Perplexity's gpt-oss $/token numbers assume a $3.00/hr H200 rate they say is not their real price [274].

## 4. Five open questions

1. **Does per-query routing beat Best-Single in production, net of its own overhead?** The academic wins [004][009][017][020][045] and the fair benchmark [006] disagree, and both agree routers sit far below oracle. No source measures end-to-end routing cost (classifier calls + fallbacks + escalation + cache-rebuild on model switches) against a single well-chosen model on real traffic [006][045][230][245].

2. **What is the real, measured savings from SLM substitution in agentic systems?** The 40–70% replaceable-call claim is an estimate [041]; no source runs the 6-step LLM→SLM conversion on a live agent and reports actual cost-per-successful-task before/after with quality held constant.

3. **When does compaction/context-engineering pay for itself versus cost more?** [084][207][270] promote it; [224] shows it losing money on short chats and busting the cache on the next turn. The break-even (chat length, summary size, cache TTL, reuse frequency) is undetermined.

4. **How durable are speculative-decoding and caching speedups on long-horizon agent/reasoning workloads?** Acceptance length decays with output length [027] and cache hits are best-effort/short-lived (minutes) under real multi-tenant load [231][257][276]; there is no independent measurement of sustained speedup or hit-rate across a full agent session on shared infrastructure.

5. **Why is LLM demand so price-inelastic, and will it stay that way?** A 10% price drop moved usage only ~0.5–0.7% [226], implying quality/reliability dominate and the market isn't commoditized — but this is one platform over ~13 months. It is unknown whether elasticity differs by segment (enterprise vs hobbyist, interactive vs batch) or whether continued ~1.1–1.6-yr price halving [061] eventually triggers elastic, volume-driven demand.
