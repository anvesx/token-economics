# token-economics-feat-harness-adapters

Connect a harness to the gateway: one file per harness, five functions each.

Kind: feature. Phase: P0. May import: token-economics-contracts.

Run alone: `uv run --package token-economics-feat-harness-adapters pytest features/harness-adapters`

## What it does

One file per harness under `src/token_economics_feat_harness_adapters/providers/`. Each defines `ADAPTER`, an object implementing the `Adapter` port from contracts (`name`, `provider`, `capabilities`, and the five functions `route`, `matches`, `identify`, `observe`, `cap`, `replay`). Wire parsing is shared in the private modules `_anthropic_wire.py` (Messages API) and `_responses_wire.py` (OpenAI Responses), with SSE parsing in `_sse.py`.

| Adapter | Provider | Route | Notes |
|---|---|---|---|
| `claude_code` | anthropic | `ANTHROPIC_BASE_URL`, `ANTHROPIC_CUSTOM_HEADERS: x-token-economics-key: <key>` | cap maps `budget_usd`, `max_turns` to `--max-budget-usd`, `--max-turns`; replay reads a transcript JSONL |
| `sdk` | anthropic | `ANTHROPIC_BASE_URL`, `TOKEN_ECONOMICS_KEY` (client must send it as header `x-token-economics-key`) | fallback match for any POST to `/v1/messages` |
| `codex` | openai | `model_providers.token-economics.*` config keys, `/v1` appended | Responses wire only |

`observe` is called once with the complete, decompressed response body (JSON or SSE). It never raises and returns None for non-2xx, empty, unparseable or usage-less bodies. The provider's `usage` object passes through raw; Anthropic streams merge each `message_delta` usage over `message_start`'s, so final `output_tokens` replace the placeholder. A stream cut before any `message_delta` still reports `message_start`.

`replay`: Claude Code keeps the last usage per message id, one observation per id in first-seen order, skipping `<synthetic>` and usage-less lines. Codex and SDK `replay` return nothing: not built.

Entry points (`token_economics.adapters`): `claude_code`, `sdk`, `codex`.

## Run alone

`uv run --package token-economics-feat-harness-adapters pytest features/harness-adapters`

## Unverified

None of these were checked against real traffic. A P0 spike should confirm each one:

1. Claude Code sends `user-agent` starting `claude-cli` on `/v1/messages` requests (used by `matches`).
2. Header `x-claude-code-session-id` carries the session id (used by `identify`).
3. Otherwise the session id is in the body's `metadata.user_id`, either as text containing `session_<id>` or as a JSON string with a `session_id` field.
4. Sub-agent requests carry `x-claude-code-agent-id` (or `x-claude-code-parent-session-id`); the header names are guesses.
5. Claude Code OAuth tokens start `sk-ant-oat` (used for `auth_mode = oauth`).
6. `ANTHROPIC_CUSTOM_HEADERS` takes the form `name: value` and Claude Code sends it on every request.
7. Codex sends the session id in header `session_id` or `conversation_id`.
8. Codex requests go to a path ending `/responses`, and the gateway serves `/v1` under the base URL given to `model_providers.token-economics.base_url`.
9. Anthropic returns `request-id` and OpenAI `x-request-id` as response headers.
10. The Responses stream ends with a `response.completed` event whose `response` holds `id`, `model`, `usage` and `service_tier`.
11. The SDK adapter's `TOKEN_ECONOMICS_KEY` is only a convention: the client code must add the header itself.
12. Claude Code transcript line shape (`type: assistant`, `message.id`, `message.model`, `message.usage`) was read from local files, not from documentation, and may change between versions.
