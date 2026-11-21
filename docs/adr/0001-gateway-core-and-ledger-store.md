# ADR 0001: gateway core and ledger store

Status: proposed (2026-11-21). To be accepted or replaced after spike s1.

## Decision
1. **Gateway core: a thin pass-through proxy on Starlette + uvicorn, with httpx for the upstream call.** This is the
   stack choice in `plan/13-monorepo-layout.md`. The proxy forwards request bytes and headers as they arrive and streams
   response bytes back untouched (`aiter_raw`), which is what the `replay` gate needs: byte-identical responses with and
   without the gateway. LiteLLM is not used as the core in this pass.
2. **Ledger and price store: SQLite files in local mode**, behind the `Ledger` and `PriceBook` ports in
   `modules/contracts`. Postgres comes later behind the same ports. Both tables are append-only, enforced by triggers.
3. **Packages meet through entry points.** `apps/gateway` and `apps/cli` import `contracts` only (as `layout.json`
   says) and find adapters, upstreams, normalisers and services under the `token_economics.*` entry-point groups.

## Why
- LiteLLM translates requests between provider formats. Claude Code needs every `anthropic-beta` value and every
  request field forwarded and `cache_control` left alone (`plan/02`); a translating core puts that at risk and makes
  byte-identical replay hard to hold. The playbook also records a compromised LiteLLM release (v1.107.0).
- SQLite needs no service to run and is enough for one developer or a small team in observe mode.

## Consequences and open points
- Budgets, virtual-key management and fallbacks (P1) must be built, or taken from LiteLLM if spike s1 shows it can
  forward untouched. The package boundaries hold either way.
- The request body is read in full before it is forwarded (the adapter needs it to identify the session). Responses
  are streamed.
- Detectors live in `services/insight`, which `layout.json` lists as a P1 package with no detector component. This
  placement is a proposal for the plan owner.
