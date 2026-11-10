# Kiro Learnings — Token Economics of CLI Coding Agents

Synthesized from ~43 source notes in `notes/kiro/`. Source ids in brackets. Numbers kept as stated in the notes.

## 1. The 15 most important lessons

1. **Agentic coding costs ~1000× more tokens than chat, and it is an input-token problem.** OpenHands trajectories on SWE-bench Verified averaged 4.17M tokens and $1.857/task vs $0.016–$0.023 for reasoning/chat, with an input/output ratio of 153.85 (vs ~1.33 for chat) [023]. The driver is that full conversation history is re-sent every turn, so input context compounds — not output generation.

2. **Cache reads dominate the bill by volume even though they are the cheapest token type.** Output tokens are priced ~80× higher than cache reads, yet cache reads dominate total cost because of their sheer volume [023]. A production case study saw 99.3% cache-hit rate cut realized API cost by 88.6% ($8,785 billed vs $77,059 uncached), giving an effective $0.57/M processed tokens against a $5/$25 list rate [053]. On Opus 5.5 an uncached token costs 20× a cached one [010].

3. **More tokens do not buy more accuracy.** Accuracy peaks at intermediate cost; high spend often signals unproductive repeated file views/edits, with higher-cost models doing ~50% repeated file actions [023]. Aider's leaderboard shows the weak coupling directly: DeepSeek-V3.2 Reasoner hits 74.2% at $1.30 while o3-pro reaches 84.9% for $146.32 — ~112× the cost for ~11 points [038].

4. **Cost per successful task, not token count, is the right metric — and the harness is the single biggest cost factor.** Claude Code transmits a 12–15× larger fixed prefix than a bare chat-completions harness (15,983–20,330 vs 1,147–1,642 tokens) and runs 5–30× higher cost/success on small tasks [026]. The same effort-control intervention saved 19% under one harness default and 75% under another — intervention value flips with the harness [026].

5. **Prompt verbosity silently multiplies reasoning tokens with no success gain.** "Explore multiple approaches" raised reasoning tokens +2.4–7.4× across six models at comparable success; "deep thinking" 1.6–2.2×; max-certainty wording 1.3–1.9× plus extra post-success tool calls [026]. Redundant verification scaled 1.00×/1.48×/2.36×/18.25× by level [026].

6. **Simple observation masking beats LLM summarization for context management.** Replacing old tool outputs with a placeholder halved cost vs an unmanaged agent (Gemini 2.5 Flash $0.41→$0.18, −56.1%) while matching or slightly beating LLM-summary solve rate; observations are ~84% of an average SWE-agent turn [130]. Across 8 condensers on 60 tasks, LLM-based condensers *raised* cost 24–94% and only masking netted savings (+8.6%) with no measurable quality loss [133].

7. **Context condensation only pays off on long trajectories.** Net token savings appeared only on >10-event tasks (masking +33.5%, conversation-window +26.3%); on short (≤7-event) tasks condensation cost −45% to −149% because overhead isn't amortized [133]. Choose a condenser by domain verbosity — verbose domains gain most (Sociology 52% vs MetaScience ~0) [133].

8. **The three Anthropic context primitives target different bottlenecks — diagnose first.** Clearing is cheapest and lossless-by-refetch (demo 128,740→43,060 tokens, 67% reduction); compaction is lossy and loses verbatim specifics (169,164→5,829, but obscure specifics 0/3 preserved); memory moves state out of the window across sessions [006]. In one baseline, file-read results alone were 322,946 tokens = 96.3% of final context [006].

9. **Per-step, prefix-conditioned routing roughly halves API spend; always-largest is dominated.** A trained static-label router cut SWE-bench API cost 53.1% ($25.66 vs unrouted Opus $54.73) at comparable resolve [030]. Learned routers beat the strongest fixed-model baseline by 14.6% relative while costing less, because many queries the largest model fails are solved by cheaper ones [033].

10. **A frontier model prompted as a router is unreliable — use execution-verified supervision.** Opus-4.6 as an LLM-router predicted the high tier for only 7/147 verified-high SWE steps and failed all 40 SWE trajectories [030]. Cheap, trainable static labels built from execution outcomes produce a far better router than asking a strong model to self-route [030].

11. **MCP tool definitions are a large, front-loaded tax that also degrades accuracy.** The official GitHub MCP server is ~42,000 tokens (~94 tools ≈17,600 by another count); stacking 4–5 servers hits 60,000+ tokens, 30–50% of a frontier budget [020][022]. A focused ~4-tool set scored ~95% tool-selection accuracy vs ~71% with the full GitHub MCP — a 24-point drop from context bloat alone [020]; on-demand schema loading compresses tool overhead 70–97% [022].

12. **Context acquisition is a measurable upstream cost and failure surface.** Interactive agents never touched any gold file on 27.2–35.2% of samples; an oracle gold-file seed raised final File F1 by 0.3115 and rescued 100% of no-seed misses [045]. File-level hits also overstate localization — median gold evidence is only 4.7% of the file — so budget for within-file search too [045].

13. **Prompt caching can invert the cloud-vs-on-prem decision; on-prem only wins when the GPU is shared.** Cached frontier API was cheaper per processed token than a self-hosted quantized GLM cluster; on-prem reached 40.1% TCO saving only under shared allocation ($2.83/M) and was 43.8% *more* expensive dedicated ($11.87/M) [053]. The quantized local model also carried a far higher defect burden (Fix Commit Ratio 74.93% vs 45.93%), so route high-stakes work to the frontier model [053].

14. **Scope and patch size predict both solvability and cost.** On Multi-SWE-bench, resolve rates drop sharply once fix patches exceed 600 tokens or touch >1 file (>600-token issues resolve ~50% lower) [135]. Fixed-workflow methods (MagentLess) cost less than multi-turn agents (MSWE-agent/MopenHands) because the latter burn more interaction turns and often hit the 50-round limit [135]; cheap open models (DeepSeek, Qwen) hit ~1/100th the per-issue cost of OpenAI-o1 ($0.03 vs up to $3.75) [135].

15. **Models cannot predict their own token usage, and human difficulty labels don't either — so budget from telemetry, not estimates.** Self-prediction Pearson r peaked at only 0.39 with systematic underestimation [023]; human difficulty vs cost was weakly correlated (Kendall τb=0.32), with 6.7% of "<15 min" tasks exceeding the average ">1 hr" cost [023]. The practical response is export telemetry (OpenTelemetry/`/usage` per-category) and attribute spend by model, subagent, skill, and MCP server [002][004][091].

## 2. Where sources disagree or numbers conflict

- **Is Claude Code's heavy harness worth it?** [041] frames Claude Code's grep-and-chase + large context as *worth* the 2.4× token burn because it wins success (86.7% vs Aider 71.4% on 500k-LOC tasks). [026] frames the same large fixed prefix as the *single largest cost factor* (5–30× higher cost/success on small tasks). Not strictly contradictory — [041] optimizes success, [026] optimizes cost-per-success — but they point builders in opposite directions, and [041] is an affiliate blog while [026] is a preregistered benchmark.

- **Is LLM-based summarization useful?** [006] (Anthropic) presents compaction and memory as first-class, worthwhile primitives. [130] and [133] measure LLM summarization as *adding* cost (24–94% overhead [133]; summary generation up to 7.2% of instance cost plus "trajectory elongation" [130]) with no quality gain over trivial observation masking. Direct conflict on whether the LLM-condensation complexity pays.

- **Routing savings spread widely.** Claimed/measured reductions range from +14.6% relative [033], to ~53% measured [030], to "up to 80%" [062], to "5–10×" and "80–90% of tokens moved to cheap models" [013]. The high end ([013], [062]) is self-reported/vendor; the mid-range ([030], [033]) is execution-measured.

- **Cloud vs on-prem/local economics.** [053] finds cached cloud cheaper per token yet on-prem cheaper on TCO *only* when the tray is shared. [013] and [041] assume cheap/local models straightforwardly save money. The conflict is that [013]/[041] omit the defect-repair labor that [053] measures (OR 3.61 more fixes for the local bundle).

- **How much of the context window is usable?** [036] cites ~245K of Codex's 400K advertised as usable and models degrading 30–40% before claimed limits (Zylos), with ~2/3 of models failing retrieval at 2,000 tokens. Vendor docs [073][079] present full 200K/1M windows with only representative fill figures, implying more headroom than [036].

- **The "$13/developer/active day" benchmark.** Repeated as an Anthropic figure [004][010], but [010] notes Anthropic doesn't publish how subscription limits convert to tokens and the benchmark has no stated model mix — so it's not comparable across teams.

## 3. What is hype vs what is measured

Measured (methodology, often CIs, reproducible or production-logged):
- Agentic token blowup, variance, self-prediction failure — arXiv, 8 models × 4 runs on SWE-bench Verified [023].
- Prompt/effort/harness cost effects — preregistered, 4,644 runs + 2,801 blind annotations [026].
- Observation-masking ≥ LLM-summary — SWE-bench Verified, multiple models [130]; 8 condensers × 60 tasks with Wilcoxon/Bonferroni [133].
- Routing ~53% cut and frontier-as-router failure — execution-verified leaderboard [030]; +14.6% relative across xRouteBench [033].
- Retrieval as upstream cost/failure — 427 samples, 25 repos [045].
- Patch-size/scope effects — 1,632 verified instances, 7 languages [135].
- Accuracy-vs-dollar decoupling — reproducible 225-case leaderboard [038].
- Production caching inversion — real two-period case study, though n=1 developer [053].

Hype or soft (self-reported, vendor-promotional, no methodology, or explicitly illustrative):
- "5–10× cost reduction," "80–90% of tokens to cheap models," "25× cheaper Haiku" — no benchmark or methodology, promotes own product [013].
- "Routing savings up to 80%," "caching cuts up to ~90%," "semantic caching +30–50%" — aggregated vendor ranges, not reproduced [062].
- MCP compression "almost no impact on end-to-end quality" — asserted with no numbers [022]; MCP-bloat accuracy figures (~95%/~71%) are author-measured with no released methodology, ends in a product pitch [020].
- Outcome-based pricing "you only pay on merged PRs" — single named beta testimonial, no cost figures [069].
- Claude-Code-vs-Aider decision matrix — self-run affiliate blog on undisclosed proprietary codebases, not reproducible [041].
- Vendor "representative" token counts explicitly *not* measured — all status-line/context-window figures are illustrative [079]; the 91%-cache blended-cost example is the author's assumption, not an Anthropic figure [010].
- Dollar figures from telemetry are client-side list-price *estimates*, not bills, across all observability tooling [002][004][076][085].

## 4. Five open questions

1. **How do subscription usage windows convert to tokens?** Anthropic (and OpenAI) don't publish the token-to-limit mapping or per-model weighting, so any firm "X tokens/week" figure is guesswork and the $13/day benchmark isn't portable [010][009][115].

2. **Do small-task findings transfer to repo-scale, long-horizon production?** The strongest results come from ≤4-file tasks and SWE-bench slices; authors explicitly flag that branch-waste, masking windows, and condensation thresholds may shift on real multi-hundred-iteration workflows [026][130][133][135].

3. **Does a retrieval miss actually cause repair failure?** [045] measures context acquisition as a failure *surface* but does not establish causation between a retrieval miss and end-to-end patch failure — the link to patch success is unmeasured.

4. **Can an adaptive, runtime condenser/router beat static strategies?** Multiple papers find the best condenser depends on domain and task length and motivate meta-condensers that switch mid-task, but none builds or evaluates one; the adaptive cost-controller in [026] is a design proposal, not evaluated [130][133][026].

5. **What is the true quality cost of a quantized open-weights model, isolated from harness and capability?** [053] sees a 3.61× defect odds ratio for the local bundle but cannot separate NVFP4 quantization from intrinsic model gap from the Opencode-vs-Claude-Code harness difference — no FP16/FP8 baseline exists.
