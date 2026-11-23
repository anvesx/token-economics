# Changelog: token-economics-svc-rollout

## 0.1.0

## Unreleased

- Auto-rollback (service `rollback`): canary against control per feature, five triggers, kill switch, `rollbacks.jsonl`, alert.

- First version (P2).
- Shadow sampler: opt-in config, per-session deterministic sampling, tenant/harness filters, daily USD cap.
- Pair log and report joining primary and shadow sides: cost ratio, median/P95, status mismatches.
