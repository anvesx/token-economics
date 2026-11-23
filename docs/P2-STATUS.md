# P2 status: working core

Branch `feat/p2-working-core`, 2026-11-23. P2 is "optimise". First pass on a P0 and P1 that have not met their own
exit gates. **The P2 exit gate is not met: no optimisation has a paired result, because there is no real task set.**
Every feature is off unless `policy.json` switches it on. Decisions: `docs/adr/0003`.

## What runs today
- Request rewrites: a feature may change a request before dispatch (contracts `Rewriter`). Enforced rewrites are sent,
  advisory ones logged as `would_rewrite`, failures send the original bytes. `decisions.jsonl` records each one.
- Context guard: `max_tokens`, `output_cap`, `observation_masking`, `context_clearing`, `schema_deferral`,
  `compaction_guard` (plan/06 order).
- Cache: `cache_planner` (5m or 1h TTL from each prefix's reuse gaps, frozen per session), `cache_hit_monitor` (hit
  rate per caller and model in `cache_monitor.json`, misses with a likely reason in `cache_misses.jsonl`).
- Router rung 1: `rules_router`, `sticky_model`, `switch_pricer` (marginal cost of the switch turn against the
  per-turn saving; every decision in `switch_pricer.jsonl`).
- Eval harness: `token-economics eval run|report|selftest`. Spec must be committed first; one gateway per arm; arms
  spaced past the cache TTL; success from the task's verify command; cost from the arm ledger by session id; paired
  task-clustered bootstrap on CPS, non-inferiority on success, Holm across arms. Layout in `evals/README.md`.
- Shadow runs: `<state>/shadow/shadow.json` turns sampling on; the gateway mirrors sampled sessions through
  `<state>/shadow/policy.json` into `<state>/shadow/ledger.sqlite`; pairs and report in `services/rollout`.
- Checks: ruff, mypy --strict, 514 tests (all P2 features enforced together through the real gateway; advisory sends
  the original bytes), 37 tool tests, layering (41 contracts), surface.

## Exit gate (PHASES.md)
| Gate line | Status |
|---|---|
| Every shipped optimisation has a paired win on CPS with the success bound held | **Not met.** Nothing shipped; no task set |
| Any optimisation that fails stays off (counts as a pass) | Machinery ready: `docs/evals/OFF.md`, verdict `fails_success_bound` / `no_win` |
| Router beats the best single model after overhead and cache loss, or is off | Off. Not evaluated |
| Dry run on a known no-op change reports no difference | `eval selftest` passes on synthetic data. Not run on real tasks |
| Shadow runs show no unplanned side effects | Mirroring and write isolation tested on the fake provider only |

## Not built
- A private task set with hard cases and the 80-task Lite subset: needs the owner's repositories and tasks.
- Router rungs 2 and 3 (classifier, static router, cascade, probe); effort routing; instruction and prompt lint
  (`feat-instruction-lint`, `feat-prompt-lint`); cache planner for OpenAI, Gemini, xAI; one fix card per
  behaviour-change row (waits on the row-numbering decision); papers T6-T9.
- Dashboard pages for rewrites, cache monitor and shadow report (the files exist; the admin app does not read them).

## Things a reviewer should know
- **Nothing has seen real traffic.** Unit and integration tests use a fake provider. The context-management edit
  type, tool-search tool and their beta headers are unverified guesses, configurable; Claude Code over a subscription
  login may refuse them.
- **Sample size.** On synthetic identical arms with 80 tasks x 3 seeds the success interval is about ±8 pp, wider than a
  5 pp bound, so the self-test reports `fails_success_bound` rather than `no_win`. Size the bound and task count on a
  pilot before preregistering (plan/07: "fit the variance on a P2 pilot").
- **Ledger rows do not say which features fired**; the eval harness reads it from the arm's `decisions.jsonl`.
- **Order matters.** Put `rules_router` before `sticky_model`; do not enable `sticky_model` with `switch_pricer`.
  `output_cap` before `observation_masking`. Masking only moves every `step` events so the prefix stays cached.
- **Heuristics:** compaction is detected as a prompt-token drop over 50% in one session (server-side clearing can
  look the same); output-cap protect patterns are regexes; token counts are characters / 4.
- `compaction_guard` rewrites its state file on every call; fine for one developer, not for a team gateway.
