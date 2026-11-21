# token-economics-svc-tenancy

Virtual keys hashed at rest, revocation and the append-only audit log.

Kind: service. Phase: P1. May import: token-economics-contracts, token-economics-redaction.

Run alone: `uv run --package token-economics-svc-tenancy pytest services/tenancy`

## What it does
Virtual keys (`vk-` plus 24 random bytes, urlsafe) for the gateway. The plaintext is returned once at issue and never
stored or logged. The database holds only the SHA-256 digest as raw bytes (so the hex text and the plaintext appear
nowhere in the file), the 16-hex `key_id`, and the key's tenant, team, caller and agent. Keys are revoked, never
deleted: every table (`keys`, `revocations`, `audit`) is append-only, with triggers that abort UPDATE and DELETE.
Revocation is a row in `revocations`. State lives in `state_dir/tenancy.sqlite` (WAL, one locked connection).

## API
- `KeyStore(state_dir)`, `KeyStore.in_memory()` (for tests)
  - `issue(info, *, actor="cli") -> (plaintext, key_id)`
  - `resolve(presented) -> ResolvedKey` (the `KeyResolver` port): `none` for an empty key, `unknown`, `revoked`, `active`.
    Hashes are compared with `hmac.compare_digest`. Resolution reads an in-memory map that reloads at most every
    0.5 s, so a key revoked by another process (the CLI) takes effect within about a second.
  - `revoke(key_id, *, actor="cli") -> bool`
  - `list() -> list[KeyRecord]` (key_id, info, created_at, revoked_at; never plaintext or hash)
  - `import_legacy(path) -> int`: imports a P0 plaintext `keys.json`, overwrites it with a note and renames it
    `keys.json.imported`. Idempotent.
- `AuditLog`: `record(action, subject, detail, actor="system")`, `entries(since=None)`. A value containing `vk-` or
  `sk-ant` raises `ValueError`. `KeyStore.audit` is the log in the same database.
- Entry points (`token_economics.services`): `keys` -> `open_keys(state_dir)` (creates the directory, imports
  `keys.json` if present), `audit` -> `open_audit(state_dir)`.

## Not built
Roles and authorisation, a policy-as-code store, a secrets vault, a second-approver rule, a key rotation schedule.

## Unverified
- A key revoked by another process is seen within the 0.5 s refresh; tested to 2 s on one machine, not on a network
  file system (SQLite WAL needs shared memory, so state_dir must be local).
- `key_id` is the first 16 hex chars of the digest; collisions are not handled beyond the primary-key error.
