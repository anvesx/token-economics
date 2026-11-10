# Architecture

The interactive version is `token-economics-lld.html` (8 stages, 20 groups, 79 components, every node clickable). This file is the text form.

## One request, end to end

```
harness ──► gateway ──► key + tenant ──► policy engine ──► backend
                │                            │               │
                │                  reserve worst case        │
                ▼                            │               ▼
          stream tee ◄─────────────── provider response ◄────┘
                │
                ▼
          normaliser ──► dedupe ──► cost calculator ──► ledger
                                                          │
                          budget true-up ◄────────────────┤
                          dashboards, reconciler, eval ◄──┘
```

1. The harness sends a request to the gateway URL (`ANTHROPIC_BASE_URL`, Codex `model_providers.<id>.base_url`, or `OPENAI_API_BASE`).
2. The key resolver maps the virtual key to tenant, team and agent.
3. The policy engine reserves the worst-case cost, applies turn cap, loop guard, routing, cache plan and tier.
4. The connector sends the request to the backend and tees the response stream.
5. The normaliser reads the usage object into five exclusive buckets. The dedupe guard keeps one row per provider response id.
6. The cost calculator prices the buckets with the price row stored by `price_row_id`, then writes the ledger row.
7. The budget store replaces the reservation with the true cost.
8. Hook, OpenTelemetry and transcript rows join on `session_id` and `prompt_id` for attribution. They never change the cost.

## Stages

| Stage | Role | Groups |
|---|---|---|
| 1 Ingress and adapters | Entry, per-harness control | Gateway edge, Harness adapters, Client signals |
| 2 Backends | API and CLI backends | API providers, CLI backends, Backend health |
| 3 Accounting | Truth about cost | Price book, Metering, Reconciliation |
| 4 Policy engine | Decisions before dispatch | Budgets, Run control, Routing, Tier and cache |
| 5 Context guard | Smaller prompts | Context controls |
| 6 Insight | People-facing views | Stores and attribution, Views and alerts |
| 7 Eval and rollout | Proof and safety | Evaluation, Rollout safety |
| 8 Control plane | Operators | Admin and config, Security and data |

## Integration surfaces, by precedence

| Rank | Surface | Can enforce | Notes |
|---|---|---|---|
| 1 | Gateway base URL | Yes | Source of truth. Cannot be disabled by developers. |
| 2 | Managed settings that pin the route | Yes | Claude Code `allowedProviders: ["customEndpoint"]`. |
| 3 | Hooks | Partly | Exit code 2 blocks on Claude Code. Developers can disable hooks. |
| 4 | OpenTelemetry | No | Metrics and events with `prompt.id`. |
| 5 | Transcripts and local files | No | Replay after the fact, labelled client estimate. |
| 6 | Vendor dashboards and exports | No | Only option for harnesses with no pluggable surface. |

## The adapter contract

Every adapter implements five functions.

| Function | Purpose |
|---|---|
| `route(env)` | Point the harness at the gateway. |
| `identify(request)` | Return tenant, team, agent, session and prompt ids. |
| `observe(stream)` | Return one normalised `UsageEvent`. |
| `cap(policy)` | Translate a policy into the controls the harness supports. |
| `replay(transcript)` | Rebuild usage rows from local files. |

Eight capability flags per harness: `baseUrl`, `oauthPassthrough`, `hooksBlocking`, `otel`, `budgetFlag`, `headless`, `modelRewrite`, `transcriptPath`. When a flag is false the policy engine degrades that control to observation.

## Normalised usage event

`harness, session_id, prompt_id, agent, model, input, output, cache_read, cache_write, cost_estimate_usd, cost_source (client|gateway|bill), auth_mode`

## Reuse before build

| Need | Reuse | Note |
|---|---|---|
| Virtual keys, budgets, budget fallbacks, cache injection points | LiteLLM | Strong fit for the gateway core. |
| 402 on budget exhaustion | Bifrost | Check client behaviour first. |
| Worst-case reservation | thealirazadev/llm-gateway | Pattern, not a dependency. |
| Trace and cost UI | Langfuse | Helicone is maintenance-only. |
| Local JSONL usage for 15+ CLIs | ccusage | Feeds the observe-only adapter. |
| Agent runs | Claude Agent SDK | For the SDK adapter. |

Reuse is a recommendation. Each choice needs a spike in phase P0 before commitment.
