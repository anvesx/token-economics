# Changelog: token-economics-svc-tenancy

## 0.1.0

- First version (P0).

## 0.2.0

- `KeyStore`: hashed virtual keys, issue, resolve, revoke (append-only), list, legacy `keys.json` import.
- `AuditLog`: append-only audit table that refuses secret-looking values.
- Entry points `keys` and `audit`.

## Unreleased (P3)

- `AdminAuth`: hashed admin tokens with roles viewer, operator, admin; resolve, revoke, audited.
- `ChangeStore`: policy and price-book changes with a second approver, as append-only events; a policy approval writes
  `policy.json` atomically.
- `FileRetention`: per-tenant retention for the metadata JSONL logs; never the ledger, price book or audit log.
- Entry points `admin_auth`, `changes` and `retention` (run `uv sync`). Three new append-only tables in `tenancy.sqlite`.
