# Data model: usage buckets, ledger, attribution

Ids: `A:nnn` API corpus, `C:nnn` CLI corpus. The ledger is the single place cost lives. Every other view is a query over it.

## Token buckets

Five buckets, mutually exclusive. Token Economics converts every provider response into these before pricing.

| Bucket | Meaning |
|---|---|
| `fresh_input` | Input billed at the full input rate |
| `cache_read` | Input served from cache |
| `cache_write_5m` | Input written to a 5 minute cache |
| `cache_write_1h` | Input written to a 1 hour cache |
| `output` | Output, with reasoning tokens inside it |

Reasoning is never added to `output` a second time. One example shows 1,186 output tokens that already include 1,024 reasoning tokens (A:197, A:251).

## Provider normalisation

| Provider | Input field | Conversion |
|---|---|---|
| Anthropic | `input_tokens` excludes cache | total input = fresh + read + creation (A:199, C:052) |
| OpenAI, xAI, OpenRouter | `prompt_tokens` includes cached | fresh = prompt − cached. Example: 17,903 prompt with 17,817 cached gives 86 fresh (A:233) |
| Cloudflare style | input includes read and write | 1,000 input, 600 read, 200 write gives 200 fresh (A:190) |
| Bedrock Converse | `inputTokens` plus cache fields | total = sum of the three (A:157, A:159) |
| DeepSeek | `prompt_cache_hit_tokens`, `prompt_cache_miss_tokens` | native pair, seen in one corpus text only (A:182) |
| Gemini | `cachedContentTokenCount` | candidate vs total split is not in the corpus |

Rules:

1. Reject a usage object that carries unknown keys. A gateway adding extra keys defeats the conversion silently (A:233).
2. A single `cache_write` bucket must allow a 1x rate, because pre-5.6 OpenAI and DeepSeek charge no write premium.
3. Mistral and Groq cached-token field names are not in the corpus. Adapters for them stay disabled until a spike fills the gap.

## Ledger row

One row per provider response id.

| Field group | Fields |
|---|---|
| Identity | `response_id`, `request_id`, `ts` |
| Attribution | `tenant`, `team`, `caller`, `agent`, `harness`, `session_id`, `prompt_id`, `query_source` (main, subagent, auxiliary) |
| Routing key | exact `model` id, `provider`, `service_tier`, `speed`, `effort`, `inference_geo`, `ttl_class` |
| Tokens | the five buckets |
| Cost | `cost_estimate_usd`, `cost_source` (client, gateway, bill), `price_row_id`, `auth_mode` |
| Outcome | `attempt`, `task_id`, `success` (null until known) |

Rules the ledger enforces:

1. **One row per response id.** Parallel tool calls that share a message id count once. Ignore placeholder per-step `output_tokens` and use the final result (A:216).
2. **Count each call once.** A call seen by SDK telemetry and by the gateway must not be summed twice (A:216, A:217).
3. **Subagent spend is its own row.** `result.usage` alone excludes subagents (A:216, A:217).
4. **Resume does not re-add.** A resumed session reports a total that includes earlier spend (A:216).
5. **Exact model ids only.** Partial-name matching produced a silent wrong price (A:232).
6. **Ingested cost wins over inferred cost.** When the provider reports a cost, store it and prefer it (A:232, A:233).
7. **History is frozen.** A new price row never rewrites old ledger rows (A:232).
8. **Failed and retried attempts are spend.** Cost per successful task is total spend of all attempts divided by successes (C:122, C:028, A:207). Failed runs are 17 percent of tasks and 32 percent of spend (C:028).
9. **Client cost is an estimate.** Label it `client` and reconcile against the invoice (A:216, C:002, C:004).

## Hit rate

`hit = cache_read / (fresh_input + cache_read + cache_write)`, measured per caller, per model and per prefix hash. An account rate of 77 percent hid a cron job near 0 percent (C:052). Alert when a caller drops below its own baseline.

## Attribution joins

| Source | Join key |
|---|---|
| Gateway log | `session_id`, `prompt_id` |
| Claude Code hook | `prompt_id` (equals OpenTelemetry `prompt.id`) |
| OpenTelemetry | `claude_code.token.usage`, `claude_code.cost.usage`, `claude_code.api_request` |
| Local transcript | `replay()` output, lowest trust |

Trust order: bill, then gateway, then client. The gateway row decides. Hook and OpenTelemetry rows fill attribution gaps and never add cost twice.

## Retention and privacy

The ledger stores metadata only. Prompt, tool and response bodies are opt-in. Transcript copies persist because one source reports 30 day retention.

## Gaps

| Gap | Resolve in |
|---|---|
| Reconciliation tolerance between ledger and invoice | P0 |
| Error bound of client-side estimates per provider | P0 |
| Mistral, Groq cached-token field names | P0 spike |
