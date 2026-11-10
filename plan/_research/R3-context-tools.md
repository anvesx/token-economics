# R3: Context management, tool-schema overhead, tool output and compression

Ids: R:nnn = research/ (API corpus), C:nnn = research-cli-agents/. Tags: [measured] controlled data with method; [self-reported] author or vendor numbers; [price-list] documented defaults; [illustrative] single synthetic example or estimate. Absent items are marked "not in corpus".

Bottom line: the evidence supports cheap mechanical controls (schema deferral, tool-output caps, masking above about 10 events, loop and budget limits, instruction-file caps). It does not support output compressors as a default: the one large measured study shows no saving or a loss [C:024].

## 1. Facts to build on

### Where the cost sits
- Harness base (system prompt plus tool definitions) 74.7% of billed cost; hidden thinking and residual 19.4%; tool outputs 3.3%; tool-call args 1.4%; retrieved files 0.8%; history 0.5%. Bill: cache creation 44.3%, cache reads 35.4%, output 10.4%. Compression ceiling about 5% [C:024, measured, 2,848 runs, 103 tasks].
- Counter-view: observations are about 84% of a SWE-agent turn [C:130, self-reported]; input is 94-98% of tokens [C:133, self-reported]. These are raw tokens, not billed cost.
- Claude Code fixed prefix 15,983-20,330 tokens vs 1,147-1,642 minimal; 24 vs 4 tool schemas; 5-30x cost per success [C:026, measured].

### Tool schemas and MCP
- GitHub MCP (93-94 tools) quoted at 8,000-12,000 [C:019], about 17,600 [C:022], about 42,000 [C:020], about 55,000 [C:107] tokens per turn; none model cache discounts. Four servers about 7,000 [C:019]; MCP tool 550-1,400 [C:108, illustrative].
- mcp-compressor: 17,600 down to 3,900 / 3,300 / 2,200 / 500 tokens with get_tool_schema and invoke_tool wrappers; quality claim has no numbers [C:022, self-reported]. Simulation of 120 tools: per-turn 47,312 to 2,368, cache hit 84% vs 22%; success and cost are projections; static pruning without recovery hurt success [C:021, illustrative]. 4-tool set 95% vs 71% tool-selection accuracy [C:020, product pitch].
- 23 schemas shown, 16 never called, 3 give 98% of calls; pruning -13.2% / -17.7% [C:028, self-reported].
- Tool search auto-on above 10% of context; guidance to defer above about 20 tools and 10-15 turns [C:019, price-list]. Codex defers by default since v0.142.2 [C:111]; tool_input_schema_max_bytes 5,000 [C:104].
- Adding or removing MCP tools invalidates the cache [C:055]. Token-efficient tool use: up to 70% output saving, average 14%, Claude 3.7 only [R:068, R:070 duplicate].

### Tool output size and filters
- Claude Code caps tool responses at 25,000 tokens; concise vs detailed format 72 vs 206 tokens [R:284, self-reported]. Codex tool_output_token_limit default 12,000 (examples 8,000/10,000, CI 6,000) [C:106, C:036, price-list]. Hook output cap 10,000 chars [C:090].
- Failing npm test about 15,000 tokens where about 50 needed [C:128, illustrative].
- RTK cost -2.7% (CI -5.6 to -0.1; holdout -2.3%, not significant). RTK-ML cut 38.4% of tool-output tokens, cost +6.8%. Headroom +48.4% (+67% on Opus 4.8). Token reduction vs cost r=0.154. Compression delayed first edit by 0.94 turns and raised repeated searches. Codex: Headroom -12.49% cost, wall time +238% [C:024, measured].
- RTK alone raised cost in 12 of 30 cells [C:028]. Go study: cost -59%, patch apply 27/40 to 15/40; byte-exact grounding restored apply 31% to 83%. Pytest filter 31.9% savings at 56.1% recall, fixed to 15.3% at 99.2%. Compressed search piped to shell counting gave silently wrong answers [C:024]. Headroom "60-95%" is vendor, no method [C:060].

### Masking vs condensers
- Masking window M=10: Gemini 2.5 Flash $0.41 to $0.18 (-56.1%); LLM-Summary $0.24. Qwen3-Coder solve rate: Masking 54.8%, Summary 53.8%, Raw 53.4%. Summary cost up to 7.2% of instance; summaries lengthen runs (52 vs 44 turns). Window needs re-tuning per scaffold [C:130, self-reported, SE only].
- DiscoveryBench, 60 tasks, 8 condensers, baseline about 75,147 tokens, 9.0 events: only masking saved (+8.6%); LLM condensers cost more (-23.6% to -93.9%); quality not significantly different. Masking +33.5% on long tasks, -45% to -149% at 7 events or fewer [C:133, self-reported].
- OpenHands condensation up to 2x lower per-turn cost, solve 54% vs 53%; thresholds not stated [C:122].

### Clearing, compaction, memory
- Defaults: clear_tool_uses_20250919 trigger 100,000, keep 3; compact_20260112 trigger 150,000 (minimum 50,000); thinking keep 1 turn [C:065, C:066, R:271, price-list]. Production guidance: trigger 30-40k, keep 5, clear_at_least 3,000-5,000 [C:066].
- Clearing invalidates the cached prefix; keeping thinking preserves it; cleared content is unrecoverable [C:065].
- Cookbook, one synthetic task: baseline peak 335,279 (file reads 96.3%); clearing peak 173,137; compaction peak 169,164 with a 2,783-token summary; high-level facts kept 3/3, obscure specifics 0/3; memory run peak 172,623 vs 333,977. No dollars, single run [C:006, R:271, illustrative]. Context editing -84% tokens in a 100-turn test, baseline undescribed [R:268, self-reported].
- One compaction at 125,000 tokens costs $0.40, about 21 cached turns [C:112, secondary]. Grok: 3 compactions cost 1.4/1.7/3.3 cents, removed 600-900 tokens, next turn missed cache [R:224, self-reported]. Multiple Codex compactions reduce accuracy; every one is an LLM call [C:106]. Thrashing when one output refills context [C:089].
- Thresholds: Gemini CLI about 50%, Claude Code about 89%, Codex about 90% [C:112]; Claude Code = window - min(max output, 20,000) - 13,000 [C:007, estimate].
- Cache invalidators: model switch, effort change, fast-mode toggle, MCP tool change, compaction. Forks inherit the parent prefix; subagents do not [C:055]. Blanket 1h TTL made the bill 8.6% worse [C:052, measured]. Timestamp at prompt top: reuse 87% to 3% [R:224]. Byte-stable tools, effort, model [R:204].
- Memory: first 200 lines or 25 KB of MEMORY.md [R:269]; search plus wiki saved about 20,000 tokens/question over 25 questions [R:269, self-reported]. Dreaming cost not in corpus.

### Prompt compression, RAG
- LLMLingua: GSM8K 2,366 to 117 tokens at 77.33 EM vs 78.85; BBH -8.5 to -13.2 EM at higher ratios; GPT-3.5/Claude-v1.3 [R:079]. LLMLingua-2: 3-6x faster, 2-5x compression, MeetingBank-trained [R:081]. Agent traces: not in corpus.
- SELF-ROUTE 38.39% of LC tokens at 46.41 vs 49.70 (Gemini); 61.40% at 48.89 vs 48.67 (GPT-4O) [R:117]. OP-RAG 44.43 F1 at 16K vs 34.32 at 128K [R:118]. LC wins at 32k, RAG at 128k by 3.68%; LC wins reasoning [R:119]. Agents with grep beat SOTA by 17.3% [C:046]. All self-reported, 2024-era models.

### Context acquisition, repeats
- Agents touched no gold file in 35.2% (OpenAI) and 27.2-29.3% (Codex) of samples; miss causing failure not shown [C:045].
- Repeated retrieval, similar scripts, unchanged test reruns: 79-98% of tasks, 6.86-22.75% of cost. Seven short principles cut cost 7.88-41.73% in 6 of 8 settings (one -1.5 pp Pass@1). Code-graph tool +28.14% cost [R:059, self-reported, authors own the winner]. Failed runs 17% of tasks, 32% of spend [C:028]. Redundant verification 1.48x / 2.36x / 18.25x [C:026].

### Instruction files, skills, subagents
- CLAUDE.md under 200 lines [C:077]; AGENTS.md 32 KiB with silent truncation [C:036]. Skill descriptions load each turn (1,536-char cap); invoked skills re-attach after compaction at 5,000 each, 25,000 total [C:075, C:079]. Codex skills 2% of window, cap 10,000 [C:104]. Stale skills re-billed each prefix [C:028].
- Subagent reports under 30 lines [C:035]; "1,000-2,000 tokens" returned [R:084, qualitative]. maxTurns, effort, omitClaudeMd exist [C:072]. Agent teams "significantly more" tokens, no multiple [C:081].

### Reasoning, output, loops
- "Multiple approaches" +2.4-7.4x reasoning tokens at similar success; "deep thinking" 1.6-2.2x [C:026, measured]. Effort does not cap tokens; max_tokens does [C:073, C:093]. OpenAI: reserve 25,000 tokens [R:197].
- "Be concise" -48.70% output, -22.67% cost, -27.69% accuracy for GPT-3.5 math [R:104]. NoWait -27 to -51%, only -13 to -16% on Qwen3-32B, needs logits [R:091]. CoThink -21.1% [R:135]. L1 needs training [R:095]. Hosted-API support: not in corpus.
- Turn cap at p75 with reminder: Sonnet -23.62% cost, solve 75% to 71%; at p25 without reminders solve fell to 24% [C:025, caching off]. Budget Tracker -31.3% cost at equal accuracy [C:131]. Agents ignored budgets across 14,000+ messages; request_more_budget called 0 times [C:136]. Post-success polishing wastes tokens [C:134].

## 2. Interventions ranked by evidence

1. Defer or prune schemas with a recovery path. Pays above about 20 tools and 10-15 turns [C:019]. Loses without a recovery path [C:021] or if tool lists change mid-session [C:055]. Billed saving: not in corpus.
2. Cap tool output (25,000 / 12,000 / 6,000) with pagination. Pays on outliers (610 KB spec reread [C:036]). Loses if it truncates tracebacks or anchors [C:024].
3. Anti-repetition rules. Pays 7.88-41.73% in 6 of 8 settings [R:059]. Loses: one Pass@1 drop; needs local replication.
4. External loop, turn and spend limits. Pays on failed runs (32% of spend [C:028]). Loses at p25 caps [C:025] and past the capability wall [C:132].
5. Observation masking. Pays above about 10 events (-56.1% [C:130]). Loses at 7 events or fewer [C:133]. Apply only at a trigger (history edits break the cache).
6. Server-side clearing. Pays when re-fetchable results dominate (96.3% in cookbook [R:271]) and the yield exceeds the cache re-write. Loses if it fires often with small yield [C:066].
7. Compaction. Pays only near the window with a summary far below history size. Loses on short sessions [R:224], at $0.40 per 125K [C:112], and on specifics [R:271].
8. Instruction and skill caps. Cheap; saving figure not in corpus.
9. Effort and thinking caps by task class. Thinking plus residual is 19.4% [C:024]. Per-step saving only illustrative [C:073]. Loses on hard tasks.
10. Subagent isolation. Pays when exploration output is large and the return is small. Loses: no cache sharing [C:055]; model-mix shift +8.30% / +12.19% [R:059]. Net saving: not in corpus.
11. Memory tool. Pays across sessions [R:271, R:269]; single runs only.
12. Output compressors. Do not default. Range -2.7% to +48.4% [C:024]; sign flips by harness. Pays only after a per-workload A/B with recall check.
13. LLMLingua-family on agent context. Untested in corpus.
14. RAG/SELF-ROUTE. Document QA only; pays beyond 32k-128k for lookups [R:117, R:119]; loses on comparison and reasoning.
15. Output-length tricks. Only "be concise" works on hosted APIs; test on math [R:104].

## 3. Context guard: outside vs inside the harness

Proxy or gateway:
- Can: set max_tokens; strip or inject cache_control (LiteLLM cache_control_injection_points [C:060]); flag volatile prefix content [R:224]; track per-caller cache-hit rate and miss cause [R:204, C:055]; enforce budgets and fallbacks (budget_fallbacks [C:060]); rate-based loop breaker [C:062]; cap tool-result size before forwarding; defer MCP tools (mcp_tool_search_enabled, mcp-compressor wrapper [C:060, C:022]); add context_management to requests if the client allows [C:065].
- Cannot: edit history without breaking the exact-prefix cache; see hidden thinking content [C:026]. A gateway credential bills at API rates; no non-Claude models through it [C:088].

Hook (Claude Code and similar):
- Can: PostToolUse updatedToolOutput to filter or cap output; PreToolUse updatedInput; PreCompact block or add summary instructions; SessionStart cache-expiry and cost fields; model-switch block [C:074, C:090]. Command hooks cost no model tokens.

Needs the harness: transcript masking with a tuned window [C:130]; turn caps with reminders [C:025]; tool-pruning re-audit [C:028]; forks [C:055]; memory backend [R:268]; subagent settings [C:072]; skill loading [C:079]; auto-compact threshold [C:034, C:106].

## 4. Rules the system MUST enforce

1. No volatile values at prompt top; tools, order, model and effort fixed mid-session. Evidence: 87% to 3% reuse [R:224]; [C:055, R:204].
2. Defer tool schemas above about 20 tools or 10% of context, with a lookup path [C:019, C:021, C:022].
3. Cap every tool result (25,000 interactive, 6,000-12,000 batch); never truncate tracebacks, test failures or edit anchors [R:284, C:106, C:024].
4. No output compressor live without a per-workload A/B on cost per successful run and at least 99% marker recall [C:024].
5. Never pipe compressed output into shell counting or parsing [C:024].
6. History edits only at a trigger; clearing starts at trigger 30-40k, keep 5, clear_at_least 3,000-5,000, then tune per scaffold [C:066, C:130].
7. No condensation below about 10 events [C:133].
8. Prefer masking over LLM summaries for tool observations [C:130, C:133].
9. Compact only near the window; count compactions; recommend restart at 3 [R:224, C:112, C:106].
10. Protect non-re-fetchable results with exclude_tools; persist state to a handoff or memory file before clearing [C:067, C:035].
11. Hard max_tokens on every call; per-task turn cap with reminder starting at p75, never p25 [C:025].
12. Spend limits live outside the model [C:136].
13. Rate-based loop breaker for repeated reads, unchanged test reruns and repeated failures [R:059, C:028, C:062].
14. Cap instruction files (CLAUDE.md 200 lines; AGENTS.md 32 KiB); retire stale skills [C:077, C:036, C:028].
15. Set cache TTL from measured reuse gaps, not blanket 1h [C:052].
16. No "multiple approaches" or "think deeply" wording by default [C:026].
17. Log tokens by category per task; judge on billed cost per success, not token reduction [C:024].

## 5. Conflicts

- Compressors: C:024 (Headroom +48.4%, RTK about -2.7%) and C:028 (RTK worse in 12 of 30 cells) vs C:060 (60-95%, vendor) and C:107 (45,000 to 12,000/turn, self-reported). Headroom -12.49% on Codex [C:024].
- Masking vs summaries: C:130, C:133 vs C:122 (up to 2x, no threshold).
- Compaction and cache: C:112 says it destroys the cache; C:055 says it reuses the parent prefix at a 5-minute TTL; R:224 shows a miss and net loss.
- Compaction threshold: 50% [C:112] vs about 90% [C:106] vs window minus 33,000 [C:007]; no head-to-head.
- Cost share: tool outputs 3.3% [C:024] vs observations 84% [C:130]. Different metrics; use billed cost.
- Input vs output driver: C:023 vs C:027.
- Budget visibility: helps [C:025, C:131]; ignored [C:136].
- MCP overhead: 8,000 to 55,000 tokens for one server [C:019, C:022, C:020, C:107].
- RAG vs long context vs grep: R:117, R:118 vs R:119 vs C:046; mostly 2024-era models.
- NoWait 27-51% vs 13-16% on Qwen3-32B [R:091]; "up to 70%" vs 14% average [R:068].
- Subagents: forks save [C:055]; teams cost more [C:081]; model-mix shift raised cost [R:059]; the 50-70% orchestrator claim is unsourced [C:073].

## 6. Experiments required

1. Replicate C:024 on our harnesses (RTK, Headroom, none; 3 repeats; cache reset between arms).
2. Masking window (M=5, 10, 20) and trigger (30k, 60k, 100k) sweep per scaffold, billed cost with caching on.
3. Clearing yield: clear_at_least 3k, 5k, 10k vs compaction at 150K; count cache re-writes.
4. Compaction break-even at 50K, 100K, 200K contexts; accuracy after 1, 2, 3 compactions.
5. Tool deferral A/B at about 20, 50, 90 tools: billed cost, selection accuracy, extra lookup turns.
6. Output cap sweep (6k, 12k, 25k): re-read loops and first-edit turn.
7. Local replication of R:059 principles; track Pass@1.
8. Turn cap p75 vs p50 with reminder on our models.
9. LLMLingua-2 on agent tool output (not in corpus): cost, success, byte-exact failures.
10. Effort and thinking cap sweep by task class on hosted models.
11. Proxy-only guard prototype (cache-hit monitor, max_tokens, loop breaker, output cap): measured saving with no harness change.
12. Subagent isolation net cost, fork vs subagent cache behaviour.
