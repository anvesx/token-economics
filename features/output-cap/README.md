# token-economics-feat-output-cap

Cap oversized tool results before they are sent, never cutting tracebacks or edit anchors.

Kind: feature. Phase: P2. May import: token-economics-contracts.

Run alone: `uv run --package token-economics-feat-output-cap pytest features/output-cap`

## What it does

A `Feature` and `Rewriter` (`name = "output_cap"`, `fail_closed = False`). Its `rewrite` caps oversized `tool_result` text in Anthropic Messages bodies before they are sent. A capped result keeps the head (`head_share` of the allowed characters) and the tail, with one line between them: `[token-economics: N characters removed from this tool result]`. Only text is capped (a string, or `{"type": "text"}` blocks); images and other blocks are untouched. Each text block is capped on its own.

Never capped: results of a protected tool (they are edit anchors), results with `is_error: true`, and results whose text matches a protected pattern (tracebacks, stack frames, test failures). The tool name comes from the matching `tool_use` block in an earlier assistant message; an unknown id counts as unprotected. The note is counts only: `capped 2 tool results, 180000 chars removed`.

## Config

```json
{"limit_tokens": 25000, "chars_per_token": 4, "head_share": 0.7,
 "protect_tools": ["Read", "Edit", "MultiEdit", "Write", "NotebookEdit", "NotebookRead"],
 "protect_patterns": ["<regex>", "..."]}
```

The allowance is `limit_tokens * chars_per_token` characters. The plan suggests 25,000 tokens interactive and 6,000 to 12,000 batch. `protect_tools` and `protect_patterns` replace their defaults (Python, JS, Java, Go and Rust traces and frames, `FAILED`, `AssertionError`, `panic:`, `error[E`, pytest failure summaries); a regex that does not compile is dropped. Bad values fall back to defaults.

## Prompt cache

Claude Code resends the whole history, and the cap depends only on the text and the config, so a result capped on turn 5 is capped identically on turn 6 and the cached prefix stays stable. The first turn the cap applies it changes the prefix once.

## Unverified

Characters stand in for tokens (`chars_per_token`); no tokenizer is used. Patterns are heuristics, tested on small samples only. Not run against a live agent session; whether head+tail loses information an agent needs is a question for the P2 eval.
