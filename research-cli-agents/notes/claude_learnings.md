# Learnings from the 86 Claude-batch notes

Source ids are the note file numbers in notes/claude/ (for example [055] is 055.md). Numbers are copied from the notes. Nothing here comes from outside them. Note: the folder holds 86 files, not about 85.

## 1. The 15 most important lessons

1. **Cost is mostly re-sent input, and the ratio is large.** Each turn re-sends the system prompt, files, edits, errors and full history, giving roughly 25:1 input to output in an illustrative 50-turn session (about 1M input, 40K output) [124]. On SWE-bench Verified with caching off, baseline runs used about 159M-240M input tokens against 0.47M-4.3M output [025]. Retries are billed at the inflated context size, and two retries can triple cost [124][129].

2. **Prompt-cache hit rate is the dominant lever.** Across Requesty gateway data (May 2025 to April 2026) per-user cost rose 3.8x ($14 to $54/month) while per-call cost stayed flat, because platform cache hit rose from 52% to 86% [054]. Claude Code ran at 92% hit and $0.050/call, against Kilo Code at 46% [054]. At 92% hit the effective input rate was about $0.30/M against $3.00 list, a 5.4x gap to the 46% case [054]. Cache reads and writes are about four fifths of Claude Code spend in LangWatch orgs [005].

3. **A few routine actions silently invalidate the Claude Code cache.** Anthropic's docs list these as invalidators: model switch, effort change, fast-mode toggle, adding or removing MCP tool definitions, compaction, many images, and Claude Code upgrade [055]. Turning on fast mode mid-conversation bills the whole context at the fast uncached input price (Opus 5.5 fast: $8/$40 per MTok) [086]. Set model, effort and fast mode at session start [055][086]. Gateways that strip cache_control make the whole history bill as uncached every turn [055].

4. **Do not set a blanket 1-hour cache TTL, and subagents do not share the parent's cache.** Multipliers are 5m write 1.25x, 1h write 2x, read 0.1x on most models [052][051]. One operator's blanket 1h TTL made the bill 8.6% worse, because 98% of reuse happened within about 34 s of the write [052]. Targeted fixes (1h write on dispatch turn, persistent static prefix, dynamic content after the stable prefix) gave -6.0%, -1.0%, -7.6%, and -13.6% combined [052]. Subagents, workflows, compaction and titles get 5 minutes by default, and a non-fork subagent starts cold, while a fork inherits the parent prefix [055][052]. Cron runs that start fresh sessions get about 0% hit (672 runs/day x ~30K-token prefix, about 20M input tokens/day uncached) [052].

5. **Fixed per-turn overhead (tool schemas, instructions) is a recurring tax.** Four MCP servers cost about 7,000 tokens before the first prompt, and a heavy config cost 66,000 (nearly a third of a 200k window) [019]. A 93-tool GitHub MCP is about 55,000 tokens per turn [021][107][108]. In a TokenEconomizer profile the agent saw 23 tool schemas every turn, no repo used more than 7, 16 were never called, and 3 accounted for 98% of calls [028]. Pruning tools cut Claude Code cost by 13.2% and 17.7% in the ablation [028]. Claude Code defers MCP tool definitions by default via tool search, so only names load until use [089]; Codex tool search has been default since v0.142.2 [111].

6. **Keep always-loaded context small and path-scoped.** Claude Code guidance is CLAUDE.md under 200 lines, procedures in skills, path-scoped rules, and unused MCP servers off [077][080]. @imports do not reduce cost [077]. Skill descriptions load every turn and truncate at 1,536 characters; disable-model-invocation removes them from context [075]. Plugins carry an always-on description cost (example plugin about 146 tokens; 2,000 tokens or more is flagged), measurable with `claude plugin details` [084]. Start sessions from the package directory and deny-read generated paths in monorepos [083].

7. **Tool results dominate context, so clear them first and compact late and deliberately.** In a constructed 26-message session, 5 tool results were about 12,500 of about 15,400 tokens (81%) [007]. Claude Code layers zero-LLM clearing of old tool results, prefix-preserving edits, then a 9-section summary [007]. Auto-compact threshold is the effective window minus 13,000 tokens [007]. Anthropic's context-editing defaults are trigger 100,000, keep 3 tool uses, with production guidance of 30-40k trigger and clear_at_least 3,000-5,000 [065][066]. One estimate puts a compaction on a 125,000-token context at $0.40, about 21 cached follow-up turns [112]. Compaction can drop information the agent still needs [067][005].

8. **Turn and budget caps cut cost with small quality loss, if the cap comes with a reminder and enforcement is external.** Capping turns at the 75th percentile of an unrestricted baseline cut cost 23.62% (Sonnet 4, solve 75% to 71%), 68.28% (Gemini 2.5 Pro) and 38.43% (GPT 4.1) [025]. A "start small, one extension" policy saved a further 5%-24% [025]. A budget tracker at budget 10 matched ReAct at budget 100 (12.8% vs 12.6%) with 31.3% lower cost [131]. Claude Code has --max-turns and --max-budget-usd for unattended runs [080].

9. **Failed and looping runs are the largest avoidable waste, and variance is huge.** In TokenEconomizer profiling, 10 failed runs were 17% of tasks but 32% of spend, and 51% of spend came after the first repeated failure signature [028]. Identical runs can differ up to 30x [027][110]. Geometric run-to-run SD is x1.34 [027]. One probe run ($0.11) cuts median prediction error from 161% to 36%, and a 1.9x multiplier covers 90% of runs [027]. Raising the budget does not help a capability-limited agent: Gemini 2.5 Pro scored 13.2 at default and about 13.0 at 40M [132].

10. **Concrete task specs and the language choice move cost.** Cutting a full spec to a bare user story raised spend 29.7% and turns 16.4%, positive on all five tasks [027]. A raw failing-test spec cost 0.73x-1.10x the full spec and was cheapest at low effort on 4 of 5 tasks [027]. OCaml cost 1.28x-1.69x Python output tokens at comparable accuracy; waste came from compile-error loops and rewriting already-passing solutions [134].

11. **Route by turn type and effort, and verify with cheap post-hoc checks.** Anthropic recommends defaults, a smaller model for routine work, and raising effort only when Claude skipped steps [093][080]. A planner-only frontier orchestrator with cheap workers had 84-98% of team input tokens billed at the worker rate [012]. A proxy that kept tool-call turns on Opus and sent simple text turns to a cheap model reported 45.8% savings on 125 requests [031]. Static routers fail out of distribution (8.93-21.43% OOD vs 62.50% for ACRouter) [032]. Noisy estimators give about 1% gain [029]. Cascade from cheap on failed tests, since post-hoc signals work [029].

12. **Subagents and agent teams trade tokens for context hygiene.** Anthropic says teams use significantly more tokens, with no measured multiple [081]. A cited figure is about 7x for teams in plan mode [001]. Subagents spend their own requests against the same limits [072][080]. OpenAI's docs say the same for Codex [102]. Use them for read-heavy exploration, route them to Haiku or a cheap model, cap concurrency (Claude default 20, nesting 3; Amp advice about three) [072][070]. In USACOArena a blind parallel swarm scored 3 against 8 for a cost-aware one [132].

13. **Pricing is moving to token-metered, and cost is heavy-tailed.** Cursor moved Pro from 500 requests to $20 of API-rate usage because hard requests cost about 10x simple ones [015][016]. Copilot legacy billing is per prompt ($0.04 per extra request) and decoupled from tokens [117]. Gemini CLI caps requests per day (1,000 to 2,000 on paid tiers, 250 free) [057]. Claude Code active users averaged $108/month but the median was $23 and P95 $291 [054]. ChatGPT Work annualized median ~$53 vs average ~$309 vs P90 ~$1,154 [101]. Budget around P95, not the mean [054].

14. **Instrument per-call usage before optimizing, and attribute by caller.** Read cache_read_input_tokens and cache_creation_input_tokens per response [128][051]. Claude Code has /usage, /context, OTel export and /usage flags at 10% of usage [080][005]. Gateways add per-developer budgets with HTTP 402 on exhaustion [001][060]. Track hit rate per caller, since an account-level 77% hid cron at about 0% [052]. A resume hook with prompt_cache_likely_expired can warn before a stale session re-sends 182,340 tokens (example estimate $1.1396) [074].

15. **Trim tool output and read less; agentic search beats stuffing.** A failed npm test can dump about 15,000 tokens against about 50 needed [128]. Codex tool_output_token_limit and Claude PostToolUse updatedToolOutput cap output [104][074]. Coding agents using grep and sed on files beat published SOTA by 17.3% on average across five long-context benchmarks, though RAG stayed cheapest per query (for example $0.111 vs $0.703 on BrowseComp-Plus) [046]. Aider's "whole" edit format is token-hungry vs diffs and unknown models silently default to it [039].

## 2. Where sources disagree or numbers conflict

- **Input vs output as the cost driver.** Input dominates in [124] (about 85% of session total), [128] and [110]. At a 96.3% cache hit, output was 2.7% of tokens but 51.1% of dollars, and cached input was 94% of tokens but 35% of dollars [027]. [114] says output dominates (8x input). Which one wins depends on cache hit and price schedule.
- **Does compaction destroy the cache?** [112] says every compaction destroys the cache. [055] says compaction reuses the cached prefix while warm and costs most when resuming after TTL expiry. [007] says Claude Code avoids altering the prefix. [052] says compaction uses a different system prompt and so can miss the cache.
- **Auto-compact thresholds.** Claude Code: window minus 13,000 [007]; about 89% [112]; "95% judged too late" [034]; author prefers 400000 [005]. Codex default: 80% of window [108]; about 90% [112]; about 200K on a 272K input budget [111]; example 180000 [035]. Manual advice: 50% [034], about 60% [107], 250k-450k for Claude Code [005].
- **MCP schema size.** GitHub MCP is about 55,000 tokens (93 tools) in [021][107][108] but about 8,000-12,000 in [019]. Per-schema size is 394 [021], 200-500 [021 alpha], 550-1,400 [107], and 610 for two Codex tools [019]. Playwright is about 3,442 for 22 tools [019].
- **MCP deferral default.** [089] says deferred by default via tool search. [019] says auto-on above a 10%-of-context threshold. [055] notes MCP changes invalidate cache when tool search is off.
- **Claude Code spend per developer.** Anthropic average $13/active day and $150-$250/month [001][005][129]. Requesty observed active mean $108/month, median $23, P95 $291 [054]. [129] says the average implies $1.60-2.60 per task but its own summary says $0.03-$2.60 and $0.03-$0.13.
- **Requesty internal conflict.** Claude Code input is 84K per call in the chart but "exceeds 200,000" in the text [054].
- **Cache price ratios.** Read is 0.1x [051][052][128][056]. [052] also lists Opus 5.5 read at 0.05x and Fable 5.1 at 0.025x, and [119] shows Opus 5.5 $4 input / $0.2 read (0.05x). [012] lists Sonnet 5.5 read $0.20 vs $0.1 in [119].
- **Model prices.** Opus 4.8 is $5.50/$27.50 in [031] but $5/$25 in [128]. Opus 4.6 is $5/$25 in [032] and in [124] for output.
- **Cache TTL behavior.** [052] says docs and observed subagent TTL conflict. Defaults differ by billing: 1h only on subscription in plan usage, 5m otherwise [055][080][052].
- **Reasoning-effort multipliers.** xhigh is about 8-15x medium in [105], 3-5x in [107], and "high/xhigh triple a turn" in [108]. High vs low is about 7x in [093] (illustrative). Medium to low saves 40-60% [108].
- **Claimed savings from routing/config.** 40-60% [014], 30-60% FAQ [014], 50-70% [105], about 60% [034], 45.8% vs 47.4% [031], 18.4-30.9% [028], about 40% on top of 70% from caching [037].
- **Does showing a budget work?** Budget reminders worked in [025] (without reminders Sonnet at 25th percentile fell to 24% solve) and [131] (Budget Tracker). Agents never referenced a visible 50,000-token budget in 14,000+ messages in [136]. Few-shot prompts consumed credits without better decisions [132].
- **Does extra compute help?** Spend saturates [132][110]. But [093] says a larger model on hard multi-step work can cost less per task, and [056] shows Sonnet 91% vs Haiku 63% on multi-file refactor at about 4x cost.
- **Instruction-file size targets.** CLAUDE.md under 200 lines [077], under 800 tokens [056], always-loaded under 2,000-5,000 tokens [008]. Typical overhead 1,500-4,000 [129], 2,000-5,000 [107], about 5,000 [111].
- **Codex context window.** 272K default up to 872K [035]; 400K session cap, 272K input, 1,050,000 advertised, 258,400 usable after 5% headroom [111]; 1M for GPT-5.5/5.4 [107].
- **Codex plan prices and model names.** Pro from $100 ($100/$200/$500) [096]; Pro 5x $100 and 20x $200 [114]; Pro $200 [107]. Model families differ (GPT-6.x [096] vs GPT-5.x [107][114]).
- **Cursor tiers.** Ultra $200 with $400 usage (20x Pro) and Teams $40/user [017][018][124] vs Plus $8, Ultra $200 (50x) and Teams $30/$100/$200 [119]. These reflect different dates.
- **Aider repo map.** Default `--map-tokens` is 1k [040], but one author estimates the repo map at 50-60% of session tokens [037]; [129] gives 2,000-8,000.
- **TokenEconomizer vs tool-gating.** Pruned tools and fixed compressors help some repos and hurt others (RTK alone raised cost in 12 cells) [028]. Static pruning without a recovery path can hurt success [021].
- **Agent teams.** About 7x tokens [001] vs "no measured token multiples" in the docs [081].
- **Date inconsistencies.** [018] metadata says 2025-05 but text refers to May 2026. [096] mentions GPT-5.5 retiring Oct 14, 2026.

## 3. Hype vs measured

**Measured, with caveats (trust more):**
- [054] twelve months of gateway data, nine agents (vendor gateway, selection bias, Cursor and Copilot largely missing).
- [025] 100 SWE-bench Verified tasks, three models, single run per config, caching disabled.
- [027] 2,700 runs, one model (Kimi K3), five tasks, Bayesian model.
- [028] 277 SWE-Bench tasks plus 102 Web-Bench plus 200 security tasks, three agents, three seeds (Microsoft's own).
- [134] 2,000 trajectories across five models.
- [136] Ramp's own experiment, SWE-bench Verified, six models.
- [131][132][046][122][032] authors' own benchmarks. [122] reports 54% vs 53% solved on a subset only.
- [052] one operator's data (8.6%, 13.6%); [005] author's own sessions and one controlled run (compaction at 150k halved cost but lost early-file recall).
- [110] cites Bai et al. (30x variance, self-estimate correlation at most 0.39).

**Hype, assertion or illustration (trust less):**
- [037] "80% cut, $8 to under $1.50": headline not reproduced; "40%" and "5-15x" unsupported.
- [034] "about 60%" overall and per-setting percentages: single author, no baseline.
- [056] "50-80%" headline vs "50-70%" body; no method or dataset.
- [014] "40-60%", "70-80% of work": no source or method, model names dated.
- [060] Headroom "60-95% on the compressible portion": no source; no stacked end-to-end figure.
- [061] RouteLLM 85% at 95% of GPT-4 quality, GPTCache "up to 10x", combined 30-70%: tool authors' claims on chat/RAG benchmarks, not coding agents.
- [063] 10x-100x lower token cost: table values are placeholders; [049] 40-70% replaceable queries are guesses for non-coding agents; [048] 77.55% vs Claude-CoT 2.73% suggests harness mismatch.
- [019] mcp2cli 96-99% and Anthropic 98.7% are self-reported; its $21,000/month projection ignores caching.
- [021] success 72% to 94%, latency and $/task are projections, only token counts were measured.
- [105] 50-70% saving unsourced; [108] before/after table is "based on benchmarks and community reports"; [110] SWE-Pruner 20-40% is a claim.
- [124][008][129] token and dollar examples are explicitly illustrative; [124] ignores caching.
- [031] model predicted 67.2% savings vs 47.4% empirical; the 100% vs 95% quality claim rests on one task.
- [011] doubled limits are from a competitor vendor blog, no primary Anthropic source.
- [001][060][126][128] and similar gateway or monitoring posts are product marketing.
- [112] "49% improvement" is longer summary length, not quality; "50x" KV compaction is research only.

## 4. Five open questions

1. What do cache hit rate and cost look like for Claude Code subagent-heavy workflows in real use? Docs and observation conflict on subagent TTL [052], and no measured token multiple exists for subagents or teams [081][001].
2. What is the real per-turn cost of MCP schemas under deferral and caching? Tax estimates range from about 8,000 to 55,000 for GitHub MCP [019][021] and none model cache discounts [019][124].
3. When does compaction pay off, and at what window size? Thresholds and costs conflict [005][034][112][007], one run lost early-file recall [005], and OpenHands' 2x gain is on a subset with unstated thresholds [122].
4. Do budget awareness and turn caps work on real Claude Code sessions? Visible budgets helped in [025][131] but were ignored in [136], and the studies use SWE-bench or search benchmarks, not interactive CLI sessions.
5. How much does routing save in practice for a CLI agent when tool-call turns are 70-80% of traffic? Savings claims range 18.4%-60% [028][031][034][014], tool turns must stay on the strong model [031], and real-world router gains are small [029][032].
