# Token Economics: scope and principles

Token Economics is a cost-control plane. It sits between coding harnesses (Claude Code, Codex CLI, Aider, SDK users) and any number of backends, either API providers or CLI agents such as `claude -p` and `codex exec`. It measures every token, prices it, enforces budgets and applies cost optimisations that have passed an eval.

Working name only. Evidence for every rule is in `_research/R1` to `R6` and traced in `10-requirements-traceability.md`.

## What Token Economics does

1. Routes traffic through a gateway so every request is metered, whatever the harness.
2. Turns raw provider usage into five exclusive token buckets and one priced ledger row per response.
3. Enforces budgets, turn caps and loop limits outside the agent.
4. Chooses model, cache policy and price tier per request, gated by measured quality.
5. Shrinks prompts with context controls that are proven for the harness in use.
6. Proves each saving with cost per successful task before it reaches all traffic.

## What Token Economics does not do

- It does not route Claude Code to non-Claude models. Anthropic does not support that path through a gateway.
- It does not convert plan quota (credits, premium requests, messages per five hours) into tokens. Plan quota stays in native units.
- It does not control harnesses that expose no pluggable surface (Gemini CLI, Copilot, Cursor, Amp, Kiro, Cline, OpenHands). For those it only reads dashboards, exports and local files.
- It does not store prompt or tool content by default.
- It does not trust a client hook for enforcement. Developers can disable hooks.

## Principles

| # | Principle | Why |
|---|---|---|
| 1 | The gateway is the source of truth. Hooks, OpenTelemetry and transcripts are supplements. | The gateway cannot be disabled by a developer. |
| 2 | Fail open for observation, fail closed for budgets. | A broken meter must not stop work. A broken budget must not allow unmetered spend. |
| 3 | Every cost carries a `cost_source`: client, gateway or bill. | Client-side costs are estimates, not bills. |
| 4 | Price rows are append-only and versioned. | Prices change; every past cost must be reproducible. |
| 5 | Measure before optimising. Ship in the order measure, enforce, optimise, harden. | Savings claims in the corpus vary from ties to 53 percent. |
| 6 | One optimisation, one kill-switch. | Rollback must not need a deploy. |
| 7 | Capability flags decide control. A false flag downgrades to observe-only. | Harnesses differ. |
| 8 | Cost per successful task is the headline metric, failures included. | A cheaper run that fails is not a saving. |
| 9 | Label anything without a corpus source "DevX proposal". | Keeps proposals apart from evidence. |

## Evidence limits

- All 423 sources and 411 notes in the research set are model-written. Six agents extracted the requirements from the notes plus corpus text. The plan does not rest on a first-hand read of every paper.
- Codex contributed none of the notes used here. It stopped after 24 of 93.
- Many figures are vendor or author claims. Model names such as Fable 5.1 are quoted as the corpus gives them. Some cannot be verified.
- `09-risks-and-open-questions.md` lists what the corpus does not contain.
