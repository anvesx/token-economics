# ADR 0002: fail open for observation, fail closed for budgets

Status: proposed (2026-11-21).

## Decision
1. **Observation fails open.** An error while reading usage, pricing or writing the ledger is counted and logged as
   metadata; the client's response is never affected.
2. **Budgets fail closed.** A feature declares `fail_closed`. If it is `enforced` and raises, or could not be built
   from its configuration, the request is refused with 503 `policy_unavailable`. Budgets is the only fail-closed
   feature. In `advisory` mode nothing fails closed.
3. **Every feature has three modes: off (default), advisory, enforced.** Advisory logs `would_block` and blocks
   nothing, so a limit can be watched on real traffic before it is switched on.
4. **A spent budget answers 402**, in the provider's error shape, with `x-should-retry: false`.
5. **The policy engine runs inside the gateway process**, off the event loop (`asyncio.to_thread`).

## Why
- 402 against 429 was tried with real Claude Code 2.1.330 (spike s2, `spikes/s2-claude-code-402/README.md`): both stop
  at once with no retry storm, but 429 is shown as "Server is temporarily limiting requests", which is wrong for a
  budget. 402 shows the gateway's message as is.
- Advisory mode matches the plan's "meter hard budgets in two modes, advisory and enforced".

## Consequences and open points
- If the ledger write fails after a response, the budget is not charged for it (observation failed open). Spend can
  then be under-counted until the reconciler exists.
- A gateway that is down takes Claude Code down with it: there is no bypass. The plan's "health-checked bypass" is not built.
- Turn cap and loop guard answer 429, so Claude Code shows them with the "temporarily limiting" wording.
