# Token economics: research index

259 sources, 77 PDFs in `papers/`. Collected 2026-11-09 by Codex and Kiro; every URL fetched, arXiv titles matched. Summaries are the CLIs' own one-liners, not independently checked. Flag column: `u` = site blocked the bot so the page is unverified; `t` = title taken from arXiv or weak title match.

Updated 2026-11-10: removed off-topic papers (cost, price or routing angle missing); added papers dated 2026-09-01 or later (arXiv v1 dates checked).

Part 1 = by topic (A/B). Part 2 = by vendor (round 2).

# Part 1: by topic

## A1 Routing by task/difficulty (15)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-07 | paper | ACL | [MTRouter: Cost-Aware Multi-Turn LLM Routing with History–Model Joint Embeddings](https://aclanthology.org/2026.acl-long.2045) | [pdf](papers/acl/2026.acl-long.2045__mtrouter-cost-aware-multi-turn-llm-routing-with-history-mode.pdf) |  |
| 2026-07 | paper | ACL | [FLARE: Fine-Grained Length-Aware Routing for Resource-Efficient Heterogeneous LLM Serving](https://aclanthology.org/2026.acl-long.1018) | [pdf](papers/acl/2026.acl-long.1018__flare-fine-grained-length-aware-routing-for-resource-efficie.pdf) |  |
| 2026-01 | paper | arXiv | [LLMRouterBench: A Massive Benchmark and Unified Framework for LLM Routing](https://arxiv.org/abs/2601.07206) | [pdf](papers/arxiv/2601.07206__llmrouterbench-a-massive-benchmark-and-unified-framework-for.pdf) |  |
| 2025-09 | paper | arXiv | [Efficient Training-Free Online Routing for High-Volume Multi-LLM Serving](https://arxiv.org/abs/2509.02718) | [pdf](papers/arxiv/2509.02718__efficient-training-free-online-routing-for-high-volume-multi.pdf) |  |
| 2025-06 | paper | UIUC | [Router-R1: Teaching LLMs Multi-Round Routing and Aggregation via Reinforcement Learning](https://arxiv.org/abs/2506.09033) | [pdf](papers/arxiv/2506.09033__router-r1-teaching-llms-multi-round-routing-and-aggregation-.pdf) |  |
| 2025-01 | paper | arXiv | [Rerouting LLM Routers](https://arxiv.org/abs/2501.01818) | [pdf](papers/arxiv/2501.01818__rerouting-llm-routers.pdf) |  |
| 2024-10 | paper | UIUC | [GraphRouter: A Graph-based Router for LLM Selections](https://arxiv.org/abs/2410.03834) | [pdf](papers/arxiv/2410.03834__graphrouter-a-graph-based-router-for-llm-selections.pdf) |  |
| 2024-06 | paper | LMSYS | [RouteLLM: Learning to Route LLMs with Preference Data](https://arxiv.org/abs/2406.18665) | [pdf](papers/arxiv/2406.18665__routellm-learning-to-route-llms-with-preference-data.pdf) |  |
| 2024-04 | paper | Microsoft Research | [Hybrid LLM: Cost-Efficient and Quality-Aware Query Routing](https://arxiv.org/abs/2404.14618) | [pdf](papers/arxiv/2404.14618__hybrid-llm-cost-efficient-and-quality-aware-query-routing.pdf) |  |
| 2024-03 | paper | arXiv | [RouterBench: A Benchmark for Multi-LLM Routing System](https://arxiv.org/abs/2403.12031) | [pdf](papers/arxiv/2403.12031__routerbench-a-benchmark-for-multi-llm-routing-system.pdf) |  |
| 2026-09 | paper | arXiv | [AgentRouter: Heterogeneous Model Routing for Cost-Optimal Multi-Step Agentic Workflows](https://arxiv.org/abs/2609.22951) | [pdf](papers/arxiv/2609.22951__agentrouter-heterogeneous-model-routing-for-cost-optima.pdf) |  |
| 2026-10 | paper | arXiv | [Rethinking Quality in LLM Routing: Security-Conditioned Model-and-Budget Selection (SCRouter)](https://arxiv.org/abs/2610.18566) | [pdf](papers/arxiv/2610.18566__rethinking-quality-in-llm-routing-security-conditioned.pdf) |  |
| 2026-10 | paper | arXiv | [Chance-Constrained Personalized LLM Routing with Online Preference Learning](https://arxiv.org/abs/2610.22695) | [pdf](papers/arxiv/2610.22695__chance-constrained-personalized-llm-routing-with-online.pdf) |  |
| 2026-11 | paper | arXiv | [Pathwise-Budgeted LLM Routing: Online Allocation with K-Bit Tail-Cost Learning](https://arxiv.org/abs/2611.05835) | [pdf](papers/arxiv/2611.05835__pathwise-budgeted-llm-routing-online-allocation-with-k.pdf) |  |
| 2026-11 | paper | arXiv | [MultiTurnRoute: A Platform for Building and Evaluating Multi-Turn LLM Routers](https://arxiv.org/abs/2611.10848) | [pdf](papers/arxiv/2611.10848__multiturnroute-a-platform-for-building-and-evaluating-m.pdf) |  |

## A2 Training a router / task-specialised model (9)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-11 | model | Zen AI | [Zen Router 0.6B](https://huggingface.co/zenlm/zen-router) |  |  |
| 2026-10 | model | Decision Models | [s1-llm-auto-router](https://huggingface.co/decisionmodels/s1-llm-auto-router) |  |  |
| 2025-09 | paper | arXiv | [Meta-Router: Bridging Gold-standard and Preference-based Evaluations in Large Language Model Routing](https://arxiv.org/abs/2509.25535) | [pdf](papers/arxiv/2509.25535__meta-router-bridging-gold-standard-and-preference-based-eval.pdf) |  |
| 2025-08 | paper | NeurIPS | [Cost-Aware Contrastive Routing for LLMs](https://arxiv.org/abs/2508.12491) | [pdf](papers/arxiv/2508.12491__cost-aware-contrastive-routing-for-llms.pdf) |  |
| 2025-06 | paper | Katanemo | [Arch-Router: Aligning LLM Routing with Human Preferences](https://arxiv.org/abs/2506.16655) | [pdf](papers/arxiv/2506.16655__arch-router-aligning-llm-routing-with-human-preferences.pdf) |  |
| 2025-06 | model | Katanemo | [Arch-Router-1.5B](https://huggingface.co/katanemo/Arch-Router-1.5B) |  |  |
| 2025-02 | paper | AAAI | [Capability Instruction Tuning: A New Paradigm for Dynamic LLM Routing](https://arxiv.org/abs/2502.17282) | [pdf](papers/arxiv/2502.17282__capability-instruction-tuning-a-new-paradigm-for-dynamic-llm.pdf) |  |
| 2024-10 | paper | ICLR | [EmbedLLM: Learning Compact Representations of Large Language Models](https://arxiv.org/abs/2410.02223) | [pdf](papers/arxiv/2410.02223__embedllm-learning-compact-representations-of-large-language-.pdf) |  |
| 2024-09 | paper | NeurIPS | [RouterDC: Query-Based Router by Dual Contrastive Learning for Assembling Large Language Models](https://arxiv.org/abs/2409.19886) | [pdf](papers/arxiv/2409.19886__routerdc-query-based-router-by-dual-contrastive-learning-for.pdf) |  |

## A3 Cascades, fallback, speculative decoding (6)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-07 | paper | arXiv | [Conformal Cascade: Distribution-Free Accuracy Guarantees for Multi-Tier LLM Inference](https://arxiv.org/abs/2607.25018) | [pdf](papers/arxiv/2607.25018__conformal-cascade-distribution-free-accuracy-guarantees-for-.pdf) |  |
| 2026-04 | paper | arXiv | [Knowing When to Quit: A Principled Framework for Dynamic Abstention in LLM Reasoning](https://arxiv.org/abs/2604.18419) | [pdf](papers/arxiv/2604.18419__knowing-when-to-quit-a-principled-framework-for-dynamic-abst.pdf) |  |
| 2025-06 | paper | arXiv | [Towards a Cascaded LLM Framework for Cost-effective Human-AI Decision-Making](https://arxiv.org/abs/2506.11887) | [pdf](papers/arxiv/2506.11887__towards-a-cascaded-llm-framework-for-cost-effective-human-ai.pdf) |  |
| 2025-04 | paper | Google Research | [Faster Cascades via Speculative Decoding](https://research.google/pubs/faster-cascades-via-speculative-decoding) |  |  |
| 2024-04 | paper | Google Research | [Language Model Cascades: Token-level uncertainty and beyond](https://arxiv.org/abs/2404.10136) | [pdf](papers/arxiv/2404.10136__language-model-cascades-token-level-uncertainty-and-beyond.pdf) |  |
| 2023-05 | paper | Stanford University | [FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance](https://arxiv.org/abs/2305.05176) | [pdf](papers/arxiv/2305.05176__frugalgpt-how-to-use-large-language-models-while-reducing-co.pdf) |  |

## A4 MoE and multi-LLM ensembles, cost-quality frontiers (7)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-01 | paper | arXiv | [Bayesian Orchestration of Multi-LLM Agents for Cost-Aware Sequential Decision-Making](https://arxiv.org/abs/2601.01522) | [pdf](papers/arxiv/2601.01522__bayesian-orchestration-of-multi-llm-agents-for-cost-aware-se.pdf) |  |
| 2025-06 | blog | NVIDIA | [How NVIDIA GB200 NVL72 and NVIDIA Dynamo Boost Inference Performance for MoE Models](https://developer.nvidia.com/blog/how-nvidia-gb200-nvl72-and-nvidia-dynamo-boost-inference-performance-for-moe-models) |  |  |
| 2025-04 | blog | Meta AI | [The Llama 4 herd: The beginning of a new era of natively multimodal AI innovation](https://ai.meta.com/blog/llama-4-multimodal-intelligence) |  |  |
| 2025-02 | paper | arXiv | [Rethinking Mixture-of-Agents: Is Mixing Different Large Language Models Beneficial?](https://arxiv.org/abs/2502.00674) | [pdf](papers/arxiv/2502.00674__rethinking-mixture-of-agents-is-mixing-different-large-langu.pdf) |  |
| 2024-06 | paper | Together AI | [Mixture-of-Agents Enhances Large Language Model Capabilities](https://arxiv.org/abs/2406.04692) | [pdf](papers/arxiv/2406.04692__mixture-of-agents-enhances-large-language-model-capabilities.pdf) |  |
| 2024-02 | paper | Hugging Face | [More Agents Is All You Need](https://huggingface.co/papers/2402.05120) |  |  |
| 2026-11 | paper | arXiv | [Ensemble Routing for Prompt-Adaptive Cost-Aware LLM Inference (PISA)](https://arxiv.org/abs/2611.10193) | [pdf](papers/arxiv/2611.10193__ensemble-routing-for-prompt-adaptive-cost-aware-llm-inf.pdf) |  |

## A5 Which model for which task, capability profiling (9)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-10 | paper | arXiv | [Beyond Leaderboards: A Method for Application-Specific Capability Profiling of Large Language Models](https://arxiv.org/abs/2610.25659) | [pdf](papers/arxiv/2610.25659__beyond-leaderboards-a-method-for-application-specific-capabi.pdf) |  |
| 2026-02 | paper | arXiv | [Trust by Design: Skill Profiles for Transparent, Cost-Aware LLM Routing](https://arxiv.org/abs/2602.02386) | [pdf](papers/arxiv/2602.02386__trust-by-design-skill-profiles-for-transparent-cost-aware-ll.pdf) |  |
| 2025-10 | paper | arXiv | [RouterArena: An Open Platform for Comprehensive Comparison of LLM Routers](https://arxiv.org/abs/2510.00202) | [pdf](papers/arxiv/2510.00202__routerarena-an-open-platform-for-comprehensive-comparison-of.pdf) |  |
| 2025-06 | paper | NVIDIA Research | [Small Language Models are the Future of Agentic AI](https://arxiv.org/abs/2506.02153) | [pdf](papers/arxiv/2506.02153__small-language-models-are-the-future-of-agentic-ai.pdf) |  |
| 2025-03 | paper | arXiv | [RouterEval: A Comprehensive Benchmark for Routing LLMs to Explore Model-level Scaling Up in LLMs](https://arxiv.org/abs/2503.10657) | [pdf](papers/arxiv/2503.10657__routereval-a-comprehensive-benchmark-for-routing-llms-to-exp.pdf) |  |
| 2025-01 | blog | Hugging Face | [CO₂ Emissions and Models Performance: Insights from the Open LLM Leaderboard](https://huggingface.co/blog/leaderboard-emissions-analysis) |  |  |
| 2024-05 | blog | Hugging Face | [Bringing the Artificial Analysis LLM Performance Leaderboard to Hugging Face](https://huggingface.co/blog/leaderboard-artificial-analysis) |  |  |
| 2026-10 | paper | arXiv | [Which Model for Which Role? Cost-Efficient Pareto Recommendation for LLM Agentic Workflows](https://arxiv.org/abs/2610.26676) | [pdf](papers/arxiv/2610.26676__which-model-for-which-role-cost-efficient-pareto-recomm.pdf) |  |
| 2026-10 | paper | arXiv | [COMPASS: Routing via Capability-Oriented Model Profiling with Adaptive Search, Selection, and Tool Use](https://arxiv.org/abs/2610.27822) | [pdf](papers/arxiv/2610.27822__compass-routing-via-capability-oriented-model-profiling.pdf) |  |

## A6 Agent and CLI-agent cost (12)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-11 | blog | Google | [Cost per task: Using cheap classifiers to route across Gemini models and thinking levels](https://developers.googleblog.com/cost-per-task-using-cheap-classifiers-to-route-across-gemini-models-and-thinking-levels) |  |  |
| 2026-11 | blog | AWS | [Gain per-developer visibility into Kiro Enterprise credit usage](https://aws.amazon.com/blogs/aws-cloud-financial-management/gain-per-developer-visibility-into-kiro-enterprise-credit-usage) |  |  |
| 2026-10 | blog | AWS | [Tokenomics for coding agents: benchmark cost and quality on your own code](https://aws.amazon.com/blogs/aws-cloud-financial-management/tokenomics-for-coding-agents-benchmark-cost-and-quality-on-your-own-code) |  |  |
| 2026-09 | paper | arXiv | [Analyzing and Mitigating Cost-Inefficient Behaviors in Coding Agents](https://arxiv.org/abs/2609.30725) | [pdf](papers/arxiv/2609.30725__analyzing-and-mitigating-cost-inefficient-behaviors-in-codin.pdf) |  |
| 2026-05 | blog | Google | [Subagents have arrived in Gemini CLI](https://developers.googleblog.com/en/subagents-have-arrived-in-gemini-cli) |  |  |
| 2026-04 | blog | Anthropic | [An update on Claude Code quality reports](https://www.anthropic.com/research/april-23-postmortem) |  |  |
| 2026-02 | blog | OpenAI | [Run long horizon tasks with Codex](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex) |  |  |
| 2025-09 | blog | OpenAI | [Introducing upgrades to Codex](https://openai.com/index/introducing-upgrades-to-codex) |  |  |
| 2025-04 | blog | Anthropic | [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices) |  |  |
| 2026-09 | paper | arXiv | [CliffCompaction: Cost-Efficient Compaction for Long-Horizon Coding Agents](https://arxiv.org/abs/2609.26779) | [pdf](papers/arxiv/2609.26779__cliffcompaction-cost-efficient-compaction-for-long-hori.pdf) |  |
| 2026-09 | paper | arXiv | [Beyond Token Savings: A Systematic Study of Context Compression in LLM Agents](https://arxiv.org/abs/2609.32961) | [pdf](papers/arxiv/2609.32961__beyond-token-savings-a-systematic-study-of-context-comp.pdf) |  |
| 2026-09 | paper | arXiv | [An Empirical Study of Harness Design for Coding Agents](https://arxiv.org/abs/2609.20804) | [pdf](papers/arxiv/2609.20804__an-empirical-study-of-harness-design-for-coding-agents.pdf) |  |

## A7 Pricing and token-market economics (10)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-09 | paper | arXiv | [Inference Auctions](https://arxiv.org/abs/2609.40070) | [pdf](papers/arxiv/2609.40070__inference-auctions.pdf) |  |
| 2026-09 | paper | arXiv | [Pricing Time, Not Just Tokens: Latency-Aware Mechanism Design for LLM Inference](https://arxiv.org/abs/2609.40098) | [pdf](papers/arxiv/2609.40098__pricing-time-not-just-tokens-latency-aware-mechanism-design-.pdf) |  |
| 2026-03 | paper | arXiv | [Tiered Super-Moore's Law: Price Evolution, Production Frontiers, and Market Competition in Large Language Model Inference Services](https://arxiv.org/abs/2603.28576) | [pdf](papers/arxiv/2603.28576__tiered-super-moore-s-law-price-evolution-production-frontier.pdf) |  |
| 2026-03 | paper | arXiv | [The Price Reversal Phenomenon: When Cheaper Reasoning Models End Up Costing More](https://arxiv.org/abs/2603.23971) | [pdf](papers/arxiv/2603.23971__the-price-reversal-phenomenon-when-cheaper-reasoning-models-.pdf) |  |
| 2025-10 | paper | arXiv | [Beyond Benchmarks: The Economics of AI Inference](https://arxiv.org/abs/2510.26136) | [pdf](papers/arxiv/2510.26136__beyond-benchmarks-the-economics-of-ai-inference.pdf) |  |
| 2025-06 | paper | arXiv | [Inference economics of language models](https://arxiv.org/abs/2506.04645) | [pdf](papers/arxiv/2506.04645__inference-economics-of-language-models.pdf) |  |
| 2025-06 | blog | NVIDIA | [LLM Inference Benchmarking: How Much Does Your LLM Inference Cost?](https://developer.nvidia.com/blog/?p=102298) |  |  |
| 2025-03 | blog | Anthropic | [Token-saving updates on the Anthropic API](https://www.anthropic.com/news/token-saving-updates) |  |  |
| 2025-02 | paper | arXiv | [Menu Pricing of Large Language Models](https://arxiv.org/abs/2502.07736) | [pdf](papers/arxiv/2502.07736__menu-pricing-of-large-language-models.pdf) | t |
| 2024-10 | blog | OpenAI | [Prompt Caching in the API](https://openai.com/index/api-prompt-caching) |  |  |

## B1 Prompt caching and KV cache (3)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-11 | blog | OpenAI | [Better prompt caching for GPT-6](https://openai.com/index/better-prompt-caching-for-gpt-6) |  |  |
| 2026-10 | blog | Anthropic | [How Claude Code uses prompt caching](https://code.claude.com/docs/en/prompt-caching) |  |  |
| 2025-07 | blog | Anthropic | [Token-saving updates on the Anthropic API](https://claude.com/blog/token-saving-updates) |  |  |

## B2 Prompt and context compression (8)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2025-09 | blog | Anthropic | [Effective context engineering for AI agents](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents) |  |  |
| 2025-03 | paper | arXiv | [AttentionRAG: Attention-Guided Context Pruning in Retrieval-Augmented Generation](https://arxiv.org/abs/2503.10720) | [pdf](papers/arxiv/2503.10720__attentionrag-attention-guided-context-pruning-in-retrieval-a.pdf) |  |
| 2025-01 | paper | arXiv | [Provence: Efficient and Robust Context Pruning for Retrieval-Augmented Generation](https://arxiv.org/abs/2501.16214) | [pdf](papers/arxiv/2501.16214__provence-efficient-and-robust-context-pruning-for-retrieval-.pdf) |  |
| 2024-03 | paper | Microsoft Research | [LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression](https://arxiv.org/abs/2403.12968) | [pdf](papers/arxiv/2403.12968__llmlingua-2-data-distillation-for-efficient-and-faithful-tas.pdf) |  |
| 2023-10 | paper | Microsoft Research | [LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models](https://arxiv.org/abs/2310.05736) | [pdf](papers/arxiv/2310.05736__llmlingua-compressing-prompts-for-accelerated-inference-of-l.pdf) |  |
| 2023-10 | paper | Microsoft Research | [LongLLMLingua: Accelerating and Enhancing LLMs in Long Context Scenarios via Prompt Compression](https://arxiv.org/abs/2310.06839) | [pdf](papers/arxiv/2310.06839__longllmlingua-accelerating-and-enhancing-llms-in-long-contex.pdf) |  |
| 2023-10 | paper | arXiv | [Selective Context: Compressing Context to Enhance Inference Efficiency of Large Language Models](https://arxiv.org/abs/2310.06201) | [pdf](papers/arxiv/2310.06201__selective-context-compressing-context-to-enhance-inference-e.pdf) |  |
| 2023-04 | paper | arXiv | [Learning to Compress Prompts with Gist Tokens](https://arxiv.org/abs/2304.08467) | [pdf](papers/arxiv/2304.08467__learning-to-compress-prompts-with-gist-tokens.pdf) |  |

## B3 Reasoning-token economics (9)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2025-08 | paper | arXiv | [Efficient Reasoning for Large Reasoning Language Models via Certainty-Guided Reflection Suppression](https://arxiv.org/abs/2508.05337) | [pdf](papers/arxiv/2508.05337__efficient-reasoning-for-large-reasoning-language-models-via-.pdf) |  |
| 2025-06 | paper | arXiv | [Wait, We Don't Need to Wait! Removing Thinking Tokens Improves Reasoning Efficiency](https://arxiv.org/abs/2506.08343) | [pdf](papers/arxiv/2506.08343__wait-we-don-t-need-to-wait-removing-thinking-tokens-improves.pdf) |  |
| 2025-06 | paper | arXiv | [Just Enough Thinking: Efficient Reasoning with Adaptive Length Penalties Reinforcement Learning](https://arxiv.org/abs/2506.05256) | [pdf](papers/arxiv/2506.05256__just-enough-thinking-efficient-reasoning-with-adaptive-lengt.pdf) |  |
| 2025-05 | paper | arXiv | [Efficient Reasoning via Chain of Unconscious Thought](https://arxiv.org/abs/2505.19756) | [pdf](papers/arxiv/2505.19756__efficient-reasoning-via-chain-of-unconscious-thought.pdf) |  |
| 2025-05 | paper | arXiv | [THINK-Bench: Evaluating Thinking Efficiency and Chain-of-Thought Quality of Large Reasoning Models](https://arxiv.org/abs/2505.22113) | [pdf](papers/arxiv/2505.22113__think-bench-evaluating-thinking-efficiency-and-chain-of-thou.pdf) |  |
| 2025-05 | paper | arXiv | [The Price of a Second Thought: On the Evaluation of Reasoning Efficiency in Large Language Models](https://arxiv.org/abs/2505.22017) | [pdf](papers/arxiv/2505.22017__the-price-of-a-second-thought-on-the-evaluation-of-reasoning.pdf) | t |
| 2025-03 | paper | arXiv | [L1: Controlling How Long A Reasoning Model Thinks With Reinforcement Learning](https://arxiv.org/abs/2503.04697) | [pdf](papers/arxiv/2503.04697__l1-controlling-how-long-a-reasoning-model-thinks-with-reinfo.pdf) |  |
| 2024-12 | paper | arXiv | [Do NOT Think That Much for 2+3=? On the Overthinking of o1-Like LLMs](https://arxiv.org/abs/2412.21187) | [pdf](papers/arxiv/2412.21187__do-not-think-that-much-for-2-3-on-the-overthinking-of-o1-lik.pdf) |  |
| 2024-08 | paper | Google DeepMind | [Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Model Parameters](https://arxiv.org/abs/2408.03314) | [pdf](papers/arxiv/2408.03314__scaling-llm-test-time-compute-optimally-can-be-more-effectiv.pdf) |  |

## B4 Output-side savings, tokenisers (4)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2024-12 | paper | arXiv | [TRIM: Token Reduction and Inference Modeling for Cost-Effective Language Generation](https://arxiv.org/abs/2412.07682) | [pdf](papers/arxiv/2412.07682__trim-token-reduction-and-inference-modeling-for-cost-effecti.pdf) |  |
| 2024-07 | paper | arXiv | [Concise Thoughts: Impact of Output Length on LLM Reasoning and Cost](https://arxiv.org/abs/2407.19825) | [pdf](papers/arxiv/2407.19825__concise-thoughts-impact-of-output-length-on-llm-reasoning-an.pdf) |  |
| 2024-01 | paper | arXiv | [The Benefits of a Concise Chain of Thought on Problem-Solving in Large Language Models](https://arxiv.org/abs/2401.05618) | [pdf](papers/arxiv/2401.05618__the-benefits-of-a-concise-chain-of-thought-on-problem-solvin.pdf) |  |
| 2023-05 | paper | arXiv | [Do All Languages Cost the Same? Tokenization in the Era of Commercial Language Models](https://arxiv.org/abs/2305.13707) | [pdf](papers/arxiv/2305.13707__do-all-languages-cost-the-same-tokenization-in-the-era-of-co.pdf) |  |

## B5 Serving and inference cost (2)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2025-04 | blog | NVIDIA | [LLM Inference Benchmarking: How Much Does Your LLM Inference Cost?](https://developer.nvidia.com/blog/llm-inference-benchmarking-how-much-does-your-llm-inference-cost) |  |  |
|  | blog | OpenAI | [Batch API guide](https://developers.openai.com/api/docs/guides/batch) |  |  |

## B6 Semantic caching, RAG vs long context (5)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2025-08 | paper | arXiv | [Semantic Caching for Low-Cost LLM Serving: From Offline Learning to Online Adaptation](https://arxiv.org/abs/2508.07675) | [pdf](papers/arxiv/2508.07675__semantic-caching-for-low-cost-llm-serving-from-offline-learn.pdf) |  |
| 2025-05 | blog | Google | [Gemini 2.5 Models now support implicit caching](https://developers.googleblog.com/zh-hans/gemini-2-5-models-now-support-implicit-caching) |  |  |
| 2024-11 | paper | arXiv | [GPT Semantic Cache: Reducing LLM Costs and Latency via Semantic Embedding Caching](https://arxiv.org/abs/2411.05276) | [pdf](papers/arxiv/2411.05276__gpt-semantic-cache-reducing-llm-costs-and-latency-via-semant.pdf) |  |
| 2024-05 | paper | Google DeepMind | [Retrieval Augmented Generation or Long-Context LLMs? A Comprehensive Study and Hybrid Approach](https://arxiv.org/abs/2407.16833) | [pdf](papers/arxiv/2407.16833__retrieval-augmented-generation-or-long-context-llms-a-compre.pdf) |  |
| 2024-03 | paper | arXiv | [MeanCache: A Privacy-Aware Semantic Cache for Large Language Models](https://arxiv.org/abs/2403.02694) | [pdf](papers/arxiv/2403.02694__meancache-a-privacy-aware-semantic-cache-for-large-language-.pdf) |  |

## B7 Observability, FinOps, cost-vs-quality evals (11)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-04 | blog | NVIDIA | [NVIDIA Platform Delivers Lowest Token Cost Enabled by Extreme Co-Design](https://developer.nvidia.com/blog/nvidia-extreme-co-design-delivers-new-mlperf-inference-records) |  |  |
| 2025-12 | blog | Hugging Face | [AI Energy Score: Refreshed Leaderboard, now with Reasoning](https://huggingface.co/blog/sasha/ai-energy-score-v2) |  |  |
| 2025-07 | paper | arXiv | [Economic Evaluation of LLMs](https://arxiv.org/abs/2507.03834) | [pdf](papers/arxiv/2507.03834__economic-evaluation-of-llms.pdf) |  |
| 2025-04 | paper | arXiv | [Cost-of-Pass: An Economic Framework for Evaluating Language Models](https://arxiv.org/abs/2504.13359) | [pdf](papers/arxiv/2504.13359__cost-of-pass-an-economic-framework-for-evaluating-language-m.pdf) |  |
| 2025-02 | blog | Hugging Face | [Announcing AI Energy Score Ratings](https://huggingface.co/blog/sasha/announcing-ai-energy-score) |  |  |
| 2025-02 | blog | Hugging Face | [1 Billion Classifications](https://huggingface.co/blog/billion-classifications) |  |  |
| 2024-12 | blog | Hugging Face | [Investing in Performance: Fine-tune small models with LLM insights](https://huggingface.co/blog/cfm-case-study) |  |  |
|  | blog | FinOps Foundation | [How to Build a Generative AI Cost and Usage Tracker](https://www.finops.org/wg/how-to-build-a-generative-ai-cost-and-usage-tracker) |  |  |
| 2026-09 | paper | arXiv | [Total Cost of Agency: Exact Attribution of Memory Injection Cost in Multi-Agent Workflows](https://arxiv.org/abs/2609.23790) | [pdf](papers/arxiv/2609.23790__total-cost-of-agency-exact-attribution-of-memory-inject.pdf) |  |
| 2026-09 | paper | arXiv | [Identical Runs, Different Results: Benchmarking AI Coding Agents on Open-Weight Models](https://arxiv.org/abs/2609.33812) | [pdf](papers/arxiv/2609.33812__identical-runs-different-results-benchmarking-ai-coding.pdf) |  |
| 2026-09 | paper | arXiv | [DeltaSelect: Affordable A/B Testing for Coding Agents](https://arxiv.org/abs/2609.19607) | [pdf](papers/arxiv/2609.19607__deltaselect-affordable-a-b-testing-for-coding-agents.pdf) |  |

# Part 2: by vendor

## Anthropic (17)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-11 | doc | Anthropic | [Manage costs effectively (Claude Code)](https://code.claude.com/docs/en/costs) |  |  |
| 2026-11 | doc | Anthropic | [Track cost and usage (Claude Agent SDK)](https://code.claude.com/docs/en/agent-sdk/cost-tracking) |  |  |
| 2026-11 | doc | Anthropic | [Monitoring usage (Claude Code OpenTelemetry)](https://code.claude.com/docs/en/monitoring-usage) |  |  |
| 2026-11 | blog | Anthropic | [The components of agent memory](https://www.anthropic.com/research/components-of-agent-memory) |  |  |
| 2026-11 | blog | Anthropic | [Writing effective tools for AI agents](https://www.anthropic.com/research/writing-tools-for-agents) |  |  |
| 2026-10 | blog | Anthropic | [Claude Opus 4.6](https://www.anthropic.com/news/claude-opus-4-6) |  |  |
| 2026-07 | doc | Anthropic | [Effort parameter (Claude)](https://console.anthropic.com/docs/en/build-with-claude/effort) |  |  |
| 2026-03 | doc | Anthropic | [Context engineering: memory, compaction, and tool clearing (Claude cookbook)](https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools) |  |  |
| 2025-09 | blog | Anthropic | [Managing context on the Claude Developer Platform](https://anthropic.com/news/context-management) |  |  |
| 2025-03 | doc | Anthropic | [Batch processing (Claude)](https://platform.claude.com/docs/en/build-with-claude/batch-processing) |  |  |
|  | doc | Anthropic | [LLM gateway configuration](https://docs.anthropic.com/en/docs/claude-code/llm-gateway) |  |  |
|  | doc | Anthropic | [Claude prompt caching docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) |  |  |
|  | doc | Anthropic | [Extended thinking tips](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/extended-thinking-tips) |  | t |
|  | doc | Anthropic | [Models, usage, and limits in Claude Code](https://support.claude.com/en/articles/14552983-models-usage-and-limits-in-claude-code) |  |  |
|  | doc | Anthropic | [Claude API overview (batch and token counting)](https://platform.claude.com/docs/en/api/overview) |  |  |
|  | doc | Anthropic | [What's new in Claude Opus 5](https://platform.claude.com/docs/en/about-claude/models/whats-new-opus-5) |  |  |
|  | doc | Anthropic | [Claude Fable 5.1 overview](https://platform.claude.com/docs/en/models/fable-5-1/overview) |  |  |

## OpenAI (17)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-11 | blog | OpenAI | [A model guide for the GPT-6 family](https://openai.com/index/practical-guide-building-gpt-6) |  |  |
| 2026-10 | blog | OpenAI | [The builder's guide to GPT-5.6](https://openai.com/index/builders-guide-to-gpt-5-6) |  |  |
| 2026-07 | blog | OpenAI | [Fast mode for API Customers](https://openai.com/api-fast-mode) |  |  |
| 2024-08 | doc | OpenAI | [Prompt Caching 101](https://cookbook.openai.com/examples/prompt_caching101) |  |  |
|  | doc | OpenAI | [Using Codex with your ChatGPT plan](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan) |  |  |
|  | doc | OpenAI | [Flex processing](https://developers.openai.com/api/docs/guides/flex-processing) |  |  |
|  | doc | OpenAI | [Latency optimization](https://developers.openai.com/api/docs/guides/latency-optimization) |  |  |
|  | doc | OpenAI | [Reasoning models](https://developers.openai.com/api/docs/guides/reasoning) |  |  |
|  | doc | OpenAI | [Cost optimization](https://developers.openai.com/api/docs/guides/cost-optimization) |  |  |
|  | doc | OpenAI | [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching) |  |  |
|  | doc | OpenAI | [Prompt Caching 201](https://developers.openai.com/cookbook/examples/prompt_caching_201) |  |  |
|  | doc | OpenAI | [Prompt cache diagnostics](https://developers.openai.com/api/docs/guides/prompt-caching/diagnostics) |  |  |
|  | doc | OpenAI | [Model guidance (GPT-5.6)](https://developers.openai.com/api/docs/guides/prompt-guidance-gpt-5p6) |  |  |
|  | doc | OpenAI | [GPT-5 prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide) |  |  |
|  | doc | OpenAI | [Codex Prompting Guide](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide) |  |  |
|  | blog | OpenAI | [Building more with GPT-5.1-Codex-Max](https://openai.com/index/gpt-5-1-codex-max) |  |  |
|  | doc | OpenAI | [Reasoning models (OpenAI platform)](https://platform.openai.com/docs/guides/reasoning) |  |  |

## Google (12)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-11 | doc | Google | [Batch inference (Gemini Enterprise)](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/batch-inference) |  |  |
| 2026-05 | doc | Google | [Context caching overview (Vertex AI)](https://cloud.google.com/vertex-ai/generative-ai/docs/context-cache/context-cache-overview) |  |  |
| 2025-10 | blog | Google Cloud | [Save costs and decrease latency while using Gemini with Vertex AI context caching](https://cloud.google.com/blog/products/ai-machine-learning/vertex-ai-context-caching) |  | t |
|  | doc | Google | [Gemini Developer API pricing](https://ai.google.dev/gemini-api/docs/pricing?authuser=6) |  |  |
|  | doc | Google | [Context caching](https://ai.google.dev/gemini-api/docs/caching?authuser=01&hl=en) |  |  |
|  | doc | Google | [Gemini API optimization and inference](https://ai.google.dev/gemini-api/docs/optimization?hl=en) |  |  |
|  | doc | Google | [Generating content: ThinkingConfig](https://ai.google.dev/api/generate-content?hl=en) |  |  |
|  | doc | Google | [Batch API](https://ai.google.dev/api/batch-api?hl=en) |  |  |
|  | doc | Google | [Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits?hl=en) |  |  |
|  | doc | Google Cloud | [Quotas and limits](https://docs.cloud.google.com/gemini/docs/quotas) |  |  |
|  | doc | Google Cloud | [Gemini for Google Cloud pricing](https://cloud.google.com/products/gemini/pricing?hl=en) |  |  |
|  | doc | Google Cloud | [Calculate Provisioned Throughput requirements](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/provisioned-throughput/measure-provisioned-throughput) |  |  |

## GitHub (8)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-04 | blog | GitHub | [GitHub Copilot is moving to usage-based billing](https://github.blog/news-insights/company-news/github-copilot-is-moving-to-usage-based-billing) |  |  |
| 2026-02 | blog | GitHub | [GitHub Copilot CLI is now generally available](https://github.blog/changelog/2026-02-25-github-copilot-cli-is-now-generally-available) |  |  |
| 2025-11 | doc | GitHub | [About premium requests](https://docs.github.com/en/enterprise-cloud@latest/copilot/managing-copilot/monitoring-usage-and-entitlements/about-premium-requests) |  |  |
|  | doc | GitHub | [Requests in GitHub Copilot (legacy)](https://docs.github.com/en/copilot/concepts/billing/copilot-requests) |  |  |
|  | doc | GitHub | [Model multipliers for annual plans on request-based billing (legacy)](https://docs.github.com/copilot/reference/copilot-billing/model-multipliers-for-annual-plans) |  |  |
|  | doc | GitHub | [Overview of request-based billing (legacy)](https://docs.github.com/en/copilot/reference/copilot-billing/request-based-billing-legacy/github-copilot-premium-requests) |  |  |
|  | doc | GitHub | [Models and pricing for GitHub Copilot](https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing) |  |  |
|  | doc | GitHub | [Usage-based billing for organizations and enterprises (Copilot)](https://docs.github.com/en/copilot/concepts/billing-and-usage/organizations-and-enterprises/billing) |  |  |

## Hugging Face (7)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2025-11 | blog | Hugging Face | [Continuous batching](https://huggingface.co/blog/continuous_batching) |  |  |
| 2025-04 | blog | Hugging Face | [DeepInfra on Hugging Face Inference Providers](https://huggingface.co/blog/inference-providers-deepinfra) |  |  |
|  | doc | Hugging Face | [Pricing and Billing](https://huggingface.co/docs/inference-providers/pricing) |  |  |
|  | doc | Hugging Face | [Evaluating models with Inspect](https://huggingface.co/docs/inference-providers/en/guides/evaluation-inspect-ai) |  |  |
|  | doc | Hugging Face | [Inference Endpoints pricing](https://huggingface.co/docs/inference-endpoints/pricing) |  |  |
|  | doc | Hugging Face | [Autoscaling](https://huggingface.co/docs/inference-endpoints/autoscaling) |  |  |
|  | doc | Hugging Face | [Inference Providers index (Hugging Face)](https://huggingface.co/docs/inference-providers/index) |  |  |

## OpenRouter (6)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-11 | doc | OpenRouter | [Prompt caching best practices (OpenRouter)](https://openrouter.ai/docs/guides/best-practices/prompt-caching) |  |  |
| 2026-10 | blog | OpenRouter | [How OpenRouter rebuilt provider routing for better, faster inference](https://openrouter.ai/blog/announcements/how-we-rebuilt-provider-routing) |  |  |
| 2026-07 | blog | OpenRouter | [Introducing the new Auto Router](https://openrouter.ai/blog/announcements/introducing-the-new-auto-router) |  |  |
| 2025-12 | blog | OpenRouter | [State of AI 2025: 100T Token LLM Usage Study](https://openrouter.ai/state-of-ai) |  |  |
| 2025-11 | doc | OpenRouter | [Provider routing (OpenRouter)](https://openrouter.ai/docs/provider-routing) |  |  |
|  | doc | OpenRouter | [Auto Router: Smart AI Model Selection](https://openrouter.ai/docs/guides/routing/auto-model-selection) |  |  |

## Fireworks (6)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-11 | doc | Fireworks | [Batch inference (Fireworks)](https://docs.fireworks.ai/guides/batch-inference) |  |  |
| 2026-11 | doc | Fireworks | [Serverless Inference Overview (Fireworks)](https://docs.fireworks.ai/serverless/overview) |  |  |
| 2026-11 | doc | Fireworks | [Prompt caching (Fireworks)](https://docs.fireworks.ai/guides/prompt-caching) |  |  |
| 2026-11 | blog | Fireworks | [GLM 5.2 Fast: Faster Serverless Inference, Same Quality](https://fireworks.ai/blog/glm-5-2-fast-inference) |  |  |
| 2026-11 | blog | Fireworks | [Batch API: Run Async Batch Inference at 50% Lower Cost (Fireworks)](https://fireworks.ai/blog/batch-inference-api) |  |  |
| 2026-11 | doc | Fireworks | [Fast Open Model Inference: Serverless and On-Demand (Fireworks)](https://fireworks.ai/product/inference) |  |  |

## Microsoft (5)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
|  | doc | Microsoft | [Prompt caching with Azure OpenAI in Azure AI Foundry Models](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/prompt-caching) |  |  |
|  | doc | Microsoft | [Model router for Microsoft Foundry concepts](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/model-router?preserve-view=true&view=foundry) |  |  |
|  | doc | Microsoft | [Use Flex processing with Azure OpenAI in Foundry Models](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/flex-processing) |  |  |
|  | doc | Microsoft | [Provisioned throughput for Foundry Models](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/provisioned-throughput?wt.mc_id=MVP_407589) |  |  |
|  | doc | Microsoft | [How to use global batch processing with Azure OpenAI](https://learn.microsoft.com/azure/foundry/openai/how-to/batch) |  |  |

## NVIDIA (5)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-04 | blog | NVIDIA | [How NVIDIA Dynamo 1.0 Powers Multi-Node Inference at Production Scale](https://developer.nvidia.com/blog/nvidia-dynamo-1-production-ready/?trk=article-ssr-frontend-pulse_little-text-block) |  |  |
| 2026-04 | blog | NVIDIA | [Full-Stack Optimizations for Agentic Inference with NVIDIA Dynamo](https://developer.nvidia.com/blog/full-stack-optimizations-for-agentic-inference-with-nvidia-dynamo/?linkId=100000419241070) |  |  |
| 2026-03 | blog | NVIDIA | [Enhancing Distributed Inference Performance with the NVIDIA Inference Transfer Library](https://developer.nvidia.com/blog/enhancing-distributed-inference-performance-with-the-nvidia-inference-transfer-library/?trk=article-ssr-frontend-pulse_little-text-block) |  |  |
| 2025-09 | blog | NVIDIA | [How to Reduce KV Cache Bottlenecks with NVIDIA Dynamo](https://developer.nvidia.com/blog/?p=106133) |  |  |
| 2025-03 | blog | NVIDIA | [NVIDIA Dynamo, A Low-Latency Distributed Inference Framework for Scaling Reasoning AI Models](https://developer.nvidia.com/blog/?p=95274) |  |  |

## xAI (5)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-11 | doc | xAI | [Prompt Caching: Cut the Cost of Long Chats with the Grok API](https://docs.x.ai/cookbook/examples/prompt-caching) |  |  |
| 2025-03 | doc | xAI | [Prompt Caching (xAI)](https://docs.x.ai/developers/advanced-api-usage/prompt-caching) |  |  |
| 2025-03 | doc | xAI | [How Prompt Caching Works (xAI)](https://docs.x.ai/developers/advanced-api-usage/prompt-caching/how-it-works) |  |  |
|  | doc | xAI | [Usage & Pricing (xAI prompt caching)](https://docs.x.ai/developers/advanced-api-usage/prompt-caching/usage-and-pricing) |  |  |
|  | doc | xAI | [xAI pricing](https://docs.x.ai/developers/pricing) |  |  |

## Vercel (5)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-11 | doc | Vercel | [Cost-aware model routing with Vercel AI Gateway](https://vercel.com/kb/guide/cost-aware-model-routing-with-ai-gateway) |  |  |
| 2026-11 | doc | Vercel | [AI Gateway Automatic Prompt Caching (Vercel)](https://vercel.com/docs/ai-gateway/models-and-providers/automatic-caching) |  |  |
| 2026-07 | blog | Vercel | [What is an AI gateway? (Vercel)](https://vercel.com/i/what-is-an-ai-gateway) |  |  |
| 2026-07 | blog | Vercel | [AI Gateway vs. OpenAI API (Vercel)](https://vercel.com/i/ai-gateway-vs-openai-api-direct) |  |  |
| 2026-02 | doc | Vercel | [Provider Options (Vercel AI Gateway)](https://examples.vercel.com/docs/ai-gateway/provider-options) |  |  |

## Together AI (5)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-11 | doc | Together AI | [Batch API overview (Together AI)](https://docs.together.ai/docs/inference/batch/overview) |  |  |
| 2026-10 | doc | Together AI | [Choosing a deployment option (Together AI)](https://docs.together.ai/learn/choosing-a-deployment-option) |  |  |
| 2026-10 | doc | Together AI | [Dedicated endpoints pricing (Together AI)](https://docs.together.ai/docs/dedicated-endpoints/pricing) |  |  |
| 2026-07 | doc | Together AI | [Inference pricing (Together AI)](https://docs.together.ai/docs/inference/pricing) |  | t |
|  | doc | Together AI | [Serverless models (Together AI)](https://docs.together.ai/docs/serverless-models) |  |  |

## Amazon Web Services (4)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
|  | doc | Amazon Web Services | [Prompt caching for faster model inference](https://docs.aws.amazon.com/us_en/bedrock/latest/userguide/prompt-caching.html) |  |  |
|  | doc | Amazon Web Services | [Understanding intelligent prompt routing in Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-routing.html) |  |  |
|  | doc | Amazon Web Services | [Capacity and Performance](https://docs.aws.amazon.com/bedrock/latest/userguide/capacity-limits-cost-optimization.html) |  |  |
|  | doc | Amazon Web Services | [Process multiple prompts with batch inference](https://docs.aws.amazon.com/bedrock/latest/userguide/batch-inference.html?linkId=665046301&sc_campaign=Support&sc_channel=sm&sc_content=Support&sc_country=global&sc_geo=GLOBAL&sc_outcome=AWS+Support&sc_publisher=REDDIT&trk=Support) |  |  |

## Mistral AI (4)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
|  | doc | Mistral AI | [Prompt caching](https://docs.mistral.ai/inference/conversations/advanced/prompt-caching?trk=article-ssr-frontend-pulse_little-text-block) |  |  |
|  | doc | Mistral AI | [Batch Processing](https://docs.mistral.ai/inference/batch-processing) |  |  |
|  | doc | Mistral AI | [Pricing](https://docs.mistral.ai/inference/pricing?trk=article-ssr-frontend-pulse_little-text-block) |  |  |
|  | doc | Mistral AI | [Priority Tier](https://docs.mistral.ai/inference/priority-tier) |  |  |

## Cohere (4)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
|  | doc | Cohere | [How Does Cohere's Pricing Work?](https://docs.cohere.com/docs/how-does-cohere-pricing-work) |  |  |
|  | doc | Cohere | [Different Types of API Keys and Rate Limits](https://docs.cohere.com/v2/docs/rate-limits) |  |  |
|  | doc | Cohere | [Standard Vault Pricing](https://docs.cohere.com/docs/model-vault/standard/pricing) |  | t |
|  | blog | Cohere | [The Total Cost of AI Ownership](https://cohere.com/blog/blog/the-total-cost-of-ai-ownership) |  |  |

## DeepSeek (3)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
|  | doc | DeepSeek | [Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/?nb_mt=p&nbt=nb%3Aadwords%3Ag%3A22371110801%3A175662281183%3A741266097534&r=0) |  |  |
|  | doc | DeepSeek | [Context Caching](https://api-docs.deepseek.com/guides/kv_cache/?trk=article-ssr-frontend-pulse_little-text-block) |  |  |
|  | doc | DeepSeek | [Using the Anthropic API](https://api-docs.deepseek.com/guides/anthropic_api) |  |  |

## Databricks (4)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-10 | blog | Databricks | [The new economics of AI cost management](https://www.databricks.com/blog/ai-cost-management) |  |  |
| 2026-06 | blog | Databricks | [Reliable LLM Inference at Scale](https://www.databricks.com/blog/reliable-llm-inference-scale) |  |  |
| 2026-05 | blog | Databricks | [Accelerating LLM Inference with Prompt Caching for Open-Source Models on Databricks](https://www.databricks.com/blog/accelerating-llm-inference-prompt-caching-open-source-models-databricks?trk=article-ssr-frontend-pulse_little-text-block) |  |  |
|  | doc | Databricks | [Monitor model serving costs](https://docs.databricks.com/aws/en/admin/system-tables/model-serving-cost) |  |  |

## Cloudflare (4)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-11 | doc | Cloudflare | [Dynamic routes](https://developers.cloudflare.com/ai-gateway/features/routing/dynamic-routing) |  |  |
| 2026-11 | doc | Cloudflare | [Spend limits](https://developers.cloudflare.com/ai-gateway/features/spend-limits/?ref=runtimewire) |  |  |
| 2026-09 | doc | Cloudflare | [Custom costs](https://developers.cloudflare.com/ai-gateway/configuration/custom-costs) |  |  |
|  | doc | Cloudflare | [Auto Router](https://developers.cloudflare.com/ai-gateway/features/routing/auto-router) |  |  |

## Langfuse (4)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
|  | doc | Langfuse | [Token & Cost Tracking (Langfuse)](https://langfuse.com/docs/observability/features/token-and-cost-tracking) |  |  |
|  | blog | Langfuse | [LLM Cost Management: Track and Control Spend](https://langfuse.com/resources/engineering/llm-cost-management) |  |  |
|  | doc | Langfuse | [Track and optimize coding agent usage (Langfuse)](https://langfuse.com/coding-agents) |  |  |
|  | doc | Langfuse | [How do I track LLM cost and tokens in Langfuse?](https://langfuse.com/faq/all/costs-tokens-langfuse) |  |  |

## Helicone (4)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-11 | doc | Helicone | [Caching (Helicone advanced usage)](https://docs.helicone.ai/features/advanced-usage/caching) |  |  |
| 2026-03 | doc | Helicone | [Prompt caching (Helicone gateway)](https://docs.helicone.ai/gateway/concepts/prompt-caching) |  |  |
| 2026-03 | doc | Helicone | [Cost tracking cookbook (Helicone)](https://docs.helicone.ai/guides/cookbooks/cost-tracking) |  |  |
| 2025-03 | blog | Helicone | [How to Monitor Your LLM API Costs and Cut Spending by 90%](https://www.helicone.ai/blog/slash-llm-cost) |  |  |

## Portkey (4)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-11 | doc | Portkey | [Budget limits (Portkey)](https://portkey.ai/docs/product/ai-gateway/virtual-keys/budget-limits) |  |  |
| 2026-10 | doc | Portkey | [Simple and semantic cache (Portkey)](https://portkey.ai/docs/product/ai-gateway/cache-simple-and-semantic) |  |  |
| 2026-08 | doc | Portkey | [AI Gateway (Portkey)](https://portkey.ai/docs/product/ai-gateway) |  |  |
|  | doc | Portkey | [Optimizing LLM costs: operational best practices (Portkey)](https://docs.portkey.ai/docs/guides/whitepapers/optimizing-llm-costs/operational-best-practices) |  |  |

## Cursor (4)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2025-07 | blog | Cursor | [Clarifying our pricing (Cursor)](https://cursor.com/blog/june-2025-pricing) |  |  |
|  | doc | Cursor | [Cursor – Models & Pricing (usage)](https://docs.cursor.com/account/usage) |  | t |
|  | doc | Cursor | [Cursor – Models & Pricing (advanced models)](https://docs.cursor.com/advanced/models) |  | t |
|  | doc | Cursor | [Cursor – Usage and limits](https://cursor.com/help/models-and-usage/usage-limits) |  |  |

## Microsoft GitHub (3)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-07 | blog | Microsoft GitHub | [Copilot CLI auto model selection routes based on task](https://github.blog/changelog/2026-07-01-copilot-cli-auto-model-selection-routes-based-on-task) |  |  |
|  | doc | Microsoft GitHub | [Setting an AI credit session limit in GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/set-session-limit) |  |  |
|  | doc | Microsoft GitHub | [Using GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/overview?plain=1) |  |  |

## Groq (3)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2025-10 | blog | Groq | [GroqCloud Introduces GPT-OSS Improvements: Prompt Caching & Lower Pricing](https://groq.com/blog/gpt-oss-improvements-prompt-caching-and-lower-pricing) |  | t |
| 2025-08 | blog | Groq | [Introducing Prompt Caching on GroqCloud](https://groq.com/blog/introducing-prompt-caching-on-groqcloud) |  | t |
|  | doc | Groq | [Groq Batch API](https://console.groq.com/docs/batch) |  |  |

## Perplexity (3)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-03 | blog | Perplexity | [Hosting Qwen on Blackwell (Perplexity)](https://www.perplexity.ai/hub/blog/hosting-qwen-on-blackwell) |  |  |
| 2025-08 | blog | Perplexity | [GPT-OSS on Day 0 (Perplexity)](https://www.perplexity.ai/hub/blog/gpt-oss-on-day-0) |  |  |
| 2023-10 | blog | Perplexity | [Introducing pplx-api](https://www.perplexity.ai/hub/blog/introducing-pplx-api) |  |  |

## Amazon Kiro (2)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2026-08 | doc | Amazon Kiro | [Billing](https://kiro.dev/docs/billing) |  |  |
|  | blog | Amazon Kiro | [Bring Kiro agents to your terminal with Kiro CLI](https://kiro.dev/blog/introducing-kiro-cli) |  |  |

## Meta (1)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
| 2025-05 | model | Meta | [Llama 4 Maverick 17B 128E Instruct](https://huggingface.co/meta-llama/Llama-4-Maverick-17B-128E-Instruct?local-app=docker-model-runner) |  |  |

## Microsoft Research (0)

| Date | Type | Org | Title | Local | Flag |
|---|---|---|---|---|---|
