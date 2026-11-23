# cache_hit_rate

Severity: ticket. Source: features/cache-hit-monitor: alert kind cache_hit_rate (alerts.jsonl). Owner: see `ops/alerts.json` (currently UNASSIGNED until a person is named).

State dir below is `$TOKEN_ECONOMICS_STATE_DIR`, default `~/.token-economics`.

## What it means

A caller's cache hit rate over the recent window fell below the configured `alert_below`. At most one alert per caller per UTC day. A drop means money is being spent re-reading context at full price (a prefix changed, a TTL expired, a model switched, `cache_control` was stripped).

## Who is affected

The caller named in `scope`; cost rises for them until fixed.

## First checks

```bash
tail -n 20 ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/alerts.jsonl
tail -n 20 ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/cache_misses.jsonl   # reason: prefix_changed, ttl_expired or model_changed
cat ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/cache_monitor.json | head -c 800
uv run token-economics policy show
uv run token-economics report --days 1
```

## Actions

1. Read the `reason` in the recent misses. `ttl_expired`: normal for idle sessions. `model_changed`: a router or sticky-model setting is switching models. `prefix_changed`: something rewrites the start of the prompt.
2. If a rewriting optimisation was turned on recently, kill it: `uv run token-economics policy kill <feature>` (candidates: `cache_planner`, `observation_masking`, `context_clearing`, `rules_router`, `schema_deferral`).
3. If the harness changed (new client version), tell the owner: it may have changed how it sends `cache_control`.

## Confirm recovery

The next day's hit rate for the caller is back above the threshold in `cache_monitor.json`, and no new alert for them.

## Escalation

Ticket the owner. If a kill fixed it, hand the feature owner the miss log.

Kill switches and CLI verbs: see [README.md](README.md).
