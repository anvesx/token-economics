# GitHub repos: token economics

Source: web search, 2026-11-09. Savings figures are self-reported by authors, not verified. Commit dates not checked.

## Gateways, routing, caching
- https://github.com/BerriAI/litellm — SDK + proxy, routing, cost tracking, per-key/team budgets (listed via https://github.com/topics/llm-cost-reduction)
- https://github.com/Tanishpd/llm-cost-optimizer — routes each prompt to the cheapest capable model; exact + semantic cache
- https://github.com/llm0ai/llm0 — self-hosted spend firewall, hard per-user/project budget caps, semantic cache, failover
- https://github.com/prakhar083/llm-gateway — OpenAI/Anthropic-compatible, exact + semantic cache, per-key budgets, OTel tracing
- https://github.com/seanmcrae/llm-gateway-cost-aware-LLM-router- — picks model tier within a tenant budget
- https://github.com/thealirazadev/llm-gateway — virtual keys, monthly budgets, worst-case cost reservation
- https://github.com/Muhaman/llm-gateway — Anthropic gateway, Redis cache, rate limits, daily cost tracking
- https://github.com/Akhilesh0605/LLM_GATEWAY — cost-aware gateway, semantic cache, complexity-based routing

## Prompt / context compression
- https://github.com/headroomlabs-ai/headroom — compresses tool outputs, logs, files, RAG chunks
- https://github.com/jia-gao/leanctx — drop-in compression on LLMLingua-2, MIT
- https://github.com/shaminchokshi/less-tokens — deterministic lexical compression, compare() helper
- https://github.com/maheshmakvana/llm-token-optimizer — compression, cost estimation, budgets, routing
- https://github.com/base76-research-lab/token-compressor — local Ollama rewrite + embedding similarity check
- https://github.com/metawake/prompt_compressor — rule-based compression + CLI (possibly stale)
- https://github.com/coreymichaud/promptcompression — simple filler-word stripping
- https://github.com/JacobHuang91/prompt-refiner — ARCHIVED April 2026, do not use

## Tracking / observability
- https://github.com/ryoppippi/ccusage — local CLI, tokens and cost across coding agents
- https://github.com/langfuse/langfuse — MIT observability with cost tracking
- https://github.com/dvlshah/tokenx — Python decorators for API cost + latency
- Helicone — maintenance-only since Mintlify acquisition (Mar 2026)

## Coding-agent token savers
- https://github.com/rtk-ai/rtk — CLI proxy, claims 60-90% fewer tokens on dev commands (verify repo URL)

## Curated lists
- https://github.com/ishandutta2007/Awesome-LLM-Token-Optimization
- https://github.com/enhansome/enhansome-llm-token-optimization
- https://github.com/topics/token-optimization
- https://github.com/topics/llm-cost-reduction
- https://github.com/topics/llm-cost
- https://github.com/topics/token-reduction
