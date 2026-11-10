# Monorepo layout (Python)

One repository, 45 packages, each one a folder that can leave the repo as its own installable module. All code is Python 3.12 or later. Every one of the 79 components in the plan lands in exactly one package (generated from `model/layout.json`, checked by `model/build_layout.py`).

## The four rules

1. **Five kinds, one direction.** `contracts` then `modules` then `features` then `services` then `apps`. A package imports only from kinds to its left. Nothing imports sideways.
2. **Contracts are the only shared code.** Types, ports and events live in `modules/contracts`. It has no I/O and no third-party runtime dependency beyond the standard library and one validation library.
3. **Packages meet at runtime, not at import time.** A feature never imports another feature. The policy service finds features through the Python entry point `token_economics.features` and calls them through ports from `contracts`.
   **Split by capability, not by provider.** A provider or harness is a file inside the package that owns the capability (`providers/anthropic.py`, `providers/openai.py`), never a package of its own. Each file implements the same port from `contracts`. Adding a provider means adding one file to each package it touches.
4. **Each folder ships alone.** Own `pyproject.toml`, own tests, own README, own changelog, own version. Delete every other folder and its tests still pass.

## Tree

```
token-economics/
├─ apps/            deployables, compose everything          4 packages
├─ services/        stateful, own a store, serve a port      10 packages
├─ features/        one capability each, behind a flag; provider files inside  25 packages
├─ modules/         pure libraries and plugins               5 packages + contracts
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

### Contracts (1)

| Folder | Phase | Job | Plan components | May import |
|---|---|---|---|---|
| modules/contracts | P0 | Token buckets, ledger row, events, capability flags, Feature and Adapter ports. No I/O. | Capability registry | nothing |

### Modules (5)

| Folder | Phase | Job | Plan components | May import |
|---|---|---|---|---|
| modules/metering | P0 | Five-bucket normaliser, dedupe guard, ordered cost formula. | Usage normaliser, Dedupe and resume guard, Cost calculator | contracts |
| modules/pricebook-core | P0 | Append-only price rows, 30-day flag, stale block, plan units. | Price book, Price-row lifecycle, Plan-units table | contracts |
| modules/stats | P2 | Paired task-clustered bootstrap, non-inferiority test, cost per successful task. | Paired bootstrap stats, CPS calculator | contracts |
| modules/redaction | P0 | Metadata-only logging policy, retention, redaction. | Content-logging policy, Retention and redaction | contracts |
| modules/joiner | P0 | Join gateway, hook and OTel rows on session and prompt id. | Session and prompt-id joiner | contracts |

### Features (25)

| Folder | Phase | Job | Plan components | May import |
|---|---|---|---|---|
| features/upstream | P0 | Send the request upstream: one file per provider, the model catalogue, and the pass-through of OAuth tokens (never stored). | Anthropic connector, OpenAI connector, xAI connector, Gemini connector, Aggregator connector, Model catalogue, OAuth passthrough guard | contracts |
| features/harness-adapters | P0 | Connect a harness to the gateway: one file per harness (base URL, hooks, OTel, transcripts). | Claude Code adapter, Codex adapter, OpenAI-compatible adapter, SDK wrapper adapter, Observe-only adapter | contracts |
| features/headless-runner | P1 | Run a CLI agent as a backend: one file per CLI (budget, turns, schema, bare flags). | Headless CLI adapter, claude -p runner, codex exec runner | contracts |
| features/budgets | P1 | Virtual-key budgets, reserve then true-up, 75/90/100 alerts. | Budget store, Reserve and reconcile, Budget alerts | contracts, metering |
| features/turn-cap | P1 | Turn cap at P75 of own baseline. | Turn cap | contracts |
| features/loop-guard | P1 | Stop after the first repeated-failure signature. | Loop guard | contracts |
| features/sticky-model | P2 | Cache key per session, rate cap. | Session stickiness | contracts |
| features/switch-pricer | P2 | Price the cache loss at a model change. | Switch pricer | contracts, metering |
| features/rules-router | P2 | Rules and atomic classifier, ship-first routing. | Rules and atomic classifier | contracts |
| features/static-router | P2 | Router trained on execution-verified labels. | Static router | contracts |
| features/cascade | P2 | Cascade with fallback, only when acceptance beats the extra call. | Cascade with fallback | contracts |
| features/probe | P2 | One-probe cost predictor. | Probe cost predictor | contracts |
| features/strong-share | P3 | Per-tenant strong-model ceiling. | Strong-share ceiling | contracts |
| features/cache-planner | P2 | TTL from the observed reuse gap. | Cache planner | contracts |
| features/tier-selector | P3 | Batch, flex, priority, reserved, small. | Tier selector | contracts |
| features/cache-hit-monitor | P2 | Hit rate per caller against its own baseline. | Cache-hit monitor | contracts |
| features/schema-deferral | P2 | Defer tool schemas above about 20 tools. | Tool-schema deferral | contracts |
| features/output-cap | P2 | Tool-output cap, keep tracebacks. | Tool-output cap | contracts |
| features/observation-masking | P2 | Mask stale observations above about 10 events. | Observation masking | contracts |
| features/context-clearing | P2 | Clear at 30 to 40k, keep 5. | Context clearing | contracts |
| features/compaction-guard | P2 | Compaction last, restart at the third. | Compaction guard | contracts |
| features/max-tokens | P1 | Hard max_tokens on every call. | Max-tokens enforcer | contracts |
| features/instruction-lint | P2 | CLAUDE.md and AGENTS.md size linter. | Instruction-file linter | contracts |
| features/prompt-lint | P2 | Prompt-wording lint. | Prompt-wording lint | contracts |
| features/anomaly | P3 | Anomaly detector (DevX proposal). | Anomaly detector | contracts |

### Services (10)

| Folder | Phase | Job | Plan components | May import |
|---|---|---|---|---|
| services/ledger | P0 | Append-only ledger and metadata store. | Append-only ledger, Metadata store | contracts, metering |
| services/pricebook | P0 | Serves price rows, owns the price store. | none (new in code) | contracts, pricebook-core |
| services/signals | P0 | Hook, OTel and transcript receivers. | Hook receiver, OTel receiver, Transcript replayer | contracts, joiner |
| services/health | P1 | Rate-limit tracker and priced fallback chain. | Rate-limit tracker, Fallback chain | contracts |
| services/reconciler | P1 | Invoice reconciler, weekly price canary, plan quota. | Invoice reconciler, Weekly price canary, Plan-quota tracker | contracts, metering |
| services/policy | P1 | Runs the feature pipeline in order, applies flags. | none (new in code) | contracts |
| services/insight | P1 | Attribution and reports. | Spend attribution, Dashboards and reports | contracts |
| services/eval | P2 | Paired runs, private task set, isolated cache per arm. | Eval harness, Private eval set | contracts, stats |
| services/rollout | P2 | Shadow, canary, kill-switch, rollback. | Shadow runner, Canary controller, Kill-switch, Rollback triggers | contracts, stats |
| services/tenancy | P1 | Tenants, keys, policy-as-code, audit, roles, secrets. | Tenant and key manager, Policy-as-code store, Audit log, Admin authorisation, Secrets vault | contracts, redaction |

### Apps (4)

| Folder | Phase | Job | Plan components | May import |
|---|---|---|---|---|
| apps/gateway | P0 | The request path: async web-server proxy, key resolve, stream tee, failure mode. | Edge gateway, Key and tenant resolver, Stream tee and observer, Failure-mode switch | contracts |
| apps/admin-api | P1 | Keys, budgets, policies, reports over HTTP. | Admin API | contracts |
| apps/worker | P1 | Reconciler, canary, evals and rollout jobs. | none (new in code) | contracts |
| apps/cli | P0 | token-economics CLI: init, replay, report, lint. | none (new in code) | contracts |

### Provider and harness files

| Package | File | What differs |
|---|---|---|
| features/upstream/src/.../providers/ | anthropic.py | Messages API, cache_control, tiers |
| features/upstream/src/.../providers/ | openai.py | Responses API, prompt_cache_key |
| features/upstream/src/.../providers/ | xai.py | x-grok-conv-id, band repricing |
| features/upstream/src/.../providers/ | gemini.py | implicit and explicit cache, storage fee |
| features/upstream/src/.../providers/ | bedrock.py | aggregator |
| features/upstream/src/.../providers/ | openrouter.py | aggregator |
| features/upstream/src/.../providers/ | vercel.py | aggregator |
| features/upstream/src/.../providers/ | catalogue.py | exact model ids, tiers, limits |
| features/upstream/src/.../providers/ | oauth.py | forward anthropic-beta and tokens, never store |
| features/harness-adapters/src/.../providers/ | claude_code.py | base URL, hooks, OTel, transcripts |
| features/harness-adapters/src/.../providers/ | codex.py | model_providers base_url, Responses wire |
| features/harness-adapters/src/.../providers/ | openai_compat.py | Aider and any OPENAI_API_BASE client |
| features/harness-adapters/src/.../providers/ | sdk.py | Agent SDK and API clients |
| features/harness-adapters/src/.../providers/ | observe.py | observe-only: exports, local JSONL |
| features/headless-runner/src/.../providers/ | claude_cli.py | claude -p flags and budget |
| features/headless-runner/src/.../providers/ | codex_cli.py | codex exec, user-level config |
| features/cache-planner/src/.../providers/ | anthropic.py | explicit TTL and breakpoints |
| features/cache-planner/src/.../providers/ | openai.py | prompt_cache_key |
| features/cache-planner/src/.../providers/ | xai.py | conversation id header |
| features/cache-planner/src/.../providers/ | gemini.py | explicit cache and storage fee |
| features/cache-hit-monitor/src/.../providers/ | anthropic.py | cache read and write fields |
| features/cache-hit-monitor/src/.../providers/ | openai.py | cached_tokens |
| features/cache-hit-monitor/src/.../providers/ | xai.py | cached prompt tokens |
| features/cache-hit-monitor/src/.../providers/ | gemini.py | cached content tokens |
| features/sticky-model/src/.../providers/ | anthropic.py | cache scope per session |
| features/sticky-model/src/.../providers/ | openai.py | key per session |
| features/sticky-model/src/.../providers/ | xai.py | conv id per session |
| features/sticky-model/src/.../providers/ | gemini.py | cache name per session |
| features/tier-selector/src/.../providers/ | anthropic.py | batch and priority tiers |
| features/tier-selector/src/.../providers/ | openai.py | batch, flex, priority |
| features/tier-selector/src/.../providers/ | gemini.py | batch tier |
| modules/metering/src/.../providers/ | anthropic.py | usage fields to five buckets |
| modules/metering/src/.../providers/ | openai.py | usage fields to five buckets |
| modules/metering/src/.../providers/ | xai.py | usage fields to five buckets |
| modules/metering/src/.../providers/ | gemini.py | usage fields to five buckets |
| modules/pricebook-core/src/.../providers/ | anthropic.py | price rows and multipliers |
| modules/pricebook-core/src/.../providers/ | openai.py | price rows and multipliers |
| modules/pricebook-core/src/.../providers/ | xai.py | price rows, bands |
| modules/pricebook-core/src/.../providers/ | gemini.py | price rows, storage fee |


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
