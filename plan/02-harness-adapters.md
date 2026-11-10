# Harness adapters

Only Claude Code and Codex CLI have documented, machine-readable surfaces in the corpus. Aider has a base URL. The rest have pricing or blog pages only. Ids: `A:nnn` is the API corpus, `C:nnn` is the CLI corpus.

## Capability matrix

`Y` = documented. `n/c` = not in corpus. Token Economics treats `n/c` as false.

| Harness | baseUrl | oauthPassthrough | hooksBlocking | otel | budgetFlag | headless | modelRewrite | transcriptPath |
|---|---|---|---|---|---|---|---|---|
| Claude Code | Y | Y, gateway must forward the OAuth beta value | Y, exit code 2 | Y | Y, `--max-budget-usd`, `--max-turns` | Y, `claude -p` | risk, body rewrite not documented as supported | Y |
| Codex CLI | Y, `wire_api = "responses"` only | n/c | schema n/c | Y | n/c | Y, `codex exec` | n/c | Y, history.jsonl |
| Aider | Y, `OPENAI_API_BASE` | n/a | n/c | n/c | n/c | n/c | n/c | n/c |
| Gemini CLI | n/c | n/c | n/c | n/c | quotas only | n/c | n/c | n/c |
| Copilot, Cursor, Amp, Kiro, Cline, OpenHands | n/c | n/c | n/c | n/c | vendor-side only | n/c | n/c | n/c |

Sources: A:193, A:217, C:074, C:080, C:094, C:104, C:037, C:057.

For every harness marked n/c, Token Economics reads vendor dashboards, exports or local files only. `ccusage` reads local JSONL for 15 or more agent CLIs (C:003). Kiro has an open-source AWS cost tool (A:056).

## The five adapter functions

| Function | Input | Output |
|---|---|---|
| `route(env)` | harness environment | proxy settings |
| `identify(request)` | request headers and body | `{session, prompt, agent, tool}` |
| `observe(stream)` | response stream | one `UsageEvent` |
| `cap(policy)` | policy | flags or config the harness accepts |
| `replay(transcript)` | local transcript | `UsageEvent[]` |

## Claude Code

Route:
- `ANTHROPIC_BASE_URL` plus `ANTHROPIC_AUTH_TOKEN` or `apiKeyHelper` (A:193, C:088).
- Pin the route in managed settings: `allowedProviders: ["customEndpoint"]`.
- The gateway must forward every `anthropic-beta` value and every request field, and must not strip or reorder `cache_control`. Check cache reads after each Claude Code upgrade.
- Anthropic does not support routing Claude Code to non-Claude models through a gateway. Downgrades stay inside the Claude family.

Identify and observe:
- Hook `prompt_id` equals OpenTelemetry `prompt.id`. This is the join key.
- OpenTelemetry attributes: `query_source`, `agent.name`, `skill.name`, `mcp_server.name`.
- Claude Code sends `traceparent` upstream only to Anthropic unless `CLAUDE_CODE_PROPAGATE_TRACEPARENT=1`, so gateway spans do not join client traces by default.
- `transcript_path` is written asynchronously and can lag. Use `last_assistant_message` on Stop.

Cap:
- Interactive: gateway virtual-key budgets. Hooks are a supplement.
- Headless: `--max-budget-usd` and `--max-turns`.
- Exit code 2 from a PreToolUse hook blocks. Developers can disable hooks, but not managed ones.
- No hook rewrites the model of an ordinary request. `PreModelSwitch` only gates a switch.

Auth modes:

| Mode | Gateway sees | Gateway controls |
|---|---|---|
| API key or auth token | Everything | Route, reject, inject cache control, budget per key |
| `apiKeyHelper` | Same, billed per token | Same |
| Subscription OAuth with base URL | Requests that carry the token | Route and observe only. Limits stay with the plan. |
| Subscription, no gateway | Nothing | Nothing. Read `/usage` and `rate_limits.*` in the status line. |

Client dollar figures (`/cost`, status line, OpenTelemetry cost) are list-price estimates, not bills (C:076).

## Codex CLI

- Route: `model_providers.<id>.base_url`. Put `model_provider` in user or managed config. Codex ignores it in project-local config (C:104).
- The gateway must speak the Responses API.
- `auth.command` prints a bearer token, the analogue of `apiKeyHelper`.
- No budget flag in the corpus. Use gateway budgets and `codex exec` wrapper limits.
- Hook stdin and exit-code schema and OpenTelemetry event names are not in the corpus. Build them from a P0 spike.
- Managed cloud ignores custom providers.

## Aider and the rest

- Aider: any OpenAI-compatible endpoint through `OPENAI_API_BASE`. It does not know it is routed. For an unknown model it assumes unlimited context and zero cost, so ignore its own cost display (C:040).
- Gemini CLI: daily request quotas only. Token caching works for API key and Vertex, not OAuth (C:057, C:121).
- Copilot: billed per premium request or credit. Tool calls do not count (C:117, A:263).
- Cursor, Amp, Kiro, Cline, OpenHands, Roo, Kilo, OpenCode: no pluggable surface in the corpus.

## Normalised event

`harness, session_id, prompt_id, agent, model, input, output, cache_read, cache_write, cost_estimate_usd, cost_source (client|gateway|bill), auth_mode`

## Adapter rules

1. Gateway first. If the harness takes a base URL, the gateway log is the source of truth.
2. Never use a client hook for enforcement.
3. Label every cost with `cost_source`.
4. Declare the eight capability flags. A false flag degrades that control to observation.
5. Match the protocol: Anthropic format for Claude Code, Responses for Codex, Chat Completions for Aider.
6. Preserve the cache. Use sticky routing so one session stays on one provider endpoint.
7. Join gateway, hook and OpenTelemetry rows on `session_id` and `prompt_id`.
8. Set caps at launch for headless runs.
9. Fail open for observation, fail closed for budgets.
10. Default to metadata only. Prompt, tool and response logging stay opt-in.

## Gateway risks to design around

| Risk | Corpus status | Action |
|---|---|---|
| Soft-budget overshoot | Not quantified | Measure in P0. Assume in-flight requests finish after the cap. |
| Gateway strips `cache_control` | Anthropic's own gateway forwards it by construction | Verify cache reads after each upgrade. |
| Claude Code on a 402 | Not in corpus | Spike in P0. |
| Transcript retention | 30 days per one source | Persist copies. |
