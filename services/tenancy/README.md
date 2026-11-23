# token-economics-svc-tenancy

Virtual keys hashed at rest, revocation, the append-only audit log, admin tokens with roles, second-approver changes
and log retention.

Kind: service. Phase: P1 (keys, audit), P3 (admin tokens, changes, retention). May import: token-economics-contracts, token-economics-redaction.

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
- `AdminAuth`: admin tokens (`adm-` plus 24 random bytes) with roles `viewer` < `operator` < `admin`
  (`role_at_least`). `issue(name, role, actor=)` returns the plaintext once; only the SHA-256 digest is stored.
  `resolve(token) -> AdminIdentity | None` reads the database on every call, so a revoked token is refused at once.
  `revoke(token_id)`, `list()`, `has_tokens()` (true once any token was ever issued, so revoking the last one does not
  reopen the admin API). Names are unique. All of it is audited.
- `ChangeStore`: changes that need a second approver (plan/08). `propose(kind, payload, proposer) -> id`,
  `approve(id, approver)`, `reject(id, who)`, `get`, `list`. Kinds: `policy` and `price_book`. State is the fold of
  append-only `change_events` rows. Approval is refused for the proposer (403), for a change that is not pending
  (409, so a change applies once) and for an unknown id (404); these are `ChangeError` with a `status`. Approving a
  `policy` change writes `<state>/policy.json` atomically (temp file, then replace) inside the same transaction, so a
  failed write leaves it pending. A `price_book` change is stored and approved only: the price book is append-only and
  has its own path for new rows, so nothing is applied for it here. Payloads that look like a key or token are refused.
- `FileRetention(state_dir).apply(now=None)`: reads `<state>/retention.json`
  (`{"default_days": 90, "tenants": {"acme": 30}}`) and drops expired lines from `decisions.jsonl`, `alerts.jsonl`,
  `cache_misses.jsonl`, `rejects.jsonl`, `switch_pricer.jsonl`, `rollbacks.jsonl` and `shadow/pairs.jsonl`, rewriting
  each atomically. A line without a `tenant` uses the default; a line without a parsable `ts` is kept; no config does
  nothing; a bad config raises. It never touches the ledger, the price book or the audit log. **Ledger retention
  conflicts with the append-only rule** (CLAUDE.md), so whether and how the ledger is ever pruned is a decision for the
  plan owner; nothing here does it.
- Entry points (`token_economics.services`): `keys` -> `open_keys(state_dir)` (creates the directory, imports
  `keys.json` if present), `audit` -> `open_audit(state_dir)`, `admin_auth` -> `open_admin_auth(state_dir)`,
  `changes` -> `open_changes(state_dir)`, `retention` -> `open_retention(state_dir)`.

## Not built
A policy-as-code store, a secrets vault, a key rotation schedule, applying price-book changes, ledger retention. Role
checks live in the admin API, not here; the store only enforces that approver and proposer differ (by admin name).

## Unverified
- A key revoked by another process is seen within the 0.5 s refresh; tested to 2 s on one machine, not on a network
  file system (SQLite WAL needs shared memory, so state_dir must be local).
- `key_id` is the first 16 hex chars of the digest; collisions are not handled beyond the primary-key error.
- Retention rewrites a log while the gateway may append to it. Bytes appended since the read are carried over, but a
  line appended in the instant between that check and the replace can be lost. Run it when traffic is low, or accept it.
- A policy change is checked to be a non-empty JSON object, not against the policy schema; a malformed policy is
  only caught by the policy engine when it reloads.
