# Disaster recovery

Tool: `tools/backup.py`. Test (the drill): `tools/tests/test_backup.py`.

## What is in the state dir

`$TOKEN_ECONOMICS_STATE_DIR` (default `~/.token-economics`): `ledger.sqlite`, `pricebook.sqlite`, `tenancy.sqlite`
(keys, audit), other `*.sqlite` (budgets), `policy.json`, `kill.json`, `keys.json`, `*.jsonl` logs and `shadow/`.
The ledger and the price book are append-only: a backup is a complete history up to its moment, and restoring never
needs a merge.

## Targets (PROPOSAL, for the plan owner)

plan/08 lists "Disaster-recovery targets" as an open gap for P3. Nothing here is decided.

| Target | Proposed | Why |
|---|---|---|
| RPO, ledger and audit | 1 hour: hourly backup | Rows can be re-priced from provider usage logs, but not rebuilt without them |
| RPO, price book and config | 24 hours | Changes are rare and each is a new row or file |
| RTO, gateway serving again | 30 minutes | Restore is seconds; the rest is finding the cause and restarting |
| Retention of backups | 14 daily, 4 weekly, stored off the machine | Not built: the tool writes a folder, copying it off-host is the operator's job |

Until the plan owner accepts targets, no scheduled backup exists. Run one by hand or from cron:
`0 * * * * cd <repo> && uv run python tools/backup.py backup $STATE /backups/te-$(date +\%Y\%m\%dT\%H)`.

## Procedure

Back up (safe while the gateway runs; SQLite files use the online backup API, so a consistent snapshot is taken even
mid-write, and `-wal`/`-shm` files are not copied):

```bash
uv run python tools/backup.py backup ~/.token-economics /backups/te-$(date +%Y%m%dT%H%M)
uv run python tools/backup.py verify /backups/te-<stamp>      # sha256 and row counts against manifest.json
```

Restore (only into an empty or missing directory; verifies the backup before and each file after copying):

```bash
# 1. stop the gateway and admin app
# 2. move the damaged state dir aside, never delete it
mv ~/.token-economics ~/.token-economics.damaged-$(date +%Y%m%dT%H%M)
# 3. restore
uv run python tools/backup.py restore /backups/te-<stamp> ~/.token-economics
# 4. start the gateway and check it
uv run token-economics-gateway --port 8787 &
curl -s 127.0.0.1:8787/_te/health
uv run token-economics report --days 1
```

Rows written after the backup and before the loss are gone from the restored ledger; they can be found in the
damaged dir if it is readable. Do not merge them by hand: the ledger refuses UPDATE and DELETE on purpose.

## Drill

Run it with `uv run pytest tools/tests/test_backup.py -q`. It:

1. builds a state dir with 50 ledger rows (through the registered `ledger` service), keys, policy, an alerts log and
   a `shadow/` file;
2. starts a writer thread that keeps appending ledger rows, waits until it has appended 30 more, and backs up while it
   is still writing;
3. checks the backup verifies and holds at least the rows written before the backup began;
4. deletes the state dir and restores it;
5. checks every ledger row in the backup is present after restore and the row count equals the manifest's, that keys,
   logs and shadow files are byte-for-byte back, that `UPDATE` and `DELETE` on the restored ledger still fail with the
   append-only message, and that the restored ledger accepts new rows and dedupes a repeated response id.

Also covered: restore refuses a non-empty directory; verify names a changed or missing file and restore then writes
nothing; backup refuses a non-empty output directory.

### Drill result

- Date: 2026-11-23, Apple M4, local disk, SQLite WAL mode.
- `uv run pytest tools/tests/test_backup.py -q`: 5 passed in 0.2 s. The drill itself took 0.02 s, which is the whole
  backup, wipe and restore for a small ledger.
- Also run once against a copy of a real developer state dir (read-only): 3 SQLite files backed up and verified
  (ledger 3 rows, price book 12 rows, tenancy 2 keys and 2 audit entries).

Not drilled: a large ledger (restore time grows with file size; measure it before accepting an RTO), an
off-host copy, and restoring onto a different machine. A person other than the builder has not yet run the drill; PHASES.md asks for that.
