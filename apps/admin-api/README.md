# token-economics-app-admin-api

Reports and the local dashboard over HTTP.

Kind: app. Phase: P1. May import: token-economics-contracts (plus starlette and uvicorn). Every service is found
through entry points; if one is not installed, the part of the page that needs it stays empty.

Run alone: `uv run --package token-economics-app-admin-api pytest apps/admin-api`
(the tests that need a real ledger and the insight summary skip themselves unless the `test` extra is installed).

## Authentication and roles

By default (no admin tokens, no `--require-auth`) this is the local read-only dashboard: no login, no TLS, bound to
`127.0.0.1`, every write route refused with 403. Never expose it to a network in that mode.

Once any admin token exists, or with `--require-auth`, every `/api` route needs `Authorization: Bearer <admin token>`
(401 if missing, wrong or revoked; 403 if the role is too low). The static page at `/` holds no data and stays open.
Revoking every token does not reopen the API. Tokens are never echoed in a response, a log line or the audit log.

| Role | May |
|---|---|
| viewer | every GET: the dashboard routes, `GET /api/kills`, `/api/audit`, `/api/changes` |
| operator | also `POST /api/kills` `{feature, tenant, reason}` and `DELETE /api/kills` `{feature, tenant}` (recorded as `admin:<name>`) |
| admin | also `POST /api/changes` `{kind: "policy"|"price_book", payload}`, `POST /api/changes/{id}/approve` and `/reject`, `GET/POST/DELETE /api/admin-tokens` (issue `{name, role}` shows the token once) |

A change needs a second approver: the admin who proposed it cannot approve it (403), and a change is decided once (409).
Approving a policy change writes `policy.json`. Approving a price-book change only records the approval; the price book
is append-only and has its own path, so nothing is applied. Canary share has no route yet.

First token: `token-economics-admin --issue-admin-token ann` (role admin; `--role` for others). It needs file access to
the state directory, which is the trust boundary. The page has no section for these routes; use the API.

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
- `#task/<session id>/<n>`: one task in full, reached by clicking a task on the session page. Breadcrumb with previous
  and next task; header (title, start, duration, models, why a new task started); tiles (cost and share of the session,
  model calls, tool calls, failed calls, edits, peak context, cache hit rate, thinking tokens, and warning chips for
  interrupted turns, compactions and cache rewrites after idle); where the tokens went (spend by token type with the raw
  token counts, spend by model, main thread vs agents); a context-size chart; tool calls; the 15 largest tool results;
  files; agents; the prompts; and a call timeline (first 100 rows, "Show more", costliest first or in order).
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
| `/api/sessions/{id}/tasks/{n}?days=30` | one task in full (summary fields plus spend by token type and model, tools, files, largest results, turns, agents, context series, call timeline); 404 if the session or task is unknown or `n` is not a positive integer |
| `/api/budgets` | list of budget windows (`scope`, `window`, `limit_usd`, `spent_usd`, `reserved_usd`, `used_share`) from the `budget_status` service; `[]` if it is not installed |
| `/api/decisions?limit=200` | last N lines of `decisions.jsonl` as objects, oldest first |
| `/api/alerts?limit=200` | same for `alerts.jsonl` |
| `/api/rejects?limit=100` | same for `rejects.jsonl` (responses that produced no ledger row) |
| `/api/keys` | `key_id`, `tenant`, `team`, `caller`, `created_at`, `revoked_at` from the `keys` service; never plaintext or hashes |

Missing files give `[]`; unparseable lines are skipped; `limit` is 1 to 1000. A bad number gives 400. If the insight
service is not installed `/api/summary`, `/api/overview`, `/api/sessions/{id}` and `/api/sessions/{id}/tasks/{n}` give 503.

## Not built

- A write API: keys, budgets and policies are changed through the CLI.
- Authentication and roles.
- A tenant filter (the page shows every tenant).
- The Grafana option from the plan (a Grafana data source over the same JSON).
