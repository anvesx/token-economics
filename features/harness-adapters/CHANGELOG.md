# Changelog: token-economics-feat-harness-adapters

## 0.2.0

- `Adapter.facts()` on all three adapters: model, max tokens, stream, turns, size estimate, repeated-failure signature (Anthropic wire). Codex: turns and failures not built.

## 0.1.0

- First version (P0).

## 0.1.0 (continued)

- Adapters `claude_code`, `sdk`, `codex` with route, matches, identify, observe, cap, replay.
- Shared Anthropic Messages and OpenAI Responses wire parsing (JSON and SSE).
- Codex and SDK `replay` are not built (empty).
