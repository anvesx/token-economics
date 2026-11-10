# R6: Measurement, evaluation, quality guardrails, variance, multi-agent cost

Ids: A### = `research/` (API corpus), C### = `research-cli-agents/`. Ids collide across folders, so the prefix matters. Tags: [measured] = run by the authors or a third party; [self] = vendor or author claim about their own product. "Not in corpus" = absent from notes and corpus text.

## 1. Facts to build on

**Cost per successful task is the right unit**
- Cost-of-pass = cost per attempt / P(correct), with a human-expert baseline; MATH-500 frontier cost-of-pass halved about every 2.6 months; majority voting (k=3,4) gave 0% economic benefit [A122, self].
- Sticker price misleads: 106 of 336 comparisons (32%) reversed the price ranking, up to 28x; Gemini 3 Flash listed $3.50 vs GPT-5.4 $17.50, yet total $705 vs $509. 8 models, 6,877 tasks [A069, measured].
- BrowseComp: GPT-5.5 84.36% at $33.27 vs GPT-5.6 Luna 84.04% at $1.33 [A207, self].
- Aider polyglot (225 exercises): gpt-5 high 88.0% at $29.08; o3-pro 84.9% at $146.32; DeepSeek-V3.2 Reasoner 74.2% at $1.30 [C038, measured]. Per-solved: GPT-5 high $0.147, Gemini 2.5 Pro $0.039 [C129, blog estimate].
- Harness effect: up to 24.3 points Pass@1 with the model fixed; an 80-task Lite subset matched the full 350 (0.6607 vs 0.6610; mean abs diff 0.81 pp, held-out max 1.70 pp) at 25.3% of the cost, 3 runs per cell [A060, measured].
- Task-level routing, 21 tasks, one repo, LLM judge: $138.84 vs $251.04 (-44.7%) for -4.8% quality [A051, self].

**Variance and prediction**
- OpenHands, SWE-bench Verified, 8 models x 500 tasks x 4 runs: same-task runs differ up to 30x; agentic average 4.17M tokens and $1.857 per task; input/output 153.85 [C023, measured]. Human difficulty labels vs cost: Kendall tau 0.32. Self-prediction Pearson r max 0.39, underestimating; prediction overhead from <6% to >2x task cost.
- Same-query repeated cost spans up to 9.7x, CV often above 0.3 [A069].
- Kimi K3, 5 tasks, 2,700 runs: geometric SD x1.34 (x1.29-x1.40). Median prediction error 161% with no probe, 36% with one probe ($0.11), 29% with three, 25% with ten. A 1.9x multiplier covers 90% of runs. Per-run r 0.08 without a probe, 0.72 with one [C027, self].
- Failed runs: 17% of tasks, 32% of spend; 51% of spend falls after the first repeated-failure signature. 23 tool schemas shown, 16 never called, 3 account for 98% of calls. 277 tasks, 3 seeds, cost -18.4% to -30.9% with overhead charged to the task [C028, self].
- Two retries can triple cost [C129].

**Multi-agent cost**
- "About 7x tokens" for agent teams in plan mode is repeated in C001 and C010, citing Anthropic docs. The actual docs page says only "significantly more tokens" and gives no multiple [C081]. So the 7x is quoted, not measured. [C062] says 3-5x (blog, no method).
- A blind swarm scored 3 vs 8 for a cost-aware one; budget increases gave nothing past the capability wall [C132]. Subagents do not share the parent's cache; default TTL 5 minutes [C052, C081].
- Voting: 0% benefit [A122]; Self-MoA beats mixed MoA by 6.6 points with fewer passes [A032]; A033 (More Agents) has an abstract only, no numbers.
- Compute-optimal test-time allocation matches best-of-N with 2-4x less compute [A094].

**Observability data quality**
- Claude Code OTel and Agent SDK costs are client-side estimates, not bills. SDK pitfalls: double counting, placeholder output tokens, subagent exclusion, resumed sessions [C002, A216].
- Token buckets differ: OpenAI `prompt_tokens` includes cache; Anthropic `input_tokens` excludes it, so naive addition double-counts [A233, A232]. A "0 cents" budget row means price unknown and not counted [A242]. Gateway budgets are soft caps that can overshoot [A234].
- Account-level cache hit 77% hid cron runs near 0% [C052]. Gateway: Claude Code 92% hit, $0.050/call; Kilo 46%; monthly P95 $291 vs median $23; error rates 0.9-11% [C054, vendor, selection-biased].
- A cache miss is defined as >5% and >=2,000 tokens reprocessed [C076]; OpenAI returns a miss reason at no fee [A204].
- Forecasting: 80% of firms miss AI infra forecasts by >25%, about 25% by >50%, 15% within 10% [A180, second-hand vendor survey]. 96% saw higher-than-expected costs.
- Vercel failover rescued 3.5% of requests carrying 4.9% of spend [A246, self].
- Spike or anomaly detection: not in corpus beyond budget alerts at 75/90/100% [A213, C116].

**Quality regressions from cost cuts**
- Turn cap at P75 with a remaining-turns reminder, 100 SWE-bench Verified tasks, caching off: Sonnet 75% to 71% solve, -23.62% cost; Gemini 63% to 65%, -68.28%; GPT-4.1 62% to 57%, -38.43%. At P25 Gemini fell to 26% (63 empty patches); Sonnet without reminder 24% [C025, measured].
- Compression: RTK-ML cut tool-output tokens 38.4% but cost +6.8%; Headroom +48.4%; token-cut to cost r=0.154; harness base is 74.7% of cost, tool outputs 3.3%; ~38-45 effective tasks per arm; cache carryover between arms is a validity threat (median gap 10.8s inside the 5-minute TTL). Single-shot Go compression: patch apply 27/40 to 15/40. Pytest rule: 31.9% savings at 56.1% recall fixed to 15.3% at 99.2% recall [C024, vendor]. Headroom +48% on Claude Code but -12.49% on Codex.
- Visible budget: budget 10 got 12.8% vs ReAct at 100 at 12.6%, -31.3% cost [C131]. Counter-case: GPT-5.4 never referenced the budget in 14,000+ messages, called request_more_budget 0 times in 5,000+ turns, 97% approval by default; a separate controller was 49-67% accurate [C136].
- Prompt waste: effort control saved 19% under one harness and 75% under another; "multiple approaches" cost 2.4-7.4x reasoning tokens with no success gain; stop-early framing caused 3/5 hidden-test failures; 4,644 runs, preregistered, paired, task-clustered bootstrap. An adaptive controller with a success non-inferiority floor is proposed, not evaluated [C026].
- Inefficient behaviours occur in 79-98% of tasks, costing 6.86-22.75%; rules cut cost 7.88-41.73% in 6/8 settings, one -1.50 pp Pass@1 [C059].
- maxOutputTokens=300 broke 7 of 25 hard tasks; a regex classifier fell from 93.8% (16 dev tasks) to 70.6% (34 held-out) [A052]. "Be concise" cost GPT-3.5 27.69% accuracy [A104].
- Condensers: masking halves cost at equal solve rate [C130]; LLM condensers +24-94% cost, no significant quality difference, negative at 7 or fewer events [C133]; condensation 54% vs 53% solve [C122]; compaction removed 600-900 tokens and missed the next cache [A224].
- Routers: top routers +4% accuracy, up to 31.7% cost cut, most tie [A006]; GPT-5 74.0% at $14.02 vs MIRT-BERT 66.9% at $0.15 [A046]; cascade degrades when judge error >0.2 [A002]; majority baseline 94.2% exposed memorisation [A019]; near random until ~1,500 gold samples [A001]. TwinRouterBench: router 75/100 at $25.66 vs Opus 74/100 at $54.73 (-53.1%), with a $0.60 penalty per unresolved instance [C030].

**Rollout evidence**
- Perplexity: ~4x cost cut ($0.62M/yr), no statistically significant difference in a 2-week A/B; no n or metric given, 2023 [A272, self].
- Shadow evals on mirrored traffic, blue/green keyed to CPS and valid@1 non-regression, auto-rollback on schema validity -2 pp, ExecRate -3 pp or p95 +20%, per-tenant kill-switches: survey with placeholder values [C063]. Portkey lists canary and A/B only as nav labels [A241, A243].
- Defect burden, one developer, 2x28 days: fix-commit ratio 45.93% vs 74.93% (local GLM); API misuse 2.7% vs 10.5%; debugging-spiral share 35.0% vs 69.8%; 15 min labor per fix [C053].
- Sourcegraph bills only on merged changesets [C069].

## 2. Metrics and unit of analysis

**Unit.** One attempt = (task, arm, seed), compared by task with repeats, clustered by task and repo. Not the token or call. Class tasks by observed behaviour, not human labels (tau 0.32) [C023].

| Metric | Formula / note |
|---|---|
| Billed cost per attempt | uncached + cache write + cache read + output, separate buckets [A233] |
| Cost per successful task (CPS) | sum of cost over all attempts incl. failed / successes [A122, C026] |
| Reconciliation ratio | client estimate / invoice, monthly [A216]; tolerance not in corpus |
| Failed-run waste share | failed spend / total (baseline 32%) [C028] |
| Spend after first repeated failure | share of total (baseline 51%) [C028] |
| Cost dispersion | geometric SD per (task, arm) (baseline x1.34) [C027] |
| Probe error | abs(pred - actual) / actual (36% with one probe) [C027] |
| Cache hit per caller | cache_read / (read + write + uncached input) [C052] |
| Cache-miss events | >5% and >=2,000 tokens reprocessed [C076] |
| Fixed-prefix tokens, turns, tool calls by type | harness base is 74.7% of cost [C024] |
| Quality floor set | pass rate, patch-apply, empty-patch, format validity, fix-commit ratio [C025, C024, C053] |
| Paired CPS ratio | CPS(arm)/CPS(baseline) with task-clustered bootstrap CI [C026] |
| Spend concentration | median and P95 per developer [C054] |
| Multi-agent multiplier | tokens(team) / tokens(single, matched task); not in corpus, system must measure |

Log with every attempt: prompt variant, effort, harness version, tool surface, retries, compaction, and whether the optimisation fired.

## 3. Eval and A/B design

**Common design.** Paired by task, several repeats, preregistered, success non-inferiority bound set before the test, charge the optimisation's own overhead to the task [C026, C028, C024]. Baseline arm on the same tasks with separate cache namespaces or spacing, since carryover is a validity threat [C024].

**Private eval set.** Our own repos and tasks, with hard cases (public sets saturate: baseline 96-98% in C024). Keep a Lite subset: 80 tasks tracked 350 within 0.81 pp at 25.3% of cost [A060]. Hold out tasks from tuning (regex router: -23.2 pts held out [A052]). Whether public scores predict our tasks: not in corpus.

**Sample sizes from corpus studies:** 100 tasks [C025]; ~38-45 effective tasks per arm [C024]; 60 tasks over 6 repos [C028]; 5 tasks x many repeats [C027]. Derived, not in corpus: with log-SD ln(1.34)=0.29, detecting a 10% paired cost difference needs far fewer runs than unpaired; fit the SD on our own pilot. Formal power formulas, minimum test duration: not in corpus (Perplexity ran 2 weeks [A272]).

| Optimisation | Primary and guard metrics | Notes |
|---|---|---|
| Cache / TTL | per-caller hit rate, cost per call, miss reasons | Judge per caller, not account [C052] |
| Turn and budget caps | CPS, solve, empty-patch rate | Start at P75 of own per-model baseline with a remaining-turns reminder; reject P25 [C025] |
| Output compression | end-to-end CPS, patch-apply, traceback integrity | Never adopt on token savings [C024] |
| Masking / condensing | CPS, solve | Only long runs; negative at 7 or fewer events [C133] |
| Tool pruning | CPS, tool-selection accuracy | -13.2%, -17.7% [C028]; re-audit with full catalog |
| Routing / cascade | CPS, success, router latency, cache loss | Must beat best single after overhead [A006]; charge failed trajectories [C030] |
| Effort / thinking | CPS, success, reasoning tokens | Gains depend on harness [C026] |
| Subagents / teams | token multiplier, CPS vs single agent | No measured multiplier in corpus [C081] |
| Voting / ensembles | CPS | Only with measured gain [A122, A032] |
| Probe budgeting | prediction error, overrun rate | One probe plus 1.9x [C027] |

Stop rules: success drop beyond the preset bound, or CPS above baseline CI. The size of an acceptable margin is not in corpus (C025 accepted about -4 points for -23.6% cost; that is a business call).

## 4. Guardrails

- **Quality floor.** A non-inferiority bound on success per optimisation, plus secondary checks (patch-apply, empty patch, format validity, fix-commit ratio) [C024, C025, C053].
- **Hard cap outside the agent.** Gateway or harness limits, not agent-honoured budgets [C136]; gateway soft caps overshoot [A234]. Keep reminders when capping turns [C025]. Early stopping needs an escalation path [C026].
- **Shadow.** Mirrored-traffic shadow runs with write isolation [C063]; shadow doubles spend. Static labelled traces can score routers without live traffic [C030]. Measured production shadow results: not in corpus.
- **Kill-switch** per tenant and per optimisation [C063]; revert on any breach to the unchanged default path (mid-run switches break caches [A204]).
- **Rollback triggers.** Success below floor; CPS above baseline CI; per-caller hit rate below baseline; empty-patch or apply-failure spike; p95 +20% [C063, placeholder]; billed vs estimate divergence.
- **Alerts.** Budget alerts at 75/90/100% [A213, C116]; budget around P95, not mean [C054]. Anomaly methods: not in corpus.

## 5. MUST rules

1. Headline metric is CPS including failed attempts; never report token savings alone [C024, A069].
2. Compare paired by task with repeats and report CIs [C027, C023].
3. Record a verifiable success flag on every attempt [C026].
4. Maintain a private eval set with hard cases and a Lite subset [A060, C024].
5. No optimisation ships without a same-task baseline arm and isolated cache state [C024, A006].
6. Declare a non-inferiority bound before the test; auto-revert on breach [C025, C024, A052].
7. Attribute cost per caller, task, repo and model [C052, C028].
8. Ingest mutually exclusive token buckets, normalise provider conventions, reconcile to invoices [A233, A216, A242].
9. Track failed-run waste and cut runs after the first repeated failure signature [C028].
10. Enforce caps externally, start at P75 of own baseline with a reminder [C025, C136].
11. Predict cost with one probe and about 1.9x headroom, not self-estimates or human labels [C023, C027].
12. No voting, ensembles or agent teams without a measured CPS gain [A122, C132, C001/C081].
13. Count cache loss in every routing or model-switch decision [C030].
14. Report spend by median and P95 [C054].
15. Roll out with shadow, kill-switch and auto-rollback [C063].
16. Track AI-generated defect burden alongside cost [C053].

## 6. Conflicts and not in corpus

**Conflicts**
- Visible budget: helps [C131, C025], no effect [C136].
- Voting: 0% benefit [A122]; Self-MoA best [A032]; More Agents scales [A033, no numbers].
- Compaction: neutral or helps [C122] vs adds cost [A224, C130, C133].
- Routers beat best single: papers yes; LLMRouterBench and RouterArena mostly no [A006, A046].
- Cost driver: input [C023] vs output (2.7% of tokens, 51.1% of dollars at 96.3% hit) [C027] vs harness base [C024].
- Effort control savings 19% vs 75% by harness [C026]; optimisations do not transfer (Headroom +48% vs -12.49%) [C024].
- Agent-team multiplier: 7x [C001, C010], "significantly more" [C081], 3-5x [C062].
- Critical error price: $0.01 vs $0.20 inside A123.
- Savings claims of 18-80% are marketing unless a method is shown.

**Not in corpus:** a measured agent-team or subagent multiplier; production shadow, canary or staged-rollout results; sample-size or power formulas and test duration; an acceptable quality-loss margin; anomaly-detection methods; reconciliation tolerance; evaluated adaptive controllers; cap tests in interactive sessions; router production dollars after cache loss; AI-defect burden beyond one developer's fix-commit ratio.
