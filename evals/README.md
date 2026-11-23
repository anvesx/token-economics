# Evals

The harness behind P2: no optimisation ships unless a paired run shows cost per successful task (CPS) down with the
success bound held (plan/07, MUST rules 1 to 4). Code: `services/eval` (runner) and `modules/stats` (statistics).

```bash
uv run token-economics eval selftest                      # two identical arms must report no difference
uv run token-economics eval run evals/runs/<name>.json    # spends real money through the arm gateways
uv run token-economics eval report evals/results/<name>/<time>
```

## Write a private task set

A task file is JSON, `evals/tasks/<set>.json`:

```json
{"tasks": [{"id": "billing-rounding", "repo": "/path/to/repo-or-folder", "ref": "abc123",
            "prompt": "...", "verify": "pytest -q tests/test_billing.py", "tags": ["hard", "lite"], "timeout_s": 900}]}
```

- `repo` is a folder or a git repo (a relative path is resolved from the git root of the spec). A git repo is checked
  out as a detached worktree at `ref`; a plain folder is copied. Each attempt gets a fresh copy, removed afterwards.
- `verify` is a shell command run in the workspace. Exit 0 is success. Make it check behaviour, not the diff, and make
  it fail on the untouched repo. Every attempt records this flag (plan/07, MUST rule 2).
- Keep the set private (do not commit proprietary repos or prompts to a public place) and include hard cases:
  public sets saturate at 96 to 98 percent, and a saturated set cannot show a success loss.
- Hold out tasks. Tune a feature on one part and run the preregistered test on tasks it never saw (a regex router
  fell from 93.8 to 70.6 percent held out).
- Tag about 80 tasks `lite` and set `"subset": "lite"` for A/B runs. The 80-task subset tracked the full 350 within
  0.81 pp at about a quarter of the cost. Run the full set for the final result of a row.
- `evals/tasks/example.json` and `evals/fixtures/toy-repo/` are a toy, to try the harness and nothing more.

## The spec (preregistration)

`evals/runs/<name>.json` names the task file, the baseline arm, one or more candidate arms (each a `policy.json` body,
plus optional `env`), seeds, the non-inferiority bound, alpha and the isolation. See `evals/runs/example-noop.json`.

- `arms.<arm>.policy` is written as that arm's `policy.json`, so a candidate is a feature switched on.
- `arms.<arm>.env` maps a variable to set to the NAME of a variable to copy it from, e.g.
  `{"CLAUDE_CODE_EFFORT": "EVAL_EFFORT_LOW"}`. Never put a secret in the spec.
- `harness_args` (optional) are extra arguments for `claude`, for example a permission mode. Choose them yourself:
  the harness does not add `--dangerously-skip-permissions`.
- Defaults: `seeds` 3, `alpha` 0.05, `isolation` "spacing", `spacing_s` 330, `n_boot` 10000, `timeout_s` 1800,
  `cluster` "task" (or "repo").

**Commit the spec before the run.** The success bound (`bound.success_pp`) is the line a candidate must not cross.
If it is chosen after the numbers are seen, it will be chosen to pass. `run` refuses a spec that git does not track or
that has uncommitted changes; `--allow-dirty` runs it anyway, and `meta.json` and `REPORT.md` then say "not
preregistered". Such a result is a pilot, not evidence for a row. The spec's sha256, the task file's sha256 and the git
commit are in `meta.json`.

## Isolation

Two arms that run the same task close together share the provider's prompt cache: the second arm reads what the first
wrote. The median gap between arms in the cited study was 10.8 s, inside the 5 minute TTL. With `"isolation":
"spacing"` the runner waits until at least `spacing_s` (default 330 s, over the 5 minute TTL) has passed since that
task last ran in a different arm. With `"none"` it does not wait; use that only for a harness with no prompt cache, or
for tests. Each arm also has its own gateway, state directory, ledger and policy, so arms never share a budget or
a ledger. Arm and task order are shuffled for each seed.

## Output

`evals/results/<name>/<UTC time>/` (or `--out`): `spec.json`, `meta.json`, `attempts.jsonl` (one attempt per line, no
prompt or response text; rerun into the same folder to resume), `result.json`, `REPORT.md`, and `arms/<arm>/state/`
(each arm's ledger and decisions).

Cost per attempt is the sum of the arm ledger's rows for that session (failed attempts count, and so does any router
or classifier call in the session). An attempt with an unpriced call, a timeout or a crash is an error and counts
as a failure.

## Read the result

- **CPS ratio** is candidate over baseline, with a task-clustered bootstrap interval. Below 1 is cheaper.
- **Success diff** is candidate minus baseline in percentage points. Non-inferiority holds when the lower end of its
  interval is above minus the bound.
- **Adjusted p** is the one-sided bootstrap p-value after Holm correction across the candidates of the spec.
- **Failed-run waste** is the share of spend that went to failed attempts. **Median cost geometric SD** is the spread
  between repeats of one task; identical runs differ a lot, so look at it before trusting a small gap.
- Verdicts: `win` needs the ratio interval wholly below 1, non-inferiority and an adjusted p below alpha.
  `fails_success_bound` means success was not shown to hold. `no_win` is everything else (including too few
  successes to estimate). Anything but `win` keeps the row off; that is a valid result.

## One result per row

Each behaviour-change row of `plan/12-fix-table-50-rows.md` gets a folder `evals/results/row-NN/` for its result
file, per harness and version. A row that does not win is listed in `docs/evals/OFF.md` with its result file and the
reason. The count of shipped rows is a result, not a target.
