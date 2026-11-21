# P0 status: working core

Branch `feat/p0-working-core`, 2026-11-21. P0 is "measure only": nothing is blocked or changed.
This is a first pass, not the P0 milestone. **The P0 exit gate is not met.**

## What runs today
- `token-economics-gateway`: pass-through proxy in observe mode. Responses are byte-identical with and without it
  (tested on a local fake provider). Each response becomes one priced ledger row after the last byte is sent.
- `token-economics init | report | detect | prices | replay`.
- 11 of the 45 packages in `plan/model/layout.json`, each with its own pyproject, tests, README and changelog.
- Checks that pass locally: ruff, mypy --strict, 149 package and integration tests, 37 tool tests, layering
  (import-linter, 16 contracts), public surface, and every package installing and passing its tests alone.

## Exit gate (PHASES.md)
| Gate line | Status |
|---|---|
| Computed cost within 1% of the vendor report for two weeks per provider | Not started. No reconciler; needs live traffic and the provider's usage and cost API |
| Every request has a `cost_source` and a `price_row_id` | Partly. Every ledger row has `cost_source`. `price_row_id` is empty when no price row is in force (all OpenAI models today) |
| 30-day baseline exists | Report command built (`token-economics report`). No data: needs 30 days of traffic through the gateway |
| Four spike results written in `09-risks-and-open-questions.md` | Not run. Question and method are in `spikes/*/README.md` |

## Cards (playbook P0, 49 cards)
| Epic | Card | Status |
|---|---|---|
| Repo setup | scaffold folders, CI, issue forms, PR template, CODEOWNERS | Done as files. CODEOWNERS and the security address are placeholders |
| | rulesets, required checks, ci-gate job | `ci-gate` job written, never run on GitHub. Rulesets, labels, milestones, project board not set up |
| | uv workspace, one pyproject per package | Done |
| | import-linter contract from layout.json | Done (`tools/check_layering.py --write-importlinter`) |
| | extraction test in a clean venv | Done (`tools/check_extractable.py`) |
| | ADR 0001 | Written, status proposed |
| Gateway in observe mode | proxy requests with virtual keys | Done. Keys live in a plain `keys.json`; an unknown key is observed as tenant "unknown", never blocked |
| | tee streamed responses without delaying the client | Done, tested |
| | define route, identify, observe, cap, replay | Done (`Adapter` port and shared contract suite) |
| | Claude Code adapter | Built, **not tried against real Claude Code**. Header names are assumptions, listed in the package README |
| | SDK adapter | Built, same caveat |
| | Codex CLI adapter | Built from `plan/02` only. No real Codex trace seen; `replay` not built |
| | replayed trace returns byte-identical responses | Done with fixtures written from the documented stream format, not recorded traffic |
| Ledger and price book | five exclusive buckets | Done for Anthropic and OpenAI. xAI, Gemini, Bedrock not built |
| | reject unknown usage keys | Done. The response still passes; the reject is logged with key names only |
| | one row per provider response id | Done (unique key, triggers block update and delete) |
| | append-only price book with 30-day staleness flag | Done. **All 12 seed rows are unverified** and flagged stale; OpenAI has no rows |
| | cost calculator in the order of 04 | Steps 1-4 done (normalise, band, base cost, multipliers). Not built: tool and storage fees, plan billing, marginal bands, batch-plus-cache stacking |
| | attribution by tenant, team, agent, session, prompt | Tenant, team, caller from the key; session from the adapter. `prompt_id` is empty: it needs the hook or OTel join (`modules/joiner`, `services/signals` not built) |
| | daily comparison with the vendor report | Not built. The nightly workflow job is a placeholder |
| Detectors in alert mode | base class and fired-count table | Done (`Detector` port, 50-row coverage table) |
| | the 50 rows | Uses the hermes-engine categories as implemented after its audit: 43 active, 7 retired (2, 3, 11, 14, 15, 19, 31). They run on **Claude Code transcripts only**, not on gateway traffic. Alerts do not yet name an owner or a recommended action |
| | coverage table doc | Generated on demand (`token-economics detect --md`), not checked in |
| Spikes | four spikes and the write-up | Not run |
| Baseline and gate | 30-day baseline report | Command built, no data |
| | gate(P0) exit review | Not met |
| Research papers | T1, T2 | Not started |

## Things a reviewer should know
- **Prices.** Seed rows come from `plan/16` and hermes-engine, not from the vendor page; `effective_from` is a
  placeholder date. Verify, then append new rows. Never edit a row.
- **Two cost models.** Ledger rows are priced by the price book. Detector estimates are priced by the vendored Hermes
  code with its own price table (which still has the stale Sonnet 5.5 cache-read price). Detector figures rank work
  only and are labelled `cost_source = client`.
- **Privacy.** The gateway stores no request or response text (tested by a storage scan). Detector findings carry a
  project folder name, file names and tool names from local transcripts: fine locally, redact before export. The model
  "prompt check" is off unless `--prompt-check` is passed.
- **Ledger fields never set yet:** `prompt_id`, `effort`, `ttl_class`, `attempt`, `task_id`, `success`. Cost per
  successful task cannot be computed until something sets `success`.
- **Gateway limits:** HTTP/1.1 only, no WebSocket; request bodies are buffered; a `zstd` response passes through but is
  not observed; a response over 64 MB is not observed.
- **Vendored code** in `services/insight/.../hermes/` is byte-identical to hermes-engine `43459d9` and excluded from
  ruff and mypy. `services/insight/tools/sync_hermes.py --check` detects edits.
