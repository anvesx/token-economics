# token-economics-feat-cache-hit-monitor

Cache hit rate and miss events per caller.

Kind: feature. Phase: P2. May import: token-economics-contracts.

Run alone: `uv run --package token-economics-feat-cache-hit-monitor pytest features/cache-hit-monitor`

## What it does

Observe only: `before` allows everything and nothing is rewritten. `after` accumulates, per caller scope
(`row.caller`, else key caller, key id, tenant) and model, read, write (5m + 1h) and fresh tokens and calls.
Hit rate = read / (read + write + fresh). Works on ledger rows, so it is provider-neutral (no `providers/` files).

- Miss: a call that is not the first in its session, with reprocessed (the previous call's prompt, which it cached, minus what this call read back from cache) at least 2,000 tokens and more
  than 5 percent of its prompt tokens. Appended to `cache_misses.jsonl` with ts, caller, session_id, model,
  reprocessed, prompt_tokens, gap_s and reason: `model_changed`, `ttl_expired` (gap over 300 s, or over 3600 s once
  the session has written 1h cache), else `prefix_changed`. No prompt text.
- `cache_monitor.json`: per caller and model calls, tokens, hit_rate, misses. Atomic, at most every `persist_interval_s`.
- Optional drop alert: with `alert_below` set, when a caller's hit rate over its last `window` calls (at least
  `min_calls`) is below it, one record goes to `alerts.jsonl` per caller per UTC day (same file as budgets; it has
  `"kind": "cache_hit_rate"`, and `scope`, `window`, `period`, `threshold` like a budget alert).

## Config keys

| key | default |
|---|---|
| `alert_below` | null (off) |
| `min_calls` | 50 |
| `window` | 200 |
| `max_sessions` | 10000 (LRU) |
| `persist_interval_s` | 30 |

## Unverified

- "1h written" is sticky for the session, so a 1h write followed by 5m writes still uses the 3600 s limit.
- Per-caller/model totals are in memory only and restart at zero; the snapshot file is not reloaded.
- Memory per caller and model is not bounded (a handful of entries each); sessions are.
