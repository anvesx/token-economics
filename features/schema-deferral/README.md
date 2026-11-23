# token-economics-feat-schema-deferral

Defer tool schemas when there are many tools, keeping a server-side search path.

Kind: feature. Phase: P2. May import: token-economics-contracts.

Run alone: `uv run --package token-economics-feat-schema-deferral pytest features/schema-deferral`

## What it does

A `Feature` and `Rewriter` (`name = "schema_deferral"`, `fail_closed = False`). For an Anthropic Messages body it fires when there are more than `min_tools` tools, or the estimated schema tokens (`len(json.dumps(tools)) / 4`) exceed `min_share` of `ctx.facts.est_input_tokens` (the share rule is skipped when that estimate is 0). It then sets `"defer_loading": true` on custom tools not in `keep`, appends the search tool and adds the beta header. The note is `deferred N of M tools`.

It does nothing when any tool already has `defer_loading` or a type starting `tool_search_tool` (the harness manages tool search; recent Claude Code does this for MCP tools), when deferring would leave no loaded tool, for non-Anthropic providers, or for odd bodies. Server tools (a `type` other than `custom`) are never deferred. The body is copied, never mutated; the same tool list gives the same output.

## Config

```json
{"min_tools": 20, "min_share": 0.10, "keep": ["Bash", "Read", "Edit", "MultiEdit", "Write", "Glob", "Grep", "Task",
 "Agent", "TodoWrite", "WebFetch", "WebSearch", "NotebookEdit", "Skill"],
 "search_tool": {"type": "tool_search_tool_regex_20251119", "name": "tool_search_tool_regex"},
 "beta": "advanced-tool-use-2025-11-20"}
```

Invalid values fall back to the default.

## Cache interaction

The tool list is part of the cached prefix. The rewrite is a pure function of the tool list, so a stable list stays stable, but the first rewritten request misses the cache. If the harness changes its tool list mid-session the prefix changes anyway.

## Unverified

The search tool type and name, the beta value and the `defer_loading` field are configurable guesses, not checked against the live API. Claude Code over a subscription login may not accept the beta header. Verify before enabling in `enforced`.
