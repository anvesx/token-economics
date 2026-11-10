# Token Economics plan

Token Economics is a control plane between coding harnesses (Claude Code, Codex CLI, Aider, SDK users) and N model backends, whether API providers or CLI agents. It measures cost per successful task, enforces budgets outside the agent, and ships each optimisation only after a paired test.

## Read in this order

| # | File | Read it for |
|---|---|---|
| 00 | [00-scope-and-principles.md](00-scope-and-principles.md) | What Token Economics does and does not do, nine principles, evidence limits |
| 01 | [01-architecture.md](01-architecture.md) | Request flow, stages, integration surfaces, reuse table |
| 02 | [02-harness-adapters.md](02-harness-adapters.md) | Capability matrix and the five adapter functions |
| 03 | [03-data-model.md](03-data-model.md) | Token buckets, ledger row, attribution joins |
| 04 | [04-cost-formula.md](04-cost-formula.md) | Price book and the six-step cost formula |
| 05 | [05-policy-router-budgets.md](05-policy-router-budgets.md) | Budgets, run control, routing ladder |
| 06 | [06-context-guard.md](06-context-guard.md) | Schema deferral, output caps, masking, clearing |
| 07 | [07-observability-eval-rollout.md](07-observability-eval-rollout.md) | Metrics, eval design, shadow and canary |
| 08 | [08-security-reliability.md](08-security-reliability.md) | Keys, isolation, failure posture, fault tests |
| 09 | [09-risks-and-open-questions.md](09-risks-and-open-questions.md) | What the corpus does not contain |
| 11 | [11-detect-measure-apply.md](11-detect-measure-apply.md) | How Token Economics detects waste, measures it and applies fixes; hermes-engine metrics mapped to open-source options |
| 12 | [12-fix-table-50-rows.md](12-fix-table-50-rows.md) | All 50 problems: fix for API agents, fix for CLI agents, named techniques, phase (generated) |
| 12a | [12a-fix-technique-detail.md](12a-fix-technique-detail.md) | Mechanism, effect, limits and test design for each technique (generated) |
| 12b | [12b-source-coverage.md](12b-source-coverage.md) | All 423 sources: what each gives the 50 rows, full-text records for 112 papers, new technique names, read depth (generated) |
| 13 | [13-monorepo-layout.md](13-monorepo-layout.md) | Python monorepo: apps, services, features, modules; 45 packages; dependency rules; per-folder release (generated) |
| 14 | [14-research-papers.md](14-research-papers.md) | 14 paper titles with citations, release calendar tied to phases, novelty check |
| 15 | [15-paper-execution-plan.md](15-paper-execution-plan.md) | Pre-registration, power, venue fit and gates for each of the 14 papers |
| 16 | [16-research-update-2026-11.md](16-research-update-2026-11.md) | Papers dated 2026-09 or later, price changes, gateway and router releases, what changed in the plan |
| P | [PHASES.md](PHASES.md) | P0 to P3 with exit gates and definition of done |
| 10 | [10-requirements-traceability.md](10-requirements-traceability.md) | Every requirement, its sources and phase (generated) |
| G | token-economics-guide.html and token-economics-guide.pdf | Architecture guide with all 50 fix rows expanded; the PDF has no dropdowns (generated) |
| LLD | token-economics-lld.html and token-economics-lld.pdf | Drill-down diagram to component spec cards (generated) |

`_research/R1` to `R6` hold the extracted evidence. `model/` holds the data model that generates the diagram and the requirements file.

## Source ids

`A:nnn` is `research/corpus/nnn.txt` (API corpus). `C:nnn` is `research-cli-agents/corpus/nnn.txt` (CLI corpus). The two id spaces collide, so the prefix is required everywhere.

## Evidence limits

- All 423 sources were covered by model readers in three passes. 86 are cited in the fix table with the passage read for each row. 112 papers were re-read in full text, each read through the main text, though some had no bibliography or appendix read. C:043 was read from a PDF you supplied after SSRN blocked the download. The other 225 vendor docs, blogs and pages were read at abstract and key-section depth, and 14 of them had too little text to assess.
- Nobody read every source cover to cover. A reader once fetched an arXiv PDF (A:025) without permission and deleted it. You later approved six downloads, and A:025 was read from that approved copy. Figures were read as extracted text only.
- Codex finished 24 of 93 notes before its usage limit. Claude readers took the rest.
- Many figures are vendor or author claims on their own product.
- Model names are quoted as the corpus gives them. Some are future-dated or unverifiable.
- Anything with no corpus source is labelled DevX proposal.

## Start here

Build P0 first: gateway in observe mode, ledger, price book, two adapters. Nothing is blocked until a 30 day baseline exists.
