# Changelog: token-economics-app-admin-api

## Unreleased

- Roles and the second approver (P3): `Authorization: Bearer <admin token>` on every `/api` route once any admin token
  exists or with `--require-auth`. New routes `GET/POST/DELETE /api/kills`, `GET /api/audit`,
  `GET/POST /api/changes`, `POST /api/changes/{id}/approve|reject`, `GET/POST/DELETE /api/admin-tokens`.
  `--issue-admin-token NAME [--role R]` prints a first token once. Without tokens the app is unchanged and read-only,
  and write routes are refused.

- Transcript views: `/api/overview` and `/api/sessions/{id}` over the insight `session_views` service (built once, lazily);
  `create_app(..., transcripts_root, prompt_check)`; flags `--transcripts` and `--prompt-check`.
- The page now has views with hash routes (overview, sessions, session detail, categories, gateway). The gateway view is
  the previous page, unchanged in content; only it auto-refreshes.

- Task detail: `GET /api/sessions/{id}/tasks/{n}` over `session_views.task`, and the page view `#task/<session id>/<n>`
  (token spend, tools, largest results, files, agents, prompts, context chart, call timeline). Each task card on the
  session page links to it.

## 0.1.0

- First version (P0).
- Read-only dashboard app: `create_app(state_dir, load=...)`, `token-economics-admin` (localhost, port 8788), the
  endpoints `/api/summary`, `/api/budgets`, `/api/decisions`, `/api/alerts`, `/api/rejects`, `/api/keys` and one static
  self-contained page at `/`. No authentication; no write endpoints.
