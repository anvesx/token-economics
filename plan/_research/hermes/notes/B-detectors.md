# B. hermes-engine detectors: how each leak is detected and measured

Source (read fully): `plugins/token-metrics/scripts/leak_report.py` (1132 lines) and `leak_extra.py` (677 lines).
Gateway column: **G** = runs from API request/response alone; **C** = needs CLI transcript/hook/attachment data; **B** = both useful (G for the core signal, C for attribution).
"Carry" = `Session.carry(t, tokens)`: tokens x sum of cache-read price of every later main call until next compaction (see Cost model).

Count: 26 core leak ids (`LEAKS` 1-26) + 77 additional "A rows" with their own detector (80 `ADDITIONAL` rows with reason `None`, minus 3 aliased by `SAME_AS`) = **103 detectors**. 29 more A rows are declared unmeasurable; 10 core/A ids are shared (see end).

## 1. Input fields the code reads

Transcript = `~/.claude/projects/**/*.jsonl`, one JSON entry per line. Entry-level: `timestamp`, `sessionId`, `uuid`, `type` (`assistant|user|attachment|system`), `subtype=="compact_boundary"`, `isCompactSummary`, `isSidechain`, `agentId`, `isMeta`, `sourceToolUseID`, `rendered`, `attachment{}`. Helper-agent entries: `isSidechain` true OR path contains "subagent" OR file name starts `agent-`.
`message`: `id` (dedup of streamed chunks: one call per message id, last usage wins), `model` (skip `"<synthetic>"`), `content[]`, `stop_reason` (`max_tokens` used), `usage`.
`usage`: `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `output_tokens`, `cache_creation{ephemeral_5m_input_tokens, ephemeral_1h_input_tokens}`.
Per call: `ctx = input + cache_creation + cache_read` (context size). `cost = (in*pi + cw*pi*wmult + cr*pr + out*po)/1e6`.
Content blocks: `tool_use{id,name,input}`, `tool_result{tool_use_id, content, is_error}`, `text`, `thinking{thinking}`, `image{source.data base64}`, `document`.
User prompts: text of non-meta user entries; "interrupted by user" in text -> interrupt.
Attachment types read: `prompt_snapshot{tools[], systemPrompt}`, `credential_org{organizationUuid}`, `skill_listing{content}`, `agent_listing_delta{addedLines}`, `instructions{files[{path,type(Project|Local|AutoMem),content}]}`, `mcp_instructions_delta{addedNames,addedBlocks}`, `hook_*`.
Tool names/inputs used: `Read{file_path,offset,limit}`, `Edit/MultiEdit/Write/NotebookEdit{file_path|notebook_path,content,new_string}`, `Grep/Glob/Bash/LS{command,path,glob,type,pattern}`, `Agent/Task{prompt,subagent_type,description}`, `Skill{skill}`, `TodoWrite/TaskCreate/TaskUpdate`, `ToolSearch/ListMcpResourcesTool`, `SendMessage`, `AskUserQuestion`, `WebFetch/WebSearch`, MCP names `mcp__<server>__<tool>`.
Hook events (`events.jsonl`, from `metrics_hook.py`): only `UserPromptSubmit` records (`ts`, `session_id`, `kind=="rating"` vs prompt) are read by leak_report (#10 and ratings). Slash `/effort` seen via `<command-name>/effort</command-name>` in prompt text.

## 2. Cost / pricing model

`PRICES` (in, out, cache-read, $/MTok), matched by version substring, longest id first (`PRICE_IDS`):
fable-5-1 (10,50,0.25); fable-5 (10,50,1.00); opus-5-5 (4,20,0.20); opus-5 (5,25,0.50); opus-4-8/4-7/4-6/4-5 (5,25,0.50); sonnet-5-5 and sonnet-5 (2,10,0.20); sonnet-4-6/4-5 (3,15,0.30); haiku-4-5 (1,5,0.10).
Unlisted version -> `FAMILY_PRICES` (fable->5-1, opus->5-5, sonnet->5-5, haiku->4-5); default sonnet.
`CHEAPER = PRICES["claude-sonnet-5-5"]` = counterfactual for leak 6.
Cache write: `WRITE_MULT = {ephemeral_5m: 1.25, ephemeral_1h: 2.0}` x input price. `write_mult()` blends by `usage.cache_creation` split; unsplit remainder uses default from `--ttl` (5m -> ttl_s 300, mult 1.25; 1h default -> ttl_s 3600, mult 2.0).
`--units tokens`: every price 1e6 (cost = tokens), write_mult 1, cache detectors report tokens via `cache_cost()`, leak 6 disabled.
Item-size estimation (no exact count available): `CHARS_PER_TOKEN = {"new": 2.37, "old": 3.10}`; `OLD_TOKENIZER` = claude-opus-4-6/4-5/4-1/4-2, sonnet-4, sonnet-3, haiku, claude-3; anything else "new". Doc header says 4 chars/token but code uses these.
Per-session calibration `_calibrate`: sample = text tool result with chars >= `CALIBRATE_CHARS`=8000, the only result between two consecutive calls of one stream on the same model, no prompt/attachment/compaction between; tokens = `ctx(next) - ctx(call) - out(call)`; ratio chars/tokens kept if in `CALIBRATE_RANGE`=(1.2, 6.0); model needs `CALIBRATE_MIN`=10 samples else default. This is a pure usage-delta method: gateway-doable.
Images: `image_tokens` = w*h/750 after scale `min(1, 1568/max(w,h), sqrt(1_150_000/(w*h)))`; reads PNG/JPEG headers; `IMAGE_DEFAULT`=1600 if unreadable.
Carry (the central cost formula): a leaked item of N tokens costs `N x sum(read_price of later main calls)` until next compaction (`comp_sorted`) or `until`. Cache-event detectors instead charge price difference (write premium `cw*(pi*wmult - pr)`, uncached `in*(pi-pr)`).
Session/task segmentation: `Session.tasks()` new task when prompt starts with `TAG_RE ^\s*\[([A-Za-z][\w-]*)\]` or idle gap >= `TASK_GAP_S`=1800s since last call. Compaction = `system/compact_boundary` entries, else `isCompactSummary` entries.
Gateway equivalents: session id, helper vs main and task boundaries are NOT in API traffic; a gateway must supply its own (conversation key, prefix hash, idle gap).

## 3. Constants (exact)

leak_report: START_BASELINE 10_000; CARRY_MIN 20_000; TASK_GAP_S 1800; EXPLORE_LIMIT 15; BIG_RESULT 4_000; BIG_KEEP 2_000; TRIVIAL_TEXT 300; THINK_BASELINE 1_000; THINK_LIMIT 3_000; VISUAL_LIMIT 3; FORK_MIN 50_000; REPORT_BIG 2_500; REPORT_KEEP 1_000; RELEARN_MIN 2; REPEAT_SIM 0.6; SIMPLE_CATEGORIES {docs, explain, question, rename, chore, commit}; TOP_TIER (opus, fable).
Regexes: `ERROR_TEXT` (error|failed|traceback|exception|exit code [1-9]|not found), `DENIED_RE` (doesn't want to proceed|permission|denied|rejected|not allowed|blocked), `SCHEMA_RE` (InputValidationError|invalid (input|param|argument|type)|required (parameter|property)|missing required|schema|unexpected (field|parameter|property)), `WRONG_ID_RE` (not found|no such|does not exist|unknown (id|tool)|404), `CORRECTION_RE` (^ no|nope|wrong|that's not|that is not|not what i|undo|revert|stop|don't|you (broke|missed|forgot|ignored)|i said|again), `DEP_DIRS` (node_modules, .venv, venv, dist, build, target, .next, vendor, __pycache__).
leak_extra: HISTORY_LIMIT 100_000; STALE_CALLS 30; PASTE_MIN 400; TRANSCRIPT_MIN 2_000; RESTART_GAP 3600; UNCACHED_MIN 10_000; CONCURRENT_S 10; PLAN_LIMIT 5; ECHO_SIM 0.7; NARRATION_KEEP 50; CODE_MIN 300; DISCOVERY_LIMIT 2; ARGS_BIG 1_000; WHOLE_FILE 5_000; SEARCH_LINES 100; BIG/KEEP 4_000/2_000; DUP_LINE_SHARE 0.5; SEARCH_RESULTS 10; IMAGE_BIG/KEEP 1_200/800; BRIEF_BIG 1_000; POLL_MIN 3; DUP_LINE_MIN 30; GUIDANCE_KEEP 2_000; EXAMPLE_KEEP 2; INJECT_KEEP 300; SKILL_BIG/KEEP 3_000/1_500; DUP_SOURCE 0.5; SHINGLE 8; UNCHANGED_SHARE 0.8. `min_cacheable(model)` = 1_024 if "sonnet" in model else 4_096 (code comment: verify vs docs).

## 4. Core detectors (leak_report.py `analyse` / `cross_session`)

Format: id name | inputs | rule | output | gateway | approximations.

**1 Heavy starting context** | first call `ctx`, first prompt tokens, `prefix_read[-1]` | `prefix = start_ctx - start_prompt` (real session start, even if cut by window); if `prefix > START_BASELINE`: cost = `(prefix - 10_000) * sum(read_price of all calls)` | USD (or tokens) + `_prefix_sizes` | **B**: prefix size = first request's input tokens minus user turn, gateway sees it directly; "session" must be inferred | start_prompt estimated by chars/token; assumes whole prefix is re-read every call.
**2 Sessions that never end** | task segmentation, `ctx` of first call per task | for each task after the first: `carried = first_call.ctx - prefix - task prompt_tokens`; if `carried > CARRY_MIN` (20_000): cost = carry(task start, carried, until task end) | USD per task; label "[category]" or "after 30 min gap" | **B**: ctx growth by request is gateway-visible; task boundary needs tag/gap (gap is gateway-computable) | task boundary heuristics (tag or 30 min).
**3 Losing the cache** (+ **3a** break-only part, 26) | per-call `cw`, `ctx`, `model`, timestamps, `prefix_events` | for call i>=1 with `cw > max(5_000, 0.5*ctx)`: `premium = cw*(pi*wmult - pr)/1e6`. Cause cascade: (a) a compaction between prev and this call -> goes to #19; (b) `model != prev.model` -> A30; (c) gap >= 3600s -> 3a "break of N min"; (d) gap >= `ttl_s` -> 3a "past cache lifetime"; (e) else look up recorded prefix event (tool order changed A29, tool definitions changed A27, system prompt timestamp A25, system prompt changed A26, effort changed A38, org switched A40) else "context changed". All also add to #3 | USD premium per rewrite, with cause label | **G**: purely usage fields (cache_creation vs read) + gaps + model; cause attribution via request-body diff is better in gateway | cause is first matching rule; prefix events only from CLI `prompt_snapshot` attachments (a gateway can hash tools/system itself).
**19 Compaction cost** | `isCompactSummary` text length, `compact_boundary`, post-compaction cw | per compaction: `summary_tokens*out_price/1e6 + sum(premium of rewrites between prev call and compaction)` (rewrites with the same >5_000/0.5 rule); summary matched to boundary within +5s | USD per compaction | **C** (compaction is a CLI event); gateway could detect as sudden ctx drop | summary size estimated chars/token.
**4 Many agents** | helper calls (sidechain) | spend of all helper calls (`helper_cost`), flagged as spend-to-review (`SPEND_NOT_WASTE` {4,15}) | USD; detail "N helper calls, X% of session cost" | **C** (helper identity) | not waste, just review.
**4a Fork context duplication** (23) | first call ctx per helper agent | helper started when `first_ctx > FORK_MIN` (50_000): cost = `(first_ctx - START_BASELINE) * sum(read_price of that agent's calls)` | USD | **B**: first request ctx of a sub-agent visible if gateway can tell it is a sub-agent | agents that began before window skipped.
**4b Overlapping agents** (24) | helper `Read` results, `file_path`, agent id | a Read of path already read by a different agent: `agent_carry(agent, t, result tokens)` | USD | **C** | only Read tool; path string equality.
**4c Verbose agent reports** (25) | `Agent/Task` tool_result size | if result tokens > `REPORT_BIG` 2_500: carry(t, tokens - `REPORT_KEEP` 1_000) | USD | **B**: tool_result size in request body next turn | tokens estimated.
**5 No clear direction** | tool_uses per task, first edit time | explore = tool uses before first `EDIT_TOOLS` use in the task; if `> EXPLORE_LIMIT` 15: cost = sum of `cost` of the distinct model calls that issued uses beyond the 15th | USD | **B**: tool names in tool_use blocks, order | every tool before first edit counts as exploration; tasks with no edit skipped.
**6 Bigger model than needed** | task category tag, call usage, model | only USD mode; for tasks tagged in SIMPLE_CATEGORIES and calls on opus/fable: `cost - cost_if_priced_at(CHEAPER=sonnet-5-5)`; also any helper call on opus/fable (no category requirement) | USD delta | **B**: needs category label (from prompt tag; gateway would need a classifier); price delta is gateway-computable | assumes same tokens on cheaper model; category only from `[tag]` prompts, so untagged work never flagged; "not applicable" in token units.
**7 Too much tool output** | tool_results, `name`, `input`, text | per result (a) duplicate `Read` with same (path, offset, limit) and path not edited since: carry(t, tokens) (also logged as A72); (b) Grep/Glob/Bash/LS result with `>= 5` lines matching `DEP_DIRS`: `dep_tokens = tokens*dep_lines/total_lines`, carry (also A76); (c) else `tokens > BIG_RESULT` 4_000: carry(t, tokens - BIG_KEEP 2_000); goes to #17 if name == Bash else #7; (d) AGENT_TOOLS results excluded (go to 4c) | USD | **B**: tool_result bodies appear in the next request; gateway needs tool name from preceding tool_use | `edited_since` tracks edits by path; "useful part" fixed at 2_000.
**14 Screenshot accumulation** | result `images` | each result with image: carry(next call time, image_tokens) | USD | **G**: image blocks in request, size from header (w*h/750) | counts all image tokens as leak, no relevance.
**16 Failed/denied tool calls** | `is_error`, text | for `is_error` results not containing "interrupted by user": kind = denied (DENIED_RE) > schema error (SCHEMA_RE) > wrong id/path (WRONG_ID_RE) > error; cost = `out_tokens_of_call*out_price/1e6 / max(1, n_tools) + carry(t, tokens)`; schema errors also A135 | USD + kind label | **B**: `is_error` flag in tool_result blocks | output cost split evenly across tools in the call; regexes on first 4000 chars of text.
**17 Noisy commands** | = branch (c) of #7 for Bash | see #7 | | | |
**8 Wordy responses** | `Write` inputs and prior reads | `Write` to a path previously Read/Edit/MultiEdit in session: cost = `tok(len(content))*out_price/1e6` ("rewrote whole file"). Also records `_output_cost` (sum out*po) as stat | USD | **B** (tool_use input in response) | whole-file Write of an existing file assumed wasteful.
**9 Retry loops** | tool name + md5(json input sorted) + `error` flag | per (name, input hash) failure counter (`error` = `is_error` or ERROR_TEXT in first 600 chars); resets to 0 on a success; from the 3rd consecutive failure: cost = `cost` of the model call that issued it | USD | **B** | consecutive-ness by result order, not time.
**10 Usage while idle** | transcript user prompts + hook `UserPromptSubmit` `ts` | prompt `p` counts if `p.t >= min(hook ts) - 15` and no hook record within 15 s; cost = sum call cost until next prompt | USD | **C** (hook needed; gateway can't tell human typed vs automation, only timing/regularity) | unmeasurable without hook data; "not typed" = no hook record.
**11 No visibility** | n/a | coverage gap statement, not a number (`unmeasurable`) | none | | |
**12 MCP tool schema bloat** | `prompt_snapshot.tools[]`, used tool names | per snapshot, per MCP server: tools whose name starts `mcp__` and not in `used`; tokens = `tok(len(json.dumps(tool)))`; cost = `unused_tokens * read_span(t, next snapshot)` | USD, "server: k/n tools never called" | **G** if request `tools[]` is parsed and tool_use usage tracked per conversation | only newer CC versions record snapshots (`NOT_RECORDED`).
**13 Unused skills/plugins** | `skill_listing`, `agent_listing_delta`, `Skill` uses, `<command-name>/x</command-name>` | listing entries split `\n(?=- )`; entry unused if its name (before `:`) not invoked; cost = carry(t, tok(chars of unused)); agent types likewise vs `subagent_type` | USD | **C** (attachments) / **G** if skill text visible in system prompt | name matching by prefix.
**18 High effort on trivial turns** | per turn: calls, `thinking` blocks, `text` blocks, `out` | turn (calls grouped by prompt time) with exactly 1 call, `n_tools == 0`, `reply = tok(text chars) <= TRIVIAL_TEXT` 300, `reasoning = out - reply > THINK_LIMIT` 3_000: cost = `(reasoning - THINK_BASELINE 1_000)*out_price/1e6` | USD | **G**: output_tokens vs visible text length; no tool_use | reasoning inferred as out minus estimated visible tokens (thinking text may be redacted).
**20 Correction churn** | prompt text | prompt matches CORRECTION_RE (after stripping [tag]): cost = sum of `cost` of all calls until the next prompt | USD | **B**: user message text visible in request | regex on start of prompt only.
**21 Visual iteration loops** | per task: edits then screenshot results | cycle = edit tool (or name endswith `__use_figma`) followed by a result with image or "screenshot" in tool name; for cycle index k >= `VISUAL_LIMIT` 3: cost of task calls between cycle k-1 and k | USD | **B** | image or name heuristic.
**15 Repeated tasks across sessions** | first typed prompt per session | word set `[a-z0-9_]{3,}` after removing tag; need >= 5 words; Jaccard with an earlier same-project session's set `>= REPEAT_SIM` 0.6: cost = whole session cost (incl. helpers); flagged as spend-to-review | USD | **B**: first user message; project/session grouping from gateway key | skip sessions cut by window; prompts starting `<` excluded.
**22 Re-learning the codebase** | `Read` before first edit, per project, across sessions | files read before first edit in a session; if `>= RELEARN_MIN` 2 earlier sessions of same project also explored it (same path): cost = sum carry(t, tokens) | USD | **B** (needs session + project identity) | "explored" = first Read of path before first edit.

## 5. Additional detectors (leak_extra.py), keyed `lid(n) = 1000 + n`

Every row below is charged via carry unless stated ("out" = `tokens*out_price/1e6`).

**Conversation history**
A1 Long history replay | per call: `ctx - first_ctx - 100_000 > 0`; cost = sum(excess * read_price) | **G**.
A5 Old tool results carried | each result still in context STALE_CALLS (30) calls after it: carry from the 30th later call of (tokens + image_tokens) | **B**.
A6 Prior assistant answers replayed | per call: carry(c.t, tok(chars of text blocks)) | **B**.
A7 Repeated pastes (cross-session) | paragraph >= 400 chars, md5 of whitespace-normalised text, seen in earlier prompt of same project | **B**.
A8 Pasted chat transcripts | prompt tokens >= 2_000 and >= 4 matches of `^\s*(Human|User|Assistant|Claude|⏺)\s*[:>]?\s` | **B**.
A9 Conversation forks (cross-session) | entry `uuid`s shared with an earlier session; cost = `(first ctx - 10_000) * prefix_read[-1]` | **C** (uuids).
A10 Rebuilding after fresh starts | new session < `RESTART_GAP` 3600s after previous session end and has an edit; cost = calls before first edit | **C** (session boundary; gateway could use idle gap).

**Instructions/memory (attachments, all C)**
A14/A16 Duplicate instruction lines | normalised line (>= 30 chars, not ```), seen in another file; A14 if both layers "Project", else A16; charged if > 50 tokens | A17 always-loaded guidance: sum tokens of "Project"/"Local" files > 2_000, charge excess | A18 stale memory: AutoMem index lines `](x.md)` whose relative file does not exist on disk (filesystem check) | A19 few-shot: `<example...>...</example>` blocks beyond 2 per file, also in system prompt and tool descriptions of snapshots (charged `tokens*read_span`) | A68 invoked skill body (`isMeta` + `sourceToolUseID`) > 3_000 tokens: carry(tokens - 1_500) | A70 `mcp_instructions_delta` block or `hook_*` attachment > 300 tokens: carry(tokens - 300).
(A19 and A70 system-prompt parts are G-capable if the gateway sees the system prompt.)

**Cache (A21-A40)**
A21 Missing caching | any call with `in > 10_000` (uncached input) | cost `in*(pi - pr)/1e6` | **G**.
A24 Below cache minimum | `cw == cr == 0`, `in > 0`, `ctx < min_cacheable(model)` (1_024 sonnet else 4_096) | cost `in*(pi-pr)` | **G**.
A22 Cold-cache requests | first call of main session and each helper (unless started before window): `cw*pi*wmult` | **G**.
A35 Cache writes never reused | call with `cw > 1_000` whose next call in the stream is not within `ttl_s` with `cr > 0`: write premium `cw*pi*(wmult-1)` | **G**.
A37 Cache-write premium | every call: `cw*pi*(wmult-1)` (reported as review spend) | **G**.
A34 Concurrent cache creation | consecutive helper-agent first calls <= `CONCURRENT_S` 10s apart both `cw > 5_000`: `cw*(pi*wmult - pr)` | **B**.
A25 timestamp in system prompt | consecutive `prompt_snapshot.systemPrompt` identical after `re.sub(r"\d","#")` but differing raw; **A26** differs otherwise; **A27** tool definitions differ (md5 of each tool JSON); **A29** same set, different order; **A38** `/effort` command; **A40** `credential_org.organizationUuid` changed; **A30** model != prev model on a rewrite (see #3). All charged as the #3 `premium` of the next rewrite within the call window | **G** if gateway hashes system/tools per request, otherwise C.

**Model/reasoning**
A45 Replanning | plan tools (`TodoWrite/TaskCreate/TaskUpdate`) in one task beyond `PLAN_LIMIT` 5: `tool_share(call) + carry(tok(json.dumps(input)))` | **B**.

**Answer generation**
A52 Repeating the question | first text block of the first call after a prompt; first sentence (split `(?<=[.!?])\s|\n`) with >= 8 words and Jaccard with prompt word set >= `ECHO_SIM` 0.7 | out + carry | **B**.
A53 Repeated explanations | paragraph >= 300 chars md5 (lowercased, whitespace-collapsed) already seen | out + carry | **B**.
A54 Progress narration | calls with tool_use and text > `NARRATION_KEEP` 50 tokens: excess out + carry (summed) | **B**.
A58 Reprinting artifacts | code block (```...```) >= 300 chars matching md5 of earlier Edit/Write content or earlier reply block | out + carry | **B**.
A60 Truncated answers | `stop_reason == "max_tokens"`: out cost of whole call | **G**.

**Tools / files**
A65 Tool discovery | ToolSearch/ListMcpResourcesTool call number > 2 per session: tool_share + carry | **B**.
A66 Large tool-call args | non-edit non-agent tool whose `tok(json.dumps(input)) > 1_000`: out + carry | **B**.
A69 Skill supporting docs | Read path contains `/skills/` and not ending SKILL.md | **C**.
A71 Whole-file reads | Read without offset/limit, tokens > 5_000: carry(tokens - 2_000) | **B**.
A72 Repeated reads | in leak_report (#7a) | **B**.
A73 Broad searches | Grep/Glob or command matching `(^|\|\s*|&&\s*)(grep|rg|ag|find)\b`, > 100 result lines: carry(tokens*(1 - 100/lines)) | **B**.
A76 Dependency reads | Read path matches DEP_DIRS (or #7b) | A77 generated: `GENERATED` regex (.lock, -lock.json, .min.js/css, .map, .pbxproj, .g.dart, .pb.go, _pb2.py, dist|build|out|.next|generated|__generated__ dirs) | **B**.
A79 Unbounded search | search with no path/glob/type (Glob: pattern not starting `**` counts as bounded; Bash counts as bounded) and tokens > 1_000: carry(tokens - 1_000) | **B**.
A128 Parent re-reads helper-read file | Read in main of a path a helper read earlier | **C**.

**Terminal / git / data**
A82 Repeated traceback | `error` result matching `TRACEBACK`; key = md5 of last 5 normalised lines (digits -> #); repeats charged | **B**.
A84 Repeated lint | command matches `LINT_CMD`; (command, result md5) repeated | **B**.
A87 Repeated log lines | tokens >= 1_000, name != Read (or .log), >= 20 non-empty normalised lines; dup share = 1 - unique/total > `DUP_LINE_SHARE` 0.5: carry(tokens*dup) | **B**.
A91 Big git diff (`git (diff|show)` > 4_000 tokens): carry(tokens - 2_000); A92 lockfile/generated diff sections (> 500 tokens). A93 `git log` without --oneline/--format/--pretty, metadata lines (commit/Author:/Date:/Merge:) > 300 tokens. A94 identical `git status` hash twice in a row. A95 PR discussions (`gh pr view --comments`, `gh api pulls|comments`, tool name contains pull_request) > 4_000. A96 issue histories (`gh issue view`, tool name contains issue/jira/linear/asana/clickup) > 4_000. A99 DB results (psql/mysql/sqlite3/mongosh/bq query/clickhouse-client, or tool name contains query/sql) > 4_000. A98 JSON result (starts with `{`/`[`, not Read) > 4_000: carry(tokens - 2_000). A100 JSON wrapper share: tokens > 2_000, JSON parses, `len(body) - leaf_chars > 0.5*len(body)`: carry(tok(wrapper - 0.5 len)) | all **B**.
A136 Polling | successful non-excluded tool call with identical (name, md5 input, result hash) count >= `POLL_MIN` 3: tool_share + carry | **B**.

**Web / retrieval / images**
A101 Full pages (page-tool names: WebFetch or contains get_page_text/read_page/fetch/scrape) > 4_000 tokens: carry(tokens - 2_000). A103 search results: distinct URLs > 10: carry(tokens*(1 - 10/urls)). A104 duplicate sources: >= 500 tokens, 8-word shingle sets, overlap with earlier source (different url/query) >= 0.5: carry(tokens*share). A105 refetch same URL; A110 same but a compaction happened between. A107 overlapping chunks: lines >= 80 chars already returned by another result, > 200 tokens. A109 prompt with `document` block or > 10_000 tokens | **B**.
A111 Large images (> 1_200 tokens): `(itok - 800)*pi/1e6` (charged at INPUT price once, not carry). A112 same image (md5 of source) again: carry. A120 same, but failed browser tool call in between (`claude-in-chrome|playwright|browser`). A114 screenshot right after another screenshot. A115 Read of .pdf. A116/A117 same document read as page images and as text (pdftotext/pdfplumber/pypdf/PyPDF2/fitz/pymupdf/pdfminer/textutil) / OCR (tesseract/ocrmypdf/easyocr/\bocr\b) | **G/B** (images are in request bodies).

**Multi-agent**
A121 = #4a, A122 = #4b, A127 = #4c (`SAME_AS`, no separate code).
A124 agent brief (`Agent/Task` input.prompt) tokens > 1_000: out of the excess. A125 each helper agent startup after the first: `in*pi + cw*pi*wmult + cr*pr` of its first call. A126 `SendMessage` tool use (out + carry) and prompts starting `<cross-session-message`, `<teammate-message`, `<task-notification`. A131 each `AskUserQuestion`: the call's whole cost | **C**.
A134 Interrupted turns: "interrupted by user" user entries; cost = calls from the turn's prompt to the interrupt | **C**.
A135 Schema-invalid tool args = #16 schema errors.
A138 Scheduled/unchanged reruns (cross-session): md5 of first request (>= 20 chars) matches earlier same-project session and >= 80% of its (>= 3) tool-result hashes (non-error, >= 50 tokens) also appeared: whole session cost | **B**.

## 6. Unmeasurable (declared, no detector)
LABEL (needs a labelled review): A3, A4, A20, A44, A46, A47, A48, A55, A56, A59, A102, A108, A113, A119, A129, A130, A132. PAYLOAD (needs exact request body incl. cache_control, edited messages): A28, A31, A32, A33 (**a gateway can see these**). EXPERIMENT: A42, A49. CONFIG: A39. HIDDEN calls: A36, A137, A140. A43 (thinking replay), A50 (tokenizer difference needs same payload on both models; a gateway could do it by counting).

## 7. Summary of approximations worth knowing
- Costs are estimates: per-call usage exact, per-item sizes are chars/token (2.37/3.10 or per-session calibration).
- "Waste" is conservatively `size - KEEP` for large results; nothing proves the content was not needed.
- Carry assumes every later call re-reads the item until compaction (true only while the prefix is cached or resent).
- Labels (task category, simple/hard) come from `[tag]` prompt prefixes only; untagged work is never flagged for model downgrade.
- Cache break cause uses 3600 s (1h) as the hard break and `--ttl` (5m or 1h) as the lifetime; both guess the cache tier.
- Detection of CLI-only concepts (helper agents, compactions, hooks, attachments, skill listings) cannot be reproduced from a gateway without equivalent signals.
- 26 core ids; Findings dict keys starting `_` are aggregate stats (`_prefix_sizes`, `_compactions`, `_thinking`, `_mcp_tokens`, `_main_cost`, `_top_tier_cost`, `_output_cost`, `_calibration`), not leaks.
- 10 A rows are implemented in `leak_report.py` rather than `leak_extra.py`: A25, 26, 27, 29, 30, 38, 40 (inside #3), A72 and A76 (#7), A135 (#16).
