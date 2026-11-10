# hermes-engine token-leak taxonomy

Sources (all in repo/): token-leak-categories.md (TLC), leak-measurability-update.md (LMU), leaderboard/lib/categories.json, plugins/token-metrics/scripts/leak_categories.py. Only what those files state. "n/g" = not given in the files.

Global facts that apply to every row:
- Per-call token counts come from transcript `usage` and are exact (CLAUDE.md). Size of individual items (tool results, prompts, injected text) is estimated in chars per token (2.37 for the Opus 4.7 tokenizer, 3.10 before; LMU says tool definitions use 4 chars/token). So "Measured" in the repo means detected from transcripts; dollar cost of an item is an estimate.
- A leaked item is charged at cache-read price on every later call that re-reads it, until the next compaction.
- Where two detectors in one row flag the same tool result, it counts once at the larger cost. Costs overlap across rows and do not sum to total.
- "(review)" = spend to look at, not all waste. Marked R below.
- Snapshot: 163 sessions, 2026-09-01 to 2026-10-02, API-equivalent spend $1,703.41. Cost column gives Est. cost for the 15 rows TLC reports (+48 and 49 from LMU).
- The 50 numbers are fixed; the report re-sorts by cost each run. Groups: 11.

## 1. The 50 curated categories (default report)

Columns: # and name (group) | definition | measure (canvas rows in brackets) | status | cause / fix stated | tools or techniques named. Status: M = measured from transcripts, M-R = measured, spend to review.

| # name (group) | definition | how measured | status | cause / fix per repo | tools/techniques named |
|---|---|---|---|---|---|
| 1 Heavy starting context (Starting context and setup) | First call already carries a large prompt (system prompt, tools, memory, CLAUDE.md), repeated every call | #1: first-request context above 10k tokens, re-read on every call. $430.19, 25.3% | M | $248 of it is never-called MCP tool defs (see 48). "Wrong working directory may explain more of 1" (unconfirmed) | n/g |
| 2 Cache-write premium (Prompt cache) | Extra paid for cache writes over normal input price | A37. $338.65, 19.9% | M-R | n/g. Pricing: 5m write 1.25x input, 1h write 2x (CLAUDE.md) | n/g |
| 3 Cold cache at session and agent start (Prompt cache) | First cache write of each session and helper agent | A22. $254.93, 15.0% | M-R | n/g | n/g |
| 4 Cache expired after a break (Prompt cache) | Break long enough for the cache to expire, whole context rewritten | #3a: rewrites of #3 after a gap of an hour, or past `--ttl`; not model switches or prefix changes. `--ttl` 5m for API-key/usage-credit users, default 1h for subscriptions. $228.45, 13.4% | M | n/g | `--ttl` |
| 5 Many agents (Agents) | Heavy use of subagents, each with own context and calls; "not always waste" | #4: helper-agent call count and share of session cost. $173.72, 10.2% | M-R | n/g | n/g |
| 6 Long history replay (Conversation history) | Calls carrying more than 100k tokens of conversation history | A1. $179.43, 10.5% | M-R | n/g | n/g |
| 7 Interrupted turns (Retries and rework) | Turns stopped before finishing, work then redone | A134 (regeneration after partially completed responses). $160.66, 9.4% | M | n/g | n/g |
| 8 Sessions that never end (Conversation history) | New task in an old session carrying all the old context | #2: new task (tag or 30+ min gap) still carrying 20k+ tokens of prior context; compaction count. $123.82, 7.3% | M | n/g | n/g |
| 9 No clear direction (Exploration and file reading) | Long exploration before any change, usually because task or target files unclear up front | #5: more than 15 reads/searches before the first edit. $90.81, 5.3% | M | Unclear task/target files | n/g |
| 10 Restarting too often (Conversation history) | New session soon after the last, rebuilding same context | A10. $87.61, 5.1% | M | n/g | n/g |
| 11 Stale tool results carried forward (Conversation history) | Tool results still re-read 30+ calls later | A5. $67.47, 4.0% | M | n/g | n/g |
| 12 Bigger model than needed (Model and output) | Opus/Fable on simple tasks and helper agents (Opus where Sonnet/Haiku would do) | #6: top-tier model on simple task categories and helper agents; note shows share of main-session spend on Opus/Fable. $57.41, 3.4% | M (weak; see Open questions) | Mostly helper agents doing searches/simple tasks; people on higher plans never switch to a cheaper model | n/g |
| 13 Fork context duplication (Agents) | Helper agents start with parent's full context (160k+) | #4a (=A121): helper agent whose first call is above 50k tokens; excess re-read on each of its calls. $34.58, 2.0% | M | Forked subagents inherit full parent context | n/g |
| 14 Large tool-call arguments (Tool and terminal output) | Tool calls with 1k+ tokens of arguments (e.g. long plans) | A66. $28.42, 1.7% | M | n/g | n/g |
| 15 Agent startup cost (Agents) | Startup call of every helper agent | A125 (repeated agent startup instructions) | M-R | n/g | n/g |
| 16 Model switch rewrote the cache (Prompt cache) | New model writes context from scratch after a switch | A30 (switch with no reusable cache on receiving model) | M | n/g | n/g |
| 17 Old replies replayed (Conversation history) | Earlier assistant text re-read on every later call | A6 | M-R | n/g | n/g |
| 18 Clarification loops (Retries and rework) | Turns spent asking clarifying questions | A131 (ambiguous prompts) | M-R | Ambiguous prompts | n/g |
| 19 Screenshot accumulation (Images and browser) | Screenshots stay in context until compaction | #14: image blocks in tool results, sized from pixels, re-read after first use until compaction | M | n/g | Figma, Chrome, simulator named as sources |
| 20 Visual iteration loops (Images and browser) | Edit -> screenshot -> tweak cycles in Figma-to-code or simulator work | #21: more than 3 edit-then-screenshot cycles in one task | M | n/g | Figma, simulator |
| 21 Cache not reused (Prompt cache) | Cache writes never read back, uncached calls, prefixes too short to cache | A35 (writes never reused), A21 (missing prompt caching), A24 (prefix below eligibility thresholds); thresholds n/g | M | n/g | n/g |
| 22 Correction churn (Retries and rework) | Work in turns starting "no", "that's wrong", "revert", "not like that" | #20: work done in turns whose prompt matches the hook's correction pattern (`CORRECTION_RE`; regex text n/g in these files) | M | n/g | hook `[category]` tag / `rate N` command |
| 23 Agents racing the cache (Prompt cache) | Helper agents writing the same cache at same moment | A34 (concurrent requests before cache creation completes) | M | n/g | n/g |
| 24 Too much tool output (Tool and terminal output) | Single non-shell tool results large enough to bloat context | #7: non-shell results above 4k tokens (duplicate reads and dependency hits go to 43 and 41) | M | n/g | n/g |
| 25 Noisy and repeated terminal output (Tool and terminal output) | Shell output above 4k tokens, repeated log lines, tracebacks, lint output | #17: Bash results above 4k tokens; A87 repeated runtime log lines; A82 repeated failure tracebacks; A84 repeated linter diagnostics | M | Build/install output dumped in full | `xcodebuild`, `npm install`, `pod install` |
| 26 Repeated tasks across sessions (Conversation history) | Same first request in earlier session of the project | #15: first prompt overlapping 60%+ (by word) with an earlier session in same project | M-R | n/g | n/g |
| 27 Failed, retried and polling calls (Retries and rework) | Errors/denials, same failing call repeated, same call returning same result | #16: `is_error` results classified denied / schema error / wrong id, error text plus wasted call output; #9: same tool input failing 3+ times; A136 repeated unchanged-state polling (A135 invalid structured outputs is part of #16) | M | Schema errors, permission denials, wrong IDs, "common with MCP tools" | n/g |
| 28 Repeated screenshots (Images and browser) | Back-to-back, unchanged, or retaken-after-failed-action screenshots | A114 (excessive during browser navigation), A112 (repeated unchanged), A120 (browser retries reloading same visual context) | M | n/g | n/g |
| 29 Progress narration (Model and output) | More than 50 tokens of text around each tool call | A54 | M-R | n/g | n/g |
| 30 Whole-file reads (Exploration and file reading) | Unsliced reads of files above 5k tokens | A71 | M | n/g | n/g |
| 31 Duplicate reading across agents (Agents) | File read by a sibling agent, or re-read by parent after helper read it | #4b (=A122): file `Read` by helper after sibling already read it; A128 parent rereading worker-reviewed material | M | Parallel agents reading same files | n/g |
| 32 Agent coordination chatter (Agents) | Messages between agents | A126 | M | n/g | n/g |
| 33 Large images and PDFs (Images and browser) | Oversized images/PDFs read into context; documents read both as images and as text | A111 large images; A115 multi-page PDF (M-R); A116 same PDF as page images and via text extractor, later read charged; A117 same doc as images and via OCR | M | n/g | `pdftotext`, `pypdf`, `tesseract`, `ocrmypdf` |
| 34 Broad or unbounded searches (Exploration and file reading) | Searches returning 100+ lines or with no path/type limit | A73, A79 (searching without path or symbol boundaries) | M | n/g | n/g |
| 35 Bloated JSON and query results (Tool and terminal output) | Large JSON/DB results, results mostly keys and wrappers | A98 large JSON with unused fields, A99 DB rows/columns not needed, A100 repetitive metadata/serialization wrappers; thresholds n/g | M | n/g | n/g |
| 36 Wordy and repeated output (Model and output) | Whole-file rewrites, restating request, repeated explanations/code, truncated replies | #8: full-file `Write` on files already read, output share of spend; A52 repeating user question; A53 repeating established explanations; A58 reprinting generated artifacts; A60 truncated answers requiring regeneration | M | Output tokens on long replies or whole-file rewrites where an edit would do | n/g |
| 37 Web pages and search results (Web research) | Full pages, attached documents, too many results, repeated fetches/passages, duplicate sources | A101 full pages vs passages; A109 entire docs attached for narrow questions (M-R); A103 excessive search-result counts; A105 repeated fetch of unchanged pages; A107 overlapping retrieval chunks; A110 repeated retrieval after losing source refs; A104 result 50%+ same (8-word shingles) as an earlier result from another URL or query | M | n/g | 8-word shingles |
| 38 Copied history (Conversation history) | Background pasted again, chat transcripts pasted, forked conversations | A7 repeatedly pasted background, A8 full transcripts copied between chats, A9 forks duplicating history; thresholds n/g | M | n/g | n/g |
| 39 Compaction cost (Conversation history) | Writing the summary and re-reading after it | #19: summary size plus cache rewrites right after each compaction (summary call's input is not in transcripts) | M (partial) | n/g | n/g |
| 40 Git and GitHub output (Tool and terminal output) | Large diffs, lockfile diffs, verbose logs, repeated status, PR/issue histories | A91 large diffs, A92 generated/lockfile diffs, A93 verbose commit metadata, A94 repeated working-tree status, A95 full PR discussions, A96 full issue histories | M | n/g | n/g |
| 41 Dependency, vendor and generated files (Exploration and file reading) | Reads/search hits in `node_modules`, build output, lockfiles, generated code | A76 dependency/vendor source, A77 generated files | M | n/g | `node_modules` |
| 42 Verbose agent reports and briefs (Agents) | Agent results above 2.5k tokens, briefs above 1k | #4c (=A127): `Agent`/`Task` result above 2.5k tokens; A124 verbose task briefs | M | Large subagent results pulled into main context | n/g |
| 43 Repeated reads of unchanged files (Exploration and file reading) | Same file read again without an edit between | A72 | M | n/g | n/g |
| 44 Re-learning the codebase (Exploration and file reading) | Files that 2+ earlier sessions also explored before first edit | #22: files read before first edit that 2+ earlier sessions of the project also explored | M | What was learned was never saved | n/g |
| 45 High effort on trivial turns (Model and output) | Long thinking behind a short reply, no tool calls | #18: turn answered in one short reply with no tool calls, whose output tokens exceed the reply by 3k+ | M | n/g | n/g |
| 46 Tool discovery and skill loading (Starting context and setup) | Repeated tool-search calls, skill supporting-doc reads, invoked skill bodies above 3k tokens | A65 unnecessary tool discovery; A69 skill supporting-document reads (M-R); A68 invoked skill bodies above 3k tokens, beyond 1.5k charged until compaction. A68 30-day $0.06 | M | n/g | Skill tool |
| 47 Usage while idle (Retries and rework) | Tokens spent with no one at keyboard: background loops, monitors, scheduled wakeups | #10: turns that started without a typed prompt, counted only after the session's first hook record | M but needs hook data | Enable hooks | hooks |
| 48 MCP tool schema bloat (Starting context and setup) | Definitions of MCP tools never called, sent every call (part of 1) | #12: tokens of each MCP server's tools that the session or helpers never called, re-read on every main call until tools change; from `prompt_snapshot` attachments. $248.34, 14.6%. Median session ~91k tokens of MCP defs. Vercel server: 212 tools, ~140k tokens, $102.33 over 117 sessions | M, only sessions with snapshots (154 of 163) | "Disconnecting rarely used servers cuts every call" | `prompt_snapshot` |
| 49 Unused skills/plugins (Starting context and setup) | Listed skills and agent types never invoked (part of 1) | #13: skill/agent listing entries for skills never invoked (Skill tool or slash command) and agent types never used, carried until compaction. $15.60 | M, snapshot-era sessions only | n/g | `skill_listing`, `agent_listing_delta` |
| 50 No visibility (Observability) | Sessions with no hook data; categories, ratings, idle unknown | #11: share of sessions with hook data | Coverage gap, not a cost | Enable hooks | hooks |

48 per-server cost (LMU, tools never called, re-read each call): claude_ai_Vercel $102.33 (117 sessions); claude_ai_Gmail $24.53 (107); claude-in-chrome $22.11 (154); claude_ai_Slack $20.15 (110); firebase $13.06 (26); plugin_figma_figma $9.22 (120); claude_ai_Google_Calendar $8.40 (107); claude_ai_Google_Drive $7.98 (110).

## 2. Canvas rows measured but kept out of the 50 (shown with `--all` only)

Split cost already counted in rows 1 or 3, so adding them would double count. All "Measured".

| id name | definition | measure | cause / fix | tools |
|---|---|---|---|---|
| #3 Losing the cache | Cache expires so next call rewrites whole context at full write price | Large cache writes after a break, model switch or recorded prefix change (tools, system prompt, effort, org), else "context changed"; compaction rewrites go to #19 | n/g | n/g |
| A14 Overlapping directory-level instructions | Duplicate lines across project CLAUDE.md levels | Lines (30+ chars) repeated between two loaded project CLAUDE.md at different directory levels. $0.00 | n/g | n/g |
| A16 Duplicate rules across instruction layers | Same | Lines repeated between layers (project, local, user, memory). $0.00 | n/g | n/g |
| A17 Irrelevant always-loaded project guidance (R) | Large always-loaded guidance | Always-loaded project+local guidance above 2k tokens. $7.51; inside #1 | n/g | n/g |
| A18 Stale auto-memory entries | Memory index points to deleted files | Index lines linking to files that no longer exist, checked when report runs, not when the session ran. $0.00 | n/g | n/g |
| A19 Excessive few-shot examples | Too many examples in prompts | `<example>` blocks beyond 2 per tool description, system prompt or instruction file. $0.01 | n/g | n/g |
| A25 Timestamps in stable prefixes | Cache rewrite from a timestamp | Rewrite after system prompt changed only in its digits; part of #3. $0.00 | n/g | n/g |
| A26 Changing system-prompt content | Cache rewrite | Rewrite after recorded system prompt changed; part of #3. $0.00 | n/g | n/g |
| A27 Changing loaded tool definitions | Cache rewrite | Rewrite after recorded tool definitions changed (web tools added/removed counted here); part of #3. $1.25 | n/g | n/g |
| A29 Unstable tool serialization/order | Cache rewrite | Rewrite after same tool defs sent in different order; part of #3. $0.00 | n/g | n/g |
| A38 Thinking/effort change invalidating cache | Cache rewrite | Rewrite right after `/effort`; part of #3. $0.00 | n/g | `/effort` |
| A40 Cache isolation across providers/workspaces | Cache rewrite | Rewrite after organization (workspace) switch; provider switches not recorded; part of #3. $0.00 | n/g | `credential_org` attachment |
| A45 Replanning after every minor update | Replanning | "Measured" but never triggered | n/g | n/g |
| A70 Verbose plugin or hook context injection | Large injected hook/MCP-instruction text | MCP server instructions and hook-injected context above 300 tokens per block. $0.42 | n/g | `mcp_instructions_delta`, `hook_*` |
| A138 Scheduled tasks repeating unchanged analysis | Re-running identical analysis | Session whose first request matches an earlier one exactly and whose tool results are 80%+ unchanged. $0.00 | n/g | n/g |

LMU: $0.00 means nothing found in the data, "not that the detector is broken"; a synthetic session triggered every new detector except A19 and A27. Counts: 77 A rows measured, 3 share a core row's measure (A121, A122, A127), 29 unmeasurable.

## 3. Proposed, not built (TLC "Still proposed")

| name | definition | proposed signal | status | fix |
|---|---|---|---|---|
| Wrong working directory | Session started from `~` so searches span home dir | cwd = home dir plus broad `find`/`grep` | Proposed, unbuilt | n/g |
| Large pastes | Logs/code pasted into prompt | User message token size | Proposed | n/g |
| Figma over-fetching | `get_design_context` on large parent frames not child nodes | Node size and repeated calls on same file | Proposed | Use child nodes (implied) |
| Abandoned sessions | Spend ending with no edits, commits or deploys | Sessions with zero write actions | Proposed | n/g |

## 4. Canvas rows the repo marks unmeasurable (29), with reason and its possible route (LMU)

| id name | reason (per repo) | possible route (per repo) |
|---|---|---|
| A3 Obsolete requirements retained in context | Needs labelled review of what was relevant | Opt-in LLM-judge pass over a sample of sessions, reported as estimates |
| A4 Abandoned approaches retained | same | same |
| A20 Conflicting instructions causing corrective turns | same (all corrections counted in row 22) | same |
| A44 Repeated reasoning over unchanged evidence | same | same |
| A46 Generating unnecessary alternative approaches | same | same |
| A47 Repeated self-critique cycles | same | same |
| A48 Model handoffs requiring context reconstruction | same (cache rewrite counted in A30) | same |
| A55 Excessive examples | same | same |
| A56 Multiple unsolicited solution variants | same | same |
| A59 Duplicating information across output formats | same | same |
| A102 Navigation, footer, website boilerplate | same | same |
| A108 Irrelevant retrieved passages | same | same |
| A113 Full-screen screenshots for small regions | same | same |
| A119 Large image batches with irrelevant images | same | same |
| A129 Repeated review and revision rounds | same | same |
| A130 Agents continuing after work complete | same | same |
| A132 Missing acceptance criteria causing rework | same | same |
| A28 Editing earlier conversation messages | Needs exact request body (cache_control breakpoints, edited messages); transcripts don't record it | Opt-in local logging proxy via `ANTHROPIC_BASE_URL` |
| A31 Cache breakpoints on changing content | same | same |
| A32 Stable content outside cached prefixes | same | same |
| A33 Cache breakpoint lookback limits | same | same |
| A36 Repeated cache warmup requests | Model calls not recorded in transcripts | Claude Code OpenTelemetry `api_request` events |
| A137 Model-powered hooks firing excessively | same | same |
| A140 Background session-analysis model calls | same | same |
| A42 Excessive extended-thinking generation | Needs matched runs with independent acceptance checks | Headless `claude -p` benchmark |
| A49 Switching models then duplicate task execution | same | same |
| A50 Tokenizer differences between model versions | Needs same payload counted on both models | `count_tokens` on both models |
| A39 Tool-choice or web-tool config changes | Settings not recorded (`tool_choice`) | Logging proxy |
| A43 Replayed thinking blocks where preserved | Transcripts record thinking blocks but not whether later requests kept them (model dependent) | Logging proxy |

## Things the repo claims without evidence

- Row 1 cause: "Wrong working directory may explain more of 1" (TLC "Where to start"); no data given.
- "Mobile/Figma sessions (BIT-landers-nsf-mobile) appear at the top of several leak rows" and Figma over-fetching suggestion: no figures given.
- "Disconnecting rarely used servers cuts every call": implied by the cost model; no before/after measurement.
- Core leak descriptions of causes (ambiguous task, forks inheriting parent context, Opus where Sonnet/Haiku would do) are stated as fact; no experiment is cited.
- Row 12's premise ("people on higher plans never switch to a cheaper model") is stated as the real problem, but the repo says it has no good measure of it.
- Thresholds (10k, 20k, 15 reads, 4k, 5k, 1k, 2.5k, 100 lines, 60%, 50%, 80%, 3k, 300 tokens, 160k+) are given as detection rules with no rationale or validation.
- Snapshot numbers come from one team's 163 sessions over one month; no generality claimed or tested.
- Many rows are named leaks ("waste") but the repo itself says only that they are spend to look at for R rows; no row's saving from a fix is measured.

## Anything the repo itself says is unmeasurable or approximate

- Item sizes are estimated: chars-per-token per session/model (2.37 for the Opus 4.7 tokenizer, 3.10 before), tool definitions at 4 chars/token, images from pixel dimensions. Only per-call usage is exact.
- Costs overlap across rows and do not add up to total; a leak item is charged at cache-read price per later re-read until next compaction.
- Rows marked "spend to review" (R): 2, 3, 5, 6, 15, 17, 18, 26, 29 (also A17, A69, A109, A115 inside other rows).
- Row 12 has "no good measure yet"; the share of main-session spend on Opus/Fable is a first signal only.
- Row 39: the summary call's input is not in transcripts, so compaction cost is partial.
- Rows 48 and 49 only cover sessions from Claude Code versions recording prompt snapshots and skill listings (154 of 163); older sessions skipped (counted inside row 1).
- Row 47 needs hook data; only prompts after the session's first hook record count. Row 50 is a coverage gap, not a cost.
- A18 checks file existence when the report runs, not when the session ran.
- A40 cannot detect provider switches (not recorded).
- Costs are API-equivalent list prices (`PRICES`); not actual billed spend.
- 29 canvas rows unmeasurable (section 4), "shown with the reason instead of $0.00". Proposed routes (LLM-judge sampling, logging proxy, OTel, benchmarks) are not built.
- A $0.00 result means nothing found in the data.
- Data window cut: sessions cut by `--days`/`--since` are skipped by cross-session detectors; only calls inside the window are charged.
- `--units tokens` mode: cache detectors count tokens that missed the cache (cache misses add no tokens, so rows 2, 3, 4, 16, 21, 23 are "events", not leaks), and row 12 is reported as not applicable.
