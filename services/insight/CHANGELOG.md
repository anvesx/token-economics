# Changelog: token-economics-svc-insight

## 0.1.0

- First version (P0).
- Leak detectors: hermes-engine categories vendored unchanged (commit in `hermes/VENDORED.md`), `HermesDetectors`
  behind the `Detector` port, 50-line coverage table and its Markdown, tamper check and sync tool.
- Baseline report from ledger rows.
- `dashboard_summary(rows, now=, days=)`: spend by UTC day (zero-filled), tenant, caller, model and harness with
  median and P95 per active day, top 20 sessions and the 50 newest requests, as frozen pydantic models. Registered as
  `dashboard_summary` under `token_economics.services`.
