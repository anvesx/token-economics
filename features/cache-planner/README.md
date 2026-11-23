# token-economics-feat-cache-planner

Pick the 5-minute or 1-hour cache TTL from the observed reuse gap.

Kind: feature. Phase: P2. May import: token-economics-contracts.

Run alone: `uv run --package token-economics-feat-cache-planner pytest features/cache-planner`

## What it does

Rewrites the TTL of the `cache_control` breakpoints a client already placed (system blocks, tools, message content
blocks) to the cheaper of 5 minutes and 1 hour for that prompt prefix. It never adds a breakpoint. Anthropic only
(`providers/anthropic.py`); Gemini, OpenAI and xAI are not built.

- Prefix key: sha256 of (model, tools, system) plus the caller scope (`key.caller`, else key id, else tenant) and
  the harness. Judged per caller, not per account.
- Per key it keeps the last `max_gaps` gaps between uses. Once it has `min_samples`, it costs both TTLs in units of the
  input price: one initial write, then per gap a read if the gap fits the TTL (300 s / 3600 s) else a rewrite.
  The cheaper wins; a tie keeps what the client sent.
- Ratios come from the price book for the model (cache_read, cache_write_5m, cache_write_1h over input); defaults
  0.1 / 1.25 / 2.0 when there is no price book or no row.
- Every breakpoint is set to the same TTL. `1h` sets `"ttl": "1h"`; 5m drops the `ttl` key (the default).
- The choice is frozen per session (bounded LRU), so a session never flips TTL midway. A tie freezes as "as sent".
- Note in the decisions log: `cache ttl 5m->1h (n=24 gaps, p50 840s)`; numbers only.
- State: `cache_planner.json` in the state dir (hashes, timestamps and gaps only), written atomically, at most every
  `persist_interval_s`; a corrupt file is a cold start.

## Config keys

| key | default |
|---|---|
| `min_samples` | 10 |
| `max_gaps` | 100 |
| `max_keys` | 5000 (LRU) |
| `max_sessions` | 10000 (LRU) |
| `persist_interval_s` | 30 |

## Unverified

- Against the real API: that the planner's 5m/1h choice raises the hit rate, and that dropping `ttl` is accepted
  everywhere a `ttl: "5m"` would be.
- The initial-write term means a client that sent 1h with all-short gaps is moved down to 5m, and one sending 1h
  with gaps beyond an hour is also moved to 5m (nothing is read back in either case, so 5m is strictly cheaper).
- Gaps are measured between requests with the same prefix and scope, including parallel sub-agent calls.
