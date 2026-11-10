# Token economics of CLI agents: research index

129 sources, 21 PDFs in `papers/`. Collected 2026-11-09 by Kiro and Claude subagents (Codex hit its usage limit); every URL fetched, arXiv titles matched. Summaries are the CLIs' own one-liners, not independently checked. Flag column: `u` = site blocked the bot so the page is unverified; `t` = title taken from arXiv or weak title match.

Updated 2026-11-10: removed off-topic papers (cost, price or routing angle missing); added papers dated 2026-09-01 or later (arXiv v1 dates checked).

Part 1 = by topic (A/B). Part 2 = by vendor (round 2).

# Part 1: by topic

## C1 Claude Code cost and context (24)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-05 | doc | Anthropic | [Week 21 - May 18-22, 2026](https://code.claude.com/docs/en/whats-new/2026-w21) |  |  |
| 2026-04 | doc | Anthropic | [Week 16 - April 13-17, 2026](https://code.claude.com/docs/en/whats-new/2026-w16) |  |  |
|  | doc | Anthropic | [Create custom subagents](https://code.claude.com/docs/en/sub-agents) |  |  |
|  | doc | Anthropic | [Model configuration and effort levels](https://code.claude.com/docs/en/model-config) |  |  |
|  | doc | Anthropic | [Hooks reference](https://code.claude.com/docs/en/hooks) |  |  |
|  | doc | Anthropic | [Extend Claude with skills](https://code.claude.com/docs/en/skills) |  |  |
|  | doc | Anthropic | [Customize your status line](https://code.claude.com/docs/en/statusline) |  |  |
|  | doc | Anthropic | [How Claude remembers your project](https://code.claude.com/docs/en/memory) |  |  |
|  | doc | Anthropic | [Common workflows](https://code.claude.com/docs/en/common-workflows) |  |  |
|  | doc | Anthropic | [Explore the context window](https://code.claude.com/docs/en/context-window) |  |  |
|  | doc | Anthropic | [Best practices for Claude Code](https://code.claude.com/docs/en/best-practices) |  |  |
|  | doc | Anthropic | [Orchestrate teams of Claude Code sessions](https://code.claude.com/docs/en/agent-teams) |  |  |
|  | doc | Anthropic | [Code Review costs and usage](https://code.claude.com/docs/en/code-review-costs.md) |  |  |
|  | doc | Anthropic | [Set up Claude Code in a monorepo or large codebase](https://code.claude.com/docs/en/large-codebases) |  |  |
|  | doc | Anthropic | [Measure plugin cost and usage](https://code.claude.com/docs/en/plugins/measure) |  |  |
|  | doc | Anthropic | [Track team usage with analytics](https://code.claude.com/docs/en/analytics) |  |  |
|  | doc | Anthropic | [Speed up responses with fast mode](https://code.claude.com/docs/en/fast-mode) |  |  |
|  | doc | Anthropic | [Checkpointing](https://code.claude.com/docs/en/checkpointing) |  |  |
|  | doc | Anthropic | [Run Claude Code through a gateway](https://code.claude.com/docs/en/gateways) |  |  |
|  | doc | Anthropic | [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works) |  |  |
|  | doc | Anthropic | [Automate actions with hooks (guide)](https://code.claude.com/docs/en/hooks-guide) |  |  |
|  | blog | Anthropic | [Choosing a Claude model and effort level in Claude Code](https://www.claude.com/blog/claude-model-and-effort-level-in-claude-code) |  |  |
|  | doc | Anthropic | [Run Claude Code programmatically](https://code.claude.com/docs/en/headless) |  |  |
|  | doc | Anthropic | [Choose a permission mode](https://code.claude.com/docs/en/permission-modes) |  |  |

## C2 Codex CLI and OpenAI agents (19)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-07 | blog | Daniel Vaughan | [Where Do Your Tokens Go: Empirical Token Consumption in Coding Agents](https://codex.danielvaughan.com/2026/07/03/where-do-your-tokens-go-empirical-token-consumption-coding-agents-codex-cli-budget-control) |  |  |
| 2026-07 | blog | Daniel Vaughan | [The Context Window Gap: Codex CLI caps GPT-5.6 at 272K](https://codex.danielvaughan.com/2026/07/20/context-window-gap-codex-cli-gpt56-advertised-vs-effective-budget-compaction-strategy) |  |  |
| 2026-06 | blog | Daniel Vaughan | [Diagnosing and Reducing Codex CLI Token Consumption (June 2026 quota)](https://codex.danielvaughan.com/2026/06/10/codex-cli-token-consumption-diagnosis-reduction-quota-drain-practitioner-toolkit) |  |  |
| 2026-06 | blog | Daniel Vaughan | [Codex CLI Rate-Limit Reset Banking and Usage Optimisation](https://codex.danielvaughan.com/2026/06/12/codex-cli-rate-limit-reset-banking-usage-optimisation-cost-control-profiles-token-budgets) |  |  |
| 2026-04 | blog | Daniel Vaughan | [Mastering Context Compaction in Codex CLI](https://codex.danielvaughan.com/2026/04/16/codex-cli-context-compaction-tuning-long-sessions) |  |  |
| 2026-04 | blog | Daniel Vaughan | [Codex CLI Performance Optimisation: Token Overhead, Hidden Costs](https://codex.danielvaughan.com/2026/04/08/codex-cli-performance-optimization) |  |  |
| 2026-03 | blog | Daniel Vaughan | [Reasoning Effort Tuning: Minimal to xhigh for Cost and Speed](https://codex.danielvaughan.com/2026/03/27/reasoning-effort-tuning) |  |  |
| 2026 | blog | Jetadmin | [Codex pricing: current costs, usage limits, and realistic budgets (2026)](https://www.jetadmin.io/blog/codex-pricing-current-costs-usage-limits-and-realistic-budgets-2026) |  |  |
|  | doc | OpenAI | [Codex Pricing](https://developers.openai.com/codex/pricing) |  |  |
|  | doc | OpenAI | [Codex local config (config.toml)](https://developers.openai.com/codex/local-config) |  |  |
|  | doc | OpenAI | [Codex best practices](https://developers.openai.com/codex/learn/best-practices) |  |  |
|  | doc | OpenAI | [Custom instructions with AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md.md) |  |  |
|  | doc | OpenAI | [ChatGPT usage limits and spend controls](https://learn.chatgpt.com/docs/enterprise/usage-limits.md) |  |  |
|  | doc | OpenAI | [ChatGPT Work: usage and cost](https://learn.chatgpt.com/docs/enterprise/chatgpt-work-usage-and-cost.md) |  |  |
|  | doc | OpenAI | [Subagents in ChatGPT and Codex](https://learn.chatgpt.com/docs/agent-configuration/subagents.md) |  |  |
|  | doc | OpenAI | [Speed (Codex)](https://learn.chatgpt.com/docs/agent-configuration/speed.md) |  |  |
|  | doc | OpenAI | [Codex configuration reference](https://developers.openai.com/codex/config-file/config-reference.md) |  |  |
|  | blog | OpenAI Community | [Codex pricing and quota feel misaligned for developers](https://community.openai.com/t/codex-pricing-and-quota-feel-misaligned-for-developers/1378225) |  |  |
|  | blog | Inventive HQ | [Codex CLI usage rate limits](https://inventivehq.com/blog/codex-cli-usage-rate-limits) |  |  |

## C3 Other CLI and IDE agents (14)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-04 | blog | Daniel Vaughan | [Context Compaction Showdown: Codex CLI, Claude Code and 5 Other Agents](https://codex.danielvaughan.com/2026/04/10/context-compaction-showdown-coding-agents) |  |  |
|  | doc | GitHub | [GitHub Copilot premium requests (billing concepts)](https://docs.github.com/en/billing/concepts/product-billing/github-copilot-premium-requests) |  |  |
|  | doc | GitHub | [Understanding and managing requests in Copilot](https://docs.github.com/en/enterprise-cloud@latest/copilot/concepts/copilot-billing/understanding-and-managing-requests-in-copilot) |  |  |
|  | doc | GitHub | [Copilot billing concepts](https://docs.github.com/en/copilot/concepts/copilot-billing) |  |  |
|  | doc | Cursor | [Cursor Models & Pricing](https://cursor.com/docs/models) |  |  |
|  | doc | Cursor | [Cursor account pricing](https://cursor.com/docs/account/pricing) |  |  |
|  | doc | Google | [Token caching and cost optimization (Gemini CLI)](https://geminicli.com/docs/cli/token-caching) |  |  |
|  | blog | OpenHands | [OpenHands Context Condensation for More Efficient AI Agents](https://openhands.dev/blog/openhands-context-condensensation-for-more-efficient-ai-agents) |  |  |
|  | blog | Amp | [1,000,000 Tokens (Amp)](https://ampcode.com/news/1m-tokens) |  |  |
|  | blog | Vantage | [The Hidden Cost Driver in Agentic Coding: Not the Per-Token Price](https://vantage.sh/blog/agentic-coding-costs) |  |  |
|  | blog | Cursor Forum | [A map of where your coding agent's tokens actually go](https://forum.cursor.com/t/a-map-of-where-your-coding-agents-tokens-actually-go-200-tools-patterns-and-setups/166868) |  |  |
|  | blog | Fast.io | [How to Monitor and Optimize Token Usage in Cline](https://fast.io/resources/cline-token-usage) |  |  |
|  | blog | Tokenade | [How to Reduce Aider Token Usage](https://tokenade.net/en/articles/reduce-aider-token-usage) |  |  |
|  | blog | Tokenade | [How to Measure AI Agent Token Usage](https://tokenade.net/en/articles/measure-agent-token-usage) |  |  |

## C4 Research on agent token burn (7)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-07 | paper | arXiv | [The Best Programming Language for Tokenmaxxing](https://arxiv.org/abs/2607.22807) | [pdf](papers/arxiv/2607.22807__the-best-programming-language-for-tokenmaxxing.pdf) |  |
| 2026-05 | paper | arXiv | [Evaluating Memory Condensation Strategies for Coding Agents in Data-Driven Scientific Discovery](https://arxiv.org/abs/2605.18854) | [pdf](papers/arxiv/2605.18854__evaluating-memory-condensation-strategies-for-coding-agents-.pdf) | t |
| 2026-04 | paper | ICLR 2026 | [Credit-Budgeted ICPC-Style Coding: When Agents Must Pay for Every Decision](https://arxiv.org/abs/2604.10182) | [pdf](papers/arxiv/2604.10182__credit-budgeted-icpc-style-coding-when-agents-must-pay-for-e.pdf) |  |
| 2026 | blog | Kunal Ganglani | [AI Agent Cost Per Task [2026]: Token Budgets and Break-Even Math](https://www.kunalganglani.com/blog/ai-agent-cost-per-task-2026) |  |  |
| 2025-11 | paper | Google DeepMind | [Budget-Aware Tool-Use Enables Effective Agent Scaling](https://arxiv.org/abs/2511.17006) | [pdf](papers/arxiv/2511.17006__budget-aware-tool-use-enables-effective-agent-scaling.pdf) |  |
| 2025-08 | paper | JetBrains Research | [The Complexity Trap: Observation Masking vs LLM Summarization](https://arxiv.org/abs/2508.21433) | [pdf](papers/arxiv/2508.21433__the-complexity-trap-observation-masking-vs-llm-summarization.pdf) |  |
|  | blog | Ramp | [Coding agents ignore spend (Ramp Labs)](https://labs.ramp.com/research/coding-agents-ignore-spend) |  |  |

## D1 Context engineering for coding agents (15)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-11 | doc | Developer Toolkit | [Context Management Across Codex Surfaces](https://developertoolkit.ai/en/codex/build/context-patterns) |  |  |
| 2026-11 | blog | Unblocked | [Codex Context Management: Auto-Compact and /context](https://getunblocked.com/blog/codex-context-window-tools) |  |  |
| 2026-11 | blog | Fast.io | [How to Manage the Aider Context Window and Token Budgets](https://about.fast.io/resources/aider-context-window) |  |  |
| 2026-04 | blog | justin3go | [Shedding Heavy Memories: Context Compaction in Codex, Claude Code, and OpenCode](https://justin3go.com/en/posts/2026/04/09-context-compaction-in-codex-claude-code-and-opencode) |  |  |
| 2026-04 | blog | Medium | [The Hidden Cost of Maximum Context in AI Coding Agents](https://codechefvaibhavkashyap.medium.com/the-hidden-cost-of-maximum-context-in-ai-coding-agents-specs-memory-chunking-and-token-burn-d73e13e3d833) |  | t |
| 2026-04 | blog | bswen | [How MCP Tool Definitions Inflate Your AI Agent Token Costs](https://docs.bswen.com/blog/2026-04-24-mcp-token-overhead) |  |  |
| 2026-04 | paper | arXiv | [Dynamic Tool Gating and Lazy Schema Loading for Eliminating the MCP/Tools Tax in Scalable Agentic Workflows](https://arxiv.org/abs/2604.21816) | [pdf](papers/arxiv/2604.21816__dynamic-tool-gating-and-lazy-schema-loading-for-eliminating-.pdf) |  |
| 2026-04 | blog | Atlassian | [MCP Compression: Preventing tool bloat in AI agents](https://www.atlassian.com/blog/developer/mcp-compression-preventing-tool-bloat-in-ai-agents) |  |  |
| 2026-03 | doc | Anthropic | [Context engineering: memory, compaction, and tool clearing](https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools) |  |  |
| 2026-03 | blog | dev.to | [MCP Tool Overload: Why More Tools Make Your Agent Worse](https://dev.to/thedailyagent/mcp-tool-overload-why-more-tools-make-your-agent-worse-5a49) |  |  |
| 2026-02 | blog | GitHub | [AGENTS.md project memory and compaction in the Codex CLI architecture](https://github.com/castasint/codex-cli-architecture/blob/main/deep-dive/03-memory-context-and-compaction.md) |  |  |
| 2026-02 | blog | Substack | [Context Editing Looks Like a Feature. It's Actually a Garbage Collector Without Write Barriers](https://conikeec.substack.com/p/context-editing-looks-like-a-feature) |  |  |
| 2025-06 | doc | Anthropic | [Context editing on the Claude Developer Platform](https://platform.claude.com/docs/en/build-with-claude/context-editing) |  |  |
| 2025-06 | doc | Anthropic | [Memory & context management with Claude (cookbook)](https://platform.claude.com/cookbook/tool-use-memory-cookbook) |  |  |
|  | doc | Aider | [Aider Benchmark notes: edit formats and token efficiency](https://aider.chat/docs/leaderboards/notes.html) |  |  |

## D2 Subagents, multi-agent cost, routing inside agents (11)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-08 | paper | arXiv | [LLMRouter: Unified Infrastructure for Developing, Evaluating, and Deploying LLM Routers](https://arxiv.org/abs/2608.06867) | [pdf](papers/arxiv/2608.06867__llmrouter-unified-infrastructure-for-developing-evaluating-a.pdf) |  |
| 2026-06 | paper | arXiv | [Response-Level Speculative Decoding for Cost-Efficient LLM API Serving](https://arxiv.org/abs/2606.22840) | [pdf](papers/arxiv/2606.22840__response-level-speculative-decoding-for-cost-efficient-llm-a.pdf) |  |
| 2026-06 | paper | arXiv | [Agentic Model Routing for Coding Tasks](https://arxiv.org/abs/2606.22902) | [pdf](papers/arxiv/2606.22902__agentic-model-routing-for-coding-tasks.pdf) |  |
| 2026-05 | doc | Anthropic | [Orchestrator pattern: big models for planning, small models for execution](https://platform.claude.com/cookbook/managed-agents-cma-plan-big-execute-small) |  |  |
| 2026-05 | paper | arXiv | [TwinRouterBench: Fast Static and Live Dynamic Evaluation for Realistic Agentic LLM Routing](https://arxiv.org/abs/2605.18859) | [pdf](papers/arxiv/2605.18859__twinrouterbench-fast-static-and-live-dynamic-evaluation-for-.pdf) |  |
| 2026-04 | blog | MindStudio | [How to Use a Smart Orchestrator Model to Direct Cheaper Sub-Agent Models in Claude Code](https://www.mindstudio.ai/blog/smart-orchestrator-cheaper-sub-agent-models-claude-code) |  |  |
| 2026-03 | blog | MindStudio | [How to Optimize AI Agent Token Costs with Multi-Model Routing](https://www.mindstudio.ai/blog/ai-agent-token-cost-optimization-multi-model-routing) |  |  |
| 2025-12 | paper | arXiv | [Small Language Models for Efficient Agentic Tool Calling](https://arxiv.org/abs/2512.15943) | [pdf](papers/arxiv/2512.15943__small-language-models-for-efficient-agentic-tool-calling.pdf) |  |
| 2025-06 | paper | arXiv | [Small Language Models are the Future of Agentic AI](https://arxiv.org/abs/2506.02153) | [pdf](papers/arxiv/2506.02153__small-language-models-are-the-future-of-agentic-ai.pdf) |  |
| 2025-04 | paper | arXiv | [Acting Less is Reasoning More! Teaching Model to Act Efficiently](https://arxiv.org/abs/2504.14870) | [pdf](papers/arxiv/2504.14870__acting-less-is-reasoning-more-teaching-model-to-act-efficien.pdf) |  |
| 2024-10 | paper | arXiv | [A Unified Approach to Routing and Cascading for LLMs](https://arxiv.org/abs/2410.10347) | [pdf](papers/arxiv/2410.10347__a-unified-approach-to-routing-and-cascading-for-llms.pdf) |  |

## D3 Usage limits, billing, subscription economics (16)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-11 | paper | SSRN | [Cutoffs, Retries, and Cost per Resolved Task](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7538000) |  | u |
| 2026-11 | blog | Kingy AI | [Amp and your Claude subscription: What Is Free and What Still Costs Money?](https://kingy.ai/blog/amp-claude-subscription-costs-limits) |  |  |
| 2026-10 | blog | TrueFoundry | [Claude Code Rate Limits & Usage Quotas Explained (2026)](https://www.truefoundry.com/blog/claude-code-limits-explained) |  |  |
| 2026-10 | blog | Codersera | [Claude Code Billing & Usage Limits Explained (Oct 2026)](https://codersera.com/blog/anthropic-june-2026-billing-change-claude-code) |  |  |
| 2026-07 | blog | InventiveHQ | [Gemini CLI Free Tier: 1,000 Requests/Day and What Happens Next](https://inventivehq.com/blog/gemini-cli-free-tier-guide) |  |  |
| 2026-07 | blog | Sourcegraph | [Coding agents usually can't price on outcomes. Ours can.](https://sourcegraph.com/blog/agentic-batch-changes-pricing) |  |  |
| 2026-06 | doc | Gemini CLI | [Gemini CLI: Quotas and pricing](https://geminicli.com/docs/resources/quota-and-pricing) |  |  |
| 2026-05 | blog | Verdent | [Claude Code Limits: 5-Hour Caps Doubled in May 2026](https://www.verdent.ai/guides/claude-code-limits-doubled-may-2026) |  |  |
| 2026-04 | blog | Requesty | [The Coding Agent Economy](https://www.requesty.ai/coding-agent-economy) |  |  |
| 2026-02 | blog | Bitdoze | [Amp Code Free: What Happened & Alternatives (2026)](https://www.bitdoze.com/amp-code-free-ai-coding-agent) |  |  |
| 2026-01 | blog | AIFreeAPI | [Gemini API Pricing and Quotas: Complete 2026 Guide](https://www.aifreeapi.com/en/posts/gemini-api-pricing-and-quotas) |  |  |
| 2025-08 | blog | Tessl | [Cursor's new pricing structure explained](https://tessl.io/blog/cursor-new-pricing-structure-explained) |  |  |
| 2025-07 | blog | TechCrunch | [Cursor apologizes for unclear pricing changes that upset users](https://techcrunch.com/2025/07/07/cursor-apologizes-for-unclear-pricing-changes-that-upset-users) |  |  |
| 2025-06 | blog | Cursor (Anysphere) | [Clarifying our pricing](https://cursor.com/blog/june-2025-pricing) |  |  |
| 2025-05 | blog | We Are Founders | [The Full Timeline of How an AI Coding Darling Burned Its Most Loyal Users](https://www.wearefounders.uk/cursors-pricing-disaster-the-full-timeline-of-how-an-ai-coding-darling-burned-its-most-loyal-users) |  |  |
|  | doc | Amp (Sourcegraph) | [Amp Docs: Pricing](https://ampcode.com/docs/pricing) |  |  |

## D4 Measuring and controlling spend (23)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-11 | blog | dev.to | [Claude Code vs Aider: Terminal Agent Benchmarks on Real 500k-LOC Codebases](https://dev.to/grfdsasdvef/claude-code-vs-aider-terminal-agent-benchmarks-on-real-500k-loc-codebases-2d6c) |  |  |
| 2026-10 | blog | dev.to | [Claude Code Token Usage: Monitor It with an AI Gateway](https://dev.to/kamya_shah_e69d5dd78f831c/claude-code-token-usage-monitor-it-with-an-ai-gateway-kih) |  |  |
| 2026-10 | blog | dev.to | [Claude Code OpenTelemetry: Track Cost and Tool Use](https://dev.to/nixonperinchery/claude-code-opentelemetry-track-cost-and-tool-use-c83) |  |  |
| 2026-10 | blog | LangWatch | [Track Claude Code Usage and Spend Across Your Company](https://langwatch.ai/blog/track-claude-code-usage-and-spend-across-your-company) |  |  |
| 2026-10 | paper | arXiv | [Experience-Driven Black-Box Cost Control for Coding Agents (TokenEconomizer)](https://arxiv.org/abs/2610.22732) | [pdf](papers/arxiv/2610.22732__experience-driven-black-box-cost-control-for-coding-agents-t.pdf) |  |
| 2026-10 | blog | dev.to | [Your cache hit rate is lying to you. It's the caller mix.](https://dev.to/theagentloop/your-cache-hit-rate-is-lying-to-you-its-the-caller-mix-ec1) |  |  |
| 2026-10 | doc | Anthropic | [How Claude Code uses prompt caching](https://docs.claude.com/en/docs/claude-code/prompt-caching) |  |  |
| 2026-08 | blog | dev.to | [How to Track Claude Code Usage in 2026: Built-in Commands, ccusage, and Desktop Dashboards Compared](https://dev.to/pederaa/how-to-track-claude-code-usage-in-2026-built-in-commands-ccusage-and-desktop-dashboards-compared-1kk1) |  |  |
| 2026-08 | paper | arXiv | [Prompt-Induced Waste in Coding Agents: Reasoning, Effort, Harness Design, and End-to-End Cost](https://arxiv.org/abs/2608.01347) | [pdf](papers/arxiv/2608.01347__prompt-induced-waste-in-coding-agents-reasoning-effort-harne.pdf) | t |
| 2026-08 | paper | arXiv | [Can your AI agent be cheaper? Investigating the effects of task specifications on token spend in agentic coding tasks](https://arxiv.org/abs/2608.25399) | [pdf](papers/arxiv/2608.25399__can-your-ai-agent-be-cheaper-investigating-the-effects-of-ta.pdf) |  |
| 2026-07 | paper | arXiv | [Token Reduction Is Not Cost Reduction](https://arxiv.org/abs/2607.12161) | [pdf](papers/arxiv/2607.12161__token-reduction-is-not-cost-reduction.pdf) |  |
| 2026-07 | paper | arXiv | [Inference Economics of Enterprise Coding Agents: A Case Study of Cloud vs. On-Premise LLMs](https://arxiv.org/abs/2607.13080) | [pdf](papers/arxiv/2607.13080__inference-economics-of-enterprise-coding-agents-a-case-study.pdf) |  |
| 2026-07 | blog | LiteLLM | [5 ways to cut Claude Code costs with LiteLLM](https://docs.litellm.ai/blog/save-claude-code-costs-with-litellm) |  |  |
| 2026-05 | blog | dev.to | [How I Cut Aider's Token Bill 80%: Prompt Caching, MCP Code Mode, and Tier Routing](https://dev.to/lynkr/run-aider-on-ollama-bedrock-or-any-llm-provider-one-gateway-every-model-3jm4) |  |  |
| 2026-04 | paper | arXiv | [How Do AI Agents Spend Your Money? Analyzing and Predicting Token Consumption in Agentic Coding Tasks](https://arxiv.org/abs/2604.22750) | [pdf](papers/arxiv/2604.22750__how-do-ai-agents-spend-your-money-analyzing-and-predicting-t.pdf) |  |
| 2026-04 | blog | Start Debugging | [How to Add Prompt Caching to an Anthropic SDK App and Measure the Hit Rate](https://startdebugging.net/2026/04/how-to-add-prompt-caching-to-an-anthropic-sdk-app-and-measure-the-hit-rate) |  |  |
| 2026-04 | blog | Traversaal | [Claude Code Cost Optimization: A Benchmark-Backed Playbook for Cutting Token Spend](https://blog.traversaal.ai/claude-code-cost-optimization-benchmark-playbook) |  |  |
| 2026-04 | blog | Finout | [5 Open-Source Tools to Control Your AI API Costs at the Code Level](https://www.finout.io/blog/5-open-source-tools-to-control-your-ai-api-costs-at-the-code-level) |  |  |
| 2026-04 | blog | Gainam | [AI Agent Cost Optimization: Token FinOps for the Age of Runaway Agent Spend](https://gainam.com/insights/ai-agent-cost-optimization) |  |  |
| 2026-03 | blog | bswen | [How to Reduce Codex CLI Token Usage: 7 Proven Optimization Strategies](https://docs.bswen.com/blog/2026-03-02-reduce-codex-cli-token-usage) |  |  |
| 2025-11 | doc | Aider | [Aider LLM Leaderboards](https://aider.chat/docs/leaderboards) |  |  |
| 2025-10 | paper | arXiv | [An Empirical Study of Turn-Control Strategies for Efficient Coding Agents](https://arxiv.org/abs/2510.16786) | [pdf](papers/arxiv/2510.16786__an-empirical-study-of-turn-control-strategies-for-efficient-.pdf) |  |
| 2025-06 | blog | OpenObserve | [Monitoring Claude Code Usage with OpenObserve and MCP](https://openobserve.ai/blog/monitor-claude-code-usage-openobserve-mcp) |  |  |

# Part 2: by vendor
