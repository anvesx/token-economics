# Security and reliability

Token Economics sits on the path of every model call and holds provider keys. That makes it a high-value target and a single point of failure. This file lists what Token Economics must do about both. Items without a corpus source are labelled DevX proposal.

## Security

| Area | Rule | Source |
|---|---|---|
| Content | Store metadata only. Prompt, tool and response bodies are opt-in. | DevX proposal |
| Provider keys | Gateway holds them. Developers get virtual keys scoped to tenant, team and budget. | A:234, C:060 |
| Key storage | Secrets manager, never environment files in the repo. Rotate on a schedule and on staff exit. | DevX proposal |
| Virtual keys | Hashed at rest, revocable, one per caller. | DevX proposal |
| OAuth passthrough | Forward the subscription token without storing it. Use it for route and observe only. | C:088 |
| Managed config | Pin the route in managed settings so a developer cannot bypass the gateway. | C:104, C:074 |
| Router attack | Cap each tenant's strong-model share. An adversarial prefix pushed routing to the strong model 73 to 100 percent of the time and raised cost over 8x. | A:010 |
| Cache isolation | Provider caches are isolated per org and workspace. Never share a cache key across tenants. | A:199 |
| Log redaction | Redact keys and bearer tokens in every log line. | DevX proposal |
| Retention | Fixed retention per tenant. Persist transcript copies because one source reports 30 day retention. | C:057 |
| Audit | Append-only log of budget changes, key issues, kill-switch use and price-book edits. | DevX proposal |
| Admin API | Role-based. Price-book and policy changes need a second approver. | DevX proposal |
| Third-party code | Treat proxy dependencies as supply chain. Pin versions and review before upgrade. | DevX proposal |

## Reliability

| Area | Rule | Source |
|---|---|---|
| Failure posture | Fail open for observation, fail closed for budgets. | 02-harness-adapters.md |
| Gateway outage | Health-checked bypass for reads. Budget calls refuse when the budget store is unreachable. | DevX proposal |
| Provider failure | Health tracking, rate-limit tracking, ordered fallback within the same model family first. | A:246, C:060 |
| Failover value | One gateway reported 3.5 percent of requests rescued, carrying 4.9 percent of spend. | A:246 |
| Fallback and cache | Falling back to another provider starts a cold cache. Price it before switching. | A:204, C:055 |
| Retries | Failed batch and flex requests cost zero. Retry on standard after a 429. | A:219, A:195 |
| Double counting | One ledger row per provider response id. Retries and stream cuts must not duplicate or lose a row. | A:216 |
| Reservation leak | A reservation with no true-up expires and is released. | DevX proposal |
| Soft budgets | Eventually consistent limits overshoot. Add a margin, measured in P1. | A:191, A:234 |
| Streaming | Tee the stream. Count tokens from the final usage event, not from chunks. | A:216 |
| Stale prices | Block billing on rows past expiry or older than 30 days. | 04-cost-formula.md |
| Canary | Weekly comparison of computed cost to invoice. | 04-cost-formula.md |
| Upgrades | Re-check cache reads after each Claude Code or Codex release. | C:052, C:054 |

## Fault-injection tests for P1

1. Provider returns 429, 500, a timeout and a cut stream. The ledger gains exactly one row per billable response.
2. Budget store down. Observation continues. Budgeted calls refuse.
3. Gateway restart mid-stream. No double count on retry.
4. Gateway strips `cache_control` in a test build. The hit monitor alerts within one window.
5. Key revoked mid-session. Next call returns 401 and the audit log records it.

## Open gaps

| Gap | Resolve in |
|---|---|
| Claude Code behaviour on a 402 | P0 spike |
| Soft-budget overshoot size | P1 |
| Latency budget for the gateway | P0 measurement |
| Disaster-recovery targets | P3 |
