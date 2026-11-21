# Contributing

## How we work

- Trunk-based. `main` is always releasable. Branches are short-lived and named `type/issue-slug`, for example `feat/142-ledger-append`.
- One pull request per issue, squash-merged. The PR title becomes the commit message, so it must be a Conventional Commit with a folder scope: `feat(ledger): append-only rows`.
- Types: `feat`, `fix`, `test`, `docs`, `chore`, `spike`, `gate`. The scope is a package folder name (`ledger`, `upstream`, `contracts`) or a top-level folder (`tools`, `docs`, `plan`). CI checks the title with `tools/check_pr_title.py`.
- A breaking change adds `!`: `feat(contracts)!: rename bucket`.

## The cycle for every change

1. **Red.** Write the test first and watch it fail. Link the failing CI run in the PR.
2. **Green.** Write the smallest change that passes.
3. **Refactor.** Clean up with the tests green.
4. **Evidence.** Show that the issue's done-when line is met (test output, a replay, a number) in the PR.
5. **Verify.** A second person checks the evidence against the done-when line before merge. The author does not verify their own work.

New flags default off. Every PR says how to roll it back.

## Definition of Ready

The issue has a done-when line, a test name, a size (0.5, 1 or 2 days) and a dependency (or "none"). Use an issue form; they ask for all four. Bigger than 2 days: split it.

## Definition of Done

- The test was red first and is green now, in CI.
- `ci-gate` is green.
- The PR has the evidence, the flag state and the rollback note.
- A second person has verified it.
- The package's `CHANGELOG.md` has a line if behaviour changed.

## Layering, in one paragraph

`contracts`, then `modules`, then `features`, then `services`, then `apps`. A package imports only the packages listed as `deps` for it in `plan/model/layout.json`, never a sibling, never a higher kind, never another package's private modules (`_internal`, or anything starting with `_`). Each folder must pass its own tests with only its declared dependencies installed. Details: `plan/13-monorepo-layout.md`.

## Running the checks locally

From the repo root:

```bash
uv sync --all-packages                                  # once
uv run ruff check .                                     # lint
uv run mypy --strict modules/metering/src               # types, one package src at a time
uv run pytest -q modules/metering/tests                 # tests of one package (or just: uv run pytest -q)
uv run pytest -q -k contract features/upstream/tests/contract
uv run python tools/check_layering.py                   # imports follow layout.json
uv run python tools/check_layering.py --write-importlinter && uv run lint-imports
uv run python tools/check_surface.py                    # __all__ matches what each package exposes
uv run python tools/check_extractable.py [svc-ledger]   # package works with only its declared deps
uv run python tools/affected.py origin/main             # which packages your change touches
uv run python tools/check_pr_title.py "feat(ledger): append-only rows"
uv run pytest -q tools/tests                            # tests of the checks themselves
```

`--write-importlinter` regenerates `.importlinter`; commit it when you add a package.

## Adding a package

The package must already be in `plan/model/layout.json` (kind, dir, deps). Then:

```bash
uv run python tools/new_package.py svc-ledger "What it does in one line"
```

This creates the folder with its own `pyproject.toml`, README, CHANGELOG, `src/` and `tests/`. Next:

1. Add `token-economics-<key> = { workspace = true }` to `[tool.uv.sources]` in the root `pyproject.toml`.
2. `uv sync --all-packages`, then `uv run python tools/check_layering.py --write-importlinter`.
3. Add a line for the folder to `.github/CODEOWNERS`.
4. Write the first test (red) before any code.

Naming: layout key `svc-ledger` is the distribution `token-economics-svc-ledger` and the module `token_economics_svc_ledger`.
