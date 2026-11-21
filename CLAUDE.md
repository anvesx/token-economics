# CLAUDE.md

Guidance for Claude Code in this repository.

## What this is
Token Economics: a gateway that prices every coding-agent model call, then budgets and optimises it. Four phases
(P0 measure, P1 enforce, P2 optimise, P3 harden). Only a first pass of P0 is built. Start with `docs/ROADMAP.md`
(what is left, lessons learned) and `docs/P0-STATUS.md`. The plan in `plan/` is the source of truth; do not edit
`plan/`, `research/` or `research-cli-agents/`.

## Commands
```bash
uv sync --all-packages                      # after any pyproject or entry-point change
uv run pytest -q                            # packages + tests/integration (real local ports)
uv run pytest tools/tests -q
uv run ruff check . && uv run ruff format <paths>
for d in modules/*/src features/*/src services/*/src apps/*/src tools; do uv run mypy $d; done
uv run python tools/check_layering.py [--write-importlinter] && uv run lint-imports
uv run python tools/check_surface.py
uv run python tools/check_extractable.py [layout-key ...]
uv run token-economics init|report|detect|prices|replay
uv run token-economics-gateway --port 8787
```
Use a scratch `TOKEN_ECONOMICS_STATE_DIR` when testing so `~/.token-economics` is not touched.

## Rules that are enforced
- Five kinds, one direction: contracts, modules, features, services, apps. A package imports only the packages in its
  `deps` in `plan/model/layout.json`. Apps import `contracts` only; implementations are found through the entry-point
  groups in `modules/contracts/.../registry.py`.
- Each package ships alone: own pyproject, tests, README, CHANGELOG. New package: `python tools/new_package.py <key> "<summary>"`.
- A provider or harness is one file inside the package that owns the capability (`providers/anthropic.py`), never its own package.
- The ledger and the price book are append-only. Never add an UPDATE or DELETE. A price change is a new row.
- No prompt, tool or response text is stored. Secrets are never logged.
- `services/insight/src/.../hermes/` is vendored from hermes-engine and must stay byte-identical; change it there and
  run `services/insight/tools/sync_hermes.py`.
- Money is `Decimal`. Model ids match exactly.

## Working style
- TDD as in the playbook: failing test first, named after the behaviour, with Given / When / Then comments.
- Conventional Commits scoped by folder: `feat(ledger): one row per provider response id`. Types: feat, fix, test,
  docs, chore, spike, gate. New flags default to off.
- Commit locally on a branch; do not push or open PRs unless asked.
