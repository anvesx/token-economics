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

Open `http://127.0.0.1:8788/`. A top bar switches between views (hash routes, so back and reload work) and a 1 / 7 / 30
day selector applies to all of them. Overview, Sessions, Session detail and Categories read your own Claude Code
transcripts through the insight `session_views` service; they load on navigation, are kept in memory per period, and
have a Refresh button (an analysis takes several seconds the first time). Only Gateway refreshes every 10 seconds.

- `#overview`: tiles (spend, sessions, tasks, average cost per task, estimated leak cost), spend by token type, model and
  project (top 8), top leak categories, most expensive sessions.
- `#sessions`: every session with search, project filter, sort (newest, cost, leak cost, tasks) and "show more" in
  steps of 50. A row opens `#session/<id>`.
- `#session/<id>`: the session's facts, its tasks in order (cost and share, calls, edits, top tools, why a new task
  started) and its leaks. Says whether tasks were split by a model or by the simple rule.
- `#categories`: the curated leak categories (cost, share, findings, sessions, note), a group filter, "Spend to review",
  and the retired categories. Costs overlap, so they do not add up to the total.
- `#gateway`: the original page. Headline tiles (spend, requests, cache hit rate, blocked requests, unpriced requests as a warning), spend per UTC day,
tables by caller, model and tenant (requests, spend, share, cache hit, median and P95 spend per active day), top
sessions, recent requests, one progress bar per budget (amber at 75%, orange at 90%, red at 100%), and the recent policy
decisions and budget alerts. With no ledger it says "No traffic yet: point Claude Code at the gateway."

Gateway costs are estimates at price-book rates (cost_source = gateway), not bills; session, task and category
figures are estimates at API list prices from your transcripts. No prompt or response text is stored, so
none can be shown. The page is one static file (`static/index.html`): no CDN, no external requests, no build step, and
it puts server data into the page with `textContent` only. Responses carry `Cache-Control: no-store`, and the page a
`Content-Security-Policy` that allows only its own inline script and requests to its own origin.

Privacy: session titles are the first characters of your own prompts, read live from your own transcripts and shown only
here; nothing is stored or sent. With `--prompt-check` prompt text is sent to a model (Sonnet, through your own Claude
Code login) so tasks are split more accurately; it is off by default, and labels the Hermes plugin already cached are
reused either way.

## Run

```bash
uv sync --all-packages                      # or: pip install "token-economics-app-admin-api[all]"
token-economics-admin                       # http://127.0.0.1:8788/ ; --host and --port to change
token-economics-admin --transcripts PATH    # transcripts, default ~/.claude/projects
token-economics-admin --prompt-check        # model-labelled task split; sends prompt text to the model
```

The state directory is `TOKEN_ECONOMICS_STATE_DIR` (default `~/.token-economics`), the same as the CLI. The app never
creates the ledger. `create_app(state_dir, load=..., transcripts_root=None, prompt_check=False)` builds the app; tests inject `load` to fake
services. The `session_views` service is built once, on first use, with `state_dir/detectors` as its state directory.

## Endpoints (GET only)

| path | returns |
|---|---|
| `/` | the dashboard page |
| `/api/summary?days=30` | the insight `dashboard_summary` as JSON (money as strings) plus `has_ledger`; `days` is 1 to 365 |
| `/api/overview?days=30` | the `session_views` overview: sessions, categories, retired rows and spend by token type, model and project |
| `/api/sessions/{id}?days=30` | one session with its tasks and leaks; 404 if unknown in the period (full id or first 8 characters) |
| `/api/budgets` | list of budget windows (`scope`, `window`, `limit_usd`, `spent_usd`, `reserved_usd`, `used_share`) from the `budget_status` service; `[]` if it is not installed |
| `/api/decisions?limit=200` | last N lines of `decisions.jsonl` as objects, oldest first |
| `/api/alerts?limit=200` | same for `alerts.jsonl` |
| `/api/rejects?limit=100` | same for `rejects.jsonl` (responses that produced no ledger row) |
| `/api/keys` | `key_id`, `tenant`, `team`, `caller`, `created_at`, `revoked_at` from the `keys` service; never plaintext or hashes |

Missing files give `[]`; unparseable lines are skipped; `limit` is 1 to 1000. A bad number gives 400. If the insight
service is not installed `/api/summary`, `/api/overview` and `/api/sessions/{id}` give 503.

## Not built

- A write API: keys, budgets and policies are changed through the CLI.
- Authentication and roles.
- A tenant filter (the page shows every tenant).
- The Grafana option from the plan (a Grafana data source over the same JSON).
