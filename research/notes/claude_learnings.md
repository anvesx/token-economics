# Learnings from notes/claude (92 notes on LLM token economics)

Source ids are the note numbers in brackets. Note 254 has no readable text and is not used. Where a note gives only a vendor figure, the lesson says so.

## 1. The 15 most important lessons

1. Output and reasoning tokens drive cost and latency more than input tokens. Cutting 50% of output tokens may cut about 50% of latency, while cutting 50% of the prompt gives only 1-5% [196]. Reasoning tokens bill at the output rate and fill context, and OpenAI advises reserving at least 25,000 tokens for them [197]. Output is typically 5x input price (Claude Sonnet 4.6 $3.00 in, $15.00 out per 1M [214]). Thinking models write 5-10x more on the same problem (AIME24 average: Qwen2.5-32B-Instruct 770 tokens, QwQ 6,067) [135]. A 4-8x output blowup made WiNGPT-3.0 cost $3.47 vs $0.25-$0.97 for most peers in the same benchmark [065].

2. Cache hit rate is the main cost lever for agent loops. On OpenAI GPT-5.6+, reads cost 0.1x (0.05x on GPT-6.1 Sol and Terra) and writes cost 1.25x (30m) or 2.5x (12h). One write plus nine reads over ten requests costs 2.15x vs 10x uncached [201]. Cached input is 10% of input price on most listed models and 2.5% on Claude Fable 5.1 [214]. Fireworks says its average prompt is about 90k tokens and mostly cached, with a 90% cached discount [258]. NVIDIA reports 85-97% cache hits in Claude Code sessions [167].

3. Caches break silently, so check usage fields instead of assuming a hit. Changing tools, model, effort, verbosity or early messages turns cached input into full-price input [204]. Claude Code advises avoiding mid-task model or effort switches and keeping MCP tool sets stable [071]. A gateway that drops cache_control markers bills the whole conversation uncached every turn [071]. Routers and gateways need a stable session id because switching models forfeits cached prefixes [192, 228, 248]. Minimum cacheable prefix varies: 512, 1,024 or 4,096 tokens by model on Bedrock [157]. Prefixes under 1,024 tokens get no OpenAI caching [201].

4. Latency-tolerant work should move to discounted tiers. Batch is 50% off at Mistral, Anthropic and Gemini [174, 220, 281]. OpenAI Flex is priced at Batch API rates [195]. On Gemini 3+ the batch and cache discounts stack to 95% on cached input, but on Gemini 2.5 they do not [281]. Priority tier costs 1.75x list, applied after the cache discount, and carries a 99.5% uptime SLA [176].

5. Routing saves real money, but the saving varies by workload and router. RouteLLM cut cost 3.66x vs random on MT Bench but only 1.41x on MMLU and 1.49x on GSM8K [001]. On RouterArena, vLLM-SR and CARROT cut cost about 35% with under 2% accuracy loss. GPT-5 scored 74.0% at $14.02 per 1k queries; MIRT-BERT scored 66.9% at $0.15 [046]. Router overhead is small in the RouteLLM cost model (at most 0.4% of GPT-4 generation cost) [001]. Measured router latency ranges from 11.1 ms to 546.8 ms [046].

6. Learned routers need in-domain, balanced labels. Arena-only RouteLLM routers were near random on MMLU and GSM8K until about 1,500 gold-labeled samples (under 2% of training data) were added [001]. A router trained on logs where one model served almost everything just predicted the majority model (94.2% of labels in Run A) [019]. On RouterArena, RouteLLM scored 48.1 and RouterDC 33.8 against MIRT-BERT at 66.9 [046].

7. A cascade saves money only if the small tier accepts enough queries. With cost ratio 1 : 2.7, break-even acceptance is 1/2.7 = about 0.37, and 80% acceptance gives 1.54 vs 2.7, a 43% saving [028]. The small tier pays for 16 samples before any escalation, and acceptance at alpha=0.10 ranged from 0% (MMLU-Pro, GPQA-Diamond) to 95.6% (Belebele-Eng) [028]. Summed token log-probability is a biased deferral score because of length bias [022].

8. Put a dollar value on errors before minimising tokens. On level-5 MATH, reasoning models cost 10-100x more per query with up to 10x the latency, yet win once an error costs more than $0.20 (body text; the abstract says $0.01) [123]. A single large model (Qwen3 235B-A22B) beats cascades above a $0.10 error price at zero latency price. The Llama3.1 405B to Qwen3 cascade is an exception because of strong self-verification [123].

9. Reasoning length can be cut, but the method and model type matter. LCPO (L1) beat S1 by 100-150% relative and 20-25% absolute at 512 and 1024 token budgets, and L1-Exact is about 1% below unconstrained DeepScaleR-4K [095]. NoWait cut chain-of-thought 27%-51% across five model series but degraded distilled Qwen3-4B/8B/14B [091]. CoThink cut tokens 21.1% on average with +1.66% accuracy [135]. "Be concise" CoT cut output 48.70% and total cost 22.67%, but cost GPT-3.5 27.69% accuracy on math [104]. Compute-optimal allocation beat best-of-N with 2-4x less compute [094].

10. Coding agents waste a measurable share of spend on repeated behaviours. Subsumed retrieval, similar script generation and test re-execution appear in 79.00-98.00% of tasks and cost 6.86-22.75% [059]. Short developer-written rules (DevSkills) cut cost 7.88-41.73% in 6 of 8 settings, while a code-graph retrieval tool raised cost up to 28.14% [059]. Context editing cut tokens 84% in a 100-turn search test [268]. Concise tool responses use 72 tokens vs 206 [284]. Tool output capped at 10k tokens [249]; Claude Code caps tool responses at 25,000 by default [284].

11. Shrinking input is a second lever, with accuracy conditions. LLMLingua compressed GSM8K prompts 20x (2,366 to 117 tokens) with 77.33 EM vs 78.85 full-shot, and cut GPT-3.5 cost on GSM8K from $5.2 to $0.5 (estimated from pricing) [079]. SELF-ROUTE (RAG first, long-context fallback) used 38.39% of long-context tokens on Gemini-1.5-Pro and 61.40% on GPT-4O at similar quality [117]. At 128k, RAG beat long-context by 3.68% on average, but long-context won reasoning and comparison tasks for GPT-4o and Claude-3.5-Sonnet [119].

12. Self-hosting economics are set by utilization, not list GPU price. Together AI's example puts the dedicated-vs-serverless crossover near 72M tokens per day (H100 at $3/hour vs $1 per 1M tokens) [277]. An H100 replica at $5.49/hour is about $132/day, and steady low-volume 24/7 traffic is the worst case [278]. Cohere's vendor analysis says owning beats renting at about four hours of use per day [180]. Epoch's model gives about $0.11 per 1M tokens for Llama 3 70B at 100% H100 utilization, implying about 17% in its own table [062].

13. For self-hosted serving, batching, phase separation and KV memory set the cost per token. Orca reported 36.9x over FasterTransformer [109]. Sarathi-Serve reported 2.6x to 5.6x capacity over vLLM [110]. DistServe reported 2.0x-4.6x over vLLM on chat and up to 7.4x more requests [106]. Mistral Large 2 KV reads alone set a floor of $6.06 per 1M output tokens at 100K context [062]. kvtc compressed KV about 20x within 1 point of vanilla [074]. Per-token cost follows activated parameters (DeepSeekMoE 16B: 39.6% of LLaMA2 7B compute) [034].

14. Small specialised models and tokenizer efficiency can beat paying frontier rates per token. One-time labelling of 900k samples with Llama 3.1 70B cost about $70 and the fine-tuned small encoder ran about 80x cheaper per hour on CPU [129]. Perplexity cut one feature's cost about 4x ($0.62M per year) with no significant difference in a 2-week A/B test [272]. Non-Latin scripts need up to 5x more tokens, and Telugu and Amharic cost up to 4x English on XLSUM [100]. Mistral-Small used 2,113,182 input tokens vs about 1.3M for peers on Chinese [065].

15. Per-request and flat pricing is giving way to token-based billing, so track tokens and cost per task. Cursor moved to a $20 usage pool at API prices because hard requests cost about an order of magnitude more than simple ones [265]. GitHub Copilot moved to usage-based billing on June 1, 2026, with 1 credit = $0.01 [211, 214]. Under legacy multipliers Opus 4.8 cost 27 vs Haiku 4.5 at 0.33, about 82x [211]. 80% of firms missed AI infrastructure forecasts by more than 25% [180]. SDK cost figures are client-side estimates, not billing [216].

## 2. Where sources disagree or numbers conflict

- Critical error price for reasoning models: $0.01 in the abstract and conclusion, $0.20 in the body and Figure 3 of the same paper [123].
- Do cascades pay? A cascade saves 43% at 80% acceptance [028], but a single large model beats cascades above $0.10 error price, and only a strong-verifier cascade (405B to Qwen3) wins [123]. Both are self-reported; the cost bases differ (fixed ratio 2.7 vs dollar-priced API calls).
- RouteLLM: 95% of GPT-4 quality at 3.66x savings on MT Bench [001], but RouteLLM scored 48.1 accuracy (47.0% at $0.27) in a later comparison, near the bottom of 12 routers [046]. The test sets and baselines differ.
- Router claims vs router behaviour: s1 reports routing agreement 0.742 on its own set but 0.60 on blind Claude Opus labels (n=100) [018]. Zen Router's own RouterBench result is below statically picking one model (AIQ 0.6248 vs untrained prior 0.7427) [019]. OpenRouter's default policy costs more per task than its prior generation [228].
- RouterArena internal mismatches: NIRT-BERT is 66.1 in the leaderboard figure but 62.0% in Table 6, and its cost is 378% in text vs 400% in a figure label [046].
- RAG vs long context: long-context beats RAG on average (+7.6% Gemini, +13.1% GPT-4O, +3.6% GPT-3.5-Turbo) [117], while at 128k RAG beats long-context by 3.68% [119]. 117 has GPT-3.5-Turbo 16k RAG beating LC on En.QA and En.MC, which fits 119's model-size and length dependence. Synthetic PassKey: RAG 80.34 vs LC 65.25, but 4.58 vs 69.32 with "special token" wording [117].
- NoWait: abstract range of 27%-51% shorter reasoning, but Qwen3-32B only 13%-16%, QwQ AIME 2024 -16%, and GPQA-Diamond -11.67% [091].
- Test-time compute saving: "2-4x" in the discussion, 4x (16 vs 64 generations) and 4x (64 vs 256) in the results [094].
- MoE training penalty: 2.4x-4.3x in the body vs 2.5-3.5x in the abstract [036].
- Fireworks Fast speedup: "~2x" and "2-3x" in the same post [258].
- H100 hourly price: $2 (Epoch model) [062], $3 (Together example) [277], $5.49 (Together list) [278], $10 (GCP, x1) vs H200 $5 (AWS, x1) [170]; H800 $2 [184]. The $0.11 per 1M tokens figure appears for a model at 100% utilization [062] and as Lenovo's owned-H100 figure [180]; these are different bases.
- Request multipliers vs token prices: Opus 4.8 to Sonnet 4.6 is 3x in Copilot's legacy multipliers (27 vs 9) [211] but 1.67x in token price ($5/$25 vs $3/$15) [214]. Haiku 4.5 to Sonnet 4.6 is 27x vs 3x. Sonnet 4.6 is 3x Haiku 4.5 in token price in both [059, 214].
- Cache parameters differ by vendor: Claude TTL 5 min or 1 h [071, 157], GPT-5.6+ 30 min and 12 h [157, 201], Nova 5 min [157]. Discounts: up to 90% [176, 258, 281], up to 95% [201, 281], 2.5% of input on Fable 5.1 [214].
- Serving speedups use incompatible baselines: 36.9x [109], 7.4x [106], 5.6x [110], 6x simulated and 3x [038], up to 7x on InferenceX [166]. None share a baseline, hardware or workload.
- Internal inconsistency in HF pricing: $0.064 vs $0.067 per hour on the same CPU example [170].
- Chain-of-thought length: thinking models 5-10x longer [135] vs `<think>` about 40% of generated tokens in agent traces [167]. These measure different workloads.

## 3. Hype vs measured

Closest to independent measurement (still imperfect):
- Token-count measurement of language cost, academic, not billing-based [100].
- Blind Claude Opus labels (n=100, about +-8 points) on the s1 router, which show a gap vs its own held-out results [018].
- A 2-week A/B test with no significant difference, but vendor-run, one feature, 2023 [272].
- Trajectory measurements on 1,200 runs, but by the authors of the winning intervention [059].
- A roofline model checked against Artificial Analysis provider speeds and prices within about 2x, by one author [062].
- RouterArena comparisons of 12 routers, run by the platform's own authors and with different pools per router [046].
- LiveBench and HELM, run by their authors on their chosen models [049, 050].
- Gartner, IDC, McKinsey and Mavvrik survey numbers, quoted second-hand inside a vendor page [180].

Self-reported or vendor claims (treat as claims):
- Router vendor results with no cost data: Arch-Router "SOTA" with no figures [012], s1 [018], Foundry model router [149], Cloudflare Auto Router [192], OpenRouter [228].
- Vendor hardware: simulated 6x and 3x [038]; "up to 7x", "up to 4x" with baselines not described, cache pinning experimental [166]; Claude Code cache stats from NVIDIA's own undetailed analysis [167].
- Academic self-evaluations on one benchmark family: [001, 005, 007, 022, 028, 034, 036, 074, 077, 079, 082, 086, 091, 094, 095, 097, 104, 106, 110, 115, 117, 119, 123, 135]. Several use fixed cost ratios, token counts or FLOPs rather than dollars [005, 007, 028, 034, 091, 135].
- Illustrative numbers presented as examples: Helicone's 73% hit rate and $1,247 per month [239], OpenAI's 70% and over 90% hit rates [201], Portkey "up to 20x faster and cheaper" [240].
- Vendor case studies: CFM "80x cheaper" with a 105-sample test set and per-hour not per-task cost [129]; Cohere's total-cost analysis built on Lenovo and NVIDIA figures [180]; Fireworks quality parity and speed [258].
- Vendor postmortem and product claims: usage-limit link "we believe" [054]; Anthropic's 39%, 29% and 84% figures on an undescribed internal eval [268]; OpenAI's "more token efficient" Codex claim with no numbers [249].
- Price lists and rate tables are facts of a price list, not measured savings [145, 153, 170, 174, 176, 178, 211, 212, 214, 220, 278, 281]. Costs derived from them still depend on workload.

## 4. Five open questions

1. What do routers actually save in production dollars? The notes give savings against a random router [001], list-price estimates [046], or none [149, 192, 228], and one default policy costs more per task [228].
2. How much cache value does a router or fallback give up? Switching models loses cached prefixes [192, 204, 228], but no note measures a router's net cost after cache loss against a fixed model.
3. Do the reasoning-trimming methods work on hosted APIs? NoWait, L1 and CoThink were tested on open-weight models with visible logits or training access [091, 095, 135], and hidden reasoning tokens usually do not allow the same control [091].
4. Do 2023-2024 results still hold with current tokenizers and prices? Language cost [100], concise CoT [104], LLMLingua [079] and Perplexity's 4x [272] were measured on older models; no note repeats them.
5. What utilization do operators really reach, and where is the break-even? Break-evens rest on assumptions of 100% [065, 062], about 17% [062], or four hours per day [180], on H100 prices from $2 to $10 per hour [062, 170, 277, 278].
