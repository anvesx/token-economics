# token-economics-feat-sticky-model

One model per session: flag or undo a mid-session model change.

Kind: feature. Phase: P2. May import: token-economics-contracts. Policy name: `sticky_model`. Off by default.

Run alone: `uv run --package token-economics-feat-sticky-model pytest features/sticky-model`

## What it does
- Pins the first model seen in each MAIN or SUBAGENT conversation (key: session id, agent, query source).
- A later request in that conversation naming another model is rewritten back to the pin; note
  `model claude-haiku-5-5->claude-opus-5-5 (pinned for session)`.
- AUXILIARY requests (title generation on a small model) are ignored and never pinned. A request at `turns == 0`
  starts a new pin. Requests without a session id have no state. Only Anthropic Messages bodies
  (`providers/anthropic.py`); gemini, openai and xai are not built.
- State: `<state_dir>/sticky_model.json` (atomic, throttled writes, 24 h prune, at most 2000 entries), so a restart does
  not unpin a live session.

## Config
None. Enable with `{"mode": "advisory"}` or `"enforced"`.

## Order
Put `"rules_router"` before `"sticky_model"` in `order`, so the pin is the routed model.
Do not enable it together with `switch_pricer`: both answer whether the model may change mid-session; switch_pricer
prices the answer, this one always says no.

## Unverified
Not run against a live Claude Code session. A user's deliberate /model switch is undone too (that is the point of the
feature); use `switch_pricer` or leave this off if switches should be allowed.
