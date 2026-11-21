# token-economics-svc-health

Backend health and rate-limit tracking.

Kind: service. Phase: P1. May import: token-economics-contracts.

Run alone: `uv run --package token-economics-svc-health pytest services/health`

## What it does
In-memory health and rate-limit tracking per provider, over a sliding 5-minute window (injectable clock). No disk.
Per provider: request count, 2xx / 429 / 5xx / other counts, last status, last error time, consecutive failures
(429 or 5xx; a 2xx resets), `retry-after` (seconds or HTTP date, on 429 and 529) as `retry_until`, and rate-limit
headers when present.

## API
- `InMemoryHealth(clock=time.time, window_s=300)` implements `HealthTracker`.
  - `record(provider, status, headers)` (header names case-insensitive)
  - `snapshot() -> dict`: per provider `requests`, `ok_2xx`, `rate_limited_429`, `errors_5xx`, `other`, `error_rate`,
    `last_status`, `last_error_at`, `consecutive_failures`, `state`, `retry_until`, `limits`.
    `state` is `rate_limited` while now < `retry_until`, else `degraded` (error rate >= 20% with at least 5
    requests, or 3+ consecutive failures), else `healthy`.
  - `healthy(provider) -> bool` (an unseen provider is healthy)
- Entry point `health` -> `open_health()` under `token_economics.services`.

## Not built
The priced fallback chain. Only one upstream per provider exists today, and falling back across providers starts a
cold cache, so it must be priced first.

## Unverified
The rate-limit header names (`anthropic-ratelimit-requests-remaining`, `-tokens-remaining`, `-requests-reset`,
`-tokens-reset`; `x-ratelimit-remaining-requests`, `-tokens`) are taken from provider documentation, not checked
against live traffic. Consecutive failures do not expire with the window.
