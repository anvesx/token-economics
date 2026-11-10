# Context guard

The context guard cuts tokens the model never needed to see. It is the second optimisation layer after the cache planner. The evidence supports cheap mechanical controls and does not support output compressors as a default (C:024). Ids: `A:nnn` API corpus, `C:nnn` CLI corpus.

## Where the cost sits

| Share of billed cost | Item | Source |
|---|---|---|
| 74.7% | Harness base: system prompt plus tool definitions | C:024 |
| 19.4% | Hidden thinking and residual | C:024 |
| 3.3% | Tool outputs | C:024 |
| 1.4% | Tool-call arguments | C:024 |
| 0.8% | Retrieved files | C:024 |
| 0.5% | History | C:024 |

C:024 measured 2,848 runs on 103 tasks. Compression of tool output has a ceiling near 5 percent. C:130 reports observations at about 84 percent of a SWE-agent turn, but that counts raw tokens, not billed cost. Token Economics judges on billed cost.

## Interventions, ranked by evidence

| # | Control | Pays when | Loses when |
|---|---|---|---|
| 1 | Defer or prune tool schemas, with a lookup path | Above about 20 tools or 10 percent of context (C:019) | No recovery path (C:021), or the tool list changes mid-session (C:055) |
| 2 | Cap tool output: 25,000 interactive, 6,000 to 12,000 batch | Outliers such as a 610 KB spec reread (C:036) | It truncates tracebacks or edit anchors (C:024) |
| 3 | Anti-repetition rules | 7.88 to 41.73 percent cost cut in 6 of 8 settings (A:059) | One setting lost 1.5 pp Pass@1. Replicate locally. |
| 4 | External turn, loop and spend limits | Failed runs (32 percent of spend, C:028) | Cap set at P25 (C:025), or past the capability wall (C:132) |
| 5 | Observation masking | Above about 10 events: −56.1 percent cost (C:130) | At 7 events or fewer: −45 to −149 percent savings (C:133) |
| 6 | Server-side clearing | Re-fetchable results dominate (96.3 percent in one cookbook, A:271) | It fires often with small yield (C:066) |
| 7 | Compaction | Near the window, summary far below history size | Short sessions (A:224), $0.40 per 125K compaction (C:112) |
| 8 | Instruction and skill caps | Always cheap | Saving not in corpus |
| 9 | Effort and thinking caps by task class | Tasks that need little reasoning | Hard tasks |
| 10 | Subagent isolation | Large exploration, small return | No cache sharing (C:055), model-mix shift (A:059) |
| 11 | Memory tool | Across sessions (A:271, A:269) | Single runs only |
| 12 | Output compressors | Never by default | Range −2.7 to +48.4 percent cost; sign flips by harness (C:024) |

## Defaults Token Economics ships

| Control | Default |
|---|---|
| Schema deferral | On above about 20 tools or 10 percent of context, with a `get_tool_schema` and `invoke_tool` recovery path (C:019, C:022) |
| Tool output cap | 25,000 tokens interactive (A:284). Codex default 12,000 (C:106). Batch 6,000. |
| Never truncate | Tracebacks, test failures, edit anchors (C:024) |
| Masking | Only above about 10 events, window tuned per scaffold, applied at a trigger (C:130, C:133) |
| Clearing | Trigger 30 to 40k, keep 5, clear at least 3,000 to 5,000 (C:066). Provider defaults are 100,000 and keep 3 (C:065). |
| Compaction | Last resort. Count compactions. Recommend a restart at 3 (C:106, C:112, A:224). When used, drop old turns outright. Never rewrite or re-compact (CliffCompaction, 2609.26779: up to 50% cost cut). Rule-based elision beat LLM summarisation across 176 matched settings (2609.20804). |
| Black-box controller | Tool pruning plus loop interruption cut token cost 18.4 to 30.9% on three CLIs (TokenEconomizer, 2610.22732). Matches controls 1 and 4. Replicate before quoting. |
| Judge on bill | Fewer tokens did not mean cheaper or faster in 35,000 runs (2609.32961). No control ships on token count. |
| `max_tokens` | Hard cap on every call. Effort does not cap tokens (C:073, C:093). |
| Instruction files | CLAUDE.md under 200 lines (C:077). AGENTS.md under 32 KiB, which truncates silently (C:036). |
| Skills | Retire stale skills. Descriptions load every turn (C:075, C:079). |
| Output compressors | Off. A per-workload A/B with at least 99 percent marker recall is required first (C:024). |
| Wording | No "multiple approaches" or "think deeply" by default. Reasoning tokens rose 1.6 to 7.4 times at similar success (C:026). |

Never pipe compressed output into shell counting or parsing. One study produced silently wrong answers (C:024).

## Cache interaction

History edits break the exact-prefix cache. So:

1. Edit history only at a trigger, not every turn (C:065, C:066).
2. Clearing invalidates the cached prefix. Keeping thinking blocks preserves it (C:065).
3. Keep tools, order, model and effort fixed mid-session. A timestamp at the prompt top dropped reuse from 87 to 3 percent (A:224, A:204).
4. Adding or removing Model Context Protocol (MCP) tools invalidates the cache (C:055).
5. Protect results that cannot be re-fetched with `exclude_tools`, and write state to a handoff or memory file before clearing (C:067, C:035).

## What Token Economics can do from where

| Place | Can | Cannot |
|---|---|---|
| Gateway | Set `max_tokens`. Inject or strip `cache_control`. Flag volatile prefix text. Cap tool-result size before forwarding. Defer MCP tools. Add `context_management` if the client allows it. Break rate-based loops. | Edit history without breaking the cache. See hidden thinking. |
| Hook | PostToolUse `updatedToolOutput` to filter or cap. PreCompact block or add instructions. Command hooks cost no model tokens. | Enforce against a developer who disables unmanaged hooks. |
| Needs the harness | Transcript masking with a tuned window. Turn caps with reminders. Skill loading. Subagent settings. | Not available through a gateway. |

Sources: A:204, A:284, C:055, C:060, C:062, C:065, C:074, C:090.

## Loop guard

Rate-based breaker for repeated reads, unchanged test reruns and repeated failures (A:059, C:028, C:062). Detect the first repeated-failure signature, redirect once, then stop. Repeated retrieval and unchanged reruns hit 79 to 98 percent of tasks and 6.86 to 22.75 percent of cost (A:059).

## Conflicts

| Question | Evidence | Token Economics default |
|---|---|---|
| Compressors | C:024 and C:028 show losses. C:060 and C:107 claim 45 to 95 percent, vendor-reported. | Off |
| Masking vs summaries | C:130 and C:133 favour masking. C:122 reports up to 2x per-turn saving with no threshold. | Masking |
| Compaction vs cache | C:112 says it destroys the cache. C:055 says it reuses the parent prefix. A:224 shows a miss and net loss. | Last resort |
| Compaction threshold | About 50 percent (C:112), about 90 percent (C:106), window minus 33,000 (C:007) | Per harness, no head-to-head exists |
| Budget visibility | Helps (C:025, C:131). Agents ignored it (C:136). | Enforce outside the agent |

## Experiments before enabling a control

1. Replicate C:024 on our harnesses: RTK, Headroom and none, three repeats, cache reset between arms.
2. Sweep masking window (5, 10, 20) and trigger (30k, 60k, 100k) per scaffold on billed cost with caching on.
3. Compare clearing yield (3k, 5k, 10k) against compaction at 150K, counting cache rewrites.
4. Measure compaction break-even at 50K, 100K and 200K contexts, and accuracy after 1, 2 and 3 compactions.
5. A/B tool deferral at about 20, 50 and 90 tools: billed cost, selection accuracy, extra lookup turns.
6. Sweep the output cap at 6k, 12k and 25k.
7. Prototype a proxy-only guard (hit monitor, `max_tokens`, loop breaker, output cap) and measure the saving with no harness change.

Not in the corpus: billed saving from schema deferral, net saving from subagent isolation, LLMLingua on agent traces, hosted-API support for output-length tricks.
