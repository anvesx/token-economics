# Cost formula and price book

Source ids: `A:nnn` is `research/corpus/nnn.txt`. `C:nnn` is `research-cli-agents/corpus/nnn.txt`. The two id spaces collide, so the prefix is required.

Price is not a constant. Vendors differ on cache stacking, tier scope, token counting and window rules, and price lists expire. Token Economics therefore needs a versioned, expiring price book and a formula with per-vendor flags.

## Price book row

One row per `(provider, model, service_tier, context_band, region, effective_from)`. Rows are append-only. Each ledger row stores the `price_row_id` it was costed against.

| Field group | Fields |
|---|---|
| Rates per 1M tokens | input, output, cache_read, cache_write_5m, cache_write_1h, reasoning (defaults to output) |
| Multipliers | batch, flex, priority, fast, region, residency, each with `applies_to` (input, output, cached, all) and `order` against the cache discount |
| Flags | `batch_stacks_with_cache` (true, false, unknown), `band_scope` (marginal or all_tokens), `input_includes_cached`, `reasoning_in_output`, `billed_units_source` |
| Cache | min_prefix, TTLs, max_breakpoints, storage_rate |
| Limits | rpm, tpm, rpd, batch_max_requests, batch_max_bytes, batch_window, service-level agreement (SLA), `429_billed`, `auto_fallback` |
| Lifecycle | effective_from, expires_at, source_id, snapshot_date, last_verified_at, confidence |

Plan rows live in a separate table: plan, fee, unit (API-rate tokens, credits, premium requests, requests per day, messages per five hours, pool multiple), included_qty, credit_usd, reset_rule, overage_rate, model_weighting.

Lifecycle rules:

1. A daily job flags rows within 30 days of `expires_at` or unverified for 30 days.
2. Billing decisions block on rows past expiry or older than 30 days. Expired promos fall back to list price and raise an alert.
3. A weekly canary compares computed cost with the vendor usage report or invoice. Target error is under 1 percent. The tolerance itself is not in the corpus.

## Per-request formula

Buckets: `I` uncached input, `Cr` cache read, `Cw5` and `Cw1h` cache writes, `O` output, `R` reasoning.

1. Normalise buckets to the vendor's accounting. Anthropic reports them separately. OpenAI, xAI and OpenRouter include cached tokens in `prompt_tokens`. Prefer vendor billed units over local counts (A:177).
2. Pick the context band from total prompt tokens. If `band_scope = all_tokens`, reprice every bucket (A:225, A:270).
3. Base cost = (I × in + Cr × read + Cw5 × w5 + Cw1h × w1h + (O + R) × out) / 1e6.
4. Apply tier multipliers by `applies_to` and `order`. Batch discounts the cache component only if the stacking flag is true. Otherwise bill reads at the batch input rate (A:252). Use the expected hit rate in batch, not the ideal one (A:219).
5. Add per-call tool fees, storage and per-review fees (A:225, A:214). Failed batch or flex requests cost zero (A:219, A:195).
6. Plan billing: marginal dollars are zero inside the pool and priced after it. Track vendor units. Report a shadow API cost plus the amortised fee. Never convert Claude plan limits to tokens (C:010).

## Facts the table must encode

| Topic | Fact | Source |
|---|---|---|
| Batch | 50 percent off at OpenAI, Azure, Anthropic, Mistral, Groq, Fireworks, Bedrock, Gemini. xAI is 20 percent. | A:111, A:152, A:219, A:174, A:252, A:255, A:159, A:281, A:225 |
| Batch plus cache | Anthropic and Fireworks stack. Groq does not. Gemini 3+ does, 2.5 does not. Bedrock has no cache in batch. | A:219, A:255, A:252, A:281, A:157 |
| Anthropic cache | 5 minute write 1.25x, 1 hour write 2x, read 0.1x (0.05x on Opus and Sonnet 5.5, 0.025x on Fable and Mythos 5.1) | A:199 |
| OpenAI cache | One write plus nine reads costs 2.15x against 10x uncached. Break-even prefix is 102.4 + 1,177.6 / N tokens. | A:201 |
| Long context | xAI over 200k reprices all tokens, cached included. Opus 4.6 over 200k is $10 and $37.50 against $5 and $25. | A:225, A:270 |
| OpenAI cache write | GPT-6 and 6.1 add a write charge. Multiplier conflicts: 1.25x on a third-party sheet, 2.5x in a changelog snippet. A 12-hour cache is optional. Break-even reuse count is `write multiplier − 1` divided by `1 − read multiplier`. Read OpenAI's page before use. | 16-research-update-2026-11.md |
| Length cliffs | Haiku 5.5 reprices a request above 100K tokens (cache reads count). Grok 4.7 doubles all rates from 200K. | 16-research-update-2026-11.md |
| Scheduled changes | Gemini 4 Argon doubles on 2026-12-01. Gemini 3.8 and 3.6 Flash double on 2027-01-01. Sonnet 5 held at $2 and $10. | 16-research-update-2026-11.md |
| Tokenizer and region | Claude 4.7 and later emit about 30% more tokens per text. `inference_geo: "us"` adds 1.1x on every bucket. | 16-research-update-2026-11.md |
| Price reversal | 106 of 336 comparisons reversed the price ranking, up to 28x | A:069 |
| Cache hit | Claude Code 92 percent, Cline 61, Kilo 46. Effective input $0.30 per M against $1.62. | C:054 |
| Spend spread | Claude Code active users: mean $108, median $23, P95 $291 | C:054 |

Model names and prices are quoted as the corpus gives them. Several are future-dated or unverifiable. The canary exists to catch that.

## Self-host and small-model rules

Self-host only if `GPU_hr_cost × GPU_hours_for_peak / u + ops + rework < tokens × effective_API_$/M`. In daily form, tokens per day (millions) must exceed `24 × $/GPU-hr / (u × API_$/M)`. Use the cache-adjusted API rate, not list price (C:053 measured $0.57 per M). The corpus has no default utilisation `u`; the buyer must measure it. Refuse a self-host recommendation without a measured `u` (A:062, A:277).

Route to a small model only if `cost_small + P(fail_small) × cost_escalation < cost_big`, with `P(fail)` from a labelled slice of the buyer's own work (A:129, C:050).

## Rules the cost layer must enforce

1. Version every price row and store `price_row_id` per request.
2. Block billing on rows past expiry or older than 30 days.
3. Decide batch-plus-cache stacking per provider and model.
4. Re-band on total prompt tokens and reprice cached tokens where the scope is `all_tokens`.
5. Use vendor billed units, not local token counts.
6. Count reasoning as output. Rank models by cost per solved task, not list price.
7. Give every price row an `effective_from` date and an optional `effective_to`. Reprice history with the row in force on the request date, and flag a cost trend that crosses a cutover.
8. Make the cache-read and cache-write multipliers per-model columns, never a provider constant.
9. Reconcile against the provider's usage and cost API. Client cost displays lag price changes.
7. Enable caching only when the prefix meets the minimum and expected reads repay the write. Keep volatile text out of the prefix. A timestamp raised cost 2.2 to 2.9 times (A:224).
8. Never change tier or model mid-conversation without costing a cold cache.
9. Send only latency-tolerant, non-streaming, non-SLA work to batch or flex. Retry on standard after a 429.
10. Track plan quota in native units.
11. Report mean, median and P95 per user, and alert on the tail.
12. Enforce budgets in the layer, not in the prompt (C:136).
