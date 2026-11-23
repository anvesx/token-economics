# Load test

Tool: `tools/loadtest.py`. Exit gate it serves (plan/PHASES.md, P3): "A load test holds the gateway latency budget
set in P0."

**No latency budget was ever recorded in P0** (plan/08 lists "Latency budget for the gateway" as a P0 measurement; P0
never measured it). The number below is therefore a proposal for the plan owner, not a decision.

## How it works

```bash
uv run python tools/loadtest.py [--requests 2000] [--concurrency 50] [--stream] [--policy policy.json] \
    [--out report.json] [--budget-ms P95]
```

A fake Anthropic provider (fixed 20 ms delay before the first byte; with `--stream`, 5 SSE deltas 2 ms apart) and the
real gateway run on free local ports with a scratch state dir. The same requests go straight to the provider and then
through the gateway, after a 100-request warm-up for each. Added latency = gateway minus direct, per percentile.
The ledger must end with exactly one row per successful gateway request (warm-up included) and no duplicate response
ids. `--budget-ms` makes the run exit 1 when added p95 time to first byte (TTFB) is over the budget.

Caveat: the load generator, the provider and the gateway share one Python process (threads, one GIL). Past a few
concurrent requests the process saturates and queueing, not the gateway, dominates the numbers. Read the low
concurrency run as the gateway's own overhead and the high concurrency run as a stress check (no errors, no lost
rows).

## Measured (2026-11-23, Apple M4, 10 cores, local ports, no policy file so no feature enabled)

Low concurrency, 1000 requests, concurrency 5 (not saturated: the useful overhead figure).

| mode | added p50 TTFB | added p95 TTFB | added p99 TTFB | added p95 total | gateway throughput | errors | ledger rows |
|---|---|---|---|---|---|---|---|
| JSON | 4.0 ms | 6.4 ms | 7.0 ms | 7.0 ms | 182 rps | 0 | 1100 of 1100 |
| stream | 1.5 ms | 3.4 ms | 14.5 ms | 4.7 ms | 114 rps | 0 | 1100 of 1100 |

Default size, 2000 requests, concurrency 50 (saturated, stress check only).

| mode | added p50 TTFB | added p95 TTFB | added p99 TTFB | gateway throughput | direct throughput | errors | ledger rows |
|---|---|---|---|---|---|---|---|
| JSON | 47.8 ms | 277.4 ms | 459.2 ms | 138 rps | 186 rps | 0 | 2100 of 2100 |
| stream | 83.0 ms | 206.4 ms | 304.9 ms | 117 rps | 157 rps | 0 | 2100 of 2100 |

Direct p50 TTFB was already 187 ms at concurrency 50 against a 20 ms provider, so the harness itself was saturated;
the added figures there are queueing and not a production estimate.

What held: zero errors in every run, and the ledger had one row per request with no duplicates under 50 concurrent
streams.

## PROPOSED budget (for the plan owner to accept or change)

- Added p95 TTFB through the gateway: **15 ms** at 5 concurrent requests on the reference machine (about 2x the
  measured 6.4 ms, to leave room for noise and for features switched on in P2).
- Zero lost or double ledger rows at any load.
- Enforce it with `uv run python tools/loadtest.py --requests 1000 --concurrency 5 --budget-ms 15`.

Not measured and still open: a run with P2 features enforced (pass `--policy`), a gateway in its own process, a
real provider's network path, and large request bodies (the fake body is a few hundred bytes).
