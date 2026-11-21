# What is left to build

Written 2026-11-21 at the end of the first P0 pass. Read this first in a new session, then `CLAUDE.md` (how the repo
works) and `docs/P0-STATUS.md` (card-by-card state of P0). The plan itself is in `plan/`; this file only lists what is
not built yet and what was learned while building.

## Where things are
- Repo: `anvesx/token-economics`. Local clone `~/HRMS/token-economics`, branch `feat/p0-working-core`, 16 local
  commits, **not pushed**. `main` is blocked for the author; a senior dev merges.
- Sister repo: `~/HRMS/hermes-engine` (branch `m-agents`). Its leak detectors are vendored here unchanged from commit
  `43459d9`. The category audit behind them is `AUDIT-with-original-categories.md` in that repo.
- Source of every gate: `plan/PHASES.md`. Package map: `plan/13-monorepo-layout.md` and `plan/model/layout.json`.
  The 154 cards are in `token-economics-phase-playbook.pdf` (repo root) and `plan/phase-playbook.html`.

## 0. Test P0 before building more
Nothing here has seen real traffic. Do these first; each can change the design.
1. `uv sync --all-packages`, then `uv run token-economics init --tenant devx` and `uv run token-economics-gateway`.
2. Run Claude Code through it: `ANTHROPIC_BASE_URL=http://127.0.0.1:8787 claude -p "hi"`. Check:
   - the reply is normal and `curl 127.0.0.1:8787/_te/stats` shows `rows` going up, not `unknown_usage_key`,
     `no_usage` or `observer_errors` (rejects are in `~/.token-economics/rejects.jsonl`, key names only);
   - the ledger row's tokens equal the usage in the session transcript;
   - cache still works: `cache_read` tokens on the second turn are close to what a session without the gateway gets;
   - a subscription (OAuth) login works, not only an API key.
3. Confirm the adapter assumptions listed in `features/harness-adapters/README.md` ("Unverified"): the
   `x-claude-code-session-id` header, the `claude-cli` user agent, `metadata.user_id` shape, sub-agent headers,
   `ANTHROPIC_CUSTOM_HEADERS` format. Fix `providers/claude_code.py` to match what the real request carries.
4. Record two or three real responses, scrub the text, and replace the hand-written fixtures in `tests/integration`.
5. Verify the 12 seed prices on Anthropic's pricing page; append verified rows (never edit a row).

## 1. Finish P0 (exit gate not met)
| Item | What to build | Where |
|---|---|---|
| Vendor reconciliation, within 1% for two weeks | Daily job comparing ledger cost with the provider's usage and cost API; needs an admin API key | `services/reconciler` (new), `apps/worker` (new), nightly workflow placeholder exists |
| `prompt_id` and sub-agent attribution | Hook and OTel receivers, join on `session_id` + `prompt_id` | `modules/joiner`, `services/signals` (both new) |
| 30-day baseline | Only needs 30 days of traffic; `token-economics report` is built. Check the report in under `reports/baseline/` | data, not code |
| Four spikes | LiteLLM as core; Claude Code on a 402; cache loss on model switch; sub-agent multiplier. Write results into `plan/09-risks-and-open-questions.md` | `spikes/*/README.md` hold question and method |
| Detectors on gateway traffic | Today they read Claude Code transcripts only. PHASES wants all 50 on API traffic where the signal is in request and response bodies (families table in `plan/11`) | `services/insight` |
| Alert owner and recommended action | Each class 0 and class 3 row (7, 9, 10, 22, 26, 35, 38, 41, 44, 46, 47, 48, 49, 50) names an owner and an action | `services/insight` |
| Detector prices | Vendored Hermes uses its own price table (stale Sonnet 5.5 cache read). Fix in hermes-engine, then re-sync | `services/insight/tools/sync_hermes.py` |
| Cost formula steps 5 and 6 | Tool and storage fees (`server_tool_use`), plan billing, marginal bands, batch-plus-cache stacking | `modules/metering`, `modules/pricebook-core` |
| More providers | OpenAI price rows (blocked on the GPT-6 cache-write conflict in `plan/04`), xAI, Gemini, Bedrock normalisers and upstreams | one file per provider in each package |
| Codex adapter | Built from notes only; needs a real trace and `replay` | `features/harness-adapters/providers/codex.py` |
| Ledger store | Postgres behind the same `Ledger` port | `services/ledger` |
| Papers T1, T2 | Drafts, data, scripts | `papers/` (new) |
| GitHub | Rulesets, required `ci-gate` check, labels (`.github/labels.yml`), milestones, project board, real CODEOWNERS and security address | on GitHub |

## 2. P1: enforce (4 weeks, 20 cards)
Limits move outside the agent. New packages: `features/budgets`, `turn-cap`, `loop-guard`, `max-tokens`,
`headless-runner`; `services/health`, `policy`, `tenancy`, `insight` (dashboards), `reconciler`; `apps/admin-api`, `worker`.
- Per-key budget: reserve the worst case, then true up; 402 or 429 at the gateway when over; alerts at 75, 90, 100%.
- Turn cap at P75 of each model's own baseline (from the P0 baseline file, not a constant), with a remaining-turns reminder.
- Loop guard: stop at the first repeated-failure signature.
- Backend health, rate-limit tracking, fallback route.
- Failure posture: observation fails open, budgets fail closed (`docs/adr/0002`).
- Capability flags: no harness with `base_url` false is ever marked enforced.
- Zero-risk guards for rows 15, 36, 42, each with a replay showing task success unchanged. **Row 15 is retired in
  Hermes and row 42 dropped "briefs": agree the numbering with the plan owner first.**
- Invoice reconciler with weekly canary; dashboard by tenant, caller, model with median and P95.
- Papers T3, T4, T5.
- Exit gate: a test key cannot exceed budget by more than the measured overshoot; fault injection (429, timeout,
  stream cut) never double-counts or loses a row; both failure postures shown.
- Depends on: the P0 baseline (turn cap), spike s2 (how to signal a spent budget), spike s1 (build or reuse LiteLLM).

## 3. P2: optimise (6 weeks, 59 cards)
Every optimisation ships behind its own flag, off by default, and only after a paired win in cost per successful task.
- Eval harness first: private task set, 80-task Lite subset, paired task-clustered bootstrap, non-inferiority bound
  committed before each run, isolated cache per arm, a no-op change must report no difference. `modules/stats`,
  `services/eval`, `evals/`.
- Cache planner (TTL from the observed reuse gap) and per-caller hit-rate monitor.
- Context guard, in order: schema deferral, output caps, observation masking, tool-result clearing, compaction last.
- Router, in order: rules, atomic classifier, best-single baseline; static router and cascade only if they beat it
  after their own overhead and cache loss (`docs/adr/0003`).
- Shadow runs on mirrored traffic with write isolation. `services/rollout`.
- One fix card per behaviour-change row (33 candidates), each with a result file `evals/results/row-NN/`; failures go
  in `docs/evals/OFF.md`. **The playbook still lists retired rows 2, 3, 11, 14, 19, 31.**
- Papers T6-T9.
- Needs something to set `success` on ledger rows; nothing does today, so cost per successful task cannot be computed.

## 4. P3: harden (4 weeks, 26 cards)
- Canary stage and kill-switch per optimisation and tenant; with a switch off, responses match the P1 baseline byte for byte.
- Auto-rollback when success falls below the floor, cost per success rises above the baseline interval, cache hit
  rate drops, or billed cost diverges from the estimate. One drill per trigger, no deploy.
- Security: secrets handling, authorisation per tenant and role, retention and redaction, storage scan as a test.
- Multi-tenant limits, strong-model share ceiling, append-only audit log, admin API, anomaly detector, tier selector.
- Ops: every alert has an owner and a runbook, load test holds the P0 latency budget, disaster-recovery drill.
- Papers T10-T13, T14 outline. Tag v1.0.0.

## Decisions waiting on the plan owner
1. Row numbering: Hermes after the audit (43 active, 7 retired) or the playbook's original 50.
2. Detector placement: `layout.json` has no detector package; they sit in `services/insight` (a P1 package there).
3. Gateway core: ADR 0001 proposes the thin Starlette proxy over LiteLLM, pending spike s1.
4. Who owns the price book and how often rows are verified.
5. How Hermes itself continues: stay a plugin feeding this system (paper T12), or fold in.

## Lessons from the first pass (keep these)
- Apps import `contracts` only and find everything through entry points; after adding or changing an entry point run
  `uv sync --all-packages` or it will not resolve.
- The gateway must send headers upstream as a list, not a dict: Claude Code repeats `anthropic-beta`.
- Run the gateway's uvicorn with `server_header=False, date_header=False`, or responses gain headers.
- httpx adds default headers (`accept`, `accept-encoding`, `user-agent`); strip the ones the client did not send.
- Stream with `aiter_raw()` so compressed bodies pass through untouched; decompress only the observer's copy.
- Write the reject log line before bumping its counter (a test raced on this).
- Real Anthropic usage objects carry `service_tier`, `inference_geo`, `speed`, `output_tokens_details`,
  `server_tool_use`, `iterations`, `fallback_credit`; the normaliser must know them or it rejects every response.
- Model ids in real traffic are short (`claude-opus-5-5`); price lookup is exact-match only.
- Vendored Hermes modules read `CC_METRICS_DIR` at import and share one config dict; load them only through
  `_hermes_loader.py`. The model prompt check is off unless asked.
- `tools/check_surface.py` fails on anything public bound in a package `__init__.py` that is not in `__all__`; keep
  `__init__.py` to re-exports.
