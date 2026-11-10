# R1: Prompt caching, token accounting, usage ledger

Ids are corpus source numbers. "[A]" = research/ (API-side), "[C]" = research-cli-agents/. Where the id is unmarked, it is API-side. Model names (Fable 5.1, Opus 5.5, GPT-5.6, Grok 4.7, Gemini 3/4) are quoted as written; all prices are snapshots and must live in a versioned price table, not code.

Tags: [price-list] vendor price page; [measured] observed by the author; [self-reported] vendor or author claim; [illustrative] worked example.

## 1. Facts to build on

**Anthropic**
- Multipliers: read 0.1x, 5m write 1.25x, 1h write 2x. Exceptions: Fable 5.1 and Mythos 5.1 read 0.025x; Opus 5.5 and Sonnet 5.5 read 0.05x. [199][283][C-010] [price-list]
- Per MTok (input / output / 5m write / 1h write / read): Fable 5.1 $10/$50/$12.50/$20/$0.25; Opus 5.5 $4/$20/$5/$8/$0.20; Sonnet 5.5 $2/$10/$2.50/$4/$0.10; Opus 5 $5/$25/$6.25/$10/$0.50; Sonnet 4.5 $3/$15/$3.75/$6/$0.30; Haiku 4.5 $1/$5/$1.25/$2/$0.10. [283][199][C-010] [price-list]
- Haiku 5.5 is tiered by prompt size: $0.10/$0.50 up to 100K, $0.50/$2.50 above. [C-010] [price-list]
- Prefix order is tools, system, messages. The key is a hash of the whole prefix up to the breakpoint. Max 4 explicit breakpoints; top-level automatic mode moves the breakpoint forward. Lookback is 20 blocks. Longer-TTL entries must precede shorter ones. `system` must be an array of blocks. [199][283] [price-list]
- TTL is measured from request start and refreshed free on each use. Pre-warm with `max_tokens:0`. Caches are isolated per org, and per workspace on the Claude API. [199] [price-list]
- Minimum prefix: 512 (5/5.5/5.1 families); 1,024 (Opus 4.8, Sonnet 5, Sonnet 4.6/4.5, Opus 4.1/4); 2,048 (Mythos Preview, Opus 4.7); 4,096 (Opus 4.6/4.5, Haiku 4.5). [199] [price-list]
- Invalidators in Claude Code: model switch (opusplan, fallback, skills naming a model), effort change on most models, fast-mode toggle, MCP tools added or removed with tool search off, denying a whole tool, compaction, image/PDF removal, Claude Code upgrade. [055][071][C-051] [self-reported]
- Effort changes keep the cache on Opus 5.5, Sonnet 5.5, Haiku 5.5, Fable 5.1. Fast and standard speed have separate caches. [055] [self-reported]
- Cache-safe: file edits, mid-session CLAUDE.md edits, permission mode, skills, /rewind, spawning subagents. [055] [self-reported]
- Subagents do not read the parent cache; forks do. Fan-out holds all but the first agent for up to 5s. [055][C-052] [self-reported]
- A gateway that strips `cache_control` or the `anthropic-beta` header bills the whole history uncached. [C-052][C-054] [measured]
- Batch: 50% off, caching stacks, hit rate "typically 30%-98%", best-effort. Unsupported: stream, speed, fallbacks, `max_tokens:0`. Results kept 29 days; errored/canceled/expired not billed. [219] [price-list]
- Above 200K input Opus 4.6 is $10/$37.50 instead of $5/$25. US-only inference 1.1x. [270][216][215] [price-list]
- Fast mode: Opus 5.5 $8/$40; Opus 5 and 4.8 $10/$50. [C-086][C-010] [price-list]

**OpenAI / Azure**
- Automatic caching, prefix 1,024+ tokens, hits in 128-token increments. Pre-5.6 retention: `prompt_cache_retention` in_memory (5-10 min, up to 1h) or 24h, no write fee. [201][202][203] [price-list]
- GPT-5.6+: `prompt_cache_options.mode` implicit (default) | explicit; `prompt_cache_options.ttl` "30m" (default) | "12h"; write 1.25x (30m) or 2.5x (12h); read 0.1x (0.05x on GPT-6.1 Sol/Terra); up to 4 writes per request; lookup covers first 2 and latest 50 breakpoints. [201][204] [price-list]
- Routing hashes the first ~256 tokens plus `prompt_cache_key`; about 15 requests per minute per prefix+key, then overflow misses. [202][148] [self-reported]
- Reported hit rates: Manus about 85% to above 90%, Wordsmith 83% to 91% [072]; 60% to 87% with `prompt_cache_key` [202] [self-reported]
- Flex: `service_tier:"flex"`, Batch rates (50%), 429 with no charge, caching stacks; Azure has no auto-fallback. Flex vs Batch test: +8.5% cache hit, 23% lower input cost. [195][150][202] [measured]
- Azure: GPT-5.6+ 12h write charges from Nov 1 2026; Global Batch 50% off, `completion_window` "24h". [148][152][150] [price-list]
- Reasoning tokens are billed as output and sit inside `output_tokens`. Example: input 75, output 1186, reasoning 1024, total 1261. [197][251] [illustrative]

**xAI**: `x-grok-conv-id` header or `prompt_cache_key`; cached rate 1/4 of input; 128-token blocks. At 200K+ ALL tokens (cached included) reprice at 2x. Priority is 2x all token types, cache applied first. US endpoint 1.1x. Batch 20% off. [221-225] [price-list] Time at the top of the system prompt gave 87% vs 3% cache and 2.2-2.9x cost. [224] [measured]

**Gemini**: implicit caching on by default. Explicit `CachedContent` has a storage fee (2.5 Pro $4.50/MTok/h). 200K tiers (2.5 Pro $1.25 to $2.50 input). Batch 50%; stacks with cache to 95% on Gemini 3+, not on 2.5. [121][143][237][280][281][231] [price-list]

**Bedrock**: `cachePoint`; total input = inputTokens + cacheRead + cacheWrite. Nova: implicit, not billed or reported as reads, 20K max cacheable. No caching in batch inference. Batch 50%, up to 168h. Tiers Flex, Standard, Priority, Reserved. [157][159][160] [price-list]

**Others**
- OpenRouter: `session_id` / `x-session-id` (max 256 chars), sticky routing, 60-minute expiry. Default router cost 6.0% more per request (7.3% per MTok) for lower latency. [231][227][229] [measured]
- DeepSeek: on-disk caching; hit $0.003 vs miss $0.15/MTok on flash; peak vs off-peak. [181-183] [price-list]
- Mistral: Priority 1.75x applied after the cache discount. [173-176] [price-list]
- Fireworks: cached 50% default (90% on GLM 5.2); batch 50% plus an additional 50% on cached; "up to 99.6%". [255-260] [self-reported]
- Together: caching best-effort; US-only 1.25x. [276] [price-list]
- Copilot: 1 credit = $0.01; long-context threshold roughly doubles price. [214] [price-list]

**Accounting**
- Langfuse buckets are mutually exclusive; ingested cost beats inferred; tier condition `input>200000`; historical costs are not recalculated after a price change. [232][233] [self-reported]
- OpenAI inclusive example: 17,903 prompt with 17,817 cached becomes input 86 + input_cached_tokens 17,817 + output 188 = total 18,091. [233] [illustrative]
- Cloudflare inclusive example: 1,000 input, 600 read, 200 write, 100 output gives 200 fresh. [190] [illustrative]
- Agent SDK: costs are client-side estimates; `modelUsage` carries per-model cost and `costBasis`; resumed totals include earlier spend. [216] [self-reported]
- Claude Code OTel: `claude_code.token.usage` (type input, output, cacheRead, cacheCreation); `claude_code.cost.usage`; attributes model, query_source (main|subagent|auxiliary), speed, effort, agent.name, skill.name, mcp_server.name; event `claude_code.api_request`. [217][C-002] [price-list]
- Status-line `prompt_cache` object: warm, hit_ratio, requests, misses, cache_write_tokens, miss_recache_tokens, last_miss_cause, miss_causes. A miss is >5% and 2,000+ tokens re-processed. [C-076] [self-reported]
- Per-caller measurement: account hit rate 77% hid a cron at about 0% (672 runs/day, ~30K prefix). Blanket 1h TTL made the bill 8.6% worse; targeted fixes gave -6.0%, -1.0%, -7.6%, -13.6% combined. 98% of reuse happened within about 34s of the write. Keepalive crossover 62.5 minutes. [C-052] [measured]
- Gateway hit rates: Claude Code 92%, OpenCode 89%, Aider 84%, Zed 80%, Roo 74%, Forge 64%, Cline 61%, Kilo 46%. At 92% effective input is about $0.30/M vs $3.00 list. [C-054] [measured]
- At 96.3% hit rate output is 2.7% of tokens but 51.1% of dollars. [C-027] [measured]
- Cost per success: BrowseComp 84.04% at $1.33 vs 84.36% at $33.27 [207] [measured]; Aider $0.147 per solved [C-129]; cost-of-pass definition [C-122] [self-reported]. Failed runs are 17% of tasks and 32% of spend [C-028]. Same-task runs differ up to 30x in tokens [C-023] [measured].

## 2. Field / header / endpoint names the normaliser must handle

| Provider | Request controls | Response usage fields | Notes / source |
|---|---|---|---|
| Anthropic Messages | `cache_control:{"type":"ephemeral","ttl":"5m"\|"1h"}`; header `anthropic-beta`; `output_config.effort` low/medium/high/xhigh/max; `max_tokens:0` prewarm | `input_tokens` (excludes cache), `cache_creation_input_tokens`, `cache_read_input_tokens`, `cache_creation.ephemeral_5m` / `ephemeral_1h`, `output_tokens`, `inference_geo` | total_input = read + creation + input_tokens [199][052][282]. Per-message effort header `mid-conversation-output-config-2026-07-01` (beta) [282] |
| OpenAI Chat | `prompt_cache_key`, `prompt_cache_retention`, `service_tier` | `usage.prompt_tokens_details.cached_tokens`; `prompt_tokens` INCLUDES cached; reasoning in `completion_tokens_details` | [202][233][197] |
| OpenAI Responses | `prompt_cache_options.mode/ttl`, `prompt_cache_breakpoint`, `prewarm`, `comparison_response_id` | `usage.input_tokens_details.cached_tokens`, `cache_write_tokens` (5.6+), `prompt_cache_diagnostics` | diag types cache_hit, cache_miss, comparison_response_not_found, unavailable [204] |
| Azure OpenAI | `service_tier:"flex"`; header `x-ms-service-tier`; `completion_window` "24h" | as OpenAI | [150][152] |
| xAI | header `x-grok-conv-id`, `prompt_cache_key` | `input_tokens_details.cached_tokens` | [221-223] |
| Gemini | implicit; `CachedContent` resource | `cachedContentTokenCount` (REST) / `cached_content_token_count` (SDK) | [143][280] / [121]. Candidate-token split vs total: not in corpus |
| Bedrock Converse | `cachePoint` | `cacheReadInputTokens`, `cacheWriteInputTokens`, `cacheDetails`, `inputTokens` | total = sum [157][159]. InvokeModel uses `cache_control` [159] |
| OpenRouter | `session_id` / `x-session-id`; `:floor`, `:nitro` slugs | `usage.prompt_tokens_details.cached_tokens`, `cache_write_tokens`, `cache_discount` | [231][227][229] |
| DeepSeek | on-disk, automatic | `prompt_cache_hit_tokens`, `prompt_cache_miss_tokens` (native, seen only in corpus text 182); Anthropic-format endpoint returns `cache_read_input_tokens` | [182][183] |
| Vercel AI Gateway | `caching:'auto'`, `cache_ttl`, `cache_anchor_items` | not in corpus | [247][248] |
| Mistral | `service_tier` seen in corpus text | cached-token field name: not in corpus | [173-176] |
| Claude Agent SDK | n/a | `result.usage`, `modelUsage` (costBasis list/managed/unknown), `total_cost_usd` | [216] |
| LiteLLM | `cache_control_injection_points` | n/a | [C-060] |

## 3. Rules the system MUST enforce

1. Normalise every response to mutually exclusive buckets: fresh_input, cache_read, cache_write_5m, cache_write_1h, output (reasoning inside output). Convert OpenAI/xAI/OpenRouter inclusive counts by subtracting cached. Evidence: [233] 17,903 to 86; [199] Anthropic exclusive; [190].
2. Never also add `reasoning_tokens` to output. Evidence: [197][251] (1,186 output already includes 1,024).
3. Detect and reject usage objects with unknown extra keys instead of silently converting. Evidence: gateway extra keys defeat conversion [233].
4. One ledger row per provider response id. Dedupe parallel tool calls sharing a message id; ignore placeholder per-step `output_tokens`; use final result. Evidence: [216].
5. Count each call once whether it arrives via SDK telemetry or the gateway. Evidence: dual reporting trap [216][217].
6. Attribute subagent spend separately; never rely on `result.usage` alone. Evidence: [216] excludes subagents; [217] `query_source`.
7. Never resum totals on session resume. Evidence: [216] resumed total includes earlier spend.
8. Ledger key includes model id (exact, no partial-name matching), service tier, speed, effort, inference geo, caller id, session id, TTL class. Evidence: [232] partial-name silent wrong price; [055] separate caches by speed; [217] attributes.
9. Compute cost from a versioned price table keyed by (provider, model, effective date, tier); store provider-reported cost when present and prefer it. Keep historical rows frozen. Evidence: [232][233].
10. Apply long-context repricing to all tokens when input crosses the threshold (200K Anthropic/Gemini/xAI; Haiku 5.5 100K), and apply Priority and regional multipliers after the cache discount. Evidence: [270][224][176][237][C-010].
11. Treat client-side cost as an estimate; reconcile against provider invoices. Evidence: [216][C-002][C-004].
12. Do not change model, effort, speed, tool set, or system prefix mid-session without pricing the cache loss first. Evidence: [055][071][204] miss reasons.
13. Keep stable content first, volatile content (timestamps, per-user data) last. Evidence: [224] 87% vs 3%.
14. Carry an affinity key per session (`prompt_cache_key`, `x-grok-conv-id`, `session_id`) and cap per-key rate near 15 req/min/prefix on OpenAI. Evidence: [202][148][221][231].
15. Choose TTL per caller from observed reuse gap, not globally. Evidence: [C-052] blanket 1h +8.6% worse; 98% of reuse within 34s.
16. Skip caching where the prefix is below the model minimum, and check the write premium pays back. Evidence: [199] minimums; [201] 102 tokens never pays, 221 at N=10.
17. Do not rely on cache for Bedrock batch or Nova reads; do not send ttl to 5-minute-only Bedrock models. Evidence: [160][157].
18. Measure hit rate per caller, per model, per prefix-hash: hit = cache_read / (fresh + cache_read + cache_write). Alert on any caller below its own baseline even if the account rate is high. Evidence: [C-052] 77% hid ~0%; [C-054].
19. Record failed and retried attempts as spend against the task; report cost per successful task = total spend of all attempts / successes. Evidence: [C-122][C-028] 17% of tasks, 32% of spend; [207].
20. Reserve worst-case cost before dispatch (max_tokens x output price plus reasoning reserve) and reconcile after. Evidence: repo thealirazadev/llm-gateway (github-repos.md); [197] reserve at least 25,000 reasoning tokens.
21. Ensure the proxy forwards `cache_control` and `anthropic-beta` unchanged. Evidence: [C-052][C-054].

## 4. Pitfalls and conflicts between sources

- Gemini implicit discount: 75% [121][231][237] vs 90% [143][280][281]. Use price table per model/date.
- Gemini minimum prefix: 1024 Flash / 2048 Pro [121][237]; 1024 / 4096 [231]; 2,048 [143]; 4,096 and 6,144 for Gemini 3/4 [280].
- Anthropic minimums: Sonnet 4.6 1,024 [199] vs 2,048 [C-051]; Opus 4.7 2,048 [199] vs 4,096 [C-051]. Take the larger until tested.
- OpenAI cached discount history: 50% [067], 75% gpt-4.1, 90% gpt-5.2 [202]; OpenRouter lists 0.25x or 0.5x per provider [227].
- Mistral block size 64 vs a 1008-token example [173].
- Compaction: cache-destroying [C-112] vs reuse of warm prefix [055].
- Subagent TTL: docs say 5m; observation differs [C-052][081]. Default 1h applies only to main conversation on subscription [055].
- Vendor "up to" claims vs measured: 90% [068], 99.6% [260], 73% [239] and 70%/90% [201] are illustrative. Token-efficient tools "up to 70%" averaged 14% [068][070].
- Claude Code average input per call: 84K vs "above 200,000" [C-054].
- Batch stacking is not uniform: Gemini 2.5 no stack, Gemini 3+ 95%, Fireworks extra 50%, Groq not stated [281][260][252]. Bedrock batch has no caching [160].
- Response-level caches (Helicone, Portkey) are not provider prompt caching; do not mix their hit rates [236-240].
- Missing sources: Groq [253] is an index page and [254] unreadable.
- Zero-write-fee models (pre-5.6 OpenAI, DeepSeek 1x write) vs write-priced (Anthropic, GPT-5.6): a single `cache_write` bucket must allow 1x.

## 5. Needs our own experiment

1. Cache loss on mid-session routing/model switch: unmeasured in the corpus ("largest unknown").
2. Real minimum-prefix size per current model (conflicts above).
3. TTL refresh behaviour for subagents and forks under our fan-out.
4. OpenAI per-key overflow at about 15 req/min; whether our callers hit it.
5. Gemini implicit discount, 75% vs 90%, and storage-fee break-even for explicit caches.
6. Whether a proxy path (LiteLLM, OpenRouter) preserves Anthropic breakpoints and 1h TTL; OpenRouter 6.0% default-router premium [229].
7. Batch cache hit rate for our workloads ("30%-98%" [219]).
8. Reconcile ledger estimates against invoices for every provider; error bound unknown.
9. Break-even keepalive interval for our traffic (corpus: 62.5 min) [C-052].
10. Mistral and Groq cached-token field names (not in corpus).

## 6. Open-source repos worth reusing (research/github-repos.md)

- BerriAI/litellm: provider normalisation, `cache_control_injection_points`.
- langfuse/langfuse: usage buckets, pricing tiers, ingested vs inferred cost [232][233].
- ryoppippi/ccusage: local JSONL cost estimates for Claude Code.
- thealirazadev/llm-gateway: worst-case cost reservation.
- Muhaman/llm-gateway: Anthropic, Redis, daily cost cap.
- prakhar083/llm-gateway, llm0ai/llm0: gateway patterns.
- tokenx, headroom, rtk-ai/rtk: token counting and trimming.
- Helicone: maintenance-only since Mar 2026; reuse ideas, not dependency.
- Dynamo / NeMo router [167]: prefix-aware routing.
