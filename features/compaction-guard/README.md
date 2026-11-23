# token-economics-feat-compaction-guard

Count compactions per session and recommend a restart at the third.

Kind: feature. Phase: P2. May import: token-economics-contracts.

Run alone: `uv run --package token-economics-feat-compaction-guard pytest features/compaction-guard`

## What it does

A `Feature` (`name = "compaction_guard"`, `fail_closed = False`). It never rewrites a request.

- `after`: for main-thread calls (`query_source == main`) with a session id and a ledger row, a compaction is counted when this call's prompt tokens are below `drop_ratio` times the previous main call's prompt tokens in that session and that previous call was at least `min_prompt`.
- `before`: once a session's count reaches `restart_at`, refuses with status 429, code `compaction_limit`, telling the developer to start a new session. In advisory mode the engine only logs this.

The detection is a heuristic: a big drop in prompt tokens inside one session. It cannot see the compaction itself, so a manual `/clear`-style trim, a branch rewind or a large tool result being dropped can look the same.

## Config

```json
{"restart_at": 3, "drop_ratio": 0.5, "min_prompt": 50000}
```

Invalid values fall back to the default.

## State

`<state_dir>/compaction_guard.json`: per session id, the count, the last prompt tokens and the last-seen time. Numbers and ids only, no text. Loaded at create, written atomically (temp file and replace), sessions unseen for 7 days are pruned, and a corrupt file starts empty. State is guarded by a lock because the gateway calls from worker threads.

## Cache interaction

None; the request is not changed. The recommendation exists because a compaction rewrites the cached prefix and loses detail (plan/06, compaction as a last resort).
