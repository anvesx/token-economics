# Changelog: token-economics-app-admin-api

## 0.1.0

- First version (P0).
- Read-only dashboard app: `create_app(state_dir, load=...)`, `token-economics-admin` (localhost, port 8788), the
  endpoints `/api/summary`, `/api/budgets`, `/api/decisions`, `/api/alerts`, `/api/rejects`, `/api/keys` and one static
  self-contained page at `/`. No authentication; no write endpoints.
