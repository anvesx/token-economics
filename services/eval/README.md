# token-economics-svc-eval

Eval harness: preregistered specs, isolated arms, attempts and paired verdicts on cost per successful task.

Kind: service. Phase: P2. May import: token-economics-contracts, token-economics-stats.

Run alone: `uv run --package token-economics-svc-eval pytest services/eval`

## What it does

Registered as SERVICES `eval` (`create()` takes no arguments and returns the `EvalHarness`). See `evals/README.md` for
how to write tasks and a spec.

- `run(spec, out_dir, allow_dirty)`: refuses a spec that git does not track or that has uncommitted changes (unless
  `allow_dirty`; the result is then marked not preregistered). Per arm it runs `token-economics init` in a fresh state
  directory, writes the arm's `policy.json`, starts `token-economics-gateway` on a free port and waits for
  `/_te/health`; every gateway is stopped in a `finally`. Per seed, arm and task order are shuffled with
  `random.Random(seed)`; with `isolation: spacing` a task waits `spacing_s` after it last ran in another arm.
  Each attempt runs in a fresh workspace (git worktree at `ref`, or a copy), then `verify`; cost, buckets and call
  count come from the arm ledger rows with the attempt's session id, `fired` from `decisions.jsonl`.
  Output: `spec.json`, `meta.json`, `attempts.jsonl` (resumable), `result.json`, `REPORT.md`.
- `analyse(attempts, spec)`: per-arm summary, then each candidate against the baseline with `paired_bootstrap`, Holm
  across candidates, and a verdict. Decimal values are strings.
- `selftest(seed)`: 80 tasks, 2 arms from one distribution, 3 seeds. `passed` is "not a win and 1 is in the ratio CI".

The runner takes a `GatewayLauncher`, a `HarnessRunner` and a `CostReader` (Protocols in `parts.py`); tests use fakes
and never call a model.

## Config

The spec (see `evals/runs/example-noop.json`). An arm's `env` maps a variable to the name of a variable to copy; a
missing source variable stops the run before any spend. `harness_args` are passed to `claude` as given.

## Unverified

- Nothing here has run against a real `claude` and a real gateway. `ClaudeCodeRunner` passes `--session-id <uuid>`
  so the session of a timed-out attempt is known; this assumes Claude Code accepts the flag and that the gateway's
  adapter records that id as the ledger `session_id`. If the ids differ, attempts end as `no_ledger_rows`.
- `claude -p --output-format json` is only parsed for `session_id`. A harness error exit code is recorded as an
  error; verify is skipped and the attempt is a failure.
- Only the user-level `~/.claude/settings.json` is checked for a pinned `env.ANTHROPIC_BASE_URL`; project or
  managed settings can override it too.
- The arm gateways run with no virtual key, as `init` leaves them; budgets are not exercised.
- Arms run one attempt at a time. A long spec with spacing takes hours; there is no parallelism.
