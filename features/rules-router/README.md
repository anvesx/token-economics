# token-economics-feat-rules-router

Route a session to a model by rules, at session start, and keep it there (plan/05, routing ladder, rule rung).

Kind: feature. Phase: P2. May import: token-economics-contracts. Policy name: `rules_router`. Off by default.

Run alone: `uv run --package token-economics-feat-rules-router pytest features/rules-router`

## What it does
- When a conversation starts (`turns == 0`) the first rule whose `when` matches picks the model. The body is rewritten
  and the note is `model claude-opus-5-5->claude-sonnet-5-5 (rule 2)`.
- The choice is remembered per conversation (session id, agent, query source) and applied on every later turn, since
  the client keeps sending its own model and a flip back would break the prompt cache.
- If the client sends a model that is neither its starting model nor the routed one (the user's /model), routing stops
  for that conversation. This is recorded in the state file (`stopped`, `user_model`), not in `decisions.jsonl`.
- No route when the target equals the current model, or when a price book is present and the target has no price row
  (an unpriced model escapes budgets). Only Anthropic Messages bodies; requests without a session id are untouched.

## Config (`policy.json`, `features.rules_router`)
```json
{"mode": "advisory",
 "rules": [{"when": {"harness": "claude-code", "query_source": "subagent", "model": "claude-opus-5-5"},
            "model": "claude-sonnet-5-5", "reason": "subagents do not need opus"}]}
```
`when` keys, all optional and exact match: `harness`, `tenant`, `team`, `caller`, `query_source` (main, subagent,
auxiliary), `model`, `min_est_input_tokens`, `max_est_input_tokens`. An empty `when` matches everything. A malformed
rule or an unknown `when` key makes that rule inert (later rule numbers do not shift). Default: no rules, no routing.

State: `<state_dir>/rules_router.json` (atomic, throttled writes, entries unseen for 24 h pruned, at most 2000).

## Order
Put it before `sticky_model` in `order`, so the pin is the routed model.

## Not built
Atomic classifier, static step-level router, cascade, probe; effort routing. Rules only.

## Unverified
Not run against a live Claude Code session. Whether a client that is routed mid-flight keeps sending its original model
on every turn (assumed here) is checked only by unit tests. `est_input_tokens` is an upper estimate from body size.
