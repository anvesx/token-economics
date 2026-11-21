# Changelog: token-economics-svc-tenancy

## 0.1.0

- First version (P0).

## 0.2.0

- `KeyStore`: hashed virtual keys, issue, resolve, revoke (append-only), list, legacy `keys.json` import.
- `AuditLog`: append-only audit table that refuses secret-looking values.
- Entry points `keys` and `audit`.
