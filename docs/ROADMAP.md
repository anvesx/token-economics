# What is left to build

Written 2026-11-21, updated after the first P1 pass. Read this first in a new session, then `CLAUDE.md` (how the repo
works) and `docs/P0-STATUS.md` (card-by-card state of P0). The plan itself is in `plan/`; this file only lists what is
not built yet and what was learned while building.

## Where things are
- Repo: `anvesx/token-economics`. Local clone `~/HRMS/token-economics`. **Nothing is pushed.** `main` is blocked for
  the author; a senior dev merges.
- Branches (each on top of the one before): `feat/p0-working-core` (P0 first pass), `feat/p1-working-core` (P1 first
  pass), `feat/dashboard-sessions` (dashboard), `feat/p2-working-core` (P2 first pass), then `feat/p3-working-core`.
  State of P2: `docs/P2-STATUS.md`; decisions `docs/adr/0003`.
- State by phase: `docs/P0-STATUS.md`, `docs/P1-STATUS.md`. Decisions: `docs/adr/0001`, `0002`. Spike s2 is run
  (`spikes/s2-claude-code-402`); s1, s3, s4 are not.
- Sister repo: `~/HRMS/hermes-engine` (branch `m-agents`). Its leak detectors are vendored here unchanged from commit
  `43459d9`. The category audit behind them is `AUDIT-with-original-categories.md` in that repo.
- Source of every gate: `plan/PHASES.md`. Package map: `plan/13-monorepo-layout.md` and `plan/model/layout.json`.
  The 154 cards are in `token-economics-phase-playbook.pdf` (repo root) and `plan/phase-playbook.html`.
- The user's Mac: `~/.claude/settings.json` no longer routes Claude Code through `claudex` (backup beside it); the
  user may have a gateway running on port 8787 with real state in `~/.token-economics`. Use another port and a
  scratch `TOKEN_ECONOMICS_STATE_DIR` for tests.

## Dashboard (branch `feat/dashboard-sessions`, on top of P1)
- `token-economics-admin` now has Overview, Sessions, Session detail (tasks and leaks), Task detail, Categories and
  Gateway views (hash routes in one `static/index.html`). Sessions, tasks and categories come from Claude Code
  transcripts through `services/insight/sessions.py` (`SessionViews.overview/session/task`); the gateway view comes
  from the ledger. The two are not joined by session yet.
- Task detail (`/api/sessions/{id}/tasks/{n}`): spend by token type and model, main versus agent cost, context growth,
  cache behaviour, tool calls, files, largest tool results, turns, a call timeline and agents.
- Four categories and the task split depend on model labels (12, 22, 26, 10; see hermes `prompt_check.py`). The
  dashboard makes no model calls by default: it copies the labels cached in `~/.claude/metrics/prompt_checks.json`.
  The session page does not yet show whether a session was split by labels or by the rule.
- Tasks are split by the vendored `Session.tasks()` (model labels when cached or `--prompt-check`, else an idle-gap
  rule). Not validated against a person's judgement. Each task shows why its boundary was drawn.
- Never opened in a real browser by the builder or reviewer: layout is unchecked. The owner will supply the visual design.
- Not built: the hosted version with login (the owner chose local-only first; when it comes, they are willing to send
  session and task data including titles, visible to the owner and admins). Findings carry no timestamps, so leaks are
  per session, not per task.

## Starting P2 in a new session
1. Read this file, `CLAUDE.md`, both status files, then `plan/PHASES.md` (P2), `plan/06-context-guard.md`,
   `plan/07-observability-eval-rollout.md`, `plan/05-policy-router-budgets.md` (routing ladder).
2. Build order from the plan: eval harness first (`modules/stats`, `services/eval`, `evals/`), because nothing else
   in P2 may ship without a paired result. Then cache planner, context guard, router, shadow runs.
3. P2 features are `Feature`s like budgets: a factory `(env: FeatureEnv) -> Feature` under the
   `token_economics.features` entry-point group, off by default, switched in `policy.json`. **The `Feature` port can
   only allow or block today.** P2 features change the request (defer schemas, cap output, mask, route), so the port
   needs a way to return a rewritten body, and the gateway must send it. That is the first contracts change of P2.
4. Blockers to raise before coding: nothing sets `success` on ledger rows, so cost per successful task cannot be
   computed (the eval harness must supply it); there is no real task set; row numbering is undecided.
5. P3 wraps what P2 ships (canary, kill-switch, rollback). The three modes and the hot-reloaded policy file are the
   start of a kill-switch; per-tenant switches are not built.

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

## 2. P1: enforce — first pass built on branch `feat/p1-working-core`
State and gaps: `docs/P1-STATUS.md`. Decisions: `docs/adr/0002`. Left to build:
- Measure the budget overshoot on real traffic; make the reservation less pessimistic (it holds about $1.60 for a
  Claude Code "hi"); a "require a key" switch so dropping the header cannot escape a budget.
- Turn cap fed from the P0 baseline (`p75_caps`), remaining-turns reminder, loop-guard redirect, Codex facts.
- Fallback route, gateway bypass when the gateway is down, max-tokens enforcer, headless runner.
- Reconciler with weekly canary; alert delivery; admin write API with roles; YAML policy-as-code.
- Zero-risk guards for rows 15, 36, 42 once the row numbering is agreed.
- Papers T3, T4, T5.

## 3. P2: optimise (6 weeks, 59 cards) — first pass built on branch `feat/p2-working-core`
State and gaps: `docs/P2-STATUS.md`. The first thing left is a real private task set and a pilot run to size the bound.

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
- A running `token-economics-admin` or gateway keeps its old Python code; the page file is read from disk, so a new
  page against an old server shows "not found" for new endpoints. Restart after a change. Do not stop a server the
  user started: ask them to restart it, and test on your own port.
- `env.ANTHROPIC_BASE_URL` in `~/.claude/settings.json` overrides the shell variable; check it when a call seems to
  skip the gateway.
- Check the port is free before a live test: a gateway the user started was already on 8787 and a test call went through it.
- When running `claude -p` from a script, pass `stdin=DEVNULL`, or the script text becomes part of the prompt.
- A feature that holds state (a budget reservation) must be released on every path: block by a later feature, upstream error, no usage, oversize body.
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
- (P2) A rewrite must give the same bytes for the same history, and any state that changes the output (TTL choice,
  tool deferral, route) must be frozen per session; otherwise the prompt cache is lost on every turn.
- (P2) The policy engine used to load every registered feature; one half-built package broke all of them. It now
  loads only the switched-on ones, one at a time.
- (P2) A miss is the previous call's cached prompt not read back, not "fresh plus write": a growing conversation
  writes its new turn every time.
- (P2) Run `ruff format` on your own folders only; a repo-wide run reformats untouched files (services/ledger).
