# token-economics-app-cli

token-economics CLI: init, replay, report, detect.

Kind: app. Phase: P0. May import: token-economics-contracts.

Run alone: `uv run --package token-economics-app-cli pytest apps/cli`

## eval (P2)

`token-economics eval run <spec> [--out DIR] [--allow-dirty]`, `eval report <result_dir>` and `eval selftest [--seed N]`.
Needs the eval service installed (`token-economics-svc-eval`); without it the command exits 2 and names what is missing.
`run` spends real money through real gateways: see `evals/README.md`. Unverified: `run` has only been tested with fakes.

## Rollout commands

`policy kill <feature> [--tenant T] [--reason R]`, `policy unkill <feature> [--tenant T]` and `policy kills` use the
`kill` service (`kill.json`, audited, `by = cli:<user>`). `policy canary <feature> --share S [--tenants a,b]` (or
`--off`) edits the feature's section in `policy.json`. `rollout check` runs auto-rollback now and prints one row per
canaried feature. `shadow report` prints the shadow service's report.
