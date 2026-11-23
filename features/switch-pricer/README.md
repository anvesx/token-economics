# token-economics-feat-switch-pricer

Allow a mid-session model switch only when the saving beats the cache rewrite.

Kind: feature. Phase: P2. May import: token-economics-contracts, token-economics-metering (not used so far).
Policy name: `switch_pricer`. Off by default.

Run alone: `uv run --package token-economics-feat-switch-pricer pytest features/switch-pricer`

## What it does
When a request in a conversation names a different model than the conversation's previous one (key: session id, agent,
query source; `turns > 0`), it prices the switch from the price book:
- `cache_rewrite = est_input_tokens x (incoming cache_write_5m - outgoing cache_read) / 1e6`: the extra cost of the
  switch turn over staying, when the prompt would otherwise have been read from the old model's cache
- `saving_per_turn = est_input_tokens x (prev cache_read - new cache_read) / 1e6
  + expected_output_tokens x (prev output - new output) / 1e6`
- allowed when `saving_per_turn x expected_remaining_turns > cache_rewrite`; otherwise the model is rewritten back to
  the previous one, with a note giving both numbers (4 dp).
- No price row for either model (or no price book): the switch is left alone and logged `unpriced`.
- A reverted switch is repeated by the client every turn, so it is priced and logged again each turn.

Every decision (allowed, reverted, unpriced) is appended to `<state_dir>/switch_pricer.jsonl`: ts, session_id, agent,
from, to, est_input_tokens, saving_per_turn_usd, saving_usd, cost_usd, remaining_turns, verdict. Metadata only.
State: `<state_dir>/switch_pricer.json` (atomic, throttled, 24 h prune, at most 2000 entries).

## Config (`features.switch_pricer`)
`expected_output_tokens` (default 2000), `expected_remaining_turns` (default 10). Invalid values fall back to defaults.

## Order and conflicts
Place it after `rules_router`. Do not enable together with `sticky_model`.

## Caveats
`est_input_tokens` is an upper estimate from body size, so the cost side is pessimistic and some switches that would pay
off are reverted. Cache rewrite assumes the 5 minute write rate and a fully cold cache at the incoming model. Not run
against a live session.
