# token-economics-app-admin-api

Reports and the local dashboard over HTTP.

Kind: app. Phase: P1. May import: token-economics-contracts (plus starlette and uvicorn). Every service is found
through entry points; if one is not installed, the part of the page that needs it stays empty.

Run alone: `uv run --package token-economics-app-admin-api pytest apps/admin-api`
(the tests that need a real ledger and the insight summary skip themselves unless the `test` extra is installed).

## NO AUTHENTICATION: keep it on localhost

This app has no login, no roles and no TLS. It binds to `127.0.0.1` by default and warns if you pick another host.
Never expose it to a network. Everything it shows (callers, tenants, spend, key ids) is readable by anyone who can
reach the port.

## What the page shows

Open `http://127.0.0.1:8788/`. It refreshes every 10 seconds and has a 1 / 7 / 30 day selector.
Headline tiles (spend, requests, cache hit rate, blocked requests, unpriced requests as a warning), spend per UTC day,
tables by caller, model and tenant (requests, spend, share, cache hit, median and P95 spend per active day), top
sessions, recent requests, one progress bar per budget (amber at 75%, orange at 90%, red at 100%), and the recent policy
decisions and budget alerts. With no ledger it says "No traffic yet: point Claude Code at the gateway."

Costs are estimates at price-book rates (cost_source = gateway), not bills. No prompt or response text is stored, so
none can be shown. The page is one static file (`static/index.html`): no CDN, no external requests, no build step, and
it puts server data into the page with `textContent` only. Responses carry `Cache-Control: no-store`, and the page a
`Content-Security-Policy` that allows only its own inline script and requests to its own origin.

## Run

```bash
uv sync --all-packages                      # or: pip install "token-economics-app-admin-api[all]"
token-economics-admin                       # http://127.0.0.1:8788/ ; --host and --port to change
```

The state directory is `TOKEN_ECONOMICS_STATE_DIR` (default `~/.token-economics`), the same as the CLI. The app never
creates the ledger. `create_app(state_dir, load=...)` builds the app; tests inject `load` to fake services.

## Endpoints (GET only)

| path | returns |
|---|---|
| `/` | the dashboard page |
| `/api/summary?days=30` | the insight `dashboard_summary` as JSON (money as strings) plus `has_ledger`; `days` is 1 to 365 |
| `/api/budgets` | list of budget windows (`scope`, `window`, `limit_usd`, `spent_usd`, `reserved_usd`, `used_share`) from the `budget_status` service; `[]` if it is not installed |
| `/api/decisions?limit=200` | last N lines of `decisions.jsonl` as objects, oldest first |
| `/api/alerts?limit=200` | same for `alerts.jsonl` |
| `/api/rejects?limit=100` | same for `rejects.jsonl` (responses that produced no ledger row) |
| `/api/keys` | `key_id`, `tenant`, `team`, `caller`, `created_at`, `revoked_at` from the `keys` service; never plaintext or hashes |

Missing files give `[]`; unparseable lines are skipped; `limit` is 1 to 1000. A bad number gives 400. If the insight
service is not installed `/api/summary` gives 503.

## Not built

- A write API: keys, budgets and policies are changed through the CLI.
- Authentication and roles.
- A tenant filter (the page shows every tenant).
- The Grafana option from the plan (a Grafana data source over the same JSON).
