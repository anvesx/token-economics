# hermes-engine: capture, scoring, outputs, assumptions

Source: /Users/rachitsrivastava/Developer/company-os/token-economics/plan/_research/hermes/repo (read only).
Plugin client string: `token-metrics/1.7.0` (share.py, research.py). Python 3 stdlib only. Payload `SCHEMA = 1`.
Note: leak_report.py, leak_extra.py and leak_categories.py were skimmed (constants, categories, a few detectors), not read line by line.
Files read in full: all those listed in the brief except that the leak_report/leak_extra detector bodies were only sampled.

## 1. Hooks and events used, and what each records

One script handles every event: `plugins/token-metrics/scripts/metrics_hook.py`, timeout 5 s per hook (hooks.json).
It appends one JSON line per event to `~/.claude/metrics/events.jsonl` (dir overridable with `CC_METRICS_DIR`).

Fields on every line: `ts`, `event`, `session_id`, `transcript_path`, `cwd`.

| Event (matcher) | Extra fields recorded |
|---|---|
| SessionStart | `source`; also copies the report scripts to `~/.claude/metrics/` |
| UserPromptSubmit | see below |
| PreToolUse (`*`) | `tool`, `tool_use_id`; for Bash: `git_revert` (bool) |
| PostToolUse (`*`) | same as PreToolUse |
| PostToolUseFailure (`*`) | same, plus `is_interrupt` (bool) |
| PreCompact | `trigger` (auto or manual) |
| Stop | base fields only (no branch in the script). Used by analyze.py to time turns |
| SessionEnd | `reason`; then starts a background leaderboard sync (section 6) |

UserPromptSubmit records, depending on the prompt:
- Matches `^\s*rate\s+([1-5])(?:\s+(ok|partial|fail))?\s*$` (case-insensitive): `kind="rating"`, `rating` (int 1-5), `outcome` (ok/partial/fail or null).
- Otherwise `kind="prompt"`, `category` (from `^\s*\[([A-Za-z][\w-]*)\]`, lower-cased, else null), `correction` (bool), `prompt_chars` (length).
  - Prompt text is stored only if `CC_METRICS_KEEP_PROMPTS=1`, first 500 chars (`prompt` field). Off by default.
- `CORRECTION_RE` (prompt starts with): no, nope, wrong, that's not, that is not, not what i, undo, revert, stop, don't, "you broke/missed/forgot/ignored", "i said", again.
- `REVERT_RE` (in Bash command): `git checkout -- | .`, `git restore`, `git reset --hard`, `git revert`, `git stash`.

What the hook does NOT record: no token counts, no cost, no model. Those come from Claude Code's own transcripts
(`~/.claude/projects/*.jsonl`, `message.usage` per assistant message), read after the fact by the report scripts.
CLAUDE.md: "most leaks are detected from existing history with no hook data. Hook data adds the extras: task categories, ratings and idle detection."

## 2. Metrics stored per task / session

### 2a. Per-task row (analyze.py `FIELDS`, 24 columns; `--csv` output, not persisted anywhere by default)
```
session_id (first 8 chars), task_no, category ("untagged" if none), start (UTC %Y-%m-%d %H:%M),
prompts, api_calls, tool_calls, models ("+"-joined set),
input, cache_write, cache_read, output,
cost_usd (4 dp), cache_hit_rate (3 dp, null if no input seen),
first_response_s, median_turn_s, tool_s, total_s,
corrections, interrupts, reverts, compactions,
rating, outcome
```
Task boundary: a task starts at the session's first prompt or any prompt with a `[category]` tag, and runs to the next tagged
prompt or session end (+1 s). Untagged prompts are follow-ups. (leak_report.py separately uses `TASK_GAP_S = 30*60`: an untagged
prompt after 30 min idle starts a new task for leak detection.)

Derivations:
- `cost_usd` = sum per message of `(input*pi + cache_write*pi*write_mult + cache_read*pr + output*po)/1e6`.
- `cache_hit_rate` = `cache_read / (input + cache_write + cache_read)`.
- `first_response_s` = first assistant message time after task start minus task start.
- `median_turn_s` = median of (next Stop event ts minus prompt ts) over the task's prompts.
- `tool_s` = sum of PostToolUse(+Failure) ts minus matching PreToolUse ts (by `tool_use_id`).
- `total_s` = last non-rating activity minus task start.
- `interrupts` = transcript user messages containing "interrupted by user" + `PostToolUseFailure.is_interrupt`.
- `rating`/`outcome` = the last rating event inside the task.
- Transcript messages are deduplicated by message id; `<synthetic>` model messages are skipped.

Category summary printout (analyze.py `summarise`): per category: tasks, success (share of rated tasks with outcome ok),
tokens p50, cost p50, cost per success (sum of cost of rated tasks / count ok), turn s p50 and p90, corrections/task,
interrupts/task, mean rating (frustration 1-5).

### 2b. Pricing table (analyze.py and leak_report.py, copied in both) - $ per MTok: input, output, cache read
```
claude-fable-5-1  10.00 50.00 0.25      claude-fable-5    10.00 50.00 1.00
claude-opus-5-5    4.00 20.00 0.20      claude-opus-5      5.00 25.00 0.50
claude-opus-4-8/4-7/4-6/4-5  5.00 25.00 0.50
claude-sonnet-5-5  2.00 10.00 0.20      claude-sonnet-5    2.00 10.00 0.20
claude-sonnet-4-6/4-5  3.00 15.00 0.30  claude-haiku-4-5   1.00  5.00 0.10
```
Longest model id matched first; unlisted version falls back to family: fable -> 5-1, opus -> 5-5, sonnet -> 5-5, haiku -> 4-5; unknown family -> sonnet.
Cache write price = input price x multiplier: 1.25 (5m), 2.0 (1h), 2.0 default when the transcript has no split
(`usage.cache_creation.ephemeral_5m_input_tokens / ephemeral_1h_input_tokens`).

### 2c. Weekly / lifetime aggregate (stats.py build, validated by leaderboard/lib/validate.ts `Week`)
Per ISO week (local time), also a `lifetime` block (adds `first_day`, `longest_streak_days`):
```
tokens (ctx + out; ctx = input+cache_write+cache_read), cost_usd (2 dp), active_hours (2 dp), active_days,
sessions, hook_sessions, tasks, tagged_tasks, rated_tasks, top_category,
model_cost{fable|opus|sonnet|haiku|other: usd}, model_tokens{...}, token_split{input,cache_write,cache_read,output},
agent_tokens (subagent/helper-call tokens), leak_share{category_no: share of spend}, waste_index
```
Plus `days`: last 56 days (`DAILY_DAYS`) of `{day, tokens, cost_usd, active_hours}`. Payload covers last 8 weeks (`PAYLOAD_WEEKS`).
- Active time: sum of gaps between consecutive calls/prompts, each gap capped at `ACTIVE_GAP_S = 5*60`.
- Volume (tokens, cost, hours, days) goes to the week each call happened in. Session/task counts and leak shares go to the week the session started in.
- Model family = first of fable, opus, sonnet, haiku found in the model id, else other.
- Server side `weekly_stats` table: one row per (user_id, week) holding the JSON `payload`, replaced on each sync. `users.lifetime` and `users.days` hold the latest blocks.

### 2d. Waste index (stats.py `leak_shares`)
- `leak_share[n]` = category n cost / total spend (main + helper-agent cost) for the sessions in that week, for the 50 curated categories, excluding unmeasurable ones.
- `waste_index` = sum of `leak_share` over all categories NOT in `REVIEW = {2, 3, 5, 6, 15, 17, 18, 26, 29}`, rounded 4 dp.
- Categories overlap, so it can exceed 1.0; "compared only to the user's own baseline". Server cap: `waste_index` <= 50 per validate.ts.
- Rate/label fields: `category` (user tag), `rating` 1-5 (frustration), `outcome` ok|partial|fail. No other rate/label fields exist.

### 2e. 50 curated leak categories (leak_categories.py; number: name)
1 Heavy starting context; 2 Cache-write premium; 3 Cold cache at session and agent start; 4 Cache expired after a break;
5 Many agents; 6 Long history replay; 7 Interrupted turns; 8 Sessions that never end; 9 No clear direction;
10 Restarting too often; 11 Stale tool results carried forward; 12 Bigger model than needed; 13 Fork context duplication;
14 Large tool-call arguments; 15 Agent startup cost; 16 Model switch rewrote the cache; 17 Old replies replayed;
18 Clarification loops; 19 Screenshot accumulation; 20 Visual iteration loops; 21 Cache not reused; 22 Correction churn;
23 Agents racing the cache; 24 Too much tool output; 25 Noisy and repeated terminal output; 26 Repeated tasks across sessions;
27 Failed, retried and polling calls; 28 Repeated screenshots; 29 Progress narration; 30 Whole-file reads;
31 Duplicate reading across agents; 32 Agent coordination chatter; 33 Large images and PDFs; 34 Broad or unbounded searches;
35 Bloated JSON and query results; 36 Wordy and repeated output; 37 Web pages and search results;
38 Copied history (pastes, transcripts, forks); 39 Compaction cost; 40 Git and GitHub output;
41 Dependency, vendor and generated files; 42 Verbose agent reports and briefs; 43 Repeated reads of unchanged files;
44 Re-learning the codebase; 45 High effort on trivial turns; 46 Tool discovery and skill loading; 47 Usage while idle;
48 MCP tool schema bloat; 49 Unused skills/plugins; 50 No visibility.
`CACHE_EVENTS = {2, 3, 4, 16, 21, 23}` (in `--units tokens` mode these are tokens that missed the cache, not extra tokens).
Cost method: a leaked item is charged at the cache-read price on every later call that re-reads it, until the next compaction.

### 2f. Selected detector constants (leak_report.py)
```
START_BASELINE 10_000 tok (reasonable starting context)   CARRY_MIN 20_000   TASK_GAP_S 1800
EXPLORE_LIMIT 15 reads/searches before first edit          BIG_RESULT 4_000 (BIG_KEEP 2_000 counted useful)
TRIVIAL_TEXT 300 chars; THINK_BASELINE 1_000; THINK_LIMIT 3_000 reasoning tok on a trivial turn
VISUAL_LIMIT 3 edit->screenshot cycles                     FORK_MIN 50_000   REPORT_BIG 2_500 (REPORT_KEEP 1_000)
RELEARN_MIN 2 earlier sessions                              REPEAT_SIM 0.6 first-prompt word overlap
IMAGE_DEFAULT 1_600 tok                                     CHARS_PER_TOKEN new 2.37, old 3.10 (per-session calibrated; CALIBRATE_MIN 10, CALIBRATE_CHARS 8_000, range 1.2-6.0)
SIMPLE_CATEGORIES {docs, explain, question, rename, chore, commit}; CHEAPER = sonnet-5-5 price; TOP_TIER (opus, fable)
```
Cache break rule (cat 4 / core leak 26): gap before a call with a full cache rewrite: model change -> "model switch" (cat 16);
gap >= 3600 s -> break; gap >= `ttl_s` (3600 default, 300 with `--ttl 5m`) -> past cache lifetime; else attributed to prefix changes.
Premium charged = `cache_write * (price_in * write_mult - price_cache_read)/1e6`.
Usage-while-idle (cat 47): a prompt in the transcript with no hook UserPromptSubmit within 15 s (after the session's first hook record) = not typed by the developer (scheduled task, loop, background); cost = calls until next prompt.

## 3. Scoring and points (leaderboard/lib/score.ts; gamify.md agrees)

Scores recomputed from stored weekly stats on every request (rule change applies retroactively). Points only for weeks from the join week on; earlier history sets the baseline only. A week counts if `sessions > 0`.

RULES (exact): `synced 10, hooked 10, hookedShare 0.8, perTagged 2, taggedCap 20, perRated 3, ratedCap 30, improvementCap 50, minActiveDays 3`.

Per active week:
```
participation = 10
              + 10 if hook_sessions >= 0.8 * sessions
              + min(20, tagged_tasks * 2)
              + min(30, rated_tasks * 3)
improvement   = 0 unless baseline set, week not a baseline week, active_days >= 3:
                pct = (baseline - waste_index) / baseline * 100
                improvement = round(clamp(pct, 0, 50))
points = participation + improvement
```
Max per week = 10 + 10 + 20 + 30 + 50 = 120. Example in gamify.md: baseline 0.85, week 0.81 -> 4.7% -> +5.
Baseline = median `waste_index` of the first 2 weeks with `active_days >= 3` (those weeks earn no improvement).
Volume (tokens, cost, hours) never earns points: "otherwise the heaviest spenders would win a leaderboard meant to reduce waste".

Levels (points): 1 Rookie 0; 2 Apprentice 50; 3 Practitioner 150; 4 Optimizer 300; 5 Specialist 500; 6 Expert 800; 7 Master 1200; 8 Grandmaster 1700; 9 Legend 2300; 10 Mythic 3000.

Streaks: consecutive active weeks ending this week (or last week if this week has none yet). Counts all synced history including pre-join.

Badges: First Sync (join); Fully Hooked (a joined week with hook_sessions >= 80% of sessions); Tagger (50 tagged tasks); Honest Rater (25 rated);
Leak Plugger (a week with improvement >= 25); Cache Keeper (week with active_days >= 3 and `leak_share["4"] < 0.02`);
Lean Start (week with active_days >= 3 and `leak_share["1"]` below company median cat-1 share, last 4 weeks);
On a Roll (4-week streak); Unstoppable (12-week); volume, cosmetic: 100M Club (1e8 tokens), Billionaire (1e9), Token Titan (1e10), Centurion (100 active h), Lifer (500 active h).
All-time volume = max(sum of stored weeks, latest lifetime block), because local transcripts are deleted after ~30 days (gamify.md).

Leaderboard: periods week / last 4 weeks / all time; rank by points, then current streak, then name; ties share a rank.
Admin view: spend, tokens, hours, hook coverage, tagged/rated counts, week-by-week adoption, biggest leaks weighted by spend, users not synced in 7 days, CSV export.

Server validation (validate.ts) per-week ceilings: tokens 1e12, cost_usd 1e6, active_hours 168, active_days 7, sessions 10_000, hook_sessions 10_000,
tasks/tagged/rated 50_000, waste_index 50; lifetime blocks get 60x (except waste_index, longest_streak_days 3660, day hours 24).
Rejects: week keys older than 60 weeks or more than 1 week ahead, > 60 weeks, > 62 days, `hook_sessions > sessions`, `tagged_tasks > tasks`,
`rated_tasks > 3*tasks + 3`, token_split sum > `tokens*1.01 + 1`, `agent_tokens > tokens`. Leak share accepted only for categories 1-50, value 0-5.
Known families: fable, opus, sonnet, haiku, other. Unknown fields are dropped. gamify.md: "Treat the leaderboard as a game, not an audit."

## 4. Statusline and report outputs

Statusline (statusline.py, `/token-metrics:statusline [keep|replace|off]`): reads Claude Code's status-line JSON on stdin, uses
`prompt_cache` (needs Claude Code 2.1.251+; miss cause 2.1.260+), `model.id`, `context_window.total_input_tokens`. Refresh every 30 s (`REFRESH_S`).
Constants: `BIG_CHAT = 300_000`; chat colors: >= 600k red, >= 500k yellow, >= 300k white, else dim; `HIT_LOW = 0.80` (hit rate yellow below it, "our choice; Claude Code defines none"); bar width 6.
Cost math: `cold_cost = n * price_in * write_mult(ttl 5m=1.25, 1h=2.0, default 2.0) / 1e6`; `warm_cost = n * price_cache_read / 1e6`, n = `recache_tokens_if_cold` or `total_input_tokens`.
Warm: `cache ● 1h ████░░ 37m left · hit 91% · chat 152k · re-read $0.03 · if cold $1.22` (yellow when < 20% of TTL left; adds "misses N", "/compact at next break" when chat >= 300k).
Cold: `cache ○ cold · chat 152k · next msg re-caches ≈ $1.22 · new task? /clear` (adds "same task? /compact" when >= 300k; "last miss: <causes>").
Other states: "cache · waiting for first reply", "cache · off" (`caching_observed` false). Docstring: "On a subscription they show the relative weight against usage limits."

Reports (all local, stdout, optional files):
- `leak_report.py`: ranked leak table by cost (50 curated default; `--all`, `--all --core`, `--units tokens`, `--ttl 5m|1h`, `--days`, `--since`, `--top`, `--md`). `/token-metrics:leak-report` = `--days 30 --top 2`.
- `analyze.py`: per-category task table; `--csv` per-task rows; `/token-metrics:task-report`.
- `stats.py`: "Wrapped" summary (tokens, API-equivalent spend, token split %, subagent %, active hours, longest streak, tasks/tagged/rated, model mix by spend, top 3 leaks, weekly table with waste index); `--json` prints the exact sync payload; `--weeks` default 8.
- `research.py export|preview|merge`: anonymous aggregate JSON (`FORMAT = 1`): spend by token type and model, 50 category shares in USD and tokens, context-size buckets (0-100k, 100-250k, 250-500k, 500k+), idle-gap rewrite buckets (5-60, 60-180, 180-720, 720+ min), per-session sizes in random order, random `export_id`. Nothing is sent; the user sends the file.
- `share.py`: `preview`, `join`, `verify`, `sync [--force]`, `me`, `dashboard`, `leaderboard --period week|month|all` (`--top` 15), `card --hide/--show`, `leave`.
- Web dashboard `/u/<handle>`: token usage, week vs last week, 12-week trend charts, leaks vs company, level/points/streak/badges, leaderboard; public card 1200x630.

## 5. Assumptions about the harness

- Claude Code only. Name, README and CLAUDE.md: "Token Metrics for Claude Code", "Claude Code plugin". It is loaded via `claude --plugin-dir` or `/plugin install`; hooks come from the Claude Code plugin hook system (`${CLAUDE_PLUGIN_ROOT}`).
- Transcript path: reads `~/.claude/projects/*.jsonl` (`--root` overrides) and uses `transcript_path` from hook payloads; events in `~/.claude/metrics/events.jsonl`. Usage fields assumed: `message.usage.input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `output_tokens`, `cache_creation.ephemeral_5m/1h_input_tokens`; model `<synthetic>` skipped; helper (subagent) calls tracked; tool names Agent/Task, Edit/MultiEdit/Write/NotebookEdit are hard-coded.
- Pricing: Anthropic first-party API list prices, hard-coded per model version. Spend is labeled "API-equivalent spend". README/leak_report docstring: "for subscription users this is API-equivalent usage, which is what drains the plan's allowance"; analyze.py: "for subscription users that is the API-equivalent cost, not what you pay."
- Subscription vs API: default cache lifetime is 1h "for subscriptions"; `--ttl 5m` "if you are on an API key or usage credits (5-minute cache)". Cache-write pricing is per recorded lifetime when the transcript has it. It never measures actual billed amounts, plan limits or remaining allowance.
- Newer Claude Code versions are needed for some features: loaded tool definitions/skill listings in transcripts (cats 48, 49; older sessions skipped), `prompt_cache` in the status line (2.1.251+).
- Models: only Claude models priced (fable, opus, sonnet, haiku). Non-Claude model ids fall back to sonnet pricing; no mention of OpenAI, Gemini, Codex, Cursor, Aider, Copilot, Bedrock, Vertex, or a gateway/proxy anywhere in the files read (grep found none). Nothing addresses API-based agents or other CLI agents; "API key" appears only as the `--ttl` hint.
- Org: requires a `@devxlabs.ai` email (`DOMAIN` in share.py), Google Workspace sign-in; backend is Next.js on Vercel + Postgres.
- Tokenizer: chars-per-token default 2.37 for the tokenizer introduced with Opus 4.7 (also Opus 5.x, Fable, Sonnet 5.x), 3.10 before; ~30% more tokens for the same text.

## 6. Automatic versus report-only

Mostly observe-only. The actions it does take:
1. Blocks one prompt type: `rate N [ok|partial|fail]` returns `{"decision":"block","reason":"Recorded: frustration N/5 ... Not sent to Claude."}` so the rating never reaches the model (zero tokens). This is the only place it changes harness behaviour, and it only intercepts its own command.
2. Never blocks tool calls, compaction, models, spend, or any other prompt. It never rewrites prompts, switches models, runs /clear or /compact, or auto-fixes anything. Status line only suggests ("new task? /clear", "/compact at next break").
3. Hook failure policy: every exception is swallowed and exit code is 0 ("must never break Claude Code"). Statusline failure prints nothing.
4. Automatic side effects (not behaviour-changing): SessionStart/other events copy scripts into `~/.claude/metrics/` (overwrite if content differs); SessionEnd spawns a detached `share.py sync --background` if the user joined and `last_sync` is over 3600 s old (`SYNC_EVERY_S`, lock file `share.lock`, stale after 600 s). Sync is opt-in and uploads only aggregates.
5. `/token-metrics:statusline` edits the user's `~/.claude/settings.json` (backup `settings.json.bak-token-metrics`) on explicit command only; README states the plugin does not otherwise modify settings.json. It warns if managed settings override.
6. Slash commands run `python3` scripts via `!` shell blocks and tell Claude to "Show the output above exactly as written", i.e. display-only.
7. Gamification is the only nudge mechanism: points/badges for tagging, rating and lower waste index; no enforcement, no budgets, no limits, no alerts, no cost caps.

Privacy rules (README): prompt text not stored by default; sync sends only per-week/day aggregates (no prompts, code, project names, file paths, session ids); `/token-metrics:share leave` calls `DELETE /api/me` and removes `share.json`.

## 7. Gaps the repo admits

- Self-reported metrics: "Users report their own stats, so the server can only check that the numbers are plausible... Treat the leaderboard as a game, not an audit." (gamify.md)
- Categories overlap, so the waste index "can go above 1" and is comparable only to the user's own baseline (stats.py, gamify.md).
- Item sizes (tool results, prompts, injected text) are estimated from chars-per-token, not exact; only per-call token counts are exact (CLAUDE.md "Cost model").
- Spend is API-equivalent list price, not what a subscriber pays (analyze.py, stats.py, README).
- Cache lifetime must be chosen by flag (`--ttl`) when transcripts lack the 5m/1h split; the default 1h assumes a subscription.
- Some categories are "unmeasurable" and shown as such: e.g. "unmeasurable without hook data (see #11)" when no session has hook data; #12 and #13 need loaded-definition records that only newer Claude Code versions write; the hook-coverage note "N/M sessions have hook data".
- Local transcripts are deleted after about 30 days, so history beyond that exists only if previously synced (gamify.md).
- Copied definitions across files must be kept in sync by hand (PRICES in leak_report.py and analyze.py; CORRECTION_RE, TAG_RE, SYNC_EVERY_S; statusline's cache-write multipliers). CLAUDE.md: "no test suite and no linter config".
- Not built (gamify.md "Ideas not built yet"): team leaderboards and team-vs-team challenges; weekly Slack digest; seasonal resets; badges tied to specific leaks (#8, #9); rewarding streaks of `ok`-rated tasks.
- `--units tokens` mode: "Bigger model than needed" reported as not applicable; cache categories become events, not leaks.
- Plugin cannot set the status line itself ("A plugin can't set the main status line"), so statusline install edits settings.json.
- Rating/tagging are manual user habits; without them, per-task success and category views are empty (README troubleshooting).
