# R4: Harness integration surfaces for a cost-optimising control layer

Citation key: [C-nnn] = research-cli-agents/corpus/nnn.txt. [A-nnn] = research/corpus/nnn.txt. "not in corpus" means a grep of both corpora found nothing.

## Conclusions first

1. Only Claude Code and Codex CLI have documented, machine-readable surfaces in the corpus (proxy, hooks, OTel, caps, headless). Everything else is covered by pricing or blog pages only.
2. The one universal control point is the HTTP base URL. It works for Claude Code, Codex (custom provider) and Aider. It does not work for subscription traffic unless the gateway forwards OAuth.
3. Hooks are the second control point. They run inside the client, so a developer can disable them. A gateway cannot be disabled by the developer [A-234].
4. Every dollar figure a client or gateway emits is a list-price estimate, not a bill [C-076, C-094, A-232].
5. A new harness needs one adapter with five functions: route, identify, observe, cap, replay. Section 5 defines them.

## 1. Matrix: harness x surface

| Harness | Proxy / base URL | Hooks | OTel | Transcript | Caps | Headless |
|---|---|---|---|---|---|---|
| Claude Code | `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN` or `apiKeyHelper` [A-193, C-088] | 30 events; command, http, mcp_tool handlers [C-074] | Yes, full [A-217] | `transcript_path` in hook JSON; local JSONL [C-074, C-003] | `--max-budget-usd`, `--max-turns` (named in [C-080]; `--max-turns` flag text only there) | `claude -p`, `--output-format json`, `--json-schema`, `--bare`, `--permission-mode` [C-094] |
| Codex CLI | `model_providers.<id>.base_url`; `openai_base_url` [C-104] | `hooks` table in config.toml, 14 events [C-104]; also `notify` | Yes: `[otel]` table [C-104] | `history.persistence`, `history.max_bytes` -> history.jsonl [C-104] | not in corpus (no budget flag); `tool_output_token_limit`, `model_auto_compact_token_limit` style keys only [C-104] | `codex exec`, `codex exec resume --last` [C-035] |
| Aider | `OPENAI_API_BASE`, `OPENAI_API_KEY` [C-037] | not in corpus | not in corpus | not in corpus | `--map-tokens` (default 1k, not a hard cap) [C-127] | not in corpus |
| Gemini CLI | not in corpus | not in corpus | not in corpus | not in corpus | Daily request quotas only [C-057] | not in corpus |
| Copilot CLI | not in corpus | not in corpus | not in corpus | not in corpus | Premium-request or AI-credit billing; spend limit [C-117, A-263] | not in corpus |
| Cursor | not in corpus | Hooks listed in docs nav only [C-119] | not in corpus | not in corpus | Usage pools, spend limit [C-119, A-267] | CLI exists in docs nav [C-119]; flags not in corpus |
| Amp | not in corpus | not in corpus | not in corpus | not in corpus | Pricing page only [C-068] | not in corpus |
| Cline | not in corpus | not in corpus | not in corpus | Tracks `tokensIn` and related streams [C-126] | not in corpus | not in corpus |
| OpenHands | not in corpus | not in corpus | not in corpus | not in corpus | Context condenser (cost control, not a cap) [C-122] | not in corpus |
| Kiro | not in corpus | not in corpus | not in corpus | not in corpus | Enterprise credit usage via AWS Kiro Cost Optimizer [A-056] | not in corpus |
| OpenCode, Roo, Kilo | not in corpus | not in corpus | not in corpus | not in corpus | not in corpus | not in corpus |

Claude Code settings files and order: user `~/.claude/settings.json`, project, local, `--settings` payload, then managed settings last and highest [C-081, C-074]. Codex order, highest first: CLI flags and `--config`; project `.codex/config.toml`; `--profile` file; `~/.codex/config.toml`; cloud-managed; `/etc/codex/config.toml`; defaults [C-097]. Codex ignores `openai_base_url`, `model_provider(s)`, `notify`, `profile(s)` and `otel` in a project-local file. Put them in user-level config [C-104].

## 2. Exact names and schemas

### 2.1 Claude Code hooks [C-074]

Events (from the reference): SessionStart, Setup, UserPromptSubmit, UserPromptExpansion, PreToolUse, PermissionRequest, PermissionDenied, PostToolUse, PostToolUseFailure, Notification, SubagentStart, SubagentStop, TaskCreated, TaskCompleted, TeammateIdle, Stop, StopFailure, InstructionsLoaded, ConfigChange, CwdChanged, FileChanged, WorktreeCreate, WorktreeRemove, PreCompact, PostCompact, PreModelSwitch, PostModelSwitch, Elicitation, ElicitationResult, SessionEnd. DirectoryAdded also appears as a matcher source.

Handler types: `command` (JSON on stdin), `http` (JSON as POST body), `mcp_tool` (tool text output treated as stdout). Prompt and agent handlers exist for Claude Code [C-090].

Common stdin fields: `session_id`, `prompt_id`, `transcript_path`, `cwd`, `permission_mode`, `hook_event_name`, `effort.level`, `agent_id`, `agent_type`, `scratchpad_dir`. PreToolUse adds `tool_name`, `tool_input`, `tool_use_id`.

Key facts for control:
- `prompt_id` equals OTel `prompt.id`. This is the join key between hooks and telemetry.
- `transcript_path` is written asynchronously and can lag the current turn. Use `last_assistant_message` on Stop and SubagentStop instead.
- Exit 0 + JSON = structured control. Exit 2 = block (PreToolUse blocks; PermissionRequest ignores exit 2). Exit 1 without valid JSON = non-blocking error. Use exit 2 for policy.
- Output: `hookSpecificOutput.permissionDecision` ("deny" etc.), `decision: "block"` + `reason`, `updatedInput` (rewrite tool input), `additionalContext`, `systemMessage`. Each string and plain stdout is capped at 10,000 characters.
- PreModelSwitch can block a model switch. A timed-out hook yields no decision on most events. `onFailure: "block"` blocks when the hook cannot start.
- `if` takes exactly one permission rule, for example `Bash(rm *)`. Deny wins when several hooks disagree.
- `disableAllHooks` set below managed level cannot disable managed hooks. `allowManagedHooksOnly` removes custom status lines [C-076].

Model-choice hook gap: no event rewrites the model of an ordinary request. PreModelSwitch only gates `/model`-style switches [C-074, C-073].

### 2.2 Claude Code OTel [A-217]

Enable: `CLAUDE_CODE_ENABLE_TELEMETRY=1`. Exporters: `OTEL_METRICS_EXPORTER`, `OTEL_LOGS_EXPORTER`, `OTEL_TRACES_EXPORTER`; `OTEL_EXPORTER_OTLP_ENDPOINT`, `_PROTOCOL`, `_HEADERS`, per-signal variants; intervals `OTEL_METRIC_EXPORT_INTERVAL`, `OTEL_LOGS_EXPORT_INTERVAL`; `OTEL_RESOURCE_ATTRIBUTES`. Content opt-ins: `OTEL_LOG_USER_PROMPTS`, `OTEL_LOG_TOOL_DETAILS`, `OTEL_LOG_TOOL_CONTENT`, `OTEL_LOG_ASSISTANT_RESPONSES`, `OTEL_LOG_RAW_API_BODIES`. Cardinality: `OTEL_METRICS_INCLUDE_ACCOUNT_UUID`, `_ENTRYPOINT`, `_REPOSITORY`, `_RESOURCE_ATTRIBUTES`. Others: `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA`, `CLAUDE_CODE_PROPAGATE_TRACEPARENT`, `CLAUDE_CODE_OTEL_HEADERS_HELPER_DEBOUNCE_MS`, `CLAUDE_CODE_CLIENT_KEY`.

Metrics: `claude_code.session.count`, `.token.usage` (tokens), `.cost.usage` (USD), `.active_time.total`, `.lines_of_code.count`, `.commit.count`, `.pull_request.count`, `.code_edit_tool.decision`.

Events: `claude_code.user_prompt`, `.tool_result`, `.tool_decision`, `.api_request`, `.api_error`, `.api_refusal`, `.hook`, `.interaction`, `.llm_request`, `.assistant_response`, `.system_prompt`, `.api_request_body`, `.api_response_body`, `.safety_event`, `.tool`, `.tool.execution`, `.tool.blocked_on_user`.

Attribution attributes: `prompt.id`, `query_source`, `query_source_safe` (values like `repl_main_thread`, `agent.builtin.general-purpose`, `agent.custom.<name>`), `agent.name`, `skill.name`, `mcp_server.name`, `gen_ai.system` (always `anthropic`), `gen_ai.request.model`.

Trace context: Bash and PowerShell children inherit `TRACEPARENT`. Claude Code sends traceparent upstream only to Anthropic unless `CLAUDE_CODE_PROPAGATE_TRACEPARENT=1`. A gateway therefore cannot join its spans to the client trace by default.

### 2.3 Claude Code status line [C-076]

Config: `statusLine: {type: "command", command, padding, refreshInterval (min 1s), hideVimModeIndicator}`. Script reads JSON on stdin. Fields: `model.display_name`, `context_window.used_percentage`, `cost.total_cost_usd` (client-side list-price estimate, May differ from bill; resets on `/clear`), `cost.total_duration_ms`, `rate_limits.five_hour.{used_percentage,resets_at}`, `rate_limits.seven_day.{used_percentage,resets_at}`, `rate_limits.spend_limit.{used_percentage,resets_at}` (behind a Claude apps gateway). This is a free, per-event read channel for subscription limit state.

### 2.4 Claude Code headless, models, permissions

- Headless [C-094]: `claude -p`, exit 0 on success, non-zero on failure. `--output-format json` returns session id, usage and `structured_output` with `--json-schema`. `--max-budget-usd` stops remaining background work at the cap. Piped stdin cap is 10MB. Resumed runs report whole-conversation totals. Figures are client-side estimates. `--bare` skips hooks, skills, MCP, plugins, memory and CLAUDE.md; hooks still do not run unless passed explicitly via `--settings`.
- Load flags: `--settings <file-or-json>`, `--mcp-config`, `--agents`, `--append-system-prompt(-file)`, `--plugin-dir`, `--allowedTools`, `--permission-mode`.
- Model selection [C-073]: `--model`, `ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU,FABLE}_MODEL`, `ANTHROPIC_DEFAULT_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_CODE_AUTO_MODE_MODEL`, `CLAUDE_CODE_EFFORT_LEVEL`, `MAX_THINKING_TOKENS`, `CLAUDE_CODE_AUTO_COMPACT_WINDOW`, `CLAUDE_CODE_MAX_CONTEXT_TOKENS`, `availableModels`. A subagent inherits the session model unless its definition sets `model` [C-072, C-073].
- Permission modes [C-095]: `default` (labelled Manual; `manual` accepted as alias), `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`. Set with `--permission-mode` or `permissions.defaultMode`.
- Usage commands [C-003, A-218]: `/usage` (5-hour and weekly windows, subscription), `/cost` (session spend, API key), `/status`, `/context`.
- Cost pricing override: managed setting `modelPricing` changes the client-side estimate [C-076].

### 2.5 Codex CLI [C-104, C-097]

- Provider: `model_provider`, `model_providers.<id>.{name, base_url, env_key, env_key_instructions, experimental_bearer_token, requires_openai_auth, wire_api, query_params, http_headers, env_http_headers, request_max_retries, stream_max_retries, stream_idle_timeout_ms, supports_websockets, auth.command, auth.args, auth.timeout_ms, auth.refresh_interval_ms}`. `wire_api` accepts only `responses`. A gateway for Codex must therefore speak the Responses API. `auth.command` prints a bearer token to stdout (the `apiKeyHelper` analogue). Bedrock and GCP providers have `aws.profile`, `aws.region`, `gcp.project_id`.
- Hooks: `hooks` table or `hooks.json`. Events: PreModelRequest, PostModelRequest, PreToolUse, PermissionRequest, PostToolUse, PreCompact, PostCompact, SessionStart, SessionEnd, SubagentStart, SubagentStop, UserPromptSubmit, Stop, Interrupt. Command and MCP-tool handlers run; prompt and agent handlers are parsed but skipped. `async` and `additionalContextLimit` per handler. Stdin and exit-code schema: not in corpus. Command, local-config and plugin hooks are unsupported under cloud orchestration.
- Also: `notify` (array command, receives JSON payload).
- OTel: `otel.environment` (default `dev`), `otel.exporter`, `otel.trace_exporter` (none | otlp-http | otlp-grpc), `otel.metrics_exporter` (none | statsig | otlp-http | otlp-grpc; default statsig follows `analytics.enabled`), `otel.log_user_prompt`, `otel.log_agent_responses` (64 KiB cap per response), `otel.log_guardian_assessments`, `otel.span_attributes`, `otel.tracestate`, `otel.tool_result.max_bytes`, endpoint/protocol/headers/tls keys. Metric and event names: not in corpus.
- Subagents: `agents.enabled`, `agents.max_threads`, `agents.max_concurrent_threads_per_session`, `agents.default_subagent_model`, `agents.default_subagent_reasoning_effort`, `agents.<name>.config_file`. Model: `model_reasoning_effort`, `service_tier`.
- MCP: `mcp_servers.<id>.{command,args,env,url,bearer_token_env_var,http_headers_helper,enabled_tools,disabled_tools,tool_input_schema_max_bytes (default 5,000),omit_tools_from,default_tools_approval_mode}`.
- Sandbox and approval: `approval_policy` (`untrusted` retired), `sandbox_mode`, `default_permissions`, `permissions.<id>.network.proxy_url`, `features.network_proxy.proxy_url` (default `http://127.0.0.1:3128`). This network proxy governs sandboxed tool traffic, not model traffic.
- Managed Work Cloud ignores `model_provider(s)`. Custom gateways do not carry over there [C-104].

### 2.6 Aider, Gemini, Copilot, Cursor

- Aider: any OpenAI-compatible router via `OPENAI_API_BASE` + `OPENAI_API_KEY`; the harness does not know it is routed [C-037]. An unknown `--model` yields "Unknown context window size and costs" and Aider assumes unlimited context and zero cost [C-040]. So Aider's own cost display is unreliable behind a router.
- Gemini CLI: quota by auth method: Code Assist Individual 1,000/day; AI Pro 1,500; AI Ultra 2,000; API key free 250; Workspace Standard 1,500 [C-057]. Token caching works for API key and Vertex only, not OAuth [C-121]. `/stats` shows tokens and cached savings. Gemini CLI was replaced by Antigravity CLI on 2026-06-18 for unpaid and Google One users [C-057].
- Copilot CLI: billed per premium request or AI credit; one user prompt = one request times the model multiplier; tool calls do not count; `/plan` counts as one [C-117, A-263]. Code review multiplier 13 from 2026-06-01. Org budgets and cost centers exist [A-263]. No client hooks or env overrides in corpus.
- Cursor: pools and API-list-price overage on prepaid credit [C-119]. Hooks and CLI exist in docs navigation only.
- Kiro: credit usage per developer via an open-source serverless AWS tool [A-056]. Interface details: not in corpus (CLI notes folder exists but no source covers settings).

## 3. Observable vs controllable per auth mode

| Mode | Gateway can see | Gateway can control | Client can see | Client-side control left |
|---|---|---|---|---|
| Claude Code, API key or `ANTHROPIC_AUTH_TOKEN` via `ANTHROPIC_BASE_URL` | Full request and response, usage, cache read/write tokens, model, headers | Route, reject (402/429), inject `cache_control`, rewrite the model field in the body, budget per virtual key [A-193, C-060] | `/cost`, status line cost, OTel | Hooks, `--max-budget-usd`, model flags |
| Claude Code, `apiKeyHelper` | Same as above; subscription bypassed, billed per token [A-193] | Same | Same | Same |
| Claude Code, subscription (claude.ai OAuth) with `ANTHROPIC_BASE_URL` only | Requests that carry the OAuth token; gateway must forward the OAuth capability in `anthropic-beta` [A-193] | Route and observe. Billing and limits stay with the subscription | `/usage`, `rate_limits.*` in status line | Hooks, OTel |
| Claude Code, subscription, no gateway | Nothing | Nothing | `/usage`, status line, local JSONL via ccusage [C-003] | Hooks, settings, flags |
| Codex, API key through `model_providers` | Full Responses API traffic | Route, reject, budget | OTel, history.jsonl | Hooks, config |
| Codex, ChatGPT sign-in (`requires_openai_auth`) | Not in corpus whether a custom provider can carry it | not in corpus | `/status`-class views: not in corpus | Hooks, config |
| Gemini CLI, OAuth | Not in corpus | Not in corpus. No cached content creation on OAuth [C-121] | `/stats` | Not in corpus |
| Copilot, Cursor, Amp, Kiro | Nothing; traffic goes to the vendor | Vendor-side budgets only [A-263, C-119, A-056] | Vendor dashboards | not in corpus |

Rules drawn from the table:
- Anthropic does not support routing Claude Code to non-Claude models through a gateway [A-193]. Model downgrade must happen inside the Claude family, by client config or by body rewrite at the gateway. The body-rewrite route is not documented as supported; treat it as a risk.
- Model switching on the client mid-session invalidates the prompt cache. Effort change, fast-mode toggle, MCP tool changes, compaction and upgrades do too [C-055 via notes]. Downgrades must be per session start or per subagent, not per turn.
- Subscription spend is not metered in dollars. Control there means window management through `rate_limits.*`.

## 4. Gaps: nothing pluggable

1. Gemini CLI, Copilot CLI, Cursor, Amp, Kiro, OpenHands, Cline, Roo, Kilo, OpenCode: no base-URL, hook, OTel or headless surface appears in the corpus. For these the layer can only read vendor dashboards, vendor exports or local files (Kiro Cost Optimizer [A-056]; ccusage reads local JSONL for 15+ agent CLIs [C-003]).
2. Codex hook stdin, stdout and exit-code schema, and Codex OTel event names, are not in corpus.
3. Codex has no budget flag in corpus. Claude Code has no per-call hook that can change the model of a normal request.
4. Subscription traffic carries no dollar figure anywhere. Only percentage windows exist.
5. Bedrock, Vertex and Foundry usage does not appear in Anthropic dashboards. Anthropic points to OTel or a gateway [C-005].
6. Claude Code transcript retention is 30 days per one source [C-003]. Persist copies if history is needed.

## 5. Rules so one adapter adds a harness

Adapter interface (five functions): `route(env) -> proxy settings`, `identify(request) -> {session, prompt, agent, tool}`, `observe(stream) -> UsageEvent`, `cap(policy) -> flags/config`, `replay(transcript) -> UsageEvent[]`.

1. **Gateway first.** If the harness allows a base URL, route through the gateway and treat the gateway log as the source of truth. Hooks and OTel are supplements.
2. **Never rely on a client hook for enforcement.** Developers can disable hooks; managed hooks and gateways cannot be disabled by them [A-234, C-074]. Enforce budgets at the gateway or managed settings.
3. **Normalise to one UsageEvent:** `harness, session_id, prompt_id, agent, model, input, output, cache_read, cache_write, cost_estimate_usd, cost_source (client|gateway|bill), auth_mode`. Map Claude `query_source`, `prompt.id` and Codex equivalents into it.
4. **Label every cost.** Client figures are list-price estimates. Gateway figures are computed from usage and a price table (Langfuse: ingested cost overrides inferred cost [A-232]). Only the provider invoice is a bill.
5. **Declare capability flags per harness:** `baseUrl`, `oauthPassthrough`, `hooksBlocking`, `otel`, `budgetFlag`, `headless`, `modelRewrite`, `transcriptPath`. The policy engine reads flags and degrades to observe-only when a flag is false.
6. **Pin the route.** Use `allowedProviders: ["customEndpoint"]` in Claude Code managed settings so a developer cannot bypass the gateway [C-001 notes, A-193]. Codex: put `model_provider` in user or managed config, never project config [C-104].
7. **Protocol match.** Claude Code needs an Anthropic-format endpoint that forwards `anthropic-beta` values and request fields. Codex needs `wire_api = "responses"`. Aider needs Chat Completions [A-193, C-104, C-037].
8. **Preserve the cache.** Do not strip or reorder `cache_control`. Use sticky routing to keep one provider endpoint per session (OpenRouter sticky routing [A-231]; Vercel session-affinity header [A-247]). Switching provider or model mid-session loses the cache.
9. **Join by id.** Join gateway, hook and OTel data on `session_id` and `prompt_id`. Hooks `prompt_id` equals OTel `prompt.id` [C-074].
10. **Set caps at launch.** Pass `--max-budget-usd` and `--max-turns` for headless runs; use gateway virtual-key budgets for interactive runs.
11. **Fail open for observation, fail closed for budgets.** A timed-out hook yields no decision on most Claude events [C-074]; the gateway returns 402 when exhausted.
12. **Never assume content access.** Prompt, tool and response logging are opt-in (`OTEL_LOG_*`, `otel.log_user_prompt`). Default to metadata only.

## 6. Reusable open-source components

| Component | What it gives | Limits stated in corpus | Source |
|---|---|---|---|
| LiteLLM proxy (MIT, about 38.9k stars) | Virtual keys; `max_budget` + `budget_duration` windows, stackable (for example $10/day and $100/month); budget fallbacks; `cache_control_injection_points`; 100+ providers; OpenAI-compatible | Budgets enforced per key at the proxy; overshoot and 402 behaviour not quantified in the sources I read | [C-060, C-061] |
| Bifrost | Per-developer virtual keys; Prometheus metrics; OTel spans; HTTP 402 once developer, team or customer budget is spent; works for Anthropic, Bedrock, Vertex | Vendor marketing; self-reported benchmarks | [C-001] |
| Claude apps gateway (Anthropic, inside the `claude` binary) | IdP SSO via `/login`; model access and managed settings by group; OTLP usage metrics; forwards `anthropic-beta` values; upstream Bedrock, Vertex, Foundry or Anthropic API | Self-hosted; adds `rate_limits.spend_limit.*` to status line | [C-088, C-076] |
| Lynkr | OpenAI-compatible translator in front of Aider; upstream Ollama, Bedrock, Anthropic, Azure, OpenRouter | Single blog source | [C-037] |
| Langfuse | `usage_details` plus `cost_details`; ingested cost beats inferred; model price table; traces by team, repo, model; ingestion via gateway or hooks | Inferred cost depends on price definitions | [A-232, A-234, A-235] |
| Helicone | Gateway logging; per-request cost tracking; response cache; provider prompt-caching pass-through | Response cache differs from provider cache | [A-237, A-238, A-239] |
| Portkey | AI gateway, virtual keys, budget limits (cost or tokens), simple and semantic cache | Budget limits on Enterprise and select Pro plans | [A-241, A-242, A-240] |
| OpenRouter | Provider routing (`order`, `allow_fallbacks`, `require_parameters`, `data_collection`); sticky routing for cache hits | Provider fallbacks can break cache | [A-227, A-231] |
| Vercel AI Gateway | Automatic prompt caching, session affinity header, provider options, model fallbacks, BYOK | Cost tradeoff section exists; details in [A-247] | [A-244, A-245, A-247, A-248] |
| Cloudflare AI Gateway | not in corpus | not in corpus | not in corpus |
| Azure Foundry | Model router, prompt caching, provisioned throughput, flex and global batch | Cache only on supported models | [A-148 to A-152] |
| Amazon Bedrock | Intelligent prompt routing | Routes within a family | [A-158] |
| ccusage | Reads local JSONL logs; daily, weekly, monthly, session and 5-hour block reports; cache token tracking; 15+ agent CLIs; USD estimates | Estimates, local only | [C-003] |
| Claude Code Usage Monitor (`claude-monitor`) | Real-time burn rate | Community tool | [C-003] |
| Kiro Cost Optimizer (AWS, open source, serverless) | Per-developer Kiro credit usage | Kiro only | [A-056] |
| RouteLLM, LLMLingua | Model routing, prompt compression | Out of R4 scope | [C-061] |
| Claude Agent SDK | Per-turn usage and `total_cost_usd` for embedded use | Client-side estimate | [A-216] |
| Claude Code analytics | claude.ai analytics dashboard; Console Claude Code Analytics API with daily numbers | Excludes Bedrock, Vertex, Foundry and gateway-billed use | [C-085, C-005] |

Known gateway limits to design around (each stated as a risk, with the corpus gap marked):
- Soft-budget overshoot: not quantified in corpus. Assume in-flight requests complete after the budget is crossed.
- Stripping `cache_control`: a separately maintained gateway must forward every field and beta value Claude Code sends. Anthropic's own gateway does so by construction [C-088]. Verify cache reads after each Claude Code upgrade.
- 402 on exhaustion: documented for Bifrost [C-001]. Claude Code behaviour on 402 is not in corpus; test it.
- Cost is an estimate, not a bill, in every tool above.
