# token-economics-feat-anomaly

Spend anomaly alerts per caller against its own trailing baseline. Kind: feature. Phase: P3.
May import: token-economics-contracts.

Run alone: `uv run --package token-economics-feat-anomaly pytest features/anomaly`

## Method

plan/07 says the corpus has no anomaly-detection method and P1 picks one. This is a robust z-score on daily spend:

- Daily spend per caller (UTC days) comes from ledger rows in `after()`. Rows without a price count as nothing.
- Baseline: median and MAD (median absolute deviation) of the previous `baseline_days` days that had spend.
- Alert when today's running spend `> median + k x 1.4826 x MAD` **and** `> min_usd` **and** the baseline has at least
  `min_days` days. 1.4826 makes MAD comparable to a standard deviation. Median and MAD resist the one bad day that
  would inflate a mean and stdev and hide the next anomaly.
- Today must also exceed `min_ratio` x median (default 1.25): when MAD is 0 (perfectly steady spend) the robust rule alone would fire on a few cents.
- Second trigger: one session spending over `session_usd` (off by default).
- One alert per caller per trigger per UTC day in `alerts.jsonl` (`kind: "spend_anomaly"`, `trigger: "daily"` or
  `"session"`, with the median, MAD, threshold and today's spend).

## Config (the feature's section of `policy.json`)

| key | default | meaning |
|---|---|---|
| `baseline_days` | 14 | days looked back for the baseline |
| `k` | 5 | MAD multiples above the median |
| `min_usd` | 5 | spend floor below which nothing alerts |
| `min_ratio` | 1.25 | today must exceed this multiple of the median |
| `min_days` | 7 | days of history needed before alerting |
| `session_usd` | null (off) | per-session spend that alerts |
| `block` | false | true: refuse the caller's further calls today with 429 `spend_anomaly` |

State: `anomaly.json` (daily totals per caller, kept for `max(2 x baseline_days, 30)` days and at most 5000 callers;
today's per-session totals; alert and block markers). Atomic writes, throttled to 30 s, immediate on an alert. A
corrupt file reads as empty. Fails open.

## Unverified

- k = 5, min_usd = 5 and 14 days are untested defaults. The plan asks for the method to be checked against the P0
  baseline; that replay has not been done. Expect to tune `k` and `min_usd` per team.
- Calls from a caller with no name are not tracked. A caller's first `min_days` days never alert (only the session
  trigger works then).
