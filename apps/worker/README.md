# token-economics-app-worker

Scheduled jobs: auto-rollback checks, retention and backups.

Kind: app. Phase: P1. May import: token-economics-contracts.

Run alone: `uv run --package token-economics-app-worker pytest apps/worker`

## Use

`token-economics-worker [--once] [--interval 300] [--state-dir D]`. Each tick runs the `rollback` service's `check()`
and, when the tenancy service is installed, the `retention` service's `apply()`, then prints one JSON line
(`{"ts", "jobs": {"rollback": {...}, "retention": {...}}}`). A failing job is reported in its entry and does not stop
the others. `--once` runs one tick and exits (1 if a job failed), for cron.
