# Research papers: release plan and titles

Token Economics produces its own data: a ledger of billed tokens, paired experiments and rollout results. Each phase ends with a paper that reports what that phase measured. The first release is about 4 weeks after P0 starts, then one about every 4 weeks.

Sources use the plan's ids (`A:nnn`, `C:nnn`). Items marked **new** were found by the novelty check in `_research/R7-paper-novelty.md` and are not in the corpus. Venues are DevX proposals, not commitments.

## What the novelty check found

14 candidate titles were searched against 2025 and 2026 work. 4 are open, 9 are partly covered, 1 is mostly covered.

| Verdict | Candidates | What it means for the title |
|---|---|---|
| Open | 7 cache-lifetime planning, 12 gateway vs transcript detection, 13 stale price book, 2 five exclusive buckets | Write them as stated |
| Partly covered | 1, 3, 4, 5, 6, 8, 10, 11, 14 | Claim only the part no one has done (the sharper titles below) |
| Mostly covered | 9 compressor flips by harness | Publish only as a controlled replication |

Most arXiv items were read at abstract level. "Not stated" means not on the abstract page. Read the full text of 2607.12161, 2608.01347, 2607.00053, 2605.18859 and 2606.04056 before final positioning. Several sources are vendor reports (PointFive, Dasein, Fireworks, LiteLLM); cite them as vendor reports.

## Novelty recheck after the November 2026 update

Fourteen papers dated 2026-09-17 to 2026-11-07 were read at abstract level (16-research-update-2026-11.md). Re-check these titles before drafting:

| Title | Overlap | Action |
|---|---|---|
| T3 Where the billed dollar goes | Total Cost of Agency (2609.23790), CliffCompaction (2609.26779) | Claim the per-harness decomposition from a gateway ledger |
| T6 Paired, task-clustered evaluation | Identical Runs, Different Results (2609.33812), DeltaSelect (2609.19607) | Cite both. Claim cache isolation and non-inferiority margins |
| T8 Router vs best single model | COMPASS (2610.27822), AgentRouter (2609.22951), Pathwise-Budgeted Routing (2611.05835) | Claim the overhead and cache-loss accounting only |
| T9 Same compressor, different harness | Harness design study (2609.20804), Beyond Token Savings (2609.32961) | Replication only, as before |
| T10 Stopping rules for retries | TokenEconomizer loop interruption (2610.22732) | Claim dollar-denominated rules |
| T11 Strong-model share ceilings | SCRouter (2610.18566) | Claim the budget bound, not the security condition |
| T13 Stale price books | Scheduled doublings and per-model multipliers in 2026 | Stronger case. Add the effective-date finding |

Read the full text of each before final positioning.

## Release calendar

| # | Slot | Working title | Data it needs | Phase gate that produces it |
|---|---|---|---|---|
| T1 | P0, week 4 | Cost per Successful Task, Specified: Numerator, Denominator and Failure Handling for Billed Coding-Agent Spend | 30-day baseline ledger | P0 exit: baseline exists |
| T2 | P0, week 4 | Five Exclusive Token Buckets: Auditing Usage Schemas Across Five Vendors | Raw `usage` blocks, price book | P0 exit: ledger matches invoice |
| T3 | P1, week 6 | Where the Billed Dollar Goes: A Four-Component Cost Decomposition of Three Production Coding Harnesses | Ledger by harness | P0 data, written during P1 |
| T4 | P1, week 8 | How Much Does a Soft Budget Leak? Overshoot of Post-Hoc vs Reserve-and-True-Up Caps | Budget enforcement logs | P1 exit: budgets enforced |
| T5 | P1, week 8 | Telling the Agent vs Stopping the Agent: Visible Budget Reminders vs Gateway Caps | Randomised arms in P1 | P1 exit |
| T6 | P2, week 10 | Paired, Task-Clustered Evaluation of Cost Optimisations with Cache Isolation and Non-Inferiority Margins | Eval harness | P2 week 2: harness runs |
| T7 | P2, week 14 | 5 Minutes or 1 Hour? Planning Prompt-Cache Lifetime from Measured Reuse-Gap Distributions | Reuse gaps from ledger | P2 exit |
| T8 | P2, week 14 | Does a Router Beat the Best Single Model After Overhead and Cache Loss? | Shadow routing results | P2 exit |
| T9 | P2, week 14 | Same Compressor, Same Model, Different Harness: Why Output Compression Moves Billed Cost in Opposite Directions | Paired runs, 3+ harnesses | P2 exit (replication only) |
| T10 | P3, week 16 | When Does Another Attempt Stop Paying? Dollar-Denominated Stopping Rules for Agent Retries and Step Caps | Loop and retry events | P3 week 2 |
| T11 | P3, week 18 | Bounding the Bill, Not Detecting the Prompt: Strong-Model Share Ceilings as a Router Defence | Adversarial test traffic | P3 week 4 |
| T12 | P3, week 18 | What a Gateway Can See That a Transcript Cannot, and the Reverse: Waste Detection Across Two Vantage Points | Gateway rows joined to transcripts | P3 exit |
| T13 | P3, week 18 | Price Books Go Stale: Lifecycle and Canaries for Billing-Accurate Cost Tracking | Weekly canary history | P3 exit |
| T14 | After P3 | Token Economics: A Harness-Agnostic Cost Control Plane for API and CLI Coding Agents | All of the above | Release 1.0 |

Order inside a phase follows the novelty check: T6 and T7 are the strongest gaps, so they are written first. T1 is written fast because two 2026 papers already use the metric.

Release rule per paper: data frozen and a reproduction folder at `papers/<id>/` before the draft starts; an internal review against the playbook's evidence rules; preprint first. Code and data go public only after the tenant-data check passes (metadata-only logging, per `08-security-reliability.md`).

## Paper detail

Each entry gives the question, the claim, the closest prior work, and what stays unsettled.

### T1. Cost per successful task, specified
- **Question.** What counts as cost and what counts as success when comparing agents across vendors?
- **Claim.** Numerator includes failed attempts, retries, router and judge cost. Denominator is verified success. Failed-run censoring is stated.
- **Prior work.**
  - Weinberger and Hozez, *Prompt-Induced Waste in Coding Agents*, arXiv 2608.01347 (**new**).
  - Weinberger and Hozez, *Token Reduction Is Not Cost Reduction*, arXiv 2607.12161 (**new**).
  - *Cutoffs, Retries, and Cost per Resolved Task* (C:043; the extracted text is only a title, so the claim rests on the title alone).
  - *Cost-of-Pass: An Economic Framework for Evaluating Language Models* (A:122).
  - *Economic Evaluation of LLMs* (A:123).
  - Ni et al., *GitTaskBench*, arXiv 2508.18993 (**new**).
- **Unsettled.** The metric name is no longer new. The paper is about the accounting rules.

### T2. Five exclusive token buckets
- **Question.** Do the five usage schemas agree on what "input" means, and how large is the error when they are summed naively?
- **Claim.** A conformance suite and an audit across five vendors.
- **Prior work.** No paper found. Practitioner sources only: CrewAI issue 6768 and the LiteLLM cost-discrepancy doc (**new**).
- **Unsettled.** The OpenTelemetry GenAI usage attributes were not read. Check them before writing.

### T3. Where the billed dollar goes
- **Question.** What share of the bill is base prompt, tool schemas, history and tool output, per harness?
- **Claim.** A four-component split in billed dollars for Claude Code, Codex and one more harness.
- **Prior work.**
  - *How Do AI Agents Spend Your Money?* (C:023).
  - *Analyzing and Mitigating Cost-Inefficient Behaviors in Coding Agents* (A:059).
  - Fan et al., *An Empirical Study of Harness Design for Coding Agents*, arXiv 2609.20804 (**new**). A Claude Code vs OpenCode blog test exists but contradicts itself on tool-schema tokens.

### T4. How much does a soft budget leak
- **Question.** How far past the limit do harness-side and post-hoc budgets let spend run, and what does reserve-then-true-up cost?
- **Claim.** Overshoot distributions for both designs on the same traffic.
- **Prior work.** *Token Budgets: 63 LLM-Agent Budget-Overrun Incidents*, arXiv 2606.04056 (**new**), which measures this in-process. Gateway vendors claim hard limits but publish no mechanics.

### T5. Telling the agent vs stopping the agent
- **Question.** Does showing a budget change behaviour, or does only an enforced cap?
- **Claim.** A randomised three-arm test: nothing, visible reminder, gateway cap.
- **Prior work.** *Budget-Aware Tool-Use Enables Effective Agent Scaling* (C:131) finds awareness helps. Ramp Labs, *Coding agents ignore their own budgets* (**new**, vendor report) finds a live counter changed nothing. Lin et al., *BAGEN*, arXiv 2606.00198 (**new**). The conflict is in `09-risks-and-open-questions.md`.

### T6. Paired, task-clustered evaluation
- **Question.** What design lets a cost optimisation be shipped with a stated bound on quality loss?
- **Claim.** Paired by task, clustered by repository, cache isolated per arm, non-inferiority margin on success, superiority test on cost.
- **Prior work.**
  - Miller, *Adding Error Bars to Evals*, arXiv 2411.00640.
  - Bjarnason et al., *On Randomness in Agentic Evals*, arXiv 2602.07150 (**new**).
  - Quesma's RTK benchmark (**new**, 5 repeats, no margin).
  - the two PointFive papers above. None states cache isolation between arms.
- **Why first.** Strongest gap, and every later paper depends on this method.

### T7. 5 minutes or 1 hour (cache lifetime)
- **Question.** For which reuse-gap distributions does the longer cache TTL pay for its write premium?
- **Claim.** A planner rule and its measured saving.
- **Prior work.** Lumer et al., *Don't Break the Cache*, arXiv 2601.06007 (**new**), has no lifetime analysis. Li et al., *Continuum*, arXiv 2511.02230 (**new**), covers self-hosted key-value caches only. LiteLLM reports 97.4% warm at 5 minutes (vendor figure).
- **Unsettled.** A claim that Anthropic changed its default cache lifetime in 2026 was not confirmed on an official page. Do not cite it.

### T8. Router vs best single model
- **Question.** After router overhead, judge cost and cache loss, does routing beat the best single model with its own cache?
- **Claim.** A billed-dollar comparison on real harness traffic.
- **Prior work.**
  - *LLMRouterBench* (A:006).
  - *RouterArena* (A:046).
  - *TwinRouterBench* (C:030).
  - *Agentic Model Routing for Coding Tasks* (C:032).
  - *LLMRouter* (C:033).
  - *A Unified Approach to Routing and Cascading for LLMs* (C:029).
  - Son et al., *SWE-Router*, arXiv 2607.00053 (**new**).
  - LiteLLM and vLLM session-aware routing posts (**new**, vendor-reported).

### T9. Same compressor, different harness
- **Question.** Why does one output compressor raise billed cost on one harness and lower it on another?
- **Claim.** A controlled replication with the same model on three or more harnesses, with a mechanism (extra turns, cache-prefix breakage).
- **Prior work.**
  - PointFive, Dasein and Quesma already show the direction (**new**, all vendor-affiliated). Quesma shows the same tool at -5% and +5% on two harnesses. The "+48%" in our notes is PointFive's Headroom figure (+48.4% on Claude Code, -12.49% on Codex; C:024).
  - confirm before reusing it.
- **Unsettled.** Publish only if the replication holds.

### T10. When does another attempt stop paying
- **Question.** At what retry or step count does the next attempt cost more than it returns, in dollars?
- **Prior work.** Kiecker et al., *Is Three the Magic Number?*, arXiv 2607.05197 (**new**), finds a knee at 3 to 4 repair rounds for code repair, not full sessions. Meir et al., *Reset and Discard*, arXiv 2601.21522 (**new**). *Cutoffs, Retries, and Cost per Resolved Task* (C:043).

### T11. Strong-model share ceilings
- **Question.** If a router is attacked, does a cap on strong-model share bound the loss?
- **Prior work.**
  - *Rerouting LLM Routers* (A:010).
  - Tang et al., *Route to Rome*, arXiv 2604.15022 (**new**).
  - Zhang et al., *RerouteGuard*, arXiv 2601.21380 (**new**). They attack and detect.
  - none bounds the bill.

### T12. Two vantage points for waste detection
- **Question.** Which waste patterns can a wire-level gateway see, and which only a transcript shows?
- **Prior work.** Zhu et al., *RedundancyBench*, arXiv 2605.29893 (**new**), and the Agent Waste Index forum post (**new**, not a paper) use trajectories only. No gateway comparison found. Method maps to `11-detect-measure-apply.md`.

### T13. Stale price books
- **Question.** How far does tracked cost drift from the invoice when prices change, and does a weekly canary catch it?
- **Prior work.** Vendor docs only. Thin academically, so fold into T2 if the data is small. *The Price Reversal Phenomenon* (A:069) and *Beyond Benchmarks: The Economics of AI Inference* (A:065) give pricing context.

### T14. System paper
- **Claim.** One control plane joins accounting, budgets, routing and measurement across harnesses and CLI backends.
- **Prior work.**
  - Gateway products (agentgateway, Portkey) have per-tool spend and hard limits.
  - no academic system paper found. Publish last and cite T1, T3, T4, T6 and T8.

## How papers fit the repo

- Folder: `papers/<id>-<slug>/` with `draft/`, `data/`, `code/`, `figures/`. Code that is reused moves into a package; the paper folder keeps only the glue.
- Data comes from the ledger export in `evals/`. Each number in a paper has a script that regenerates it.
- Papers are a board column in the GitHub project. A paper card is Done when the preprint is posted and the reproduction folder runs from a clean checkout.
- A paper never blocks a phase gate. If the data is not ready, the paper slips and the phase does not.

## Risks to the plan

| Risk | Effect | Handling |
|---|---|---|
| Others publish first (the field moved fast in 2026) | A title loses its claim | Re-run the novelty check at each draft start |
| Tenant data in a paper | Privacy breach | Aggregate only; tenant-data check before release |
| Vendor-reported baselines | Weak comparison | Reproduce them in our paired design |
| A phase result is negative | A paper has nothing to say | Report it. A stated non-result is a valid paper. |
