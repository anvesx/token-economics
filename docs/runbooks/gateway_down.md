# gateway_down

Severity: page. Source: apps/gateway: health probe on /_te/health. Owner: see `ops/alerts.json` (currently UNASSIGNED until a person is named).

State dir below is `$TOKEN_ECONOMICS_STATE_DIR`, default `~/.token-economics`.

## What it means

The gateway does not answer on its port. Every coding agent pointed at it gets connection errors, so developers cannot work and nothing is priced or budgeted.

## Who is affected

Everyone whose harness base URL is the gateway.

## First checks

```bash
curl -s 127.0.0.1:8787/_te/health
lsof -i :8787
df -h ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics} && ls -la ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}
uv run token-economics policy show   # a broken policy.json shows up here
```

## Actions

1. Restart: `uv run token-economics-gateway --port 8787` (same state dir, same environment).
2. If it will not start, read its stderr. Usual causes: port in use, disk full, unreadable `policy.json` or `keys.json`, locked SQLite file.
3. If a bad optimisation caused crashes, switch it off first (`uv run token-economics policy kill <feature>`) and restart.
4. If it cannot be fixed fast, developers can point the harness straight at the provider. That loses metering and every budget until the gateway is back: tell the plan owner.

## Confirm recovery

`curl -s 127.0.0.1:8787/_te/health` returns `"status": "ok"`, `curl 127.0.0.1:8787/_te/stats` shows `rows` rising under live traffic, and the ledger has new rows (`uv run token-economics report --days 1`).

## Escalation

Page the alert owner in `ops/alerts.json`. If there is no answer in 15 minutes, go to the plan owner.

Kill switches and CLI verbs: see [README.md](README.md).
