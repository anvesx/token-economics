# ADR 0003: features may rewrite a request; the router stops at rules

Status: proposed (2026-11-23).

## Decision
1. **A feature changes a request by returning a `Rewrite`** (contracts `Rewriter` port): the whole new body, short
   metadata notes, and headers to append (an `anthropic-beta` value). It never mutates the body it is given.
2. **Rewrites run after every `before` has allowed the request**, in policy order; each sees the previous one's output.
   Budgets reserve on the original request, so a rewrite that lowers cost only makes the reservation more pessimistic.
3. **Rewrites always fail open.** Each rewriter gets its own copy; one that raises is skipped and logged. With no
   enforced rewrite, the original bytes go upstream untouched (tested byte for byte). Compressed request bodies are
   never rewritten.
4. **Advisory rewrites are logged as `would_rewrite` and not sent**, so a change can be watched before it is switched on.
5. **Determinism is a contract.** Claude Code resends the whole history; a rewrite must give the same output for the
   same input, and state that changes the output (TTL, deferral, route) is frozen per session, or the prompt cache is lost.
6. **Router ladder, rung 1 only:** rules at session start, kept for the conversation, plus stickiness and a switch
   pricer. The atomic classifier, static step-level router, cascade and probe are not built. Each needs execution-
   verified labels and must beat the best single model in the eval harness after its own overhead and cache loss.
7. **Shadow runs mirror one request, not a task**: they measure per-call cost and errors of the candidate policy, not
   success. Success comes from the eval harness only.
8. **The policy engine loads only switched-on features, one at a time**, so a broken package breaks only itself.

## Why
- Every P2 control (caps, masking, clearing, deferral, cache TTL, routing) changes the request; the P1 port could only
  allow or block.
- plan/06 "Cache interaction" and plan/05 "Cache keys": history edits and model changes break the exact-prefix cache.

## Consequences and open points
- The decisions log says which features rewrote a request, keyed by the gateway's request id and session id; ledger
  rows do not carry it. Joining a row to its rewrites goes through session id and time.
- Several API names (context-management edit type, tool-search tool, beta headers) are unverified and configurable.
- Re-serialising the body changes its bytes (spacing, key order is kept). Providers do not care; a byte-level audit
  of the original request is impossible once a rewrite applied.
