# Monorepo layout (Python)

One repository, __NPKG__ packages, each one a folder that can leave the repo as its own installable module. All code is Python 3.12 or later. Every one of the __NCOMP__ components in the plan lands in exactly one package (generated from `model/layout.json`, checked by `model/build_layout.py`).

## The four rules

1. **Five kinds, one direction.** `contracts` then `modules` then `features` then `services` then `apps`. A package imports only from kinds to its left. Nothing imports sideways.
2. **Contracts are the only shared code.** Types, ports and events live in `modules/contracts`. It has no I/O and no third-party runtime dependency beyond the standard library and one validation library.
3. **Packages meet at runtime, not at import time.** A feature never imports another feature. The policy service finds features through the Python entry point `token_economics.features` and calls them through ports from `contracts`.
   **Split by capability, not by provider.** A provider or harness is a file inside the package that owns the capability (`providers/anthropic.py`, `providers/openai.py`), never a package of its own. Each file implements the same port from `contracts`. Adding a provider means adding one file to each package it touches.
4. **Each folder ships alone.** Own `pyproject.toml`, own tests, own README, own changelog, own version. Delete every other folder and its tests still pass.

## Tree

```
token-economics/
├─ apps/            deployables, compose everything          __NAPP__ packages
├─ services/        stateful, own a store, serve a port      __NSVC__ packages
├─ features/        one capability each, behind a flag; provider files inside  __NFEAT__ packages
├─ modules/         pure libraries and plugins               __NMOD__ packages + contracts
├─ papers/          one folder per paper: draft, data, code, figures
├─ evals/           task sets, bounds, results (data, not code)
├─ ops/             alerts, load tests, drills, runbooks
├─ spikes/          throwaway, never imported
├─ tools/           repo checks: layering, extractability, release
├─ docs/            adr/  runbooks/
├─ plan/  research/  research-cli-agents/    existing, unchanged
├─ pyproject.toml   uv workspace root: members = apps/*, services/*, features/*, modules/*
├─ uv.lock  .python-version  ruff.toml  .importlinter
└─ .github/         workflows, CODEOWNERS, templates
```

One package, expanded:

```
features/budgets/
├─ pyproject.toml        name = "token-economics-feat-budgets", own version, own deps
├─ README.md             what it does, the port it implements, how to run alone
├─ CHANGELOG.md
├─ src/token_economics_feat_budgets/
│  ├─ __init__.py        exports the Feature object
│  └─ py.typed
└─ tests/
   ├─ unit/  property/   fast, no network
   └─ contract/          runs the shared port suite from contracts against this feature
```

## Package map

__TABLES__

## How a package stays extractable

| Check | Tool | Fails the build when |
|---|---|---|
| Layering | `import-linter` contracts generated from `layout.json` | A package imports a sibling or a higher kind |
| Declared deps | tools/check_extractable.py | A clean virtual environment with only the declared dependencies cannot import the package and pass its tests |
| No deep imports | `import-linter` (forbidden: `*._internal`) | Code reaches into another package's private modules |
| Public surface | tools/check_surface.py | A package exports a name that is not in its `__all__` |
| Types and style | `ruff`, `mypy --strict` per package | Any error |
| Port compliance | shared contract suite in `contracts` | A feature, adapter or backend breaks its port |

CI runs only the packages a change touches, plus everything that depends on them (computed from `layout.json`). One required job, `ci-gate`, aggregates the results.

## Releasing one folder

- Tags per package: `feat-budgets/v0.3.0`. One changelog and one version per package, driven by conventional commits and release-please in manifest mode (DevX proposal).
- A breaking change to `contracts` bumps its major version. Every dependent package pins token-economics-contracts at the same major version and is tested against both ends of the range.
- To extract a folder: `git subtree split -P features/budgets -b out/budgets`, then publish. The history comes with it.

## Stack choices (DevX proposals, each settled by a P0 spike or ADR)

| Concern | Choice | Why |
|---|---|---|
| Workspace | `uv` workspace | One lockfile, per-package builds |
| Gateway | Starlette on uvicorn, httpx for upstream | Stream tee needs raw async-server control. A spike compares it with LiteLLM as the core |
| Types | `pydantic` v2 in `contracts` only | Validation at the edge, plain dataclasses inside |
| Store | Postgres for ledger and price book, SQLite for local mode | Append-only rows, one SQL dialect family |
| Tests | `pytest`, `hypothesis` (property), recorded-fixture replay, fault injection | Matches the TDD format in the phase playbook |
| Config | policy-as-code in YAML, validated against `contracts` | Review before apply |

## What this layout does not settle

- Whether `svc-policy` runs in the gateway process or beside it. The latency spike in P0 decides. The package boundary is the same either way.
- Whether the dashboard is built or is a Grafana or Metabase config in `ops/`. P1 decides.
- Package names are working names. Renaming a folder is cheap until the first release.
