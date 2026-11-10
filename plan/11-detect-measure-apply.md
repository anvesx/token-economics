# Detect, measure, apply

Token Economics detects waste on its own, measures it, and applies a fix only when a paired test shows the fix lowers cost per successful task (CPS). It does not solve every problem on day 1. Day 1 turns on detectors and zero-risk guards. Everything that changes agent behaviour waits for evidence on that harness.

Source for the metric list: `anvesx/hermes-engine`, read on 2026-11-10 by three reader agents. Notes: `_research/hermes/notes/A-taxonomy.md`, `B-detectors.md`, `C-capture-scoring.md`. Ids: `A:nnn` API corpus, `C:nnn` CLI corpus, `H:nn` hermes leak row. Fixes and tools without a corpus source are labelled DevX proposal.

## What hermes-engine is

A Claude Code plugin that reads session transcripts and finds "token leaks" (tokens paid for and not needed). It has 50 ranked leak rows, 103 detectors, and 29 rows it declares unmeasurable.

- It only observes. The one action it takes is to hide the user's own `rate N` prompt from the model. It never caps spend, switches models or blocks a tool (C-capture-scoring).
- It reads CLI transcripts under `~/.claude/projects`. Session id, helper agent, compaction and task boundary are CLI events. API traffic has none of them.
- Its dollar figures are list-price estimates. Leak costs overlap and do not sum to the total.
- No saving from any fix is measured. Its thresholds (10k, 20k, 15 reads, 4k, 60 percent) have no stated rationale.
- Its sample is 163 sessions from one team in one month: $1,703.41 of API-equivalent spend. The top rows by its own estimate are heavy starting context (25.3 percent), cache-write premium (19.9) and cold cache (15.0).

So Token Economics takes hermes as a detector library, not as a savings forecast. This follows the corpus finding that token cuts and cost cuts diverge (C:024, A:069).

## The answer: auto-detect, then earn the right to apply

| Question | Answer |
|---|---|
| Does Token Economics auto-detect issues? | Yes. Detectors run on ledger rows after the fact, never in the request path. |
| Does it measure them? | Yes. Each finding carries tokens, an estimated dollar cost, and the evidence rows. The estimate only ranks work. Savings are measured by a paired test. |
| Does it apply fixes automatically? | Only by class. Class 0 and 1 apply on detection. Class 2 applies after a paired win on that harness. Class 3 is a recommendation to a person. |
| Does it solve everything on day 1? | No. Savings are harness-specific and some reverse sign. Headroom raised cost 48.4 percent in one setting and cut it 12.49 percent in another (C:024). Masking loses at 7 events or fewer (C:133). |

## Four fix classes

| Class | What it does | Examples | Applies when |
|---|---|---|---|
| 0 Alert | Changes nothing. Raises a finding. | Cache hit below own baseline, unused tool schemas, failed-call loops | Always on from P0 |
| 1 Zero-risk guard | Bounds a worst case and cannot change a correct answer | `max_tokens` on every call (C:073), price-book staleness block, budget alerts at 75, 90 and 100 percent (A:213) | On from P1, shadow-logged first |
| 2 Behaviour change | Changes what the model sees or which model runs | Schema deferral, output cap, masking, clearing, loop redirect, routing, effort cap, cache lifetime (TTL) change, image downscale | Only after a paired CPS win for that harness and version, then canary |
| 3 Human action | Needs a person or a repo edit | Disable an unused Model Context Protocol (MCP) server, trim `CLAUDE.md`, retire stale skills, pick a plan | Never automatic. Token Economics files a recommendation with the estimated saving |

## The loop

1. **Detect.** A detector reads ledger rows and emits a finding when its metric breaches that caller's own baseline for K windows in a row. K and the thresholds come from the P0 baseline. The hermes constants are starting guesses only.
2. **Measure.** The finding records tokens at risk, the cost estimate, scope (tenant, caller, harness, harness version) and evidence row ids. The estimate uses hermes's carry rule: tokens times the cache-read price of every later call until the next compaction (H, leak_report.py). It ranks. It does not predict savings.
3. **Match.** The registry lists candidate fixes for the finding, each with its class and the adapter flags it needs. A missing flag means the fix degrades to a Class 0 alert on that harness.
4. **Gate.** Token Economics looks up the eval record for (fix, harness, version): untested, win, loss or inconclusive.
   - Untested: queue a replay on sampled traffic, then a paired test (07).
   - Win: start a canary slice behind the fix's flag.
   - Loss or inconclusive: stay off. Recommend only.
5. **Roll out.** Shadow, then canary, then on. Each step has a per-fix and per-tenant kill-switch (07).
6. **Watch.** The same detector keeps running on the treated slice. Rollback fires on the triggers in 07: success below floor, CPS above the baseline interval, hit rate below baseline, empty-patch spike, billed against estimate divergence, p95 latency up.
7. **Re-test.** A harness release resets that harness's eval records to untested. Cache reads changed after releases in the corpus (C:052, C:054).

## Metric to detector to open-source fix

The 50 hermes rows fold into 13 families. "Gateway" means the signal is in request and response bodies. "Hook" means it needs a CLI hook, transcript or attachment. Open-source names marked DevX proposal need a P0 spike (01 says the same for every reuse choice).

| Family | Hermes rows | Token Economics detector | Where it runs | Open-source option | Class | Phase |
|---|---|---|---|---|---|---|
| Cache | H:2, 3, 4, 16, 21, 23 | Per-caller hit rate vs own baseline; cache write never read back; rewrite cause from hashed tools and system prompt (order, timestamp, change) | Gateway, both | LiteLLM cache injection points (01); Langfuse for display | 0 alert; planner change is 2 | P0 detect, P2 fix |
| Starting context and tool schemas | H:1, 46, 48, 49 | First-request tokens minus the user turn; tools sent but never called per conversation | Gateway, both | Deferred tool loading with a lookup path (C:019, C:022); MCP proxy (DevX proposal) | 0, then 2; server removal is 3 | P0, P2 |
| History growth | H:6, 8, 10, 11, 17, 26, 38, 39 | Context above a size line; results still carried 30 calls on; compaction count | Gateway for size; hook for compaction | Harness clearing and masking (C:065, C:066, C:130) | 0, then 2 | P0, P2 |
| Tool output | H:14, 24, 25, 30, 34, 35, 40, 41, 43 | Result tokens above a size line; repeated reads of unedited files; dependency-folder hits | Gateway, both | Output cap via hook `updatedToolOutput` (06); compressors the RTK and Headroom tools stay off by default (C:024) | 0, then 2 | P0, P2 |
| Retries and loops | H:7, 9, 18, 22, 27 | Same tool and input failing in a row; spend after first repeated failure (51 percent, C:028) | Gateway, both | Loop guard built in Token Economics (06) | 0, then 2 | P1 shadow, P2 |
| Agents | H:5, 13, 15, 31, 32, 42 | Helper-agent first-call context; files read by siblings; report size | Hook (helper identity) | Subagent settings per harness (06) | 0; setting change is 3 | P0, P2 |
| Model fit | H:12, 45 | Strong-model share on tasks of low observed difficulty; price delta at same tokens | Gateway; class from behaviour (C:023) | LiteLLM router; RouteLLM (DevX proposal) | 0, then 2 | P2 |
| Output and thinking | H:29, 36, 45 | Output beyond visible text; truncation by `max_tokens` | Gateway | `max_tokens` cap; effort cap per class (C:026) | 1 for cap; 2 for effort | P1, P2 |
| Images and PDFs | H:19, 20, 28, 33 | Image tokens (w × h / 750); unchanged repeat screenshots; edit-screenshot cycles | Gateway | Image downscale with Pillow; `pdftotext`, `ocrmypdf` (named in hermes) | 0, then 2 | P0, P2 |
| Web and retrieval | H:37 | Repeated fetch of unchanged pages; overlapping results | Gateway | Response cache (DevX proposal, correctness risk) | 0; 2 only after a test | P2 |
| Instructions and skills | H:46, 49, A14–A19, A68, A70 | `CLAUDE.md` over 200 lines; `AGENTS.md` over 32 KiB (C:077, C:036); stale skills | Hook | A linter in Token Economics's CLI; no gateway fix | 0 and 3 | P1 |
| Idle and repeat work | H:44, 47, 50 | Turns with no typed prompt; same first request across sessions | Hook | Memory or handoff file (C:035) | 0 and 3 | P1 |
| Cost accounting | H:2, 3 | Reconciliation ratio: client estimate over invoice | Gateway | ccusage for CLI usage; Langfuse (01) | 0 | P0 |

### Coverage, API against CLI

By my reading of `B-detectors.md`, of the 26 core detectors:

- 4 run from the gateway alone (cache loss, screenshots, MCP schema bloat, trivial-turn thinking).
- 14 take the signal from the gateway and need an identity from a key, prefix hash or hook.
- 5 need CLI-only data: compaction, helper identity, the idle hook, skill listings.
- 3 are aliases or a coverage statement.

For API agents Token Economics derives its own conversation key (prefix hash plus idle gap), because API traffic carries no session id (B-detectors §2). For CLI agents it joins gateway rows to hook and OpenTelemetry rows on `session_id` and `prompt_id` (02). A harness without `baseUrl` gets the hook and transcript path only. Its Class 2 fixes drop to alerts.

### What the gateway adds to hermes

Hermes lists 29 rows it cannot measure. Token Economics's position on the request path closes some of them. This is a mapping, not a tested result.

| Hermes reason | Rows | Token Economics route |
|---|---|---|
| Needs the exact request body | A28, A31, A32, A33, A39, A43 | Gateway sees `cache_control` breakpoints, edited messages and `tool_choice` |
| Needs model calls not in transcripts | A36, A137, A140 | Gateway ledger and OpenTelemetry |
| Needs matched runs or a second tokenizer | A42, A49, A50 | Token Economics's own eval harness (07) and `count_tokens` |
| Needs labelled review | 17 rows (A3, A4, A20, A44, A46, A47, A48, A55, A56, A59, A102, A108, A113, A119, A129, A130, A132) | Opt-in judge on a sample, reported as an estimate. Never a trigger for a Class 2 fix. |

## How open-source tools plug in

Each tool sits behind one contract, so Token Economics can swap it without touching the policy engine.

| Part | Contract | Note |
|---|---|---|
| Detector | Reads ledger rows, returns findings | Runs async. Fails open. |
| Fix | `preconditions`, `apply`, `revert`, `metrics`, `class` | `revert` must restore the unchanged path. |
| Registry | Detector → fixes, plus eval record per (fix, harness, version) | One row per pairing. |
| Flag state | off, shadow, canary, on, rolled back | Per fix and per tenant. |

Three ways a tool attaches:

1. **In the gateway.** LiteLLM is the gateway core (01), so cache injection, budgets and routing are config, not new code.
2. **As a sidecar.** Langfuse and an OpenTelemetry collector receive events and draw the dashboards. They never change the cost.
3. **In the harness.** Hook scripts and managed settings carry fixes the gateway cannot make, such as output caps and subagent settings. Managed config stops a developer from bypassing them (C:104, C:074).

A tool that cannot supply `revert` does not ship as a fix.

## What auto-applies, and what must not

| Auto-apply on detection | Needs a paired win first | Never automatic |
|---|---|---|
| `max_tokens` cap, stale-price block, budget alerts, cache-hit alert | Schema deferral, output cap, masking, clearing, loop redirect, routing, effort cap, TTL change, image downscale | Disable an MCP server, edit `CLAUDE.md`, change plan, turn on output compressors |

Compressors stay off until a per-workload A/B shows at least 99 percent marker recall (06). A semantic response cache is unproven for correctness and stays off.

## Rollout by phase

| Phase | Detect, measure, apply |
|---|---|
| P0 | Detectors for the 13 families run in alert mode. Baselines per caller. Nothing blocks. |
| P1 | Class 1 guards go on, shadow-logged first. Loop guard in shadow. Instruction linter. |
| P2 | Each Class 2 fix runs the paired test per harness. Wins get a canary. Losses stay off. |
| P3 | Auto-canary on a win. Auto-rollback drills. Kill-switch per fix and per tenant. |

## Open questions

| Question | Resolve in |
|---|---|
| Detector thresholds. Hermes's have no stated basis. | P0 baseline |
| How many windows (K) before a finding triggers the loop | P0 baseline |
| Whether `revert` is clean for each open-source option | P0 spike |
| Licence and maintenance status of each named tool | P0 spike |
| Detection delay against cost: async detection cannot stop the first bad call | P1 measurement |
| Which hermes rows mean real waste, since its own costs overlap | P2 paired tests |
