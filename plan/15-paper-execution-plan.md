# Paper execution plan for the Token Economics 14-paper series

**Bottom line.** Run the 14 papers as one registered programme on one shared harness. Expect no Nature-family paper from this series. Aim for top machine-learning (ML) and systems venues, and submit only what clears the gate in section 5.

This plan turns `14-research-papers.md` into checkable work. It adds numbers, tests, files and dates. It invents no citations, effect sizes or venue policies. Anything not in the plan or the corpus is marked "unverified". Section 7 lists all of them.

Terms used throughout.

- Cost per successful task (CPS) is the series metric.
- A pilot is a named phase task that measures an assumed number.
- Confidence interval (CI), standard deviation (SD) and intra-class correlation (ICC) carry their usual meaning.
- Design effect (DEFF) is the variance inflation from clustering.
- Two one-sided tests (TOST) test equivalence.
- Benjamini-Hochberg (BH) controls the false discovery rate.
- Open Science Framework (OSF) is the registry target.
- Terms of service (ToS) are the provider contracts.
- Time to live (TTL) is the cache lifetime.
- The International Committee of Medical Journal Editors (ICMJE) and the Committee on Publication Ethics (COPE) set AI-disclosure norms.
- Contributor Roles Taxonomy (CRediT) lists 14 author roles.
- P0 to P3 are the phases in `PHASES.md`. W counts weeks from the start of P0.
- Venue acronyms, all "verify at submission". Mining Software Repositories (MSR). International Conference on Software Engineering (ICSE). Foundations of Software Engineering (FSE). Transactions on Machine Learning Research (TMLR). International Conference on Machine Learning (ICML). Empirical Methods in Natural Language Processing (EMNLP). Association for Computational Linguistics (ACL). Operating Systems Design and Implementation (OSDI). Advanced Computing Systems Association (USENIX) Annual Technical Conference (ATC). Machine Learning and Systems (MLSys).

## 1. Series-level plan

*Method source. `scientific-writing` (salami and duplicate-publication checks), `statistical-analysis` (one family per claim), `scientific-critical-thinking` (null results).*

**One harness, one task set, one method paper first.** Every confirmatory result runs through `services/eval` and `modules/stats`. T6 fixes the method. Later papers cite it and do not restate it.

### 1.1 Order

| Wave | Papers | Why this order |
|---|---|---|
| A, P0 data | T1, T2, T3 | Needs only the ledger. T2 may absorb T13. |
| B, P1 data | T4, T5 | Needs the enforcement logs and randomised arms. |
| C, method | T6 | Strongest gap. Every P2 paper depends on its harness. Write it first in P2. |
| D, P2 data | T7, T8, T9 | Each uses the T6 harness. T9 is a replication. |
| E, P3 data | T10, T11, T12, T13 | T11 and T13 are small. Fold if the data is thin. |
| F, synthesis | T14 | Reports only the composed system. Cites the rest. |

### 1.2 Shared evaluation harness

| Element | Fixed value | Source |
|---|---|---|
| Design | Paired by task, clustered by repository, cache isolated per arm | `PHASES.md` P2 gate |
| Success test | Non-inferiority (NI) margin on success, set before data | `PHASES.md` P2 gate |
| Cost test | Superiority on log cost per successful task | `14-research-papers.md` T6 |
| Combined test | Intersection-union test, so both must pass | Method, `statistical-analysis` |
| Dry run | A no-op change must report no difference | `PHASES.md` P2 done table |
| Code | `modules/stats` and `services/eval`, tagged per paper | `13-monorepo-layout.md` |
| Tooling | Python 3.12, scipy 1.18.1, numpy 2.5.2, no statsmodels | Local check, this session |

### 1.3 Shared task sets

| Set | Size | Use | Constraint |
|---|---|---|---|
| Private hard set | To be built in P2 | Confirmatory runs | Baseline success on public sets is 96 to 98% (C:024), which leaves no room to detect harm. |
| Public Lite subset | 80 tasks, from Claw-SWE-Bench (A:060, 350 tasks) | Dry runs and external check | Cannot support a 5 percentage point (pp) margin. Minimum margin is about 8 to 19 pp (section 4.3). |
| Pilot split | Disjoint from confirmatory | Tune thresholds, estimate variance | Never reused for a confirmatory test. |
| Contamination canary | Fresh tasks written after the model cutoff | Detect leakage | Report the gap to the main set. |

**The margin follows decision value, not feasibility.** If the Lite subset cannot reach the margin, the paper says so and does not widen the margin.

### 1.4 Avoiding salami-slicing and self-plagiarism

| Rule | Check |
|---|---|
| Each paper has one primary question no other paper answers | Claim table in section 3 has no repeated primary endpoint |
| One data lineage table, shared | Each paper lists which ledger rows and eval runs it reuses |
| Method text is cited, not copied | T6 holds the method. Others cite it and quote at most the numbers |
| T14 adds no component claim | It reports the composed A/B only |
| Overlap is disclosed in every cover letter | Lists the sibling preprints and the shared data |
| Text-overlap scan before submission | Run a local similarity check against sibling drafts (tool unverified) |

### 1.5 Null-result policy

- **A null is a result.** `14-research-papers.md` says a stated non-result is a valid paper. Report it.
- **Endpoints are never dropped.** A registered endpoint appears in the paper even if it fails.
- **Failed P2 rows stay on the off list.** `PHASES.md` counts them as done.
- **Weak result.** Post the preprint, skip the journal, and fold the result into T14 or a registered-report venue (verify at submission).
- **Positive-only exceptions.** None. No paper is held back for being negative.

## 2. What Nature-grade means here

*Method source. `scholar-evaluation` (qualitative, evidence-traceable review) and `peer-review` (claim and evidence fit).*

**No title in this series is likely to reach a Nature-family venue.** The data comes from one team of about three engineers on a handful of repositories. Nature-family editors look for broad scientific significance and large, general datasets. All venue statements are unverified, check at submission.

| Title | Nature-family plausibility | Reason | Realistic venue (verify at submission) |
|---|---|---|---|
| T1 | Remote | A metric definition. Two 2026 papers already use the metric. | MSR or an empirical-software-engineering journal |
| T2 | Remote | An audit. Useful, narrow. | MSR data-showcase track, or workshop |
| T3 | Remote | Three harnesses, small user base. | MSR, ICSE software-engineering-in-practice track |
| T4 | Remote | Engineering measurement. | MLSys or a systems workshop |
| T5 | Low | Behavioural question with a clear conflict in prior work. Needs many tasks. | NeurIPS main or workshop, ACL-family if framed on language agents |
| T6 | Low, the best case | A method with wide reuse. Would need a large multi-lab validation. | NeurIPS Datasets and Benchmarks, or TMLR |
| T7 | Remote | A planning rule tied to vendor price multipliers that can change. | MLSys, or a systems venue |
| T8 | Low | Strong question. Needs real traffic from more than one organisation. | NeurIPS Datasets and Benchmarks, or EMNLP industry track |
| T9 | Remote | Mostly covered. Replication value only. | ReScience-style venue or workshop |
| T10 | Low | A general stopping-rule result could travel, if the knee holds across models. | ICML or NeurIPS main, or TMLR |
| T11 | Remote | The bound holds by construction (section 3, T11). | Security workshop, or fold into T8 |
| T12 | Remote | Method comparison on one system. | ICSE or FSE tools track |
| T13 | Remote | Thin evidence. Fold into T2. | Section of T2 |
| T14 | Remote | A system paper from one team. | EuroSys or USENIX ATC, then MLSys; OSDI only if the evidence is much larger |

**Why none reach Nature.** Four reasons recur.

1. **Scale.** P0 has about three engineers. Caller and repository counts are unknown until the P0 baseline and may be small.
2. **Vendor dependence.** Prices, cache lifetimes and usage schemas change. Results decay.
3. **Prior work.** T1, T4, T9 and T10 overlap published work (`_research/R7-paper-novelty.md`).
4. **Venue fit.** These are engineering-economics results. Nature journals want findings that matter beyond the field.

**The long shot.** One synthesis paper built from T6, T8 and T10 with several organisations as data sources could be sent to a Nature-family methods or machine-intelligence title. It needs partners and data that the plan does not have. Treat it as a stretch goal, not a plan.

## 3. Shared statistical conventions

*Method source. `statistical-power` (power as a function of assumed effect), `statistical-analysis` (tests, multiplicity, effect sizes).*

### 3.1 Planning model

| Quantity | Value | Status |
|---|---|---|
| Within-task run-to-run cost ratio | x1.34, so `sigma_w = ln 1.34 = 0.293` | From C:027, which says only "spread". Read here as a ratio SD, so it is an assumption. A smaller true value shrinks every n below. |
| Task by arm interaction SD `tau` | 0.20, range 0.10 to 0.30 | Assumed. Pilot P0 baseline and P2 pilot replace it. |
| Repeats per task `k` | 3 | Design choice |
| SD of the paired log cost difference | `sqrt(tau^2 + 2*sigma_w^2/k) = 0.312` | Computed in this session |
| Repository ICC | 0.10 with 10 tasks per repository, so DEFF = 1 + 9*0.10 = 1.9 | Assumed |
| Within-task DEFF for binary success | 1 + (k-1)*0.5 = 2.0 | Assumed |
| Attrition | 10% | Assumed |
| Test size and power | Two-sided alpha 0.05 for cost, one-sided 0.025 for NI, power 0.80 | Convention |

### 3.2 Sample size for the cost test

Formula. `n = ((z_{1-a/2} + z_{1-b}) * SD / d)^2`, then multiply by DEFF, then divide by 0.9. Here `d = -ln(1 - cut)`.

| Cost cut to detect | Tasks, no clustering | Tasks with DEFF 1.9 | Tasks enrolled with attrition |
|---|---|---|---|
| 5% | 290 | 551 | 612 |
| 10% | 69 | 131 | 145 |
| 15% | 29 | 55 | 61 |
| 20% | 16 | 30 | 33 |

At 90% power the 10% row is 92, 175 and 195.

Holm correction. The sizes above use alpha 0.05 for one contrast. For `m` contrasts, size at alpha/m. Two contrasts (T5) need about 1.2 times these tasks. Four contrasts (T8) need about 1.4 times. Apply the factor before enrolling.

### 3.3 Sample size for the non-inferiority test on success

Formula for discordant pairs. `n_pairs = (z_{1-a} + z_{1-b})^2 * pD / margin^2`. `pD` is the share of pairs where arms disagree. Then multiply by both design effects and divide by `k`.

| Margin | `pD` 0.1, tasks enrolled | `pD` 0.2, tasks enrolled | `pD` 0.3, tasks enrolled |
|---|---|---|---|
| 5 pp | 442 | 884 | 1,326 |
| 7.5 pp | 197 | 393 | 590 |
| 10 pp | 111 | 221 | 332 |
| 15 pp | 50 | 99 | 148 |

`pD` is unknown until the P2 pilot. The default plan uses 10 pp and `pD` 0.2, so 221 tasks.

### 3.4 What the 80-task Lite subset can support

Minimum detectable margin with 80 tasks and `k = 3`.

| `pD` | Within-task DEFF only | With repository DEFF too |
|---|---|---|
| 0.1 | 8.1 pp | 11.1 pp |
| 0.2 | 11.4 pp | 15.8 pp |
| 0.3 | 14.0 pp | 19.3 pp |

**Consequence.** The Lite subset is a dry-run set. It cannot carry a 5 pp margin.

### 3.5 Other conventions

| Topic | Rule |
|---|---|
| Interaction tests (T9) | Difference in log effect between harnesses. At 0.10, 0.20 and 0.528, independent tasks per harness are 153, 39 and 6. Paired halves are 77, 20 and 3. |
| Carryover between repeats | Bias of 5%, 10% and 20% needs 290, 69 and 16 tasks. |
| Zero-failure bound | `n = ln 0.05 / ln(1-p)`. For p = 1% that is 299. For p = 0.1% it is 2,995. |
| Few repositories | Wild cluster bootstrap or exact sign-flip randomisation. With n units the smallest two-sided p is `2/2^n`, so 6 units are the minimum for p < 0.05. |
| Annotation | Two annotators, Cohen's kappa threshold 0.7 (unverified). Adjudicate the rest. |
| Confirmatory families | Holm correction inside each paper. |
| The 33 P2 rows | Benjamini-Hochberg across rows, per `PHASES.md` row counts. |
| Effect sizes | Report log ratio of cost, percentage-point difference for success, and a paired standardised effect (`d_z`). |
| CI method | Cluster bootstrap by repository, 10,000 resamples, percentile intervals. BCa where n repositories is at least 20. |
| Not computable | Any power number whose input needs a pilot is written as a function. Section 7 lists each one. |

### 3.6 Run cost basis

Cost per attempt is $0.86, taken from the Quesma scale ($1,500 over 1,740 attempts, which is $0.862; totals below use the rounded $0.86 and differ from $0.862 by under 0.3%). It is a vendor-affiliated figure and unverified. Replace it with the P0 baseline mean cost per attempt.

| Run | Attempts | Cost at $0.86 |
|---|---|---|
| Two arms, 146 tasks (145 rounded up to an even count), k = 3 | 876 | $755 |
| Two arms, 221 tasks, k = 3 | 1,326 | $1,143 |
| Two arms, 299 tasks, k = 3 | 1,794 | $1,547 |
| 34 arms, 221 tasks, k = 3 | 22,542 | $19,433 |
| 66 arms, 221 tasks, k = 3 | 43,758 | $37,722 |

## 4. Reading the per-paper tables

*Method source. `scientific-writing` (reporting guideline coverage), `peer-review` (referee checklist).*

- Each table has the 11 required fields. Row numbers match the brief.
- "Frozen" means a hash or git tag recorded in the OSF registration before confirmatory data is seen.
- Registration target is OSF or an equivalent (verify at submission).
- Reporting-summary fields follow the Nature Portfolio form (unverified, check the current form at submission). Statistics, software, data, code, randomisation and blinding are in row 6 of every table.
- Every venue name is "verify at submission".

**Common frozen set.** Task manifest hash, analysis code tag, price-book snapshot id, exact model ids, margin and seeds.

**Common software line.** Python 3.12, scipy 1.18.1, numpy 2.5.2, pinned in `uv.lock`.

**Common disclosure line.** AI assistants help with drafting and code. Humans check every number and take responsibility, per ICMJE and COPE guidance (unverified, check at submission).

## 5. Per-paper plans

### T1. Cost per successful task, specified

*Method source. `statistical-power` (precision-based sizing), `scientific-critical-thinking` (construct validity of "success").*

| # | Field | Plan |
|---|---|---|
| 1 | Claim and null | Counting failed attempts, retries, router and judge cost raises CPS by more than 5% over success-only cost, or changes the harness ranking, on the P0 30-day ledger. Null: the rise is 5% or less and the ranking is unchanged. |
| 2 | Pre-registration | H1 as stated in row 1. Primary endpoint is the ratio `CPS_full / CPS_success_only` per harness. Secondary: share of spend in failed runs, share censored at the turn cap. Stopping rule is the fixed 30-day window, no peeking. Exploratory: per-model splits. Register on OSF at W1. Frozen before data: the definition of success, the censoring rule, the 5% threshold and the analysis tag. |
| 3 | Design and baselines | Observational ledger, paired within harness, clustered by developer and repository. Baselines are success-only cost, cost per call and cost per token. Ablation drops each numerator term in turn. Held-out set is the last 7 days of the window. Contamination control is not needed for live traffic. Eval-task runs use the T6 contamination canary. |
| 4 | Statistics | Unit is the task. Statistic is the log ratio. Cluster bootstrap CI by repository. Holm across at most 3 harnesses. Sizing is by precision. A CI half-width of 0.05 on the log ratio with SD 0.312 needs `(1.96*0.312/0.05)^2 = 149` tasks, 283 with DEFF 1.9. This is a function of assumed `tau`. P0 baseline measures it. |
| 5 | Threats | Internal, success labels on live traffic are proxies; mitigate by using test-pass or merge as the label and reporting label noise. External, three engineers; state it. Construct, "success" differs by harness; one definition frozen. Statistical, few clusters; use sign-flip randomisation. |
| 6 | Reproducibility | Data statement. Aggregated ledger export under `evals/`, no prompts, public after the tenant-data check. Code at `papers/t1-cps/code`, tagged. Frozen artifacts listed in section 4. Seeds fixed for the bootstrap. Rerun cost about $0 (ledger only). Reporting summary fields as in section 4. |
| 7 | Ethics and disclosure | Provider ToS on publishing usage and cost data (unverified, check each). Metadata-only logging per `08-security-reliability.md`. Conflict of interest, authors build the product. AI-use line as in section 4. No security issue to disclose. |
| 8 | CRediT roles | Conceptualization, Methodology, Data curation, Formal analysis, Software, Writing original draft, Writing review and editing, Supervision. |
| 9 | Venue fit | Primary MSR (verify at submission). Fallback an empirical software engineering journal (verify at submission). Referees ask for the success definition, prior CPS use and clear external-validity limits. |
| 10 | Referee objections | See table below. |
| 11 | Calendar | Calendar week W4 in `14-research-papers.md`. Plan: register W1, freeze W4, preprint W6, submit W8. Gate W7. Phase gate P0 exit (baseline exists). Do not submit alone if the CI on the log ratio includes 0.05 and the ranking holds. Fold into T14. |

| Objection | Answering evidence | Rebuttal plan |
|---|---|---|
| The metric is not new | Two 2026 papers use it (R7) | Claim only the accounting rules, with a worked ledger example |
| Success on live traffic is unverifiable | Label-noise audit on a 100-row sample | Report both proxy and verified-set results |
| Three users is too few | Cluster counts stated | Frame as a specification plus a case study |
| Vendor schemas differ | Ties to T2 | Cite T2 conformance suite |
| Censoring hides cost | Censor share reported | Sensitivity run with censored runs priced at cap |

### T2. Five exclusive token buckets

*Method source. `statistical-power` (zero-failure bound), `scientific-writing` (data and code statements).*

| # | Field | Plan |
|---|---|---|
| 1 | Claim and null | Naively summing reported input fields mis-states billed tokens by more than 2% on at least one of five vendors. The 2% tolerance is the plan's attribution figure (unverified). Null: error is 2% or less on all five. |
| 2 | Pre-registration | H1 as stated in row 1. Primary endpoint is relative error between naive sum and invoice, per vendor. Secondary: share of responses with any bucket mismatch, and dollar error. Stopping rule is the P0 two-week reconciliation window. Exploratory: per-model error. Register at W1. Frozen: golden usage fixtures, the five-vendor list (unverified) and the error definition. |
| 3 | Design and baselines | Conformance suite of golden `usage` blocks per vendor, replayed on the ledger. Baselines are naive sum, the LiteLLM normaliser (vendor data) and OpenTelemetry GenAI attributes (not yet read). Ablation removes one bucket rule at a time. Held-out set is fixtures not used to write the normaliser. |
| 4 | Statistics | Unit is the response id. Clopper-Pearson CI on mismatch share. Holm across 5 vendors. Zero-failure sizing. To show a mismatch rate below 1% with none seen needs 299 responses per vendor. Below 0.1% needs 2,995. Effect size is the relative dollar error. |
| 5 | Threats | Internal, fixtures encode the project's own reading of the schema; mitigate with vendor doc cites and an invoice match. External, schemas change; date-stamp each. Construct, "exclusive bucket" is our definition; state it. Statistical, rare mismatches; use the bound. |
| 6 | Reproducibility | Fixtures and normaliser public in `modules/metering`. Ledger sample public after the tenant-data check. Seeds not needed. Pins on SDK versions. Rerun cost about $0 for replay, a few dollars to refresh fixtures. Reporting summary as in section 4. |
| 7 | Ethics and disclosure | Provider ToS on API output redistribution (unverified). Fixtures contain no customer prompts. Conflict of interest as T1. AI-use line as in section 4. Disclose schema discrepancies to vendors before posting. |
| 8 | CRediT roles | Conceptualization, Methodology, Software, Validation, Investigation, Data curation, Writing original draft, Writing review and editing. |
| 9 | Venue fit | Primary MSR data showcase (verify at submission). Fallback a workshop (verify at submission). Referees ask for vendor coverage and invoice evidence. |
| 10 | Referee objections | See table below. |
| 11 | Calendar | W4 in the plan. Register W1, freeze W4, preprint W6, submit W8, gate W7. Phase gate P0 exit (ledger matches invoice within 1%). Do not submit if no vendor exceeds the 2% tolerance. Publish the suite as a package note instead. |

| Objection | Answering evidence | Rebuttal plan |
|---|---|---|
| Only a bug list | Dollar error per vendor | Quantify error with the invoice match |
| Five vendors is arbitrary | Vendor list rationale (unverified) | State selection rule before data |
| Schemas change | Date-stamped fixtures | Weekly canary from T13 |
| No prior art check | R7 found practitioner sources only | Add OpenTelemetry GenAI read |
| Invoice data is private | Aggregated error only | Publish ratios, not amounts |

### T3. Where the billed dollar goes

*Method source. `statistical-analysis` (compositional data, permutation tests), `scientific-critical-thinking` (confounding).*

| # | Field | Plan |
|---|---|---|
| 1 | Claim and null | The share of billed dollars from tool output plus history differs across Claude Code, Codex and one other harness. Null: the share vectors are equal across harnesses. |
| 2 | Pre-registration | H1 as stated in row 1. Primary endpoint is the dollar share of tool output plus history. Secondary: base prompt and schema shares. Stopping rule is the 30-day window. Exploratory: per-task-type splits. Register at W2. Frozen: the four-component definition, harness versions, the replay set. |
| 3 | Design and baselines | Ledger observation plus a fixed replay arm of 100 tasks on all 3 harnesses. Baselines are published splits (C:023, A:059). Ablation merges components. Held-out set is the replay arm. |
| 4 | Statistics | Unit is the session, clustered by developer. Isometric log-ratio transform, then permutation test on the harness label. Cluster bootstrap CI. Holm across 3 harness pairs. Sizing. A share CI half-width of 0.05 at p = 0.5 needs 385 sessions, 730 with DEFF 1.9, per harness. Assumed ICC. |
| 5 | Threats | Internal, users differ by harness; mitigate with the replay arm. External, one team. Construct, component boundaries are harness-defined; document the mapping. Statistical, small clusters; sign-flip test. |
| 6 | Reproducibility | Aggregated shares public. Replay set public if licence allows (unverified). Harness versions pinned. Rerun cost about $258 for the replay arm (100 tasks, 3 harnesses, one attempt, $0.86 each). Reporting summary as in section 4. |
| 7 | Ethics and disclosure | ToS of three harness vendors on benchmarking (unverified). Replay uses public repositories only. Conflict as T1. AI-use as section 4. |
| 8 | CRediT roles | Conceptualization, Investigation, Data curation, Formal analysis, Visualization, Writing original draft, Writing review and editing. |
| 9 | Venue fit | Primary MSR (verify at submission). Fallback ICSE software engineering in practice (verify at submission). Referees ask for confound control and harness version detail. |
| 10 | Referee objections | See table below. |
| 11 | Calendar | W6 in the plan. Register W2, freeze W5, preprint W8, submit W10, gate W9. Written in P1 from P0 data. Do not submit if the share vectors differ by less than the bootstrap CI. Fold into T14. |

| Objection | Answering evidence | Rebuttal plan |
|---|---|---|
| Blog contradicts itself on schema tokens | The project's token counts from billed usage | Cite billed tokens, not estimates |
| Users confound harness | Replay arm | Report replay as primary |
| Prior work exists (C:023, A:059) | Four-component split in dollars is new | State the delta in the intro |
| Harness versions drift | Pinned versions | Date-stamp and rerun on next version |
| Small sample | Cluster-aware CI | Show width, not only point |

### T4. How much does a soft budget leak

*Method source. `statistical-power` (quantile estimation), `scientific-critical-thinking` (simulation vs live).*

| # | Field | Plan |
|---|---|---|
| 1 | Claim and null | The 95th percentile overshoot under post-hoc caps is more than 2 times that of reserve-then-true-up caps on the same sessions. The factor 2 is a decision value. Null: ratio is 1 or less. |
| 2 | Pre-registration | H1 as stated in row 1. Primary endpoint is the ratio of P95 overshoot, as share of the limit. Secondary: mean overshoot, share of sessions over limit. Stopping rule is 400 sessions or the P1 gate, whichever is first. Exploratory: per-harness. Register at W5. Frozen: limits, session set, overshoot definition. |
| 3 | Design and baselines | Replay of the same session traces under both designs, plus the P1 live fault-injection test. Baselines are harness-side cap and post-hoc invoice cap. Ablation varies the reserve size. Held-out set is sessions after the limits are set. |
| 4 | Statistics | Unit is the session. Primary endpoint is the P95 overshoot ratio, tested by a quantile bootstrap CI. Paired Wilcoxon signed-rank on median overshoot is secondary and reported without a claim. One primary, so no correction. Sizing. P95 needs about 20 exceedances to be stable, so 400 sessions. Assumed. Flag. |
| 5 | Threats | Internal, replay ignores agent reaction to a block; mitigate with the live test. External, three harnesses. Construct, overshoot depends on stream length; report by length. Statistical, tail estimates are unstable; show bootstrap width. |
| 6 | Reproducibility | Session traces hashed, aggregated overshoot public. Code in `features/budgets`. Seeds fixed. Rerun about $0 for replay, a few dollars for live test. Reporting summary as section 4. |
| 7 | Ethics and disclosure | ToS on automated budget blocking (unverified). No content stored. Conflict as T1. AI-use as section 4. Disclose any bypass found in a vendor limit to the vendor first. |
| 8 | CRediT roles | Conceptualization, Methodology, Software, Investigation, Validation, Formal analysis, Writing original draft. |
| 9 | Venue fit | Primary MLSys (verify at submission). Fallback a systems workshop (verify at submission). Referees ask how it differs from in-process budget work (arXiv 2606.04056, abstract read only). |
| 10 | Referee objections | See table below. |
| 11 | Calendar | W8 in the plan. Register W5, freeze W8, preprint W10, submit W12, gate W11. Phase gate P1 exit. Do not submit if the ratio CI includes 1. |

| Objection | Answering evidence | Rebuttal plan |
|---|---|---|
| Overlaps 2606.04056 | Their work is in-process | Read the full text, then state the gateway delta |
| Replay is not live | Live fault-injection result | Report both and the gap |
| Factor 2 is arbitrary | Stated as decision value | Show the full ratio curve |
| Few sessions | Sizing note | Release raw overshoot list |
| Vendor limits differ | Per-vendor table | Scope to tested vendors |

### T5. Telling the agent vs stopping the agent

*Method source. `statistical-analysis` (multi-arm contrasts, Holm), `scientific-critical-thinking` (conflicting prior evidence).*

| # | Field | Plan |
|---|---|---|
| 1 | Claim and null | A visible budget reminder changes spend per task, and a gateway cap changes it more. Null: spend equals the no-intervention arm. Prior work conflicts (C:131 helps, Ramp Labs reports no change). |
| 2 | Pre-registration | H1 reminder vs none, H2 cap vs none. Primary endpoint is log spend per task. Secondary: success rate, turns used. Stopping rule is the fixed task count. Exploratory: budget tightness. Register at W5. Frozen: arms, budget levels, margin, task manifest. |
| 3 | Design and baselines | Three arms, randomised within task, repeats `k = 3`, clustered by repository, isolated cache per arm. Confirmatory runs use automated tasks, not live developers. Baselines are no intervention and a live counter. Ablation varies the reminder wording. Held-out set is a P1 task set drawn from the P0 baseline repositories. The private hard set and the T6 harness do not exist until P2, so T5 does not use them. |
| 4 | Statistics | Unit is the task. Paired log difference. Cluster bootstrap CI. Holm across 2 contrasts. NI on success at 10 pp. Sizing. 10% cost effect needs 145 tasks per contrast (section 3.2). NI needs 221 (section 3.3). Both assumed. |
| 5 | Threats | Internal, reminder text could leak hints; mitigate with a placebo reminder arm if budget allows. External, automated tasks differ from developers. Construct, spend vs cost per success; report both. Statistical, two contrasts; Holm. |
| 6 | Reproducibility | Task manifest and per-run cost public. Code in `services/eval`. Seeds fixed. Rerun cost 3 arms, 221 tasks, k = 3 is 1,989 attempts, about $1,715. Reporting summary as section 4. |
| 7 | Ethics and disclosure | ToS on automated runs (unverified). Public repositories. If live developers join, consent and employer approval first. Conflict as T1. AI-use as section 4. |
| 8 | CRediT roles | Conceptualization, Methodology, Investigation, Software, Formal analysis, Project administration, Writing original draft, Writing review and editing. |
| 9 | Venue fit | Primary NeurIPS main or workshop (verify at submission). Fallback TMLR (verify at submission). Referees ask for arm randomisation and a null-friendly test. |
| 10 | Referee objections | See table below. |
| 11 | Calendar | W8 in the plan. Register W5, freeze W8, preprint W10, submit W12, gate W11. Phase gate P1 exit. Do not submit if both CIs include zero and the paper adds no insight beyond the null. Post as a registered null. |

| Objection | Answering evidence | Rebuttal plan |
|---|---|---|
| Conflicts with C:131 | Shared design, different harness | State the reconciling condition |
| Automated tasks only | Task-level paired design | Add a small developer pilot as exploratory |
| Reminder wording drives result | Wording ablation | Pre-register wording |
| Success may drop under cap | NI test | Report the margin |
| Multiple arms | Holm | Report adjusted p |

### T6. Paired, task-clustered evaluation

*Method source. `statistical-power` (power for paired and clustered designs), `statistical-analysis` (non-inferiority, intersection-union), `peer-review` (claim and evidence fit).*

| # | Field | Plan |
|---|---|---|
| 1 | Claim and null | Without per-arm cache isolation, a no-op change shows a spurious cost difference larger than the isolated-arm CI half-width in at least one A/A run. Null: no spurious difference. |
| 2 | Pre-registration | H1 as stated in row 1. Primary endpoint is the false-positive rate of the cost test over A/A runs. Secondary: bias from shared cache, width of CI with and without clustering. Stopping rule is the fixed number of A/A runs. Exploratory: effect of `k`. Register at W9. Frozen: A/A task set, margin, bootstrap settings, tag. |
| 3 | Design and baselines | Four designs compared on the same data. Unpaired bootstrap, paired without clustering, error-bar method (arXiv 2411.00640), and the proposed design. Ablations toggle cache isolation, clustering and pairing. Held-out set is a pilot-disjoint private set. Contamination control is the canary set (section 1.3). |
| 4 | Statistics | Unit is the task. Rejection rate with exact binomial CI. Zero-failure sizing. To show a false-positive rate below 10% with no rejections needs 29 A/A runs. To show below 5% needs 59. Effect size is bias as share of the true difference. Single primary, no correction. |
| 5 | Threats | Internal, A/A runs may not reveal a leak that needs real change; add a simulated leak. External, one model family. Construct, "cache isolation" implemented per vendor; document. Statistical, rare rejections; use the exact interval. |
| 6 | Reproducibility | `modules/stats` and `services/eval` public, tagged. A/A run logs public. Seeds fixed. Rerun cost 59 A/A runs of 80 tasks, k = 1, 2 arms is 9,440 attempts, about $8,138. Reporting summary as section 4. |
| 7 | Ethics and disclosure | ToS on benchmark publication (unverified). Public task set licences (unverified). Conflict as T1. AI-use as section 4. |
| 8 | CRediT roles | Conceptualization, Methodology, Software, Validation, Formal analysis, Investigation, Visualization, Writing original draft, Writing review and editing, Supervision. |
| 9 | Venue fit | Primary NeurIPS Datasets and Benchmarks (verify at submission). Fallback TMLR (verify at submission). Referees ask for released code, power analysis and a demonstration on real optimisations. |
| 10 | Referee objections | See table below. |
| 11 | Calendar | W10 in the plan. Register W9, freeze W10, preprint W12, submit W14, gate W13. Phase gate P2 harness runs. Do not submit if the A/A false-positive rate is within the nominal 5% without isolation. |

| Objection | Answering evidence | Rebuttal plan |
|---|---|---|
| Error-bar paper covers this | It does not isolate caches | Show the bias with and without isolation |
| Margin is arbitrary | Decision-value rule | Publish margin sensitivity curve |
| Only one model family | Per-family rows | Add a second family if budget allows |
| Lite subset too small | Section 3.4 | State the limit openly |
| Uses vendor baselines | Reproduced in this design | Report both |

### T7. 5 minutes or 1 hour

*Method source. `statistical-power` (assumed-effect power), `scientific-critical-thinking` (counterfactual replay limits).*

| # | Field | Plan |
|---|---|---|
| 1 | Claim and null | A planner that picks the TTL from the measured reuse gap lowers cache cost per 1,000 requests versus a fixed 5-minute TTL. Null: no difference. |
| 2 | Pre-registration | H1 as stated in row 1. Primary endpoint is billed cache cost per 1,000 requests. Secondary: hit rate, share of callers where 1 hour pays. Stopping rule is the P2 pilot window plus a confirmatory window. Exploratory: per-model. Register at W9. Frozen: break-even rule, multipliers, gap data hash. |
| 3 | Design and baselines | Counterfactual replay of recorded reuse gaps under three policies (fixed 5 minutes, fixed 1 hour, planner), then a live confirmation. Break-even rule. The 1-hour TTL pays if `m60 < ((w5 - r)/(w60 - r)) * m5`, which is 0.605 times `m5` with multipliers 1.25, 2 and 0.1 (unverified, illustrative). Held-out set is callers not used to fit the planner. |
| 4 | Statistics | Unit is the caller. Sign-flip randomisation test on paired cost differences. CI by bootstrap over callers. No correction for one primary. Sizing. With n callers the smallest two-sided p is `2/2^n`, so at least 6 callers are needed. Effect size depends on the gap distribution, so the P0 baseline measures it. Not computable now. |
| 5 | Threats | Internal, replay assumes behaviour is unchanged; mitigate with live confirmation. External, few callers. Construct, multipliers come from vendor pages; read before each run. Statistical, small n; exact test. |
| 6 | Reproducibility | Gap distributions public, anonymised. Planner in `features/cache-planner`. Price-book snapshot frozen. Rerun cost about $0 for replay, about $755 for a 146-task live check. Reporting summary as section 4. |
| 7 | Ethics and disclosure | ToS on cache use (unverified). Gap data carries no content. Conflict as T1, since vendors price caches. AI-use as section 4. Do not cite the unconfirmed Anthropic TTL change. |
| 8 | CRediT roles | Conceptualization, Methodology, Formal analysis, Software, Data curation, Writing original draft. |
| 9 | Venue fit | Primary MLSys (verify at submission). Fallback a systems workshop (verify at submission). Referees ask why not use self-hosted cache work and how prices change the result. |
| 10 | Referee objections | See table below. |
| 11 | Calendar | W14 in the plan. Register W9, freeze W13, preprint W16, submit W18, gate W17. Phase gate P2 exit. Do not submit if fewer than 6 callers or if the planner never beats the fixed policy. |

| Objection | Answering evidence | Rebuttal plan |
|---|---|---|
| Prices change | Break-even stated as a function | Publish the rule, not one number |
| Few callers | Exact test | State the minimum n |
| LiteLLM warm rate is vendor data | The project's own gaps | Cite as vendor report only |
| Replay is not live | Live check | Report the gap |
| Closest work covers self-hosted caches | Different setting | Cite and delimit |

### T8. Router vs best single model

*Method source. `statistical-power` (NI sample size), `statistical-analysis` (Holm across arms).*

| # | Field | Plan |
|---|---|---|
| 1 | Claim and null | After overhead, judge cost and cache loss, at least one router lowers CPS versus the best single model with its own cache, with success within 10 pp. Null: every router has CPS at or above best-single. |
| 2 | Pre-registration | H1 per router. Primary endpoint is CPS ratio and the NI test on success. Secondary: overhead share, cache loss. Stopping rule is the fixed task count. Exploratory: per-task-type. Register at W9. Frozen: best-single choice (from the pilot split), router configs, margin, tag. |
| 3 | Design and baselines | Five arms. Best single, rules router, atomic classifier, static router, cascade. Paired, clustered, isolated cache. Baselines from A:006, A:046, C:030. Ablation removes overhead accounting. Held-out is the confirmatory private set. |
| 4 | Statistics | Unit is the task. Paired log CPS. Cluster bootstrap. Holm across 4 routers. Intersection-union with NI. Sizing. 221 tasks for NI at 10 pp, `pD` 0.2. 145 for a 10% cost cut. Assumed. |
| 5 | Threats | Internal, router trained on pilot leaks; split strictly. External, vendor price changes. Construct, "best single" depends on set; fix it on the pilot. Statistical, four contrasts; Holm. |
| 6 | Reproducibility | Router configs and run logs public. Seeds fixed. Rerun cost 5 arms, 221 tasks, k = 3 is 3,315 attempts, about $2,858. Reporting summary as section 4. |
| 7 | Ethics and disclosure | ToS of each routed vendor (unverified). Public repositories. Conflict as T1. AI-use as section 4. |
| 8 | CRediT roles | Conceptualization, Methodology, Software, Investigation, Formal analysis, Validation, Writing original draft, Writing review and editing. |
| 9 | Venue fit | Primary NeurIPS Datasets and Benchmarks (verify at submission). Fallback EMNLP industry track (verify at submission). Referees ask for overhead accounting and a fair single-model baseline. |
| 10 | Referee objections | See table below. |
| 11 | Calendar | W14 in the plan. Register W9, freeze W14, preprint W16, submit W18, gate W17. Phase gate P2 exit, router beats best single or stays off. Do not submit as a win if no router passes. Post as a registered null. |

| Objection | Answering evidence | Rebuttal plan |
|---|---|---|
| Best single was cherry-picked | Chosen on pilot split | Show all single models |
| Prior routers (C:032, 2607.00053) | Billed dollars, real harness | Read 2607.00053 in full |
| Cache loss ignored | Explicit term | Report cache loss separately |
| Few tasks | Section 3.3 | State margin limits |
| Vendor-reported posts | Not used as evidence | Cite as context |

### T9. Same compressor, different harness

*Method source. `statistical-power` (interaction tests), `peer-review` (replication framing).*

| # | Field | Plan |
|---|---|---|
| 1 | Claim and null | One output compressor shifts billed cost in opposite directions on two harnesses. Null: the log effect has the same sign and size on all harnesses. |
| 2 | Pre-registration | H1 is the harness by compressor interaction. Primary endpoint is the interaction on log cost. Secondary: extra turns, cache-prefix breakage. Stopping rule is the fixed task count. Exploratory: other compressors. Register at W9. Frozen: compressor version, harness versions, mechanism metrics. |
| 3 | Design and baselines | Same model, 3 or more harnesses, 2 arms, paired, clustered, isolated cache. Baselines are the vendor-reported figures (PointFive +48.4% and -12.49%, Quesma -5% and +5%; unverified). Held-out is the confirmatory set. |
| 4 | Statistics | Unit is the task. Interaction on the log scale. Cluster bootstrap. Holm over mechanism metrics. Sizing. At interaction 0.20 about 39 independent tasks per harness, 20 if paired. At 0.528 (the PointFive gap) 6 and 3. At 0.10 it is 153 and 77. Assumed. |
| 5 | Threats | Internal, harness versions drift; pin them. External, one compressor. Construct, "opposite sign" may reflect noise; use the CI. Statistical, small samples; report intervals. |
| 6 | Reproducibility | Run logs and configs public. Seeds fixed. Rerun cost 3 harnesses, 2 arms, 39 tasks, k = 3 is 702 attempts, about $605. Reporting summary as section 4. |
| 7 | Ethics and disclosure | ToS of the three harness vendors (unverified). Tell the compressor's maker before posting a negative result. Conflict as T1. AI-use as section 4. |
| 8 | CRediT roles | Methodology, Investigation, Formal analysis, Validation, Writing original draft, Writing review and editing. |
| 9 | Venue fit | Primary a replication workshop or ReScience-style venue (verify at submission). Fallback an MSR short paper (verify at submission). Referees ask what is new beyond vendor reports. |
| 10 | Referee objections | See table below. |
| 11 | Calendar | W14 in the plan. Register W9, freeze W14, preprint W16, submit W18, gate W17. Phase gate P2 exit. Do not submit if the replication shows the same sign everywhere. A null replication still goes on a preprint. |

| Objection | Answering evidence | Rebuttal plan |
|---|---|---|
| Already known | R7 marks it mostly covered | Frame as replication with mechanism |
| Vendor-affiliated sources | Independent run | Report the new numbers beside theirs |
| One compressor | Registered scope | State limit |
| Noise explains sign flip | Interval on interaction | Show per-run spread |
| Harness versions | Pins | Re-run on the next version |

### T10. When does another attempt stop paying

*Method source. `statistical-power` (precision for a knee estimate), `scientific-critical-thinking` (independence of attempts).*

| # | Field | Plan |
|---|---|---|
| 1 | Claim and null | A dollar-denominated stopping rule lowers CPS versus the fixed step cap at P75 of baseline, with success within 10 pp. Null: no CPS difference. |
| 2 | Pre-registration | H1 as stated in row 1. Primary endpoint is CPS ratio, rule vs cap. Secondary: location of the knee in attempts, stopped-run share. Stopping rule is up to 5 attempts per task. Exploratory: per-task difficulty. Register at W12. Frozen: rule form, task value parameter, margin. |
| 3 | Design and baselines | Log up to 5 attempts per task once, then evaluate stopping policies by replay. Baselines are turn cap at P75, loop guard, no cap. Ablation varies the value parameter. Held-out set is the confirmatory set. Prior knee at 3 to 4 repair rounds (arXiv 2607.05197, repair only). |
| 4 | Statistics | Unit is the task. Paired log CPS. Cluster bootstrap. Holm across 2 baselines. Sizing. 145 tasks for a 10% cost cut. Carryover bias of 10% needs 69 tasks. Replay needs attempts to be independent, which the carryover check tests. |
| 5 | Threats | Internal, attempts share context; check carryover. External, one model. Construct, task value is assumed; vary it. Statistical, knee estimates are noisy; bootstrap. |
| 6 | Reproducibility | Attempt logs public. Rules in `features/turn-cap` and `features/loop-guard`. Seeds fixed. Rerun cost 145 tasks, 5 attempts is 725 attempts, about $625. Reporting summary as section 4. |
| 7 | Ethics and disclosure | ToS on repeated automated runs (unverified). Conflict as T1. AI-use as section 4. |
| 8 | CRediT roles | Conceptualization, Methodology, Formal analysis, Software, Investigation, Writing original draft, Writing review and editing. |
| 9 | Venue fit | Primary ICML or NeurIPS main (verify at submission). Fallback TMLR (verify at submission). Referees ask for generality across models and tasks. |
| 10 | Referee objections | See table below. |
| 11 | Calendar | W16 in the plan. Register W12, freeze W16, preprint W18, submit W20, gate W19. Phase gate P3 week 2. Do not submit if the knee CI spans 1 to 5 attempts. |

| Objection | Answering evidence | Rebuttal plan |
|---|---|---|
| Repair-only knee exists | Full sessions here | State the scope |
| Attempts are not independent | Carryover test | Report bias bound |
| Task value is arbitrary | Sensitivity curve | Publish all values |
| One model | Scope limit | Add a second model if funded |
| Replay is not live | Live check on 50 tasks | Report gap |

### T11. Strong-model share ceilings

*Method source. `scientific-critical-thinking` (deductive vs empirical claims), `statistical-power` (zero-failure bound).*

| # | Field | Plan |
|---|---|---|
| 1 | Claim and null | With a strong-share ceiling `s` and price ratio `rho`, cost per request cannot exceed `s*rho + (1-s)` in weak-price units, and success on benign traffic stays within 10 pp. Null: a request exceeds the bound or success drops more. |
| 2 | Pre-registration | H1 bound conformance. H2 benign success NI. Primary endpoint is the count of bound violations (expected 0). Secondary: success loss. Stopping rule is the fixed attack set. Exploratory: attack types. Register at W14. Frozen: `s`, `rho`, attack prompts, margin. |
| 3 | Design and baselines | Adversarial set of route-to-strong prompts (A:010, arXiv 2604.15022), benign set from T8. Baselines are no ceiling and detection-based defences (arXiv 2601.21380). Held-out set is attacks written after the ceiling is built. |
| 4 | Statistics | Unit is the request. Exact binomial bound. To bound the violation rate below 1% with none seen needs 299 requests. Below 0.1% needs 2,995. Benign NI as T8. The bound holds by construction, so H1 tests the code and not the idea. |
| 5 | Threats | Internal, ceiling bug; mitigate by property tests. External, the attack set is self-written. Construct, the cost bound is tautological; state it. Statistical, zero events; use the bound. |
| 6 | Reproducibility | Attack set and ceiling code public. Seeds fixed. Rerun cost 299 attacks plus 221 benign tasks in 2 arms (k = 3), 1,625 attempts, about $1,400. Reporting summary as section 4. |
| 7 | Ethics and disclosure | Attack prompts target routers; disclose any live-router weakness to the vendor first. ToS on adversarial testing (unverified). Conflict as T1. AI-use as section 4. |
| 8 | CRediT roles | Conceptualization, Methodology, Software, Validation, Investigation, Writing original draft. |
| 9 | Venue fit | Primary a security workshop (verify at submission). Fallback fold into T8. Referees ask what is new if the bound holds by design. |
| 10 | Referee objections | See table below. |
| 11 | Calendar | W18 in the plan. Register W14, freeze W17, preprint W20, submit W22, gate W21. Phase gate P3 week 4. Default decision is to fold into T8 unless the benign-success cost is new. |

| Objection | Answering evidence | Rebuttal plan |
|---|---|---|
| Trivial by construction | Admitted in the text | Focus on benign success cost |
| Attacks are weak | Published attack sets | Add adaptive attacks |
| Ceiling hurts quality | NI test | Report margin |
| Price ratio varies | Bound as function | Publish formula |
| Not a detection method | Out of scope | Cite detection work |

### T12. Two vantage points for waste detection

*Method source. `peer-review` (annotation and agreement), `statistical-analysis` (McNemar, Benjamini-Hochberg).*

| # | Field | Plan |
|---|---|---|
| 1 | Claim and null | At least one waste pattern class is detectable only at the gateway and at least one only in transcripts. Null: the two vantage points detect the same classes with equal recall. |
| 2 | Pre-registration | H1 as stated in row 1. Primary endpoint is per-pattern recall difference, gateway vs transcript, against human labels. Secondary: precision, kappa. Stopping rule is the labelled sample. Exploratory: pattern clusters. Register at W12. Frozen: the pattern list from the 50 detectors, labelling guide, kappa threshold. |
| 3 | Design and baselines | Gateway rows joined to transcripts on session and prompt id. Two annotators label a sample. Baselines are trajectory-only detectors (arXiv 2605.29893). Held-out is sessions not used to tune detectors. |
| 4 | Statistics | Unit is the session. McNemar per pattern. Benjamini-Hochberg over the 50 rows. Sizing. For a 20 pp recall gap with discordance 0.3, two-sided 0.05, 80% power, 59 reference-positive events per pattern. Rare patterns may fall short and are reported descriptively. |
| 5 | Threats | Internal, annotator bias; mask the vantage. External, one team's traffic. Construct, "waste" definitions; reuse the detector spec. Statistical, many patterns; BH. |
| 6 | Reproducibility | Label set and guide public after redaction. Detectors in `services/insight`. Seeds fixed. Rerun cost about $0 (replay). Annotation hours instead. Reporting summary as section 4. |
| 7 | Ethics and disclosure | Transcripts hold prompts and code. Redact before release (`modules/redaction`). Tenant-data check. ToS on transcript use (unverified). Conflict as T1. AI-use as section 4. |
| 8 | CRediT roles | Conceptualization, Methodology, Investigation, Data curation, Formal analysis, Validation, Writing original draft. |
| 9 | Venue fit | Primary ICSE or FSE tools track (verify at submission). Fallback MSR (verify at submission). Referees ask for labelling quality and tool release. |
| 10 | Referee objections | See table below. |
| 11 | Calendar | W18 in the plan. Register W12, freeze W18, preprint W20, submit W22, gate W21. Phase gate P3 exit. Do not submit if kappa is under 0.7 after adjudication. |

| Objection | Answering evidence | Rebuttal plan |
|---|---|---|
| Labels are subjective | Kappa and adjudication | Release the guide |
| Prior work uses trajectories | Gateway comparison is new | Cite and delimit |
| Privacy | Redaction pipeline | Release aggregates if needed |
| One system | Scope limit | State it |
| Many patterns, few events | BH and descriptive tier | Pre-state the rule |

### T13. Price books go stale

*Method source. `statistical-power` (zero-miss bound), `scientific-critical-thinking` (simulation as evidence).*

| # | Field | Plan |
|---|---|---|
| 1 | Claim and null | After a vendor price change, tracked cost drifts more than 1% from the invoice within 7 days without a canary, and a weekly canary catches it. The 1% is the P0 gate. Null: drift stays within 1%. |
| 2 | Pre-registration | H1 as stated in row 1. Primary endpoint is days to detection and drift at detection. Secondary: false alarms. Stopping rule is the P3 canary history. Exploratory: per-vendor. Register at W12. Frozen: drift definition, injection protocol. Default plan is to fold into T2 at W10 if fewer than 5 real price changes occurred. |
| 3 | Design and baselines | Real canary history plus synthetic price-change injections. Baselines are no canary and monthly check. Held-out is the real events. |
| 4 | Statistics | Unit is the price-change event. Exact binomial CI. To show a miss rate below 10% with no misses needs 29 events. Real events are unlikely to reach that, so injected events carry the number. Not computable until the P0 price-row log counts real changes. |
| 5 | Threats | Internal, the injections are self-written; label them. External, few vendors. Construct, drift vs invoice rounding; report both. Statistical, few events; exact interval. |
| 6 | Reproducibility | Price-row log and canary code public (`modules/pricebook-core`, `services/reconciler`). Seeds for injection fixed. Rerun cost about $0. Reporting summary as section 4. |
| 7 | Ethics and disclosure | ToS on scraping price pages (unverified). Invoices are private; publish ratios. Conflict as T1. AI-use as section 4. |
| 8 | CRediT roles | Conceptualization, Methodology, Software, Data curation, Writing original draft. |
| 9 | Venue fit | Primary a section of T2 (verify venue at submission). Fallback a workshop (verify at submission). Referees ask for real-world events. |
| 10 | Referee objections | See table below. |
| 11 | Calendar | W18 in the plan. Fold decision W10. Otherwise register W12, freeze W18, preprint W20, submit W22, gate W21. Phase gate P3 exit. Do not submit standalone if real events are under 5. |

| Objection | Answering evidence | Rebuttal plan |
|---|---|---|
| Too few events | Injections | Label as simulation |
| Thin novelty | R7 finds vendor docs only | Fold into T2 |
| Invoices private | Ratios only | Aggregate |
| One canary design | Two baselines | State scope |
| Price pages change format | Parser tests | Report parse failures |

### T14. System paper

*Method source. `peer-review` (claim and evidence fit), `scholar-evaluation` (qualitative review of the whole).*

| # | Field | Plan |
|---|---|---|
| 1 | Claim and null | The composed Token Economics system lowers CPS versus the same harness without Token Economics on a frozen task set, with success within 10 pp. Null: no difference. |
| 2 | Pre-registration | H1 as stated in row 1. Primary endpoint is CPS ratio with NI on success. Secondary: latency overhead against the P0 budget, rollback drill result. Stopping rule is the fixed task count. Exploratory: per-harness. Register at W15. Frozen: system release tag, task set, margin. |
| 3 | Design and baselines | Two arms, composed system vs harness alone, paired, clustered, isolated cache. Baselines include gateway products (agentgateway, Portkey; vendor claims). Ablation drops one feature flag at a time, limited to the 3 largest. Held-out is the private set. |
| 4 | Statistics | Unit is the task. Paired log CPS. Cluster bootstrap. Intersection-union across the two endpoints, so both must pass; no Holm needed. Sizing. 221 tasks for the NI test at 10 pp, 145 for a 10% cut. Assumed. |
| 5 | Threats | Internal, features tuned on the same set; split strictly. External, one team. Construct, "system" bundles many parts; list flags. Statistical, many ablations; limit them. |
| 6 | Reproducibility | Release 1.0 tag, configs, run logs. Seeds fixed. Rerun cost 2 arms, 221 tasks, k = 3, about $1,143 plus ablations. Reporting summary as section 4. |
| 7 | Ethics and disclosure | Provider ToS (unverified). Security review closed at P3. Conflict as T1, strongest here, because it describes the product. AI-use as section 4. Responsible disclosure for any vendor bypass found. |
| 8 | CRediT roles | Conceptualization, Software, Resources, Investigation, Validation, Project administration, Funding acquisition, Supervision, Writing original draft, Writing review and editing. |
| 9 | Venue fit | Primary EuroSys or USENIX ATC (verify at submission). OSDI only if the evidence is much larger. Fallback MLSys (verify at submission). Referees ask for end-to-end evidence and honest limits. |
| 10 | Referee objections | See table below. |
| 11 | Calendar | About W22 in the plan, an estimate. Register W15, freeze W22, preprint W24, submit W26, gate W25. Phase gate Release 1.0 after P3 exit. Do not submit if the composed A/B fails NI or shows no cost gain. Publish the preprint as a report. |

| Objection | Answering evidence | Rebuttal plan |
|---|---|---|
| No academic novelty | Composition and gates | Cite T1, T3, T4, T6, T8 |
| Only one team | Scope | State it |
| Product paper | Registered A/B | Keep claims to the test |
| Gateway products exist | Comparison table | Mark vendor claims |
| Overhead | Latency report | Show P95 overhead |

## 6. Pre-submission gate checklist

*Method source. `peer-review` (reporting checks), `scientific-writing` (declarations and authorship accountability).*

A paper submits only if every row passes. The owner role signs. A second person checks, per the `PHASES.md` rule that a person other than the builder verifies.

| # | Gate | Pass when | Evidence |
|---|---|---|---|
| 1 | Registered | OSF record dated before confirmatory data | Registration id, hash list |
| 2 | Frozen artifacts | Task manifest, analysis tag, price-book snapshot, model ids recorded | Hash file in `papers/<id>/` |
| 3 | Endpoints intact | Every registered endpoint is reported, including failures | Endpoint table |
| 4 | Dry run | A no-op change reports no difference | Dry-run log |
| 5 | Reproduction | Folder runs from a clean checkout | CI run id |
| 6 | Numbers traced | Each number has a script that regenerates it | Script list |
| 7 | Tenant-data check | No prompts or tenant ids in released data | Storage scan report |
| 8 | Prior-art refresh | Novelty check re-run at draft start and at submission | Dated note |
| 9 | Overlap scan | Sibling-paper overlap disclosed and similarity checked | Overlap table |
| 10 | Statistics review | Independent person reruns the analysis | Review note |
| 11 | Declarations | Conflicts, funding, AI use, data and code statements, CRediT | Declarations page |
| 12 | Venue rules | Page limits, policy on preprints and AI use checked | Dated policy record (verify at submission) |
| 13 | Go/no-go | The paper's decision rule in section 5 row 11 is met | Signed gate note |
| 14 | Independent review | A reader outside the authors scores the draft against the referee table | Review notes |

## 7. Gaps and unknowns

*Method source. `scientific-critical-thinking` (stating limits), `scientific-writing` (never guess an absent policy).*

Every item below is unverified. None is a result.

| Area | Gap | Where it enters | How it closes |
|---|---|---|---|
| Venues | Every venue name, track and policy | Rows 9 of all papers | Check the venue page at submission |
| Nature Portfolio | Reporting-summary fields and policies | Section 4, row 6 | Read the current form at submission |
| Registration | OSF specifics and the equivalent | Row 2 | Check the registry at W1 |
| Cache prices | Multipliers 1.25, 2 and 0.1 | T7 | Read the vendor price page before each run |
| Vendor data | LiteLLM 97.4% and 99.3% warm rates | T7 | Replace with measured gap data |
| Vendor data | PointFive +48.4%, -12.49%; Quesma -5%, +5% | T9 | Own replication run |
| Cost scale | $0.86 per attempt (Quesma scale) | Section 3.6, all reruns | P0 baseline mean |
| Variance inputs | `tau`, ICC 0.10, `pD`, attrition | Section 3 | P0 baseline, P2 pilot |
| Thresholds | Kappa 0.7, 2% attribution tolerance, factor 2 in T4 | T2, T4, T12 | Set at registration, justify |
| Schema | OpenTelemetry GenAI attributes not read | T2 | Read before writing |
| Vendors | The five-vendor list for T2 | T2 | Fix selection rule at W1 |
| Prior work | Full texts of 2607.12161, 2608.01347, 2607.00053, 2605.18859, 2606.04056 | T1, T4, T8 | Read before positioning |
| Prior work | C:043 is a title only | T1, T10 | Obtain the full text |
| Claims | Anthropic TTL change in 2026 | T7 | Do not cite until an official page confirms |
| Scale | Caller and repository counts in P0 | T3, T7 | P0 baseline report |
| Task set | Private hard set not yet built | All P2 papers | P2 task 1 |
| Calendar | T14 at W22 is an estimate; P0 start date not set | Section 8 | Set the date at P0 start |
| Licences | Public task and repository licences | T3, T6 | Check each licence |
| Terms of service | Provider terms on benchmarking and publication | Row 7 of all papers | Read each provider's terms |

## 8. Calendar and decision gates

*Method source. `scientific-writing` (timeline and gate records), anchored on `PHASES.md` and `14-research-papers.md`.*

W0 is the start of P0. P0 is W1 to W4, P1 W5 to W8, P2 W9 to W14, P3 W15 to W18. Durations are estimates from `PHASES.md`.

| Paper | Plan week | Register | Freeze | Preprint | Submit | No-go gate | Phase gate |
|---|---|---|---|---|---|---|---|
| T1 | W4 | W1 | W4 | W6 | W8 | W7 | P0 exit |
| T2 | W4 | W1 | W4 | W6 | W8 | W7 | P0 exit |
| T3 | W6 | W2 | W5 | W8 | W10 | W9 | P0 data, written in P1 |
| T4 | W8 | W5 | W8 | W10 | W12 | W11 | P1 exit |
| T5 | W8 | W5 | W8 | W10 | W12 | W11 | P1 exit |
| T6 | W10 | W9 | W10 | W12 | W14 | W13 | P2 harness runs |
| T7 | W14 | W9 | W13 | W16 | W18 | W17 | P2 exit |
| T8 | W14 | W9 | W14 | W16 | W18 | W17 | P2 exit |
| T9 | W14 | W9 | W14 | W16 | W18 | W17 | P2 exit |
| T10 | W16 | W12 | W16 | W18 | W20 | W19 | P3 week 2 |
| T11 | W18 | W14 | W17 | W20 | W22 | W21 | P3 week 4 |
| T12 | W18 | W12 | W18 | W20 | W22 | W21 | P3 exit |
| T13 | W18 | W12 | W18 | W20 | W22 | W21 | P3 exit |
| T14 | W22 | W15 | W22 | W24 | W26 | W25 | Release 1.0 |

**Preprint slips two weeks past the plan week.** The plan week is when the gate produces the data. Writing needs time after the freeze. For T1 and T2 a W4 preprint is not reachable, because the 30-day baseline closes at W4.

**A paper never blocks a phase gate.** If data is late, the paper slips and the phase does not.

**Decision gate rule.** At the no-go gate, the author compares the registered result with the decision rule in row 11. Three outcomes follow.

| Result | Action |
|---|---|
| Passes the rule | Submit at the date shown |
| Null or weak | Post the preprint, skip or delay the journal, fold into T14 |
| Gate item fails (section 6) | Hold until fixed. Slip the paper. |

## 9. Next actions

1. At W1, register T1 and T2 on OSF (or an equivalent, verify).
2. Write the margin rule and the `tau` pilot plan into `services/eval` before P2.
3. Read the five arXiv full texts listed in section 7.
4. Read the OpenTelemetry GenAI attributes before T2 is drafted.
5. Decide the T13 fold into T2 at W10.

## 10. Limits of this plan

- No pilot data exists. Every sample size is a function of assumed inputs.
- No venue policy was checked against a primary source.
- Costs use one vendor-affiliated per-attempt figure.
- The plan was written without a statistics package beyond scipy and numpy.
