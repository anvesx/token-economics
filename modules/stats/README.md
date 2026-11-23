# token-economics-stats

Paired task-clustered bootstrap, CPS, non-inferiority and Holm correction for the eval harness.

Kind: module. Phase: P2. May import: token-economics-contracts.

Run alone: `uv run --package token-economics-stats pytest modules/stats`

## What it does

Pure functions, deterministic for a fixed seed, standard library only (money stays `Decimal`).

- `cps(attempts)`: all spend, failed attempts included, over the number of successes (`None` with no success).
- `paired_bootstrap(attempts, baseline, candidate, n_boot=10000, level=0.95, seed=0, cluster="task"|"repo")`: pairs by
  task (only tasks both arms ran), resamples clusters with replacement (each draw takes all attempts of a cluster, both
  arms), CPS per arm is sum cost over sum successes. Percentile intervals for the ratio and the success difference.
  Resamples where an arm has no success are dropped and counted; more than 5 percent dropped sets `unstable`.
  `p_value` is one-sided, `(k + 1) / (kept + 1)` for the `k` kept resamples with ratio at or above 1.
- `non_inferior(result, bound_pp)`, `holm(pvalues, alpha)`, `geometric_sd(values)`.
- `verdict(result, bound_pp, alpha, adjusted_p=None)`: `win`, `fails_success_bound` or `no_win`, with a reason.
  An unstable result is never a win.

## Unverified

- The intervals are percentile bootstraps; their coverage at small cluster counts (under about 30 tasks) is not
  checked. The `unstable` flag only covers dropped resamples.
- Holm rejects when the adjusted p is below alpha (strict), the same rule `verdict` uses.
- Power and minimum sample size are not computed (plan/07: fit the variance on a P2 pilot).
