# Token economics of CLI coding agents: what 136 sources teach

Spend less on a coding agent by doing four things in order: read the cache-hit rate, keep the always-loaded context small, stop failing runs early, and send simple turns to a cheaper model. Prompt caching decides most of the bill. A session is almost entirely re-sent input, so the price of one output token matters far less than what you resend on every turn.

This guide combines what Claude and Kiro took from the 136-source corpus in `research-cli-agents/`. Kiro wrote 43 notes and Claude wrote 86, which includes the shard meant for Codex. Codex hit its usage limit (resets 8:27 PM) before it wrote a single source or note, so it contributed nothing. Nobody, including me, has read the sources first-hand. The notes are model-generated summaries, and I spot-checked only the numbers this guide leans on.

**How to trust the numbers.** A figure is one of four kinds:
- *Price list.* A vendor states a rate. It records the list, not a saving.
- *Measured, independent.* Someone outside the project measured real runs.
- *Measured, self-reported.* The authors tested their own method on their own benchmark. Treat as a claim.
- *Illustrative.* An author's worked example. It is arithmetic, not evidence.

**Terms used below.**
- Command-line interface (CLI): a terminal program.
- Large language model (LLM): the model behind the agent.
- Model Context Protocol (MCP): the standard for plugging tools into an agent.
- Software Engineering (SWE) benchmark, written SWE-bench: real GitHub issues that agents try to fix.
- Generative Pre-trained Transformer (GPT): OpenAI's model family.
- Time to live (TTL): how long a cache entry survives.
- OpenTelemetry (OTel): an open standard for exporting usage data.
- P95: the value 95% of users stay under.
- Retrieval-augmented generation (RAG): fetching text snippets into the prompt.
- Total cost of ownership (TCO): all-in cost including hardware and labour.

## 1. Where the money goes

**Agent sessions are an input problem.** Each turn re-sends the system prompt, files, edits, errors and the whole history. An illustrative 50-turn session was about 1M input tokens against 40K output, roughly 25:1 [124]. Measured on SWE-bench Verified, OpenHands runs averaged 4.17M tokens and $1.857 per task, against $0.016-$0.023 for chat-style reasoning, with an input-to-output ratio of 153.85 [023]. Another run set with caching off used 159M-240M input tokens against 0.47M-4.3M output [025].

**Cache reads dominate the bill by volume.** An output token is priced about 80x a cache read, yet cache reads are the largest cost line because there are so many of them [023]. In LangWatch customer organisations, cache reads and writes were about four fifths of Claude Code spend [005].

**More tokens do not buy more accuracy.** Aider's leaderboard shows DeepSeek-V3.2 Reasoner at 74.2% for $1.30 and o3-pro at 84.9% for $146.32, about 112x the cost for about 11 points [038]. High-cost runs spent about half their file actions on repeats [023].

**Measure cost per resolved task.** The same effort-control change saved 19% under one harness default and 75% under another, so a fix's value depends on the harness [026]. Claude Code's fixed prefix was 15,983-20,330 tokens against 1,147-1,642 for a bare chat harness, and cost-per-success on small tasks ran 5-30x higher [026]. A competing blog argues the heavier harness pays for itself because it wins more tasks (86.7% against Aider's 71.4% on 500k-line codebases), but that is an affiliate post on private code [041].

## 2. Caching: the biggest lever

Cache reads cost 0.1x the input price on most Claude models, a 5-minute write costs 1.25x and a 1-hour write costs 2x [051][052]. Two sources list cheaper reads on newer models (0.05x for Opus 5.5, 2.5% for Fable 5.1) [052]. Sources that quote model names from 2026 pages I could not independently confirm.

The gateway data is the best single picture. Over May 2025 to April 2026, cost per user rose 3.8x ($14 to $54 per month) while cost per call stayed flat, because the platform cache-hit rate rose from 52% to 86% [054].

| Agent (April 2026) | Cache hit | Cost per call |
|---|---|---|
| Claude Code | 92% | $0.050 |
| OpenCode | 89% | $0.061 |
| Aider | 84% | $0.009 |
| Roo Code | 74% | $0.105 |
| Cline | 61% | $0.121 |
| Kilo Code | 46% | $0.065 |

At 92% the effective input rate was about $0.30 per million against $3.00 list, a 5.4x gap to the 46% case [054]. This is one gateway's traffic, and the vendor sells gateways, so Cursor and Copilot users are mostly missing.

**Routine actions silently break the cache.** Anthropic lists these as invalidators: switching model, changing effort, toggling fast mode, adding or removing MCP tool definitions, compaction, many images and upgrading Claude Code [055]. Turning on fast mode mid-conversation bills the whole context at the uncached fast price [086]. Rules that follow:
1. Set model, effort and fast mode at session start.
2. Put static content first and dynamic content last.
3. Check `cache_read_input_tokens` and `cache_creation_input_tokens` on every response [051][128].
4. Confirm your gateway keeps `cache_control` markers. One that strips them bills the whole history uncached each turn [055].

**A blanket one-hour TTL can cost more.** One operator's blanket 1-hour setting made the bill 8.6% worse, because 98% of reuse happened within about 34 seconds of the write. Targeted fixes (1-hour write only on dispatch turns, a persistent static prefix) cut cost 6.0%, 1.0% and 7.6% separately and 13.6% combined [052]. Subagents do not share the parent's cache unless they are forks, and cron runs that start fresh sessions hit about 0% [052][055]. An account-level 77% hit rate hid that cron traffic, so track the rate per caller [052].

## 3. Context: what fills the window

**Tool results dominate.** In a constructed 26-message session, five tool results were about 12,500 of 15,400 tokens (81%) [007]. In one baseline, file reads were 322,946 tokens, 96.3% of the final context [006]. Observations are about 84% of an average SWE-agent turn [130]. A failing npm test can dump about 15,000 tokens where about 50 are needed [128].

**Clear before you summarise.** Observation masking, replacing old tool output with a placeholder, halved cost against an unmanaged agent (Gemini 2.5 Flash $0.41 to $0.18, -56.1%) and matched LLM summaries on solve rate [130]. Across eight condensers on 60 tasks, LLM-based condensers raised cost 24-94%, and only masking saved money (+8.6%) [133]. Condensation only pays on long runs: gains appeared above 10 events and turned negative (-45% to -149%) at 7 or fewer [133].

Anthropic's own primitives differ by job. Clearing is cheap and lossless by re-fetch (128,740 to 43,060 tokens, -67%). Compaction is lossy (169,164 to 5,829 tokens, with obscure specifics preserved 0 of 3 times). Memory moves state out of the window across sessions [006]. The context-editing defaults are a 100,000-token trigger keeping 3 tool uses, and production guidance is a 30-40k trigger [065][066].

**Always-loaded context is a recurring tax.**
- Four MCP servers cost about 7,000 tokens before the first prompt, and a heavy configuration cost 66,000, nearly a third of a 200k window [019].
- The GitHub MCP server is about 55,000 tokens for 93 tools in three sources and 8,000-12,000 in another, so treat the figure as unsettled [021][019][107][108].
- In one profile, an agent saw 23 tool schemas every turn, 16 were never called and 3 made 98% of calls. Pruning tools cut Claude Code cost 13.2% and 17.7% [028].
- A focused four-tool set scored about 95% tool-selection accuracy against about 71% with the full GitHub server, so bloat also hurts quality (author-measured, ends in a product pitch) [020].
- Claude Code defers MCP definitions by default through tool search, and Codex has done so since v0.142.2 [089][111].
- Keep `CLAUDE.md` under 200 lines, move procedures into skills, and note that `@imports` do not reduce cost [077][080]. Skill descriptions load every turn [075].

**The cheapest search is the agent's own.** Coding agents using grep and file tools beat published results by 17.3% on five long-context benchmarks, although RAG stayed cheapest per query ($0.111 against $0.703 on one benchmark) [046]. Interactive agents never opened a gold file in 27.2-35.2% of samples, so retrieval misses are a real failure surface [045].

## 4. Stop waste, cap loops

**Failed runs are the biggest avoidable cost.** In one profile, 10 failed runs were 17% of tasks and 32% of spend, and 51% of spend came after the first repeated failure [028]. Identical runs differ by up to 30x, and geometric run-to-run spread is x1.34 [027][110]. Models cannot predict their own usage (best correlation 0.39), and human difficulty labels barely do (Kendall 0.32) [023]. One cheap probe run cut median prediction error from 161% to 36%, and a 1.9x multiplier covered 90% of runs [027].

**Turn caps work if the agent is told about them.** Capping turns at the 75th percentile of an unrestricted baseline cut cost on three models [025]. Sonnet 4 fell 23.62%, with solve rate dropping from 75% to 71%. Gemini 2.5 Pro fell 68.28% and GPT 4.1 fell 38.43%. A budget tracker at budget 10 matched plain ReAct at budget 100 (12.8% against 12.6%) with 31.3% lower cost [131]. Claude Code has `--max-turns` and `--max-budget-usd` for unattended runs [080]. Visible budgets are not enough alone: agents never referenced a 50,000-token budget in 14,000+ messages in one study [136].

**Prompts can multiply reasoning.** "Explore multiple approaches" raised reasoning tokens 2.4-7.4x across six models at similar success, and "deep thinking" 1.6-2.2x [026]. Cutting a full spec to a bare user story raised spend 29.7% [027]. Raising the budget does not help a capability-limited agent [132].

## 5. Routing and subagents

**Route by turn type.** A trained static router cut SWE-bench API cost 53.1% ($25.66 against $54.73 for unrouted Opus) at comparable resolve rates [030]. Learned routers beat the best fixed model by 14.6% relative [033]. A frontier model prompted as the router picked the high tier for only 7 of 147 verified-high steps [030]. A proxy that kept tool-call turns on the strong model reported 45.8% savings on 125 requests [031]. Static routers fail out of distribution [032].

**Subagents trade tokens for clean context.** Anthropic says teams use significantly more tokens without giving a multiple, and one source cites about 7x [081][001]. Subagents spend against the same limits [072][080]. Use them for read-heavy exploration on a cheap model and cap concurrency [072][070]. In a coding contest, a blind parallel swarm scored 3 against 8 for a cost-aware one [132].

## 6. Limits, billing and plans

**Pricing is moving to token-metered.** Cursor moved Pro from 500 requests to $20 of usage at API rates because hard requests cost about 10x simple ones [015][016]. Copilot legacy billing counts prompts ($0.04 per extra request), not tokens [117]. Gemini CLI caps requests per day (250 free, 1,000-2,000 paid) [057]. Anthropic does not publish how subscription limits convert to tokens, so no firm tokens-per-week figure exists [010][009].

**Budget around P95.** Claude Code active users averaged $108 per month, but the median was $23 and P95 was $291 [054]. ChatGPT Work showed median about $53, mean about $309 and P90 about $1,154 [101]. Anthropic's "$13 per active day" average is not comparable across teams [010].

**Local models are not free.** Cached frontier API was cheaper per processed token than a self-hosted quantised cluster. On-prem saved 40.1% TCO only on shared GPUs ($2.83 per million) and cost 43.8% more dedicated ($11.87 per million). The local model also needed more fixes (fix-commit ratio 74.93% against 45.93%). It is one developer's case study [053].

## 7. Measure first

1. Read per-response cache fields and compute hit rate per caller [128][052].
2. Turn on the agent's own usage view (`/usage`, `/context`) and export OTel to attribute spend by model, subagent, skill and MCP server [002][004][080].
3. Remember dollar figures from client tools are list-price estimates, not bills [076][085].
4. Set per-developer budgets at the gateway; some return HTTP 402 on exhaustion [060].
5. Warn before a stale resumed session re-sends its whole context. One hook example estimates $1.14 for 182,340 tokens [074].

## 8. What the sources disagree on

- **Is compaction good?** Anthropic presents it as a core primitive [006]. Two measurements show LLM summaries adding cost with no quality gain over masking [130][133]. One source says compaction destroys the cache [112]; another says it reuses a warm prefix [055].
- **Auto-compact thresholds** range from window minus 13,000 tokens [007] to 80-90% [108][112] to "50% is better" [034]. No source tested them head to head.
- **Does a visible budget help?** Yes in [025] and [131], no in [136].
- **Input or output drives cost?** Input in most sources. At a 96.3% hit rate, output was 2.7% of tokens but 51.1% of dollars [027], and one source says output dominates [114]. The winner depends on cache hit and price schedule.
- **Savings from routing and configuration** are quoted at 18.4%, 45.8%, 53.1%, about 60% and up to 80%, and the high figures are marketing [028][031][030][034][062].
- **Codex context window:** 272K default, 400K cap, 1M advertised, about 258K usable depending on the source [035][111][107].

## 9. Claims to discount

- "80% cut, $8 to under $1.50" for Aider [037], "50-80%" Claude Code playbook [056] and "40-60%" routing [014]: no method or baseline.
- 10x-100x lower token cost and "5-10x" routing savings [063][013]: product pages, placeholder tables.
- MCP compression "96-99%" and a $21,000 per month projection [019][022]: self-reported and ignores caching.
- Success jumping from 72% to 94% with tool gating [021]: a projection, only token counts were measured.
- Anything labelled illustrative [124][008][129].

## 10. Open questions

1. What is the real cache hit rate and cost for subagent-heavy Claude Code workflows? Docs and observation conflict on subagent TTL [052][081].
2. What do MCP schemas cost per turn under deferral and caching? Estimates run 8,000-55,000 and none model cache discounts [019][021].
3. When does compaction pay off, and at what window size? [005][034][112][007]
4. Do turn caps and budgets work on real interactive sessions rather than benchmarks? [025][131][136]
5. How much does routing save when 70-80% of turns are tool calls that must stay on the strong model? [031][029][032]
6. Can an adaptive condenser or router beat static ones? Nobody has built and tested one [130][133][026].

## Do this next

1. Pull one week of per-call cache fields and compute the hit rate per caller.
2. Find any session that switches model or effort mid-run, or any gateway that drops `cache_control`.
3. Count always-loaded tokens (tools, `CLAUDE.md`, skills) and remove what 16 of 23 tools never use.
4. Set `--max-turns` and a budget cap on every unattended run.
5. Try observation masking before any LLM summariser.

## Limits

- Codex contributed nothing here. Its usage limit hit before it wrote any source or note.
- Kiro read 43 documents and Claude read 86. Seven documents were unreadable and skipped (two papers behind paywalls or redirects and five blog or forum pages that returned almost no text) [042][043][113][118][121][123][125].
- Most numbers are vendor, blog or author self-reports, and several blogs are product marketing.
- Many pages are dated 2026 and name models I cannot confirm. Price and limit figures change monthly, so verify them against the vendor page before you act.
- Claude's learnings file was written from the notes without re-reading each one. I checked the numbers used above against the notes, but not against the original pages.
