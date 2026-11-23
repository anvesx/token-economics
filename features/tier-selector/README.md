# token-economics-feat-tier-selector

Pick the service tier per workload by rule (plan/05, "Tier and cache selection"). Kind: feature. Phase: P3.
May import: token-economics-contracts.

Run alone: `uv run --package token-economics-feat-tier-selector pytest features/tier-selector`

## What it does

A rewriter: sets the request's `service_tier` field when a rule matches, so offline or bulk work can ask for a cheaper
tier (`flex`) and only a workload with a binding SLA pays for `priority`. The decisions log gets a note such as
`service_tier -> flex (rule 1)`.

## Config (the feature's section of `policy.json`)

```json
{"mode": "advisory",
 "rules": [{"when": {"team": "batch", "query_source": "main"}, "service_tier": "flex"}],
 "override": false}
```

- `rules`: first match wins, numbered from 1. `when` keys: `harness`, `tenant`, `team`, `caller`, `query_source`,
  `model`; every key given must match exactly. An empty `when` matches everything. An unknown key never matches.
  A malformed rule never matches (but keeps its number).
- `override` (default `false`): a request that already sets `service_tier` is left alone unless this is `true`.
- Allowed values per provider: `providers/anthropic.py` (`auto`, `standard_only`) and `providers/openai.py`
  (`auto`, `default`, `flex`, `priority`). If the winning rule's value is not allowed for the request's provider,
  nothing is rewritten and later rules are not tried.

## Not built / unverified

- Gemini is in the layout but not built: its requests are never rewritten.
- A synchronous request cannot become a Batch API job at the gateway (batch is a separate endpoint with its own
  submit-and-poll flow). This feature only picks a tier on the live request.
- The tier values above are unverified against the live APIs. Check them before enforcing.
