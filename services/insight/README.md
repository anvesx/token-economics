# token-economics-svc-insight

Attribution, baseline report and the leak detectors in alert mode.

Kind: service. Phase: P0 (detectors and baseline). May import: token-economics-contracts.

## What it does

- **Leak detectors** (`HermesDetectors`, the contracts `Detector` port, name `hermes`). They run after the fact over
  Claude Code transcripts, never in the request path (plan/11). Each costed item becomes a `Finding`
  (`cost_source = client`: estimated from transcript usage at API list prices). Coverage is exactly 50 lines, one per
  fix-table row 1-50: 43 active categories plus 7 retired numbers that are never reused.
  `coverage_markdown()` renders the P0 deliverable "coverage table, 50 rows with fired counts".
- **Baseline** (`baseline(rows)`, `baseline_markdown(report)`): from ledger rows only, spend per developer (mean, median,
  P95 per day), cache hit per caller, failed-run share, period, spend by model and share of rows per `cost_source`.
  The conventions (UTC days, nearest-rank P95, unpriced rows left out of spend) are in the `baseline.py` docstring.
  In P0 nothing sets `LedgerRow.success`, so the failed-run share is `None` and the text says so.
- **Dashboard** (`dashboard_summary(rows, now=, days=30)`): spend by UTC day (zero-filled), tenant, caller, model and
  harness (requests, spend, share, tokens, cache hit, median and P95 per active day), top 20 sessions and the 50 newest
  requests, for the admin dashboard. Same conventions as the baseline; see the `dashboard.py` docstring.

The estimate ranks work to look at first. It does not predict savings.

## Where the categories come from

The product owner's decision: use the hermes-engine categories as implemented. They live in the sibling repo
`hermes-engine`, folder `plugins/token-metrics/scripts/`, and are vendored here unchanged in
`src/token_economics_svc_insight/hermes/` (`leak_report.py`, `leak_extra.py`, `leak_categories.py`, `leak_config.py`,
`prompt_check.py`). Stdlib only, untyped legacy code, imported as flat modules. Row numbers match
`plan/12-fix-table-50-rows.md`. `hermes/VENDORED.md` records the source commit and a sha256 per file.

### Vendoring

Do not edit the vendored files. Change hermes-engine, commit there, then:

    python services/insight/tools/sync_hermes.py /path/to/hermes-engine   # copy the five files, rewrite VENDORED.md
    python services/insight/tools/sync_hermes.py --check                  # exit 1 if a file differs from its recorded sha256

`--check` needs no other repo and is meant for CI. After a sync, check that rows 1-50 are still each active or retired
(the coverage code raises if a number is in neither).

### How the modules are isolated (`_hermes_loader.py`)

The files import each other by bare name (`import leak_extra`) and `leak_config` reads `CC_METRICS_DIR` at import time
to pick its config and cache directory. The loader, per state directory:

1. puts `hermes/` first on `sys.path` and sets `CC_METRICS_DIR` to the caller's `state_dir`,
2. imports the modules under their bare names,
3. removes those names from `sys.modules` and restores `sys.path` and the environment (a same-named module that was
   already loaded is put back), and caches the result per state directory.

So nothing is read from or written to `~/.claude/metrics`, nothing named `leak_report` stays importable, and two
state directories get two independent module sets. The loader checks `leak_config.METRICS_DIR` after import.
Everything coming out of the vendored modules is `Any`; `detectors.py` converts it to typed contracts objects at one
marked boundary (`HermesDetectors._analyse`).

## Privacy defaults

- **The model prompt check is off.** `prompt_check.label_sessions` decides it is enabled from the shared config dict
  (`leak_config.CONFIG["prompt_check"]`, the same dict `leak_report.CFG` points to), the `claude` binary being on PATH,
  and the env switches `CC_METRICS_PROMPT_CHECK=0` / `CC_METRICS_OFF=1`. The cleanest hook is the config dict: `run()`
  sets `CONFIG["prompt_check"]` to the constructor's `prompt_check` flag for the duration of the call (under a lock) and
  restores it afterwards. No environment variable is changed. With it off, no `claude -p` process starts and no prompt
  text leaves the machine; the four rows that use it (new task, correction, could have continued, repeated task) fall
  back to heuristics and to labels already cached in `state_dir/prompt_checks.json`.
  Pass `prompt_check=True` (or `open_detectors(..., prompt_check=True)`) to opt in.
- Finding details are built by the vendored detectors from tool names, file names, skill names, model names and
  counts. A scan of real output found no prompt text. `scope` is `<project folder>/<session short id>`; the project
  folder is the directory name under the transcripts root, which Claude Code derives from the working directory path,
  so treat findings as local data.
- Hook data (`events.jsonl`) is not read: the detectors run from transcripts alone, and rows that need hook data
  report as unmeasurable or fall back.

## Run alone

    uv run --package token-economics-svc-insight pytest services/insight

    from pathlib import Path
    from token_economics_svc_insight import HermesDetectors, coverage_markdown
    d = HermesDetectors(Path.home() / ".claude/projects", Path("/tmp/te-state"))
    findings, coverage = d.run()
    print(coverage_markdown(coverage, d.last_total_usd))

Opt-in smoke test on your own transcripts: `TOKEN_ECONOMICS_REAL_TRANSCRIPTS=1 uv run pytest services/insight -k smoke -s`.

Entry points under `token_economics.services`: `detectors` = `open_detectors(transcripts_root, state_dir,
prompt_check=False)` and `baseline` = `baseline(rows)`.

## Typing and lint

Own modules pass `mypy --strict`. The vendored folder is untyped legacy code and must be excluded from the root mypy
run (a per-package override is not read when mypy runs from the root): in the root `pyproject.toml`
`[tool.mypy]` add `exclude = ["services/insight/src/token_economics_svc_insight/hermes/"]`. Nothing imports the folder
statically, so excluding it is enough. Ruff already excludes it at the root.

## Placement note for the plan owner

`plan/model/layout.json` lists svc-insight as a P1 package with dependencies on `contracts` only and has no detector
package. Putting the detectors and the baseline here in P0 is a proposal: P0 needs both, and they only need contracts.
