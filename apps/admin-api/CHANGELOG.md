# Changelog: token-economics-app-admin-api

## Unreleased

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
