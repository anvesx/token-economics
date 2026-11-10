# R5 - Pricing, billing, limits, tiers, self-hosting, small models

Ids: [A-n] = research/ (API), [C-n] = research-cli-agents/. Tags: PL price-list, M measured, SR self-reported, IL illustrative. (guide) = taken from a synthesis guide, not re-checked in the note.

Conclusion: price is not a constant. Vendors differ on cache stacking, tier scope, token counting and window rules, and price lists expire. The layer needs a versioned, expiring price book and a formula with per-vendor flags. Subscription limits do not convert to tokens, so plan spend needs its own unit. Self-hosting and small models pay off only in narrow, measured cases.

## 1. Facts to build on

**Tiers [PL].**
- Batch is 50% off at OpenAI [A-111], Azure [A-152], Anthropic [A-219], Mistral [A-174], Groq [A-252], Fireworks [A-255], Bedrock [A-159], Gemini [A-281]. Together says "up to 50%", one named model [A-275]. xAI batch is 20%; xAI priority 2x; tool calls $5/1k [A-225].
- Windows: OpenAI 24h, 50,000 req [A-111]; Anthropic 24h, 100,000 req or 256 MB, errored/expired not billed, no streaming or fast mode [A-219]; Gemini 72h queue, outside SLA [A-281]; Azure batch not for fine-tuned models [A-152].
- Batch+cache stacking: Anthropic yes (hits best-effort 30-98%) [A-219]; Fireworks yes [A-255]; Groq no [A-252]; Gemini 3+ yes (95% off), 2.5 no [A-281]; Bedrock no cache in batch [A-157]; Mistral not stated [A-174].
- Flex: OpenAI at batch rates, 429 free, no auto-fallback [A-195]; Azure 50%, 429 not billed, no SLA [A-150].
- Priority: Mistral 1.75x after cache discount, 99.5% SLA [A-176]; Fireworks GLM 5.2 Standard $1.40/$0.14/$4.40, Priority $1.75/$0.18/$5.50, Fast $2.10/$0.21/$6.60 [A-258]; OpenAI fast = 2x Standard [A-209].
- Bedrock: Reserved saves 30-50%; move when steady load exceeds about 40% of on-demand cost [A-159].
- Long context: Opus 4.6 over 200k $10/$37.50 vs $5/$25 [A-270]; xAI over 200k reprices ALL tokens incl. cached [A-225]; Haiku 5.5 splits at 100k [A-199]. Regional: US-only 1.1x Anthropic [A-216]; Together 1.25x [A-276].

**Caching [PL].**
- Anthropic: 5m write 1.25x, 1h 2x, read 0.1x (0.05x Opus/Sonnet 5.5; 0.025x Fable/Mythos 5.1); min prefix 512-4,096 tokens by model; 4 breakpoints; input = read + creation + uncached [A-199].
- OpenAI GPT-5.6+: write 1.25x/2.5x, read 0.1x, min 1,024; one write + 9 reads = 2.15x vs 10x; break-even prefix 102.4 + 1,177.6/N tokens [A-201].
- Mistral read about 10% [A-175]; xAI 25% [A-221]; Fireworks 50% default [A-256]; Gemini 90% on 2.5+ (older note 75% [A-121] vs [A-280]); Azure 12h write charges from Nov 1 2026 [A-148].
- Cohere bills `billed_units`, not tokens (6,772 vs 7,596 in) [A-177].

**Plans and credits (CLI).**
- Claude: Pro $20, Max $100/$200, Team $20-125/seat; prompt counts per 5h approximate; Anthropic does not publish limit-to-token conversion [C-009, C-010]. API credits cover `claude -p`, not interactive use [C-010].
- Codex: Plus $20, Pro $100/$200; Plus 15-80 msgs/5h on top model; credits 1 ~ $0.04; weekly caps hit after ~2M tokens (user-reported) [C-114, C-115].
- Cursor: Plus $8 base, Premium 4x, Super 15x, Ultra 50x; pool in multiples only, no tokens; per-model per-M rates published [C-119, C-120]. Pro moved from 500 requests to a usage pool [C-015].
- Copilot: legacy 300 premium requests $10, extra $0.04, reasoning 5x/20x, review 13x [C-116, C-117]; new credits 1 = $0.01 at API-list rates, promos end Dec 1 and Dec 31 2026 [A-214].
- Gemini CLI: 1,000-2,000 requests/day, 250 unpaid Flash [C-057]. Kiro credits Pro 1,000 for $20, credits-per-token not stated [A-161]. Gemini GSU: output token = 5, cached = 0.1; 675 tokens/GSU [A-146].

**Spend distribution [M unless noted].**
- Claude Code active mean $108, median $23, P95 $291; cache hit 52% to 86% while cost per user rose 3.8x ($14 to $54); gateway selection bias [C-054]. Hit by agent: Claude Code 92%, Cline 61%, Kilo 46%; effective input $0.30/M vs $1.62/M [C-054].
- ChatGPT Work median ~$53, mean ~$309, P90 ~$1,154/year [C-101, SR]. Claude enterprise ~$13/dev/day [C-010, third party].
- Agents never reference budget in 14,000+ messages [C-136, M].

**Price dynamics.**
- About 600x decline 2020-2025; half-life pooled 1.32y [A-061, working paper]. 10% price cut gives 0.5-0.7% usage rise [A-226, one platform]. Cost-of-pass halved every 2.6-7.1 months [A-122].
- Price reversal in 32% of 336 comparisons, up to 28x; same query varies 9.7x [A-069, May 2026 snapshot]. Reasoning uses 4-8x output [A-065]; 6,067 vs 770 tokens [A-135]. Claude 4.7+ tokenizer ~30% more tokens [C-010].
- Non-Latin scripts up to 5x tokens [A-100, 2023 gpt-3.5]; OCaml 1.28-1.69x Python output tokens [C-134, M].

**Self-hosting and serving.**
- Claims: owning beats renting at ~4 h/day, $0.11/M vs $0.89 cloud vs $2.00 API [A-180, vendor marketing]. H100 $3/hr gives $72/day; crossover ~72M tokens/day at $1/M [A-277, IL]; Together lists $5.49/hr [A-278]. Epoch: 70B $0.11/M needs 100% utilisation (~17% in its table) [A-062].
- Measured: Claude API realised $0.57/M at 99.3% cache hit (caching cut cost 88.6%); on-prem $2.83/M shared, $11.87/M dedicated at $4/GPU-hr; fix-commit ratio 45.93% API vs 74.93% local; one developer [C-053, M].
- Techniques [SR, 2023-25]: Orca 36.9x [A-109]; PagedAttention 2-4x [A-073]; DistServe 2.0-4.6x [A-106]; Sarathi 2.6-5.6x [A-110]; GPTQ 3.25-4.5x at batch 1 [A-108]; kvtc ~20x KV compression [A-074]; speculative decoding 2-3x [A-132] but +25.65% energy at batch 128 [A-124], acceptance ~1.1 past 20K tokens [A-027], marginal 20B-for-120B [A-274]; MoE 39.6% of dense compute [A-034] but up to +54% energy [A-124]; autoscaling >80% GPU saving at peak [A-185]; scale-to-zero returns 502 on cold start [A-171].
- Serving $/token is rare: 120B at $0.037-$0.156/M input on an assumed $3/hr H200 [A-274, IL]. Epoch KV-read floor $6.06/M output at 100K [A-062].

**Small models.**
- 900k labels for ~$70; small model ~80x cheaper per instance-hour, 105-sample test [A-129, SR]. One feature off an external API: ~4x cheaper, $0.62M/yr, no A/B difference [A-272, 2023].
- 40-70% of agent calls replaceable, 10-30x cheaper [A-041, C-049, authors' estimate]. Sub-3B models weak on multi-turn tool use (0.6B 1.38%, 3B 55.62%) [C-050]. 5-10% of tasks need frontier [A-186]. Cascade beats single model only below ~$0.10 error price [A-123].

## 2. What the layer must model

**Price book** - one row per (provider, model, service_tier, context_band, region, effective_from):
- Rates per 1M tokens: input, output, cache_read, cache_write_5m, cache_write_1h, reasoning (default = output).
- Multipliers with `applies_to` (input/output/cached/all) and `order` vs cache discount: batch, flex, priority, fast, region, residency.
- Flags: batch_stacks_with_cache (true/false/unknown), band_scope (marginal | all_tokens), input_includes_cached, reasoning_in_output, billed_units_source.
- Cache: min_prefix, TTLs, max_breakpoints, storage_rate.
- Limits: rpm, tpm, rpd, batch_max_requests/bytes, batch_window, enqueued_quota, SLA, 429_billed, auto_fallback.
- Lifecycle: effective_from, expires_at, source_id, snapshot_date, last_verified_at, confidence.
- Plan rows: plan, fee, unit (api-rate tokens | credits | premium requests | requests/day | msgs/5h | pool multiple), included_qty (nullable), credit_usd, reset_rule, overage_rate, model_weighting (nullable).

Versioning: append-only; each request stores price_row_id. Expiry: a daily job flags rows within 30 days of expires_at or unverified for 30 days; expired promos fall back to list and alert. Weekly canary: computed cost vs vendor usage or invoice.

**Cost formula** per request. Buckets: I uncached input, C_r read, C_w5/C_w1h writes, O output, R reasoning.
1. Normalise buckets to the vendor's accounting (Anthropic reports them separately [A-199]; others include cached in input). Use vendor billed units [A-177].
2. Band from total prompt tokens; if band_scope = all_tokens reprice every bucket [A-225].
3. Base = (I*in + C_r*read + C_w5*w5 + C_w1h*w1h + (O+R)*out) / 1e6.
4. Apply tier multipliers per applies_to and order. Batch cache component only if stacking flag is true; else bill reads at the batch input rate [A-252]. Use expected, not ideal, hit rate in batch [A-219].
5. Add per-call tool fees, storage, per-review fees [A-225, A-214]. Failed batch or flex = 0 [A-219, A-195].
6. Plan billing: marginal $ = 0 inside the pool, overage after. Track vendor units (credits, requests x multiplier). Report shadow API cost plus amortised fee. No token conversion for Claude [C-010].

## 3. Levers by workload and break-even

| Workload | Lever | Condition | Evidence |
|---|---|---|---|
| Offline bulk (evals, labelling) | Batch, or flex if sync | 24h ok; check stacking | [A-219, A-195] |
| Repeated long prefix, agent loops | Cache before tier | prefix >= min and N reads repay write | [A-199, A-201, A-224] |
| Latency/SLA | Priority/fast | pay 1.75-2x only if SLA binds | [A-176, A-225] |
| Steady known load | Reserved/provisioned | >~40% of on-demand | [A-159] |
| Narrow, verifiable, high volume | Small/fine-tuned | eval parity on the slice | [A-129, A-272, C-050] |
| Open-weight, high volume | Self-host | measured utilisation | [A-277, A-062, C-053] |
| Hard repo-wide work | Keep frontier | quality gap real | [C-053, A-186] |

Self-host rule: self-host iff GPU_hr_cost x GPU_hours_for_peak / u + ops + rework < tokens x effective API $/M. Daily form: tokens/day (M) > 24 x $/GPU-hr / (u x API $/M). Anchors: $3/hr gives ~72M tokens/day at $1/M and u=1 [A-277]; $5.49/hr gives ~132M (derived). Use cache-adjusted API rate ($0.57/M, not list [C-053]) and add rework (74.93% vs 45.93% fix-commit ratio). No default u in corpus; the buyer must measure it.

Small-model rule: route iff cost_small + P(fail_small) x cost_escalation < cost_big, with P(fail) from the buyer's labelled slice.

## 4. Rules the system MUST enforce

1. Version every price row; cost each request against the row valid then; store price_row_id. Promos expire [A-214]; 32% of comparisons reversed [A-069].
2. Block billing decisions on rows older than 30 days or past expiry. Gemini cache 75% vs 90% [A-121, A-280]; Azure charge change Nov 1 2026 [A-148].
3. Decide batch+cache stacking per provider and model. Groq no, Fireworks yes, Gemini 3 vs 2.5 differ [A-252, A-255, A-281].
4. Re-band on total prompt tokens and reprice cached tokens where scope = all_tokens [A-225, A-270].
5. Use vendor billed units, not local token counts [A-177, C-010].
6. Count reasoning as output; rank models by cost per solved task, not list price [A-065, A-069, A-135].
7. Enable caching only when prefix >= min and expected reads repay the write; keep volatile text out of the prefix [A-201]; a timestamp raised cost 2.2-2.9x [A-224].
8. Do not change tier or model mid-conversation without costing a cold cache. Fast mode mid-conversation bills the whole context uncached (guide, C-086) [A-176].
9. Send only latency-tolerant, non-streaming, non-SLA work to batch/flex; retry on standard after 429 [A-195, A-281, A-219].
10. Track plan quota in native units; never convert to tokens [C-010, C-119, C-057, C-116].
11. Report mean, median and P95 per user and alert on the tail [C-054, C-101].
12. Enforce budgets in the layer, not the prompt [C-136].
13. Refuse a self-host recommendation without measured utilisation [A-062, A-277].
14. Gate small-model routing on per-task eval parity with rollback triggers (schema validity -2 pp, p95 +20% per survey [C-063, not measured]) [A-129, C-050].
15. Budget per language and code language; no English parity [A-100, C-134].
16. Use speculative decoding only at small batch and short outputs [A-124, A-027]; plan for cold-start 502s [A-171].

## 5. Conflicts and stale data

- Stacking: Groq vs Fireworks [A-252, A-255]; Gemini 2.5 vs 3+ [A-281].
- Gemini cache 75% [A-121] vs 90% [A-280].
- Together H100 $3/hr [A-277] vs $5.49/hr [A-278]; crossover moves 72M to ~132M tokens/day.
- Error-price threshold in [A-123]: $0.01 in abstract, $0.20 in note.
- OpenAI flex percentage not stated [A-195]; Together "up to 50%" [A-275].
- Claude Code input 84K per call vs ">200,000" in [C-054].
- Future-dated pages and model names (Fable 5.1, GPT-6.1, Gemini 4 Argon) are unverifiable; older guides use Sonnet 4.6, Opus 4.7 [C-009, C-010].
- Plan figures are approximate and short-lived: caps doubled May 2026, +50% weekly expired 2026-07-13 [C-011]; Pro promo ended 31 May 2026 [C-115]; Copilot request billing legacy [C-116].
- Weak sources: [A-061] single author; [A-226] one platform; [A-180] vendor marketing; [A-260] testimonial; [A-041] estimates; [C-053] one developer; [C-054] gateway bias; [A-100] 2023; serving papers 2023-24 hardware.
- Not in corpus: Azure PTU to TPM [A-151]; Gemini explicit-cache storage rate; Kiro credits per token; Mistral batch+cache; Claude tokens per week; default utilisation.

## 6. Experiments required

1. Price-book canary: 2 weeks, computed vs invoiced cost per provider and tier; target error under 1%.
2. Cache break-even: caching off, 5m, 1h per workload; confirm N-read rule and the 1h-blanket regression (guide, C-051/052/055).
3. Batch vs flex vs standard on 1,000 fixed requests: price, latency, cache hit, error and 429 rates.
4. Plan calibration: one developer-week per plan, log quota consumed vs shadow API cost; fit $/unit with a band.
5. Self-host trial: one open-weight model on one GPU under real traffic; measure u, p95, tokens/day, rework; compare with cache-adjusted API cost.
6. Small-model parity: 1,000+ labelled samples per narrow job; accuracy, cost per task, p95, rollback breaches.
7. 30-day spend baseline: mean/median/P95 per user vs [C-054].
8. Tokens per task by language and code language on each target model.
9. Monthly price-list diff to calibrate the staleness threshold.
