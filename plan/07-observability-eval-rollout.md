# Observability, evaluation and rollout

Token Economics ships no optimisation on token savings. It ships on cost per successful task (CPS) with a success bound held. Ids: `A:nnn` API corpus, `C:nnn` CLI corpus.

## Why not tokens

- 106 of 336 price comparisons reversed the sticker-price ranking, up to 28x (A:069).
- Output compressors cut tool-output tokens 38.4 percent and raised cost 6.8 percent. Token cut against cost correlated at r = 0.154 (C:024).
- One model scored 84.04 percent at $1.33 against 84.36 percent at $33.27 (A:207).

## Unit and metrics

The unit is one attempt: `(task, arm, seed)`. Compare by task with repeats, clustered by task and repo. Class tasks by observed behaviour, not human difficulty labels (Kendall tau 0.32, C:023).

| Metric | Definition | Baseline in corpus |
|---|---|---|
| Billed cost per attempt | five buckets priced separately | A:233 |
| CPS | all attempt cost, failed included, divided by successes | A:122, C:026 |
| Failed-run waste share | failed spend over total | 32 percent (C:028) |
| Spend after first repeated failure | share of total | 51 percent (C:028) |
| Cost dispersion | geometric SD per (task, arm) | x1.34 (C:027) |
| Probe error | abs(predicted − actual) / actual | 36 percent with one probe (C:027) |
| Cache hit per caller | read / (read + write + fresh) | C:052 |
| Cache-miss event | more than 5 percent and 2,000+ tokens reprocessed | C:076 |
| Reconciliation ratio | client estimate / invoice | tolerance not in corpus |
| Spend concentration | median and P95 per developer | $23 and $291 (C:054) |
| Multi-agent multiplier | team tokens / single-agent tokens, matched task | not in corpus |

Log with every attempt: prompt variant, effort, harness version, tool surface, retries, compaction, and whether the optimisation fired.

## Eval design

1. **Pair by task.** Several repeats per cell. Preregister the success bound (C:026, C:028).
2. **Isolate cache.** Separate namespaces or spacing per arm. Carryover is a validity threat: the median gap between arms was 10.8 seconds, inside the 5 minute TTL (C:024).
3. **Charge overhead to the task.** Router, probe and classifier cost count against the arm (C:028, C:030).
4. **Private task set with hard cases.** Public sets saturate at 96 to 98 percent (C:024). Hold out tasks from tuning: a regex router fell from 93.8 to 70.6 percent held out (A:052).
5. **Lite subset.** 80 tasks tracked the full 350 within 0.81 pp at 25.3 percent of the cost (A:060).
6. **Report paired CPS ratio** with a task-clustered bootstrap interval (C:026).

Added from the September to November 2026 papers (2609.33812, 2609.19607, 2609.23790):

7. **Store distributions, not points.** Identical runs differed more than the gap between agents, and cost differed over 20x on one model. Run tens to 100+ runs per agent. Capture cache read and write tokens per run.
8. **Use a fixed subset for A/B.** DeltaSelect compared configurations on a small subset for $27.86 across 13 evaluations. Report the p-value next to the cost delta.
9. **Correct for multiple comparisons.** Use a paired bootstrap with a Holm correction when several arms share tasks.
10. **Meter calls per task and injected context.** Memory injection was 13.6% of optimisable cost, 27.6% at depth 6. Log injected tokens per agent and depth, and the number of model calls per task.

Sample sizes seen in the corpus: 100 tasks (C:025), 38 to 45 effective tasks per arm (C:024), 60 tasks over 6 repos (C:028). Power formulas and minimum duration are not in the corpus. Fit the variance on a P2 pilot.

## Metrics by optimisation

| Optimisation | Primary | Guard |
|---|---|---|
| Cache and TTL | per-caller hit rate, cost per call | miss reasons (C:052) |
| Turn and budget caps | CPS | solve rate, empty-patch rate (C:025) |
| Output compression | end-to-end CPS | patch-apply, traceback integrity (C:024) |
| Masking, condensing | CPS | solve rate; negative at 7 events or fewer (C:133) |
| Tool pruning | CPS | tool-selection accuracy (C:028) |
| Routing, cascade | CPS | success, router latency, cache loss (A:006, C:030) |
| Effort, thinking | CPS | reasoning tokens (C:026) |
| Subagents, teams | token multiplier | CPS against a single agent (C:081) |
| Probe budgeting | prediction error | overrun rate (C:027) |

## Rollout

1. **Shadow.** Mirror traffic to the candidate with write isolation. Shadow doubles spend, so sample it (C:063).
2. **Canary.** A small per-tenant slice behind a flag.
3. **Kill-switch** per optimisation and per tenant. A breach reverts to the unchanged default path. A mid-run switch breaks caches (A:204, C:063).
4. **Auto-rollback triggers:**
   - success below the floor
   - CPS above the baseline interval
   - per-caller hit rate below its baseline
   - empty-patch or patch-apply spike
   - billed against estimate divergence
   - p95 latency up 20 percent (placeholder from C:063)

All thresholds are placeholders labelled DevX proposal until P2 measures them. No production shadow or canary result is in the corpus.

## Alerts

Budget alerts at 75, 90 and 100 percent (A:213, C:116). Size budgets near P95, not the mean (C:054). The corpus has no anomaly-detection method. P1 picks one and tests it against the P0 baseline.

## MUST rules

1. Headline metric is CPS including failed attempts (C:024, A:069).
2. Record a verifiable success flag on every attempt (C:026).
3. No optimisation ships without a same-task baseline arm and isolated cache (C:024, A:006).
4. Declare the non-inferiority bound before the test and revert on breach (C:025, A:052).
5. Attribute cost per caller, task, repo and model (C:052, C:028).
6. Report spend by median and P95 (C:054).
7. No voting, ensembles or agent teams without a measured CPS gain (A:122, C:132).
8. Count cache loss in every routing or model-switch decision (C:030).
9. Track defect burden next to cost. One developer's fix-commit ratio was 45.93 against 74.93 percent across two backends (C:053).

## Conflicts

| Question | Sources | Default |
|---|---|---|
| Agent-team multiplier | 7x quoted (C:001, C:010), "significantly more" (C:081), 3 to 5x (C:062) | Measure in P0 |
| Effort-control saving | 19 percent on one harness, 75 percent on another (C:026) | Test per harness |
| Optimisation transfer | Headroom +48 percent on Claude Code, −12.49 percent on Codex (C:024) | Test per harness |
| Critical error price | $0.01 and $0.20 in one paper (A:123) | Sweep it |
