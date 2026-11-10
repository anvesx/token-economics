# Requirements traceability

Every requirement Token Economics must meet, with its sources, the components that carry it and its phase. Generated from `requirements.json`. Ids: `A:nnn` API corpus, `C:nnn` CLI corpus. A row labelled proposal has no corpus source and is a DevX proposal.

## Counts

| Phase | Requirements | Sourced | Proposal |
|---|---|---|---|
| P0 | 52 | 50 | 2 |
| P1 | 82 | 65 | 17 |
| P2 | 74 | 68 | 6 |
| P3 | 25 | 13 | 12 |
| Total | 233 | 196 | 37 |

## P0: measure only

| Id | Requirement | Sources | Components |
|---|---|---|---|
| RQ-A-001 | The system MUST route every harness that allows a base URL through the gateway and treat the gateway log as the source of truth, with hooks and OpenTelemetry (OTel) as supplements. | A:193, C:074, A:234 | gw, a_cc, a_cx, a_ai, a_sdk |
| RQ-A-003 | Each adapter MUST emit one UsageEvent with harness, session_id, prompt_id, agent, model, input, output, cache_read, cache_write, cost_estimate_usd, cost_source and auth_mode. | A:216, A:217, C:074 | a_cc, a_cx, a_ai, a_sdk, a_cli, a_obs, tee |
| RQ-A-004 | Every cost figure MUST carry cost_source of client, gateway or bill; client and gateway figures are list-price estimates, only the invoice is a bill. | C:076, C:094, A:232 | tee, joiner, trans, a_sdk, a_obs, a_cli |
| RQ-A-008 | The gateway MUST match each client protocol: Anthropic format with anthropic-beta forwarded for Claude Code, Responses API for Codex (wire_api responses), Chat Completions for Aider. | A:193, C:104, C:037 | gw, a_cc, a_cx, a_ai |
| RQ-A-009 | The gateway MUST forward cache_control and every anthropic-beta value unchanged, and cache reads MUST be re-checked after each Claude Code upgrade. | C:052, C:054, A:193, C:088 | gw, tee, a_cc, p_anth |
| RQ-A-011 | Gateway, hook and OTel rows MUST be joined on session_id and prompt_id. | C:074, A:217 | joiner, hookr, otelr, gw |
| RQ-A-013 | Prompt, tool and response content logging MUST stay off by default and only metadata is stored. | A:217, C:104 | otelr, hookr, trans, a_obs, tee |
| RQ-A-017 | The stream tee MUST pass response bytes to the client unchanged and read usage from a copy. | A:233, A:199 | tee, gw |
| RQ-A-018 | The system MUST flag a usage object with unknown extra keys instead of converting it silently. | A:233 | tee, p_anth, p_oai, p_xai, p_gem, p_rtr |
| RQ-A-019 | Each model call MUST be counted once whether it arrives through SDK telemetry or the gateway. | A:216, A:217 | a_sdk, otelr, joiner, tee |
| RQ-A-020 | Subagent spend MUST be attributed separately using query_source; result.usage alone is not enough. | A:216, A:217 | otelr, joiner, a_cc, a_sdk |
| RQ-A-021 | Resumed sessions MUST NOT be summed again, because resumed totals already include earlier spend. | A:216, C:094 | a_sdk, a_cli, b_cc, trans |
| RQ-A-022 | The hook receiver MUST use last_assistant_message on Stop and SubagentStop, and the replayer MUST copy transcripts, because transcript_path lags and local retention is 30 days. | C:074, C:003 | hookr, trans |
| RQ-A-026 | Each provider connector MUST return usage fields exactly as the provider names them so the normaliser can apply the per-provider table. | A:199, A:233, A:221, A:143, A:157, A:231 | p_anth, p_oai, p_xai, p_gem, p_rtr |
| RQ-A-030 | Connectors MUST NOT add reasoning tokens to output, because they already sit inside output_tokens. | A:197, A:251 | p_oai, p_xai, p_gem |
| RQ-A-031 | The xAI connector MUST send x-grok-conv-id per session and report the 200K band so the calculator can reprice all tokens. | A:221, A:224, A:225 | p_xai |
| RQ-A-032 | The Gemini connector MUST read cachedContentTokenCount (REST) or cached_content_token_count (SDK) and record explicit-cache storage use. | A:143, A:280, A:121 | p_gem |
| RQ-A-037 | The catalogue MUST match exact model ids and MUST NOT match partial names. | A:232 | cat |
| RQ-A-044 | For harnesses with no base URL, hook or OTel surface (Gemini CLI, Copilot CLI, Cursor, Amp, Kiro, others), the system MUST read vendor dashboards, exports or local files and label the result observe-only. | C:003, A:056, C:057, C:117, C:119, A:263 | a_obs, cap |
| RQ-A-045 | The gateway MUST own Aider cost, because Aider assumes zero cost for an unknown model. | C:040, C:037 | a_ai, gw |
| RQ-A-047 | The OTel receiver MUST ingest claude_code.token.usage, claude_code.cost.usage and claude_code.api_request, and MUST set cardinality options deliberately. | A:217, C:002 | otelr, a_cc |
| RQ-A-049 | Replayed transcript rows MUST be labelled client estimate. | C:003, C:076 | trans, a_obs |
| RQ-A-050 | The headless adapter MUST parse claude -p --output-format json for session id, usage and structured_output, and treat exit 0 as success. | C:094 | a_cli, b_cc |
| RQ-B-001 | The system MUST normalise every provider response to five mutually exclusive token buckets (fresh_input, cache_read, cache_write_5m, cache_write_1h, output), subtracting cached tokens where the provider counts them inside input. | A:233, A:199, A:190 | norm |
| RQ-B-002 | The system MUST count reasoning tokens as output and MUST NOT add reasoning_tokens on top of output_tokens. | A:197, A:251, A:065 | norm, calc |
| RQ-B-003 | The normaliser MUST reject a usage object with unknown extra keys instead of converting it silently. | A:233 | norm |
| RQ-B-004 | The bucket schema and price rows MUST allow a cache write rate of 1x, because some providers charge no write premium. | A:201, A:182 | norm, pb |
| RQ-B-005 | The system MUST write one ledger row per provider response id, MUST collapse parallel tool calls that share a message id, and MUST ignore placeholder per-step output_tokens in favour of the final result. | A:216 | dedupe |
| RQ-B-006 | The system MUST count each call once, whether it arrives through SDK telemetry or through the gateway. | A:216, A:217 | dedupe, attr |
| RQ-B-007 | The system MUST NOT re-sum totals when a session resumes, because resumed totals already include earlier spend. | A:216 | dedupe, led |
| RQ-B-008 | The system MUST attribute subagent spend separately and MUST NOT rely on result.usage alone. | A:216, A:217 | attr |
| RQ-B-009 | The ledger key MUST include the exact model id (no partial-name matching), service tier, speed, effort, inference geo, caller id, session id and TTL class. | A:232, A:055, A:217 | led, calc |
| RQ-B-010 | Ledger rows MUST be append-only, and a price change MUST NOT rewrite past rows. | A:232, A:233 | led, pb |
| RQ-B-012 | The system MUST compute cost from a versioned price table keyed by provider, model, effective date and tier, MUST store provider-reported cost when present, and MUST prefer it over the computed value. | A:232, A:233 | pb, calc, led |
| RQ-B-013 | The system MUST cost each request against the price row valid at request time and MUST store price_row_id on the ledger row. | A:214, A:069 | pb, led, calc |
| RQ-B-014 | The price lookup MUST match the exact model id and MUST NOT fall back to a partial-name match. | A:232 | pb, calc |
| RQ-B-015 | Each price row MUST carry the flags band_scope, input_includes_cached, reasoning_in_output, batch_stacks_with_cache and billed_units_source. | A:225, A:233, A:197, A:252, A:177 | pb, norm |
| RQ-B-016 | The system MUST decide batch and cache stacking per provider and model, with the value true, false or unknown. | A:252, A:255, A:281 | pb, calc |
| RQ-B-017 | Gemini implicit-cache discount MUST be stored per model and date, because sources disagree between 75 percent and 90 percent. | A:121, A:280, A:281 | pb |
| RQ-B-018 | The calculator MUST re-band on total prompt tokens, MUST reprice every bucket when band_scope is all_tokens, and MUST apply Priority and regional multipliers after the cache discount. | A:225, A:270, A:176, C:010 | calc, pb |
| RQ-B-019 | The calculator MUST use vendor billed units, not local token counts, where the vendor reports them. | A:177, C:010 | calc, norm |
| RQ-B-020 | The calculator MUST treat an unknown price as unpriced and MUST NOT record it as zero cost. | A:242, A:234 | calc |
| RQ-B-021 | The calculator MUST bill a failed or expired batch or flex request at zero. | A:219, A:195 | calc |
| RQ-B-023 | Every cost MUST carry a cost_source of client, gateway or bill and an auth_mode, because only the provider invoice is a bill. | A:232, A:216, C:002 | calc, led |
| RQ-B-024 | The calculator SHOULD run off the request path and, when pricing fails, SHOULD write the row as unpriced and keep the reservation as the spend bound. | DevX proposal | calc |
| RQ-B-025 | The price book SHOULD check each stored cache rate against its vendor multiplier on insert and flag a mismatch. | A:199 | pb |
| RQ-B-028 | Plan rows MUST hold plan, fee, unit, included_qty (nullable), credit_usd, reset_rule, overage_rate and model_weighting (nullable). | C:010, C:119, C:116, C:114, C:011 | pplan |
| RQ-B-037 | The system MUST attribute cost per caller, task, repo and model. | C:052, C:028 | attr, meta |
| RQ-B-038 | The system MUST join gateway, hook and OTel rows on session_id and prompt_id. | C:074, A:217 | attr |
| RQ-B-041 | The metadata store MUST hold the UsageEvent fields (harness, session_id, prompt_id, agent, model, input, output, cache_read, cache_write, cost_estimate_usd, cost_source, auth_mode) plus price_row_id and no content. | A:217, C:074 | meta |
| RQ-B-042 | The system MUST default to metadata only and MUST treat prompt, tool and response logging as opt-in. | A:217 | meta, logp |
| RQ-B-043 | Content logging MUST default to off for OTEL_LOG_USER_PROMPTS, OTEL_LOG_TOOL_DETAILS, OTEL_LOG_TOOL_CONTENT, OTEL_LOG_ASSISTANT_RESPONSES and OTEL_LOG_RAW_API_BODIES. | A:217 | logp |

## P1: enforce

| Id | Requirement | Sources | Components |
|---|---|---|---|
| RQ-A-002 | The system MUST NOT rely on a client hook for enforcement; budgets are enforced at the gateway or in managed settings. | A:234, C:074, C:136 | gw, hookr, fmode, a_cc |
| RQ-A-005 | The capability registry MUST hold eight flags per harness (baseUrl, oauthPassthrough, hooksBlocking, otel, budgetFlag, headless, modelRewrite, transcriptPath), and the policy engine MUST degrade to observe-only when a flag is false. | C:104, A:193, C:074 | cap, a_cc, a_cx, a_ai, a_obs |
| RQ-A-006 | An unknown capability MUST be stored as unknown and treated as false until a test proves it. | C:104 | cap, a_cx, a_ai |
| RQ-A-007 | The system MUST pin the route so a developer cannot bypass the gateway: allowedProviders customEndpoint in Claude Code managed settings, model_provider in user-level or managed Codex config. | A:193, C:104 | a_cc, a_cx, authk |
| RQ-A-010 | The gateway MUST keep one provider endpoint per session, because a provider or model switch mid-session loses the cache. | A:231, A:247 | gw, p_rtr, fb, p_oai |
| RQ-A-012 | Observation paths MUST fail open and budget paths MUST fail closed with HTTP 402 when the budget is exhausted. | C:074, C:001 | fmode, gw, hookr, tee |
| RQ-A-014 | Headless runs MUST pass --max-budget-usd and --max-turns, and interactive runs MUST be capped by gateway virtual-key budgets. | C:094, C:080 | a_cli, b_cc, b_cx, gw |
| RQ-A-015 | The OAuth passthrough guard MUST forward the Authorization header and the OAuth capability in anthropic-beta, and MUST NOT store or log tokens. | A:193 | b_oauth, gw, a_cc |
| RQ-A-016 | Subscription traffic MUST be tracked as percentage windows from rate_limits, because no dollar figure exists for it. | C:076, A:193, C:010 | a_cc, a_obs, b_oauth |
| RQ-A-023 | Policy hooks MUST block with exit code 2 and keep each output string under 10,000 characters. | C:074 | hookr |
| RQ-A-028 | The OpenAI connector MUST send prompt_cache_key per session and cap each prefix and key near 15 requests per minute. | A:202, A:148 | p_oai |
| RQ-A-033 | The aggregator connector MUST sum inputTokens, cacheReadInputTokens and cacheWriteInputTokens for Bedrock, send cachePoint, and never send ttl to 5-minute-only Bedrock models. | A:157, A:159, A:160 | p_rtr |
| RQ-A-034 | The aggregator connector MUST send session_id or x-session-id (max 256 characters) to OpenRouter and set provider order, allow_fallbacks, require_parameters and data_collection explicitly. | A:231, A:227, A:229 | p_rtr |
| RQ-A-035 | Connectors MUST NOT add volatile values such as timestamps to the prompt top; stable content comes first. | A:224 | p_anth, p_oai, p_xai, p_gem, gw |
| RQ-A-038 | The catalogue and rate-limit tracker MUST hold rpm, tpm, rpd and a 429_billed flag per model and tier; flex and batch 429 responses are not charged. | A:195, A:150, A:219 | cat, rl |
| RQ-A-039 | A fallback hop MUST be priced and logged with its reason, never silent, and batch or flex work retries on the standard tier after a 429. | A:195, A:281, A:219, A:192 | fb, rl, cat |
| RQ-A-041 | The gateway MUST return 402 when the virtual key budget is spent, and in-flight requests MAY finish, so soft-cap overshoot is recorded. | C:001, A:234, A:242, A:245 | gw, authk, fmode |
| RQ-A-042 | The key resolver MUST map each virtual key to tenant, team and agent and MUST count BYOK (bring your own key) spend. | C:060, C:001, A:245 | authk |
| RQ-A-046 | The Codex adapter MUST test hook stdin and exit-code behaviour, OTel event names and ChatGPT sign-in through a custom provider before relying on them. | C:104 | a_cx, hookr, otelr, cap |
| RQ-A-048 | The gateway log MUST carry cache fields per caller so per-caller hit rate can be computed. | C:052, C:054 | tee, joiner, gw |
| RQ-A-051 | The claude -p runner MUST account for --bare skipping hooks, skills, MCP, plugins, memory and CLAUDE.md, and MUST pass hooks explicitly with --settings if needed. | C:094 | b_cc |
| RQ-A-052 | The codex exec runner MUST put model_provider in user-level config and MUST rely on gateway budgets because no Codex budget flag appears in the corpus. | C:035, C:104 | b_cx, a_cx, a_cli |
| RQ-A-053 | Spend limits MUST live outside the model. | C:136 | gw, b_cc, b_cx, a_cli |
| RQ-B-011 | A correction to a ledger row SHOULD be written as a new row that names the row it supersedes. | DevX proposal | led |
| RQ-B-026 | A daily job MUST flag price rows within 30 days of expires_at or unverified for 30 days, and expired promos MUST fall back to the list price with an alert. | A:214 | plife, pb |
| RQ-B-027 | The system MUST block billing decisions on price rows older than 30 days or past expiry. | A:121, A:280, A:148 | plife, pb |
| RQ-B-029 | Plan rows MUST carry expires_at and the plan table MUST be re-verified when a promo ends. | A:214, C:115, C:011 | pplan, plife |
| RQ-B-030 | The system MUST track plan quota in native units (credits, premium requests, messages per 5 hours, pool multiples) and MUST NOT convert them to tokens. | C:010, C:119, C:057, C:116 | pplan, planq |
| RQ-B-031 | For plan billing the system MUST record marginal dollars as zero inside the pool, overage after it, and MUST report shadow API cost plus amortised fee. | C:010 | pplan, planq, calc |
| RQ-B-039 | The system MUST record failed and retried attempts as spend against the task and MUST report cost per successful task as total spend over all attempts divided by successes. | C:122, C:028, A:207 | attr, dash |
| RQ-B-040 | The system MUST track failed-run waste share and spend after the first repeated failure signature. | C:028 | attr, dash |
| RQ-B-044 | A content-logging opt-in SHOULD be per tenant, written to the audit log and given an expiry date. | DevX proposal | logp |
| RQ-B-046 | The system MUST measure cache hit rate per caller, per model and per prefix hash as cache_read over fresh plus read plus write, and MUST alert when a caller falls below its own baseline. | C:052, C:054 | dash, meta |
| RQ-B-047 | A cache miss event SHOULD be defined as more than 5 percent and at least 2,000 tokens reprocessed. | C:076 | dash, meta |
| RQ-B-048 | The system MUST report mean, median and 95th percentile (P95) spend per user and MUST alert on the tail. | C:054, C:101 | dash |
| RQ-B-049 | Reports MUST lead with cost per successful task and MUST NOT present token savings alone. | C:024, A:069 | dash |
| RQ-C-001 | The system MUST enforce budgets at the gateway in hard-cap mode, outside the agent, and return an error when a key is exhausted. | C:136, A:234, C:062 | bst, bres |
| RQ-C-002 | The system MUST store per virtual key a max_budget and a budget_duration, and allow stacked windows such as $10 per day and $100 per month. | C:060, C:061 | bst |
| RQ-C-003 | The system MUST reserve a worst-case cost before dispatch (max_tokens times output price plus a reasoning reserve of at least 25,000 tokens) and reconcile with the true cost after the response. | A:197 | bres |
| RQ-C-004 | The system MUST price every model and every path, and MUST block a request for a model with no price row instead of counting it as zero cost. | A:191, A:242, A:245 | bres, bst |
| RQ-C-005 | The system MUST treat any eventually consistent spend limit as a soft cap and MUST apply an explicit overshoot margin. | A:191, A:234, A:246 | bst, bres |
| RQ-C-006 | The system SHOULD set the default overshoot margin to the reserved amount of in-flight requests, and report it per key. | DevX proposal | bst, bres |
| RQ-C-007 | The system MUST raise budget alerts at 75, 90 and 100 percent of each window. | A:213, C:116 | alert, bst |
| RQ-C-008 | The system SHOULD size per-user budgets around the 95th percentile of spend, not the mean. | C:054, C:101 | alert, bst |
| RQ-C-009 | The system MUST cap per-task turns at a per-model percentile of baseline turns, starting at the 75th and never at the 25th, with a remaining-turns reminder and a fallback when the cap hits. | C:025 | tcap |
| RQ-C-010 | The system MUST keep one turn baseline per model, because baselines differ across models. | C:025 | tcap |
| RQ-C-011 | The system MUST pass --max-budget-usd and --max-turns on headless Claude runs, and use gateway virtual-key budgets for interactive runs. | C:080, C:094 | tcap, bst |
| RQ-C-012 | The system MUST detect repeated failure signatures and redirect or stop the run, and MUST log the spend after the first repeated failure. | C:028, A:246 | loop |
| RQ-C-013 | The system MUST run a rate-based loop breaker for repeated reads, unchanged test reruns and repeated failures. | A:059, C:028, C:062 | loop |
| RQ-C-014 | The system MUST NOT rely on a client hook for loop detection alone, because developers can disable hooks. | A:234, C:074 | loop |
| RQ-C-015 | The system MUST carry one affinity key per session (prompt_cache_key, x-grok-conv-id or session_id) and cap each key near 15 requests per minute per prefix on OpenAI. | A:202, A:148, A:221, A:231 | stick |
| RQ-C-016 | The system MUST keep one provider endpoint per session and MUST NOT switch provider mid-session without pricing the cache loss. | A:231, A:247, A:149 | stick, swp |
| RQ-C-017 | The system MUST treat effort, fast mode, tool set and model as cache keys and change them only at session start or at a priced boundary. | C:055, C:086, A:204, A:282 | swp, stick |
| RQ-C-040 | The system MUST measure hit rate per caller, per model and per prefix hash as cache_read over fresh plus read plus write, and alert on any caller below its own baseline. | C:052, C:054 | hit |
| RQ-C-041 | The system SHOULD flag a cache miss as more than 5 percent and 2,000 or more tokens re-processed, and record the miss cause. | C:076 | hit |
| RQ-C-042 | The system SHOULD alert when a caller's hit rate falls more than 3 standard deviations below its 14-day mean. | DevX proposal | hit |
| RQ-C-050 | The system MUST fail open for observation paths and fail closed for budget paths. | C:074 | bst, bres, alert |
| RQ-D-004 | The gateway MUST cap every tool result at 25,000 tokens for interactive routes and 6,000 to 12,000 tokens for batch routes. | A:284, C:106, C:036 | ocap |
| RQ-D-005 | The output cap MUST NOT truncate tracebacks, test failures or edit anchors. | C:024, C:128 | ocap |
| RQ-D-015 | The gateway MUST set a hard max_tokens on every call, because effort does not cap tokens. | C:073, C:093, A:197 | mtok |
| RQ-D-016 | The max_tokens policy MUST have a per-class floor so the cap does not break hard tasks. | A:052 | mtok |
| RQ-D-017 | The gateway MUST NOT dispatch a request without a max_tokens value, because the budget reserve needs it. | A:197, C:136 | mtok |
| RQ-D-023 | The headline metric MUST be cost per successful task including failed attempts, and the system MUST NOT report token savings alone. | A:122, A:069, C:026, C:024 | cpsc |
| RQ-D-024 | The calculator MUST record failed and retried attempts as spend against the task. | C:028, A:122 | cpsc |
| RQ-D-055 | Budgets set through the admin API MUST be enforced outside the agent, in hard-cap mode, at the gateway or in managed settings. | C:136, A:234, A:191 | api, tenant |
| RQ-D-056 | Budget paths MUST fail closed and return HTTP 402 when the budget is exhausted; observe paths MUST fail open. | C:001, C:074 | api, tenant, pol |
| RQ-D-057 | Every admin write MUST produce an audit record with actor, time, before and after. | DevX proposal | api, audit |
| RQ-D-058 | The admin API SHOULD expose keys, budgets, policies, reports and kill state as versioned REST resources. | DevX proposal | api |
| RQ-D-059 | Policy changes MUST be versioned, reviewed before apply, and published as a signed bundle. | DevX proposal | pol |
| RQ-D-060 | Managed settings MUST pin the route: allowedProviders for Claude Code, and model_provider in user or managed config for Codex, never project config. | C:001, A:193, C:104 | pol |
| RQ-D-061 | Enforcement MUST live at the gateway or in managed settings and MUST NOT rely on a client hook. | A:234, C:074 | pol, api |
| RQ-D-062 | The gateway MUST keep the last good bundle; with no bundle it MUST pass observe paths and reject budget paths with 503. | C:074 | pol, api |
| RQ-D-063 | Virtual keys MUST carry max_budget and a duration, and windows MUST stack. | C:060, C:061, C:001 | tenant |
| RQ-D-064 | A key MUST NOT allow a model that has no price-book row. | A:242, A:245, A:191 | tenant |
| RQ-D-066 | Key revocation MUST take effect on the next request at the gateway. | DevX proposal | tenant |
| RQ-D-067 | The audit log MUST store metadata only, never prompt or response content. | A:217, C:104 | audit, ret |
| RQ-D-068 | The audit log MUST be append-only and tamper-evident. | DevX proposal | audit |
| RQ-D-069 | Provider keys MUST live in a secrets vault and MUST be fetched at call time, never stored in config. | C:104 | secrets |
| RQ-D-070 | The system MUST forward OAuth tokens and anthropic-beta values unchanged and MUST NOT store them. | A:193, C:088 | secrets |
| RQ-D-071 | A secret fetch failure MUST fail the request closed and MUST NOT fall back to another tenant key. | DevX proposal | secrets |
| RQ-D-072 | Admin access MUST use scoped tokens and roles with deny by default. | C:088 | authz |
| RQ-D-074 | Content logging MUST default to off and MUST require an explicit opt-in per tenant. | A:217, C:104 | ret |

## P2: optimise

| Id | Requirement | Sources | Components |
|---|---|---|---|
| RQ-A-024 | A model, effort, speed or tool-set change mid-session MUST be priced for cache loss first, and the hook receiver SHOULD gate PreModelSwitch. | A:204, C:055, C:074, A:192 | hookr, a_cc, fb, rl |
| RQ-A-025 | Model downgrade for Claude Code MUST stay inside the Claude family; a gateway body rewrite is a risk because it is not documented as supported. | A:193, C:073 | gw, a_cc, cap |
| RQ-A-027 | The Anthropic connector MUST send cache_control with ttl 5m or 1h, at most 4 breakpoints, longer TTL entries first, and system as an array of blocks. | A:199, A:283 | p_anth |
| RQ-A-029 | The OpenAI connector MUST use prompt_cache_options mode and ttl (30m or 12h) on GPT-5.6 and later, and prompt_cache_retention before it. | A:201, A:204 | p_oai |
| RQ-A-036 | The connector MUST skip cache_control when the prefix is below the model minimum, and the catalogue MUST hold the larger of two conflicting minimums. | A:199, C:051, A:201 | cat, p_anth, p_oai |
| RQ-A-040 | After an error the fallback chain SHOULD default to the same model unless the saving exceeds the cache-rewrite cost. | A:008, A:204, C:030 | fb |
| RQ-B-022 | The calculator SHOULD use the expected cache hit rate, not the ideal one, when estimating batch cost. | A:219 | calc |
| RQ-B-050 | The anomaly detector SHOULD alert on cost and token series outliers per caller and per model. | DevX proposal | anom |
| RQ-B-051 | The anomaly detector MUST only alert and MUST NOT block traffic, because blocking belongs to budgets. | C:136 | anom |
| RQ-C-018 | The system MUST switch models mid-session only if the expected saving exceeds the cache-rewrite cost of the incoming model, and MUST log the reason. | A:192, C:030, A:204, C:055 | swp, rules |
| RQ-C-019 | The system SHOULD stay on the current model after an error by default. | A:008 | swp, rules |
| RQ-C-020 | The system MUST prefer an effort change over a model switch when the provider keeps the cache on effort change. | A:228, A:282 | rules, swp |
| RQ-C-021 | The system MUST ship a best-single-model baseline before any router, and MUST report every router result against Best Single and an oracle in dollars per solved task. | A:006, A:002, A:001, C:026 | rules, srt, casc |
| RQ-C-022 | The system MUST classify with rules plus atomic yes or no questions at session start or at tier boundaries, and escalate on a verifiable failure. | A:052, A:018, A:245, C:031 | rules |
| RQ-C-023 | The system MUST route tool-bearing requests and requests with a failed verifiable check to the strong tier. | C:031, A:245 | rules, srt |
| RQ-C-024 | The system MUST NOT use a broad single-question classifier or a regex-only heuristic as the router. | A:052 | rules |
| RQ-C-025 | The system MUST train any step-level router on execution-verified counterfactual labels with class balance. | C:030, A:019, A:013, A:001 | srt |
| RQ-C-026 | The system MUST check router quality on blind labels and out-of-distribution tasks before rollout. | A:018, C:032, A:052 | srt, rules |
| RQ-C-027 | The system MUST NOT prompt a frontier model as the router, MUST NOT train on logs from one dominant model, and MUST keep the model pool small and complementary. | C:030, A:228, A:019, A:006 | srt, rules |
| RQ-C-028 | The system MUST log per request: caller, model, effort, prefix size, cache read and write, turns, outcome, router reason, router latency and router cost. | C:026, C:052, A:192 | rules, srt, swp |
| RQ-C-029 | The system MUST enable a cascade for a model pair only when measured tier-1 acceptance exceeds c1 over c2, with an Always-Strong fallback. | A:028, C:031, A:123 | casc |
| RQ-C-030 | The system MUST NOT use a sum log-probability deferral score without length normalisation. | A:022 | casc |
| RQ-C-031 | The system MUST price every fallback hop and judge call, and MUST NOT make fallbacks silent. | A:021, A:002 | casc |
| RQ-C-032 | The system MUST size per-task budgets from one probe run with a 1.9x multiplier, not from agent self-estimates. | C:027, C:110 | probe, bres |
| RQ-C-033 | The system MUST cap each tenant's strong-model share, with drift alerts. | A:010 | share |
| RQ-C-034 | The system SHOULD set the default strong-share ceiling at 1.5 times the tenant's own 30-day baseline share. | DevX proposal | share |
| RQ-C-035 | The system MUST enable caching only when the prefix meets the model minimum and the expected reads repay the write premium. | A:199, A:201 | cplan |
| RQ-C-036 | The system MUST choose the cache TTL per caller from the observed reuse gap, not globally. | C:052 | cplan |
| RQ-C-037 | The system MUST keep stable content first and volatile content such as timestamps last in the prefix. | A:224 | cplan |
| RQ-C-038 | The system MUST forward cache_control and the anthropic-beta header unchanged, and MUST NOT send ttl to 5-minute-only Bedrock models. | C:052, C:054, A:157 | cplan |
| RQ-C-039 | The system MUST NOT rely on cache for Bedrock batch inference or Nova reads. | A:160, A:157 | cplan, tsel |
| RQ-C-043 | The system MUST send only latency-tolerant, non-streaming, non-SLA work to batch or flex, and MUST retry on standard after a 429 from flex. | A:195, A:281, A:219 | tsel |
| RQ-C-044 | The system MUST decide batch and cache stacking per provider and model, and MUST bill cache reads at the batch input rate where stacking is false. | A:252, A:255, A:281, A:219 | tsel, cplan |
| RQ-C-045 | The system MUST NOT change tier or model mid-conversation without costing a cold cache; fast mode mid-conversation bills the whole context uncached. | C:086, A:176 | tsel, swp |
| RQ-C-046 | The system SHOULD recommend reserved capacity only when steady load exceeds about 40 percent of the on-demand cost. | A:159 | tsel |
| RQ-C-047 | The system MUST gate small-model routing on per-task eval parity with rollback triggers. | A:129, C:050 | tsel, rules |
| RQ-C-048 | The system MUST route to a small model only if cost_small plus P(fail) times cost_escalation is below cost_big, with P(fail) taken from our own labelled slice. | A:129, A:186 | tsel |
| RQ-C-049 | The system MUST rank models by cost per solved task, not list price. | A:069, A:065, A:135 | tsel, rules |
| RQ-D-001 | The system MUST defer tool schemas above about 20 tools or 10 percent of the context window, and MUST provide a schema lookup path. | C:019, C:021, C:022 | schema |
| RQ-D-002 | The system MUST decide tool deferral at session start and MUST NOT add or remove tools mid-session, because a tool change invalidates the prompt cache. | C:055, A:204 | schema |
| RQ-D-003 | The system MUST NOT prune tools without a recovery path to the full catalogue. | C:021, C:028 | schema |
| RQ-D-006 | The system MUST NOT pipe compressed tool output into shell counting or parsing. | C:024 | ocap |
| RQ-D-007 | The system MUST NOT enable any output compressor without a per-workload A/B on cost per successful task and at least 99 percent marker recall. | C:024, C:028 | ocap, evalh |
| RQ-D-008 | History edits MUST happen only at a trigger, never on every turn, because an edit breaks the exact-prefix cache from the first changed block. | C:066, C:130, C:055 | mask, clear, compact |
| RQ-D-009 | The system MUST NOT condense history below about 10 events. | C:133 | mask, compact |
| RQ-D-010 | The system MUST prefer observation masking over LLM summaries for tool observations. | C:130, C:133 | mask |
| RQ-D-011 | Context clearing MUST start at trigger 30,000 to 40,000 tokens, keep 5 tool results, clear at least 3,000 to 5,000 tokens, then be tuned per scaffold. | C:066, C:065, C:130 | clear |
| RQ-D-012 | The system MUST protect non-re-fetchable tool results with exclude_tools and MUST persist state to a handoff or memory file before clearing. | C:067, C:035, C:065 | clear |
| RQ-D-013 | Clearing MUST fire only when the tokens removed repay the cache re-write of the retained suffix. | C:066, C:065 | clear |
| RQ-D-014 | The system MUST compact only near the window limit, MUST count compactions per session, and MUST recommend a restart at 3. | A:224, C:112, C:106 | compact |
| RQ-D-018 | The linter MUST flag CLAUDE.md above 200 lines and AGENTS.md above 32 KiB, and MUST flag stale skills. | C:077, C:036, C:028 | ilint |
| RQ-D-019 | The linter MUST warn when MEMORY.md exceeds 200 lines or 25 KB, and when skill descriptions exceed 1,536 characters. | A:269, C:075, C:079 | ilint |
| RQ-D-020 | The linter MUST flag default wording that asks for multiple approaches or deep thinking. | C:026 | pwl |
| RQ-D-021 | The linter MUST flag volatile values, such as timestamps, near the top of a prompt. | A:224, A:204, C:055 | pwl |
| RQ-D-022 | The linter MUST NOT recommend generic brevity wording such as "be concise" as a default. | A:104 | pwl |
| RQ-D-025 | The system MUST report failed-run waste share and spend after the first repeated failure signature. | C:028 | cpsc |
| RQ-D-026 | The system MUST report cost dispersion per task and arm as a geometric standard deviation. | C:027, C:023 | cpsc, stats |
| RQ-D-027 | The system MUST log tokens by category per task and judge each change on billed cost per success. | C:024 | cpsc, evalh |
| RQ-D-028 | The calculator MUST output the quality floor set: pass rate, patch-apply rate, empty-patch rate, format validity and fix-commit ratio. | C:025, C:024, C:053 | cpsc, evalh |
| RQ-D-029 | Comparisons MUST be paired by task with repeats and MUST report task-clustered confidence intervals. | C:027, C:023, C:026 | stats, evalh |
| RQ-D-030 | A non-inferiority bound on success MUST be declared before the test, and a breach MUST trigger automatic revert. | C:025, C:024, A:052 | stats, canr, rollb |
| RQ-D-031 | The stats component SHOULD size the run from the standard deviation of a pilot. | C:027 | stats |
| RQ-D-032 | No optimisation MUST ship without a same-task baseline arm and isolated cache state per arm. | C:024, A:006 | evalh |
| RQ-D-033 | The harness MUST record a verifiable success flag on every attempt. | C:026 | evalh |
| RQ-D-034 | The harness MUST charge each optimisation own overhead to the task. | C:026, C:028, C:024 | evalh, cpsc |
| RQ-D-035 | The harness SHOULD log prompt variant, effort, harness version, tool surface, retries, compaction and whether the optimisation fired for every attempt. | C:026 | evalh |
| RQ-D-036 | The system MUST NOT enable voting, ensembles or agent teams without a measured gain in cost per successful task. | A:122, C:132, C:081 | evalh |
| RQ-D-037 | Every router result MUST be reported against Best Single and an oracle, in dollars per solved task. | A:006, A:002, A:001, C:026 | evalh, stats |
| RQ-D-039 | The system MUST keep a private eval set with hard cases and a Lite subset. | A:060, C:024 | gold |
| RQ-D-040 | Tasks used for tuning MUST be held out from the eval split. | A:052 | gold |
| RQ-D-041 | Router training labels MUST come from execution-verified counterfactual outcomes with class balance, or from preference labels debiased with 100 to 1,000 gold samples; the system MUST NOT train a router on logs from one dominant model. | C:030, A:019, A:013, A:001 | gold, pol |
| RQ-D-042 | Router quality MUST be checked on blind labels and out-of-distribution tasks before rollout. | A:018, C:032, A:052 | gold, evalh, canr |
| RQ-D-045 | The system SHOULD score routers on static labelled traces before any live shadow. | C:030 | shadow, evalh |
| RQ-D-065 | The tenant record MUST hold a ceiling on strong-model share, with drift alerts. | A:010 | tenant, pol |

## P3: production hardening

| Id | Requirement | Sources | Components |
|---|---|---|---|
| RQ-A-043 | Provider keys MUST be fetched from the secrets vault at call time and never stored in configuration. | A:193 | p_anth, p_oai, p_xai, p_gem, p_rtr, authk |
| RQ-A-054 | The gateway SHOULD add under 50 ms at the 95th percentile (p95) before the first byte on the pass-through path. | DevX proposal | gw, tee, authk |
| RQ-B-032 | The quota tracker SHOULD fit dollars per plan unit, with a band, from one developer-week per plan. | C:010 | planq |
| RQ-B-033 | The reconciler MUST compute the ratio of client estimate to provider invoice per provider, at least monthly. | A:216, C:002, C:004 | rec |
| RQ-B-034 | The reconciler SHOULD compare per provider key and per day, with a tolerance set from the first pilot. | DevX proposal | rec |
| RQ-B-035 | The canary MUST compare computed cost with vendor usage or invoice weekly, per provider and tier, with a target error under 1 percent. | A:216, C:002 | canary |
| RQ-B-036 | Drift above 1 percent SHOULD mark the affected price row stale and raise an alert. | DevX proposal | canary, plife |
| RQ-B-045 | Metadata rows SHOULD carry an expiry date set by the retention policy, and usage derived from transcripts SHOULD be persisted because Claude Code keeps transcripts about 30 days. | C:003 | meta |
| RQ-C-051 | The system SHOULD disable each optimisation per tenant through the kill-switch, and MUST report guard metrics for the policy components. | C:063 | tcap, loop, rules, srt, casc, cplan, tsel, share |
| RQ-D-038 | The harness SHOULD track AI-generated defect burden next to cost. | C:053 | evalh |
| RQ-D-043 | Rollout MUST use shadow runs on mirrored traffic with write isolation. | C:063 | shadow |
| RQ-D-044 | Shadow runs MUST NOT delay or alter the live response, and MUST run under a separate shadow budget because shadow doubles spend. | C:063 | shadow |
| RQ-D-046 | The canary MUST advance only on a passing verdict from the CPS calculator, in stages with guard metrics. | C:063, C:024 | canr, cpsc |
| RQ-D-047 | The canary MUST assign arms per session, never per request, because a mid-run change breaks the cache. | A:204, C:055 | canr |
| RQ-D-048 | Small-model routing MUST be gated on per-task eval parity with rollback triggers. | A:129, C:050, C:063 | canr, rollb, evalh |
| RQ-D-049 | The system MUST provide a kill-switch per tenant and per optimisation that reverts to the unchanged default path. | C:063, A:204 | kill |
| RQ-D-050 | Kill-switch state MUST be enforced at the gateway through policy and MUST NOT depend on a client hook. | A:234, C:074 | kill, pol |
| RQ-D-051 | When the policy bundle is missing or unreadable, every optimisation MUST resolve to off. | C:074 | kill, pol |
| RQ-D-052 | Auto-rollback MUST watch six triggers: success below floor, CPS above baseline interval, per-caller hit rate below baseline, empty-patch or apply-failure spike, p95 latency up 20 percent, billed versus estimate divergence. | C:063, C:025, C:052, C:076 | rollb |
| RQ-D-053 | The divergence trigger MUST compare ledger estimate to invoice per provider. | A:216, C:002 | rollb |
| RQ-D-054 | The hit-rate trigger MUST compare each caller to its own baseline, never the account rate. | C:052, C:076 | rollb |
| RQ-D-073 | Tripping a kill-switch SHOULD need a lower role than clearing it. | DevX proposal | authz, kill |
| RQ-D-075 | Retention windows MUST be set per tenant in policy and enforced by an expiry job. | C:003 | ret |
| RQ-D-076 | Retention MUST NOT delete price rows referenced by a retained ledger row. | A:232 | ret |
| RQ-D-077 | Redaction MUST drop unknown content fields on write. | DevX proposal | ret |
