# token-economics-svc-ledger

Append-only ledger: one row per provider response id.

Kind: service. Phase: P0. May import: token-economics-contracts.

Run alone: `uv run --package token-economics-svc-ledger pytest services/ledger`

## Usage

```python
from token_economics_svc_ledger import SqliteLedger

ledger = SqliteLedger("ledger.db")   # or ":memory:"; WAL for files; thread-safe
ledger.write(row)                    # True; False if (provider, response_id) already exists
ledger.count(row.response_id)        # 1
list(ledger.rows(since, until))      # since <= ts < until, ordered by ts then insertion
```

Via the registry: `load(SERVICES, "ledger")("ledger.db")`.

Append-only: the package has no UPDATE or DELETE, and SQLite triggers abort both on the table.
A row with an empty `response_id` or a naive `ts` raises ValueError.
