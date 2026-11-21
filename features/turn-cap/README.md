# token-economics-feat-turn-cap

Turn cap per model, set from the baseline.

Kind: feature. Phase: P1. May import: token-economics-contracts.

Run alone: `uv run --package token-economics-feat-turn-cap pytest features/turn-cap`

## What it does

A `Feature` (`name = "turn_cap"`, `fail_closed = False`) registered as `turn_cap` under the entry-point group `token_economics.features`. Before dispatch, if `ctx.facts.turns >= cap` for the request's model it refuses with status 429, code `turn_cap_reached`. `turns` is the number of assistant messages already in the conversation, read by the harness adapter's `facts()`.

## Config

The feature's own section of the policy file:

```json
{"caps": {"<exact model id>": 40}, "default": null}
```

Model ids match exactly. With no cap for the model and no `default`, everything is allowed. The plan sets the cap at the 75th percentile of each model's own baseline turns, never a constant in code, so the numbers come from a baseline. `p75_caps(turns_by_model)` computes them: nearest-rank 75th percentile (rank = ceil(0.75 n)), leaving out models with fewer than 20 samples, so a baseline job can write the config.

## Not built

The remaining-turns reminder from the plan. It would change the request body, which the gateway does not do.
