# Token economics: what 287 sources teach

Spend less on LLM tokens by fixing four things in order: measure cost per finished task, keep prompts cache-friendly, send low-difficulty work to cheap models, and cap output and reasoning. Routing gets the most attention. Caching and output control come first because the sources measure larger, more reliable savings there.

This guide combines what three readers took from the 287-source corpus in `research/`. Claude read 92 documents in its own shard plus 69 that Codex could not finish. Kiro read 93. Codex read 24 before hitting its usage limit (resets 8:27 PM) and has no learnings file. Every number below comes from a model-written note on a paper or vendor page. I did not read the papers myself. Bracketed numbers are corpus ids: look them up in `INDEX.md` and `corpus/<id>.txt`.

**How to trust the numbers.** A figure is one of three kinds:
- *Price list.* A vendor states a rate. It records the list, not a saving.
- *Self-reported.* The authors measured their own method on their own benchmark. Treat as a claim.
- *Independent.* Someone outside the project measured it. Rare. The guide marks these.

**Terms used below.** Generative Pre-trained Transformer (GPT): OpenAI's model family. Massive Multitask Language Understanding (MMLU): a multiple-choice knowledge benchmark. Mathematics Aptitude Test of Heuristics (MATH): a competition-math benchmark. Retrieval-augmented generation (RAG): fetch relevant passages, then prompt with only those. Key-value (KV) cache: the attention state a server keeps per request. Cost-Spectrum Contrastive Router (CSCR): a router in section 4. Generative Pre-trained Transformer Quantization (GPTQ): a method for shrinking weights to 3-4 bits. Floating-point operations (FLOPs): a compute count. Service-level agreement (SLA): an uptime promise. Exact match (EM): a scoring rule that counts only identical answers.

## 1. Where the money goes

**Output and reasoning tokens cost more than input tokens, and they cost time.** Output typically bills at 5x the input rate. Claude Sonnet 4.6 charges $3.00 in and $15.00 out per million tokens [214]. Halving output tokens can cut latency about 50%. Halving the prompt cuts it 1-5% [196]. Reasoning tokens bill at the output rate and fill the context window. OpenAI advises reserving at least 25,000 for them [197].

**Reasoning models write far more.** On AIME24, Qwen2.5-32B-Instruct averaged 770 tokens and QwQ averaged 6,067 [135]. One benchmark run cost $3.47 for a model with a 4-8x output blowup, against $0.25-$0.97 for most peers [065].

**Languages cost different amounts.** Non-Latin scripts need up to 5x more tokens, and Telugu and Amharic cost up to 4x English on XLSUM [100]. Check this before you pick a model for a non-English product.

**Measure cost per successful task, not cost per token.** On BrowseComp, GPT-5.6 Luna scored 84.04% at $1.33. GPT-5.5 scored 84.36% at $33.27 three months earlier [207]. The sticker price per token hid a 25x gap. Frontier cost per correct answer on MATH-500 halved every 2.6 months [122].

## 2. Caching: the biggest lever for agents

Agent loops resend the same prefix every turn. A cache read costs about a tenth of a normal input token.

| Vendor / model | Cache read | Cache write | Source |
|---|---|---|---|
| Anthropic Claude (most) | 0.1x input | about 1.25x (5 min) | [199][283] |
| OpenAI GPT-5.6+ | 0.1x | 1.25x (30 min) or 2.5x (12 h) | [201] |
| Claude Fable 5.1 | 2.5% of input | not in note | [214] |
| Gemini implicit | 0.25x (75% off) | none | [121] |

One write plus nine reads over ten requests costs 2.15x instead of 10x uncached [201]. Fireworks reports an average 90k-token prompt that is mostly cached [258]. NVIDIA reports 85-97% hit rates in Claude Code sessions [167].

**A cache needs a byte-identical prefix.** Putting the current time at the top of a system prompt dropped reuse from 87% to 3% and raised the cost of the same 30-message chat 2.2-2.9x [224]. Rules that follow:
1. Put static content first (tools, system prompt, documents). Put variable content last.
2. Put timestamps and request ids at the end of the newest user message.
3. Do not change tools, model, effort or verbosity mid-task. Each change turns cached input into full-price input [204].
4. Send a stable session key so requests reach the replica that holds your cache [221][231][256].
5. Check the usage fields on every response. A gateway that drops `cache_control` markers bills the whole conversation uncached each turn [071].

**Short prompts can lose money.** Prefixes under 1,024 tokens get no OpenAI caching [201]. A cache write with no later read costs 1.25x [231]. Minimum cacheable prefixes run 512, 1,024 or 4,096 tokens by model on Bedrock [157].

**Count tokens in separate buckets.** OpenAI's `prompt_tokens` includes cached tokens. Anthropic's `input_tokens` excludes them. Adding both naively double-counts cache reads [233].

## 3. Batch and tier pricing

Move anything that can wait 24 hours to a batch API. Batch is 50% off at OpenAI [111], Azure [152], Bedrock [159][160], Anthropic [219], Mistral [174], Gemini [281] and Fireworks [259]. OpenAI Flex is priced at batch rates but answers synchronously [195]. On Gemini 3+ the batch and cache discounts stack to 95% off cached input. On Gemini 2.5 they do not [281]. Priority tier costs 1.75x list, applied after the cache discount, and carries a 99.5% uptime SLA [176].

Good batch jobs: evals, bulk classification, embeddings, document processing.

## 4. Routing: send each task to the right model

A router looks at a request and picks a model. Three families exist.

**Two-model routers** choose between one strong and one weak model.
- *RouteLLM* trains on Chatbot Arena human preference data. It reached 95% of GPT-4 quality at 3.66x lower cost on MT Bench, but only 1.41x on MMLU and 1.49x on GSM8K [001].
- *Hybrid LLM* sends queries the small model will likely match to the small model. It cut large-model calls by up to 40% when the model pair suited it [003].

**Pool routers** choose among many models.
- *RouterDC* trains with contrastive learning so one query maps to several good models [015].
- *GraphRouter* treats model choice as edge prediction on a task-query-model graph [004].
- *EmbedLLM* learns a compact vector per model from a model-by-question correctness matrix [016].
- *CSCR* puts prompts and models in one embedding space and picks with one nearest-neighbor lookup. Its training favors the cheapest accurate expert [020].

**Agent routers** switch models across turns.
- *MTRouter* embeds history and model together. It gained from selective, stable switching, not from switching after every error [008].
- *Router-R1* trains a small model with reinforcement learning to alternate "think" and "route" steps. The reward includes a cost term, so it learns to try cheap models first [005].

**Cascades** try the cheap model first and escalate on doubt. FrugalGPT's learned three-model cascade matched the best single model at 59.2-98.3% lower API cost [021].

### Which model is trained for what

No source ranks models by task in a stable way. What exists is task labels attached to routers:
- *Preference-based labels.* Arch-Router (1.5B) maps a conversation to a route name you define, such as "code review" or "contract summary" [011][012]. You decide which model serves each route.
- *Skill profiles.* BELLA picks the cheapest model that meets a task's stated skill needs and explains why [042].
- *Capability instructions.* MODEL-SAT gives each model a small aptitude test. A pool of sub-10B models then matched a ~70B model [017].
- *Seven-question classifier.* s1 labels category, difficulty, stakes, tool need, vision need, long-context need and follow-up in about 14 ms on a CPU [018].
- *Cheap classifier in front of an agent.* A near-free classifier sent only complex tasks to a stronger model. It solved 50 of 50 tasks. Flash-Lite alone missed 6 of 25 hard ones [052].

For real work, benchmark model, harness and hosting together on your own repositories. In one 21-task sample, task-level routing lowered total cost with a modest drop in mean quality [051].

### How to train a router

The notes agree on this recipe:
1. **Collect labels.** Use preference data (Arena votes) for breadth and a small gold-labeled set for truth. RouteLLM routers trained on Arena alone were near random on MMLU and GSM8K until about 1,500 gold samples (under 2% of the data) were added [001]. Meta-Router models the bias between the two label sources [013].
2. **Balance the labels.** A router trained on logs where one model served nearly everything learned to predict that model (94.2% of labels) [019].
3. **Pick a model type.** K-nearest neighbors on prompt embeddings or a small MLP is enough for a baseline. RouterBench's best KNN used 40 neighbors and `all-MiniLM-L12-v2` [002]. Matrix factorization [016] and contrastive learning [015][020] come next. Reinforcement learning with a quality-minus-cost reward is the agent version [005].
4. **Make cost part of the objective.** RouterBench maximizes `λ × predicted quality − cost` [002]. CSCR bakes cost into training [020].
5. **Evaluate against the right baseline.** See below.

Training-free option: PORT routes online under per-model token budgets using nearest-neighbor lookup over past queries [007]. FLARE predicts output length to estimate cost and latency [009].

### Does routing actually pay?

**The evidence conflicts.** Academic papers report large savings [004][009][017][020][045]. Fair re-evaluations do not.
- LLMRouterBench (400K instances, 33 models, 10 routers) found most routers nearly tied. OpenRouter scored −24.7% against the best single model (GPT-5). The best routers gained up to 4% accuracy and 31.7% cost reduction [006].
- RouterArena (12 routers) found no router wins every metric, commercial routers are not automatically better, and all fall short of an oracle. MIRT-BERT scored 66.9% at $0.15 per 1,000 queries. GPT-5 scored 74.0% at $14.02. RouteLLM scored 48.1 [046].
- Zen Router's own RouterBench test scored below a fixed pick of one model [019].
- RouterBench: simple predictive routers matched the best model at similar cost but did not consistently beat the convex hull of the pool. Only a cascade with a perfect judge did [002].

**What to do with that.**
1. Benchmark "best single model" first. Your router must beat it after overhead.
2. Curate a small pool of complementary models. Adding models rarely helps [006].
3. Prefer a cheap classifier over a big-model judge. Router latency in RouterArena ran from 11.1 to 546.8 ms [046]. A 1.5B router took 51 ms against about 1,450 ms for a proprietary model [011].
4. Count cache loss. Switching models forfeits cached prefixes [192][204][228]. No note measures this net effect. That is the largest unknown.
5. Price errors. On hard MATH, reasoning models cost 10-100x more per query, yet win once an error costs more than $0.20 (the abstract says $0.01) [123]. A single large model beat cascades above a $0.10 error price. Cascades win only with a strong self-verifier [123].

**Cascade math.** With a cost ratio of 1 to 2.7, break-even acceptance is 1/2.7, about 0.37. At 80% acceptance the cost is 1.54 against 2.7, a 43% saving [028]. Summed token log-probability is a biased deferral score because of length bias [022]. Conformal prediction gives a finite-sample accuracy bound [028].

**Vendor routers.** Treat savings as claims. GitHub Copilot Auto says about 10% [155]. Kiro Auto says about 23% against always-Sonnet-4 [162]. OpenRouter's Auto Router picks model and reasoning effort [228]. Its newer version routes by what the community spends on per task type [230]. One OpenRouter default policy cost more per task than the version before it [228]. Bedrock routes between two models in one family [158]. Azure Foundry and Cloudflare offer similar routers with no cost data [149][192].

**Gateways** (LiteLLM, Portkey, Vercel, Cloudflare, OpenRouter) give you fallbacks, budgets and per-key cost reports. Vercel measured that failover rescued 3.5% of requests across its fleet [246]. Budgets are soft caps and can overshoot [234].

## 5. Cut reasoning and output

**Cap the thinking budget.** Reasoning models overthink low-difficulty questions. QwQ-plus averaged 5,738 tokens (3,092 in reflection). Claude-3.7-Sonnet used under 1,000 at similar accuracy [093]. Use effort levels. Drop from high to medium when a model overthinks [282][270].

**Methods, with their limits:**

| Method | Result | Catch | Source |
|---|---|---|---|
| L1 (LCPO) | Beat S1 by 20-25% absolute at 512 and 1,024-token budgets | Needs training access | [095] |
| NoWait | Cut chain-of-thought 27%-51% | Hurt distilled Qwen3 4B/8B/14B | [091] |
| CoThink | 21.1% fewer tokens, +1.66% accuracy | Open models | [135] |
| "Be concise" prompt | 48.70% less output, 22.67% less total cost | Cost GPT-3.5 27.69% accuracy on math | [104] |
| Chain of Unconscious Thought | About 47.6% fewer tokens | Failed on QwQ-32B; paper also says 20.51% | [090] |
| Compute-optimal allocation | Matched best-of-N with 2-4x less compute | Self-reported | [094] |

Most of these were tested on open-weight models where you control the logits. Hosted APIs hide reasoning tokens, so they may not transfer [091].

**Majority voting did not pay.** Cost-of-pass analysis found 0% economic benefit [122]. Self-MoA found that repeated samples from the one strongest model beat mixing models by 6.6 points at half the forward passes [032]. "More Agents Is All You Need" claims the opposite [033].

## 6. Cut input

**Compression.** LLMLingua squeezed GSM8K prompts 20x (2,366 to 117 tokens) at 77.33 EM against 78.85 full-shot. It cut GPT-3.5 cost from $5.2 to $0.5, an estimate from pricing [079]. LLMLingua-2 is 3-6x faster at 2-5x compression [081]. Attention-guided RAG pruning reaches up to 6.3x [088]. These ran on 2023-2024 models and tokenizers. Re-test before you rely on them.

**RAG versus long context.** Retrieval often beats stuffing the whole window. Order-Preserving RAG scored 44.43 F1 on En.QA with 16K tokens. The same Llama-3.1-70B scored 34.32 with 128K [118]. SELF-ROUTE (try RAG, fall back to long context) used 38.39% of long-context tokens on Gemini-1.5-Pro at similar quality [117]. No approach wins everywhere. Long context won on reasoning and comparison tasks, and RAG won at 128k by 3.68% on average [119].

**Agent hygiene.** Context editing cut tokens 84% in a 100-turn search test [268]. Concise tool responses used 72 tokens against 206 [284]. Claude Code caps tool responses at 25,000 tokens by default [284]. Repeated behaviors (re-reading, similar scripts, rerunning tests) appeared in 79-98% of coding tasks and cost 6.86-22.75%. Short developer-written rules cut cost 7.88-41.73% in 6 of 8 settings. A code-graph retrieval tool raised cost up to 28.14% [059].

**Compaction can lose money.** A Grok cookbook measured three compactions at 1.4-3.3 cents each, removing only 600-900 tokens. The next turn also missed the cache [224]. The break-even is unknown.

## 7. Serving your own models

Self-hosting wins on utilization, not on list GPU price.

Together AI's example puts the crossover near 72M tokens per day (H100 at $3 per hour against $1 per million tokens) [277]. An H100 replica at $5.49 per hour is about $132 a day. Steady low-volume traffic is the worst case [278]. Cohere's analysis says owning beats renting at about four hours of use per day [180]. Epoch's model gives about $0.11 per million tokens for Llama 3 70B at 100% utilization, which implies about 17% in its own table [062]. H100 hourly prices in the notes run from $2 to $10.

**What lowers cost per token:**
- *Continuous batching.* Orca reported 36.9x over FasterTransformer [109].
- *Paged KV memory.* vLLM's PagedAttention gave 2-4x throughput. Older systems used only 20.4-38.2% of KV memory for real tokens [073].
- *Phase separation.* DistServe reported 2.0-4.6x over vLLM on chat [106]. Sarathi-Serve reported 2.6-5.6x capacity [110]. NVIDIA Dynamo claims up to 30x on DeepSeek-R1 671B, explicitly projected [164].
- *Quantization.* GPTQ at 3-4 bits gave 3.25-4.5x generation speedup with at most 0.03 perplexity loss [108].
- *KV compression.* kvtc compressed KV about 20x within 1 point of vanilla [074].
- *Speculative decoding.* A small draft model proposes tokens and the large model checks them. Gains are 2-3x with identical output [132]. Acceptance collapses to about 1.1 past ~20K output tokens unless the draft adapts online [027]. For gpt-oss-20b to 120b, gains were marginal because active parameters are close (3B and 5B) [274].
- *Mixture of experts.* Cost follows active parameters. DeepSeekMoE 16B used 39.6% of LLaMA2 7B compute [034].
- *Autoscaling.* Databricks saved over 80% GPU against static provisioning [185].

The speedups above use different baselines, hardware and workloads. Do not compare them to each other.

**Small models for narrow jobs.** Labeling 900k samples with Llama 3.1 70B cost about $70. The fine-tuned small encoder then ran about 80x cheaper per hour on CPU [129]. NVIDIA estimates 40-70% of an agent's calls could use small models at 10-30x lower cost. That is a position paper's estimate, not a measurement [041]. Perplexity cut one feature's cost about 4x ($0.62M a year) with no significant difference in a 2-week A/B test [272].

## 8. Pricing and the market

**Prices fall fast, unevenly.** Input prices fell about 600x from GPT-3 ($60 per million, June 2020) to Gemini 2.0 Flash ($0.10, February 2025). Half-lives: economy tier 1.10 years, mid tier 1.55, flagship 3.59 [061]. GPT-4-class fell from $30/$60 to $2.50/$10 in 16 months [134].

**Demand barely reacts to price.** Across over 100T OpenRouter tokens, a 10% price drop raised usage 0.5-0.7%. Median cost was $0.73 per million. Reasoning models passed 50% of usage. Open-weight models reached about a third [226]. Quality and reliability win, not the lowest price. The study is single-platform and co-authored by the operator.

**Billing is moving to tokens.** Cursor moved to a $20 usage pool at API prices because hard requests cost about 10x simple ones [265]. GitHub Copilot moved to usage-based billing on June 1, 2026, with 1 credit equal to $0.01 [211][214]. Under legacy multipliers Opus 4.8 cost 27 against Haiku 4.5 at 0.33, about 82x. In token price the gap is far smaller [211][214]. Eighty percent of firms missed AI infrastructure forecasts by over 25% (a second-hand survey figure inside a vendor page) [180].

## 9. Measure first

Follow this order: track, attribute, control, optimize [233].
1. Record each call once with mutually exclusive token buckets.
2. Attribute spend per developer, repository and task.
3. Model tiered pricing. Claude Sonnet 4.5 and Gemini 2.5 Pro charge more above 200K input [233][270].
4. Enforce budgets at a gateway.
5. Remember SDK cost figures are client-side estimates, not billing [216].

Tools in the corpus: ccusage, Langfuse, Helicone (maintenance-only since March 2026), LiteLLM, Portkey. See `github-repos.md`.

## 10. What the sources disagree on

| Question | Side A | Side B |
|---|---|---|
| Do routers beat one good model? | Papers report big savings [004][020][045] | Fair benchmark says most tie or lose [006][046] |
| Do cascades pay? | 43% saving at 80% acceptance [028] | Single large model wins above $0.10 error price [123] |
| RAG or long context? | Long context wins on average [117] | RAG wins at 128k [119] |
| Speculative decoding | Stable 2-3x [132][025] | Collapses on long outputs [027] |
| Compaction | Core technique [084][270] | Costs more on short chats [224] |
| More agents? | Scaling with count [033] | One strong model sampled repeatedly wins [032] |
| US-China cost gap | 63x training cost [061] | Per-FLOP gap not significant (p=0.228) [061] |

Smaller conflicts inside single papers: the critical error price in [123] is $0.01 in the abstract and $0.20 in the body. NoWait's "27-51%" shrinks to 13-16% on Qwen3-32B [091]. "Up to 70%" token savings from Anthropic's tool use averaged 14% for early users [068][070].

## 9b. Which claims to discount

**Closest to independent:** vLLM's 2-4x throughput, widely adopted [073]; GPTQ, reproducible and open [108]; LLMRouterBench [006]; the OpenRouter usage study [226]; the token-count measurement of language cost [100]; Artificial Analysis's GDPval-AA run on Claude Opus 4.6 [270].

**Treat as claims:**
- Every vendor "up to X%": caching 90% [068], OpenAI 80% latency [203], Helicone 90% [236], Fireworks up to 4x and 99.6% cache hits [260].
- Vendor router savings with no quality evidence [155][162][149][192][228].
- Academic wins on one benchmark family, some with parameter count or FLOPs standing in for dollars [005][007][020][028][034][091][135].
- Illustrative numbers: Helicone's 73% hit rate [239], OpenAI's 70% and over 90% hit rates [201], Portkey's "up to 20x" [240].
- Case studies: CFM "80x cheaper" on 105 test samples [129]; Anthropic's 39%, 29% and 84% on an undescribed internal eval [268]; OpenAI's "93.7% fewer tokens" on internal traffic [055].
- Forward-dated pages with future model names. Prices are snapshots [111][150][199][219][282].

## 10b. Open questions

1. What do routers save in production dollars, after overhead and cache loss?
2. When does compaction pay for itself?
3. Do reasoning-trimming methods work on hosted APIs?
4. Do 2023-2024 results hold with current tokenizers and prices?
5. What utilization do operators reach, and where is the self-hosting break-even?

## Do this next

1. **Turn on cost tracking per task** (30 minutes with ccusage or Langfuse). Nothing else is safe without it.
2. **Fix your prefix order** (1 hour): static first, timestamps last. Check the cached-token field on 20 real responses.
3. **Move one batchable job to a batch API** (1 hour). Evals are the first pick.
4. **Cap output and reasoning effort** on one endpoint (1 hour). Compare cost per correct answer before and after.
5. **Only then trial a router**, against "best single model" on your own tasks, with cache loss counted (about a day).

## Limits

- Codex's individual reading is partial (24 of 93 notes). Claude read the 69 it missed, so one reader's view covers those.
- All notes are model summaries. I spot-checked none against the source text.
- Five ai.meta.com pages returned HTTP 400 and are missing. Meta results are under-represented.
- Several sources are dated 2026 and use model names I could not verify. Prices are snapshots.
- Individual learnings: `notes/claude_learnings.md`, `notes/kiro_learnings.md`. Per-document notes: `notes/{claude,claude_extra,codex,kiro}/`.
