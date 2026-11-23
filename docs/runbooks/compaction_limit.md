# compaction_limit

Severity: info. Source: features/compaction-guard: Decision code compaction_limit (HTTP 429). Owner: see `ops/alerts.json` (currently UNASSIGNED until a person is named).

State dir below is `$TOKEN_ECONOMICS_STATE_DIR`, default `~/.token-economics`.

## What it means

A session was compacted so many times that the guard refuses more requests; each compaction rewrites the cache and loses detail.

## Who is affected

One developer session at a time.

## First checks

```bash
uv run token-economics policy show
cat ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/compaction_guard.json 2>/dev/null | head -c 500
```

## Actions

1. Normal case: start a new session. No action.
2. If it fires too early across many sessions: raise the limit with `uv run token-economics policy set compaction_guard restart_at <n>`.
3. If it is blocking real work: `uv run token-economics policy kill compaction_guard`.

## Confirm recovery

A new session works; `policy show` shows the intended limit.

## Escalation

Info level. Tell the owner if it recurs for the same caller.

Kill switches and CLI verbs: see [README.md](README.md).
