# feature_error

Severity: ticket. Source: services/policy: decisions log outcome failed_open / blocked, reason feature_error. Owner: see `ops/alerts.json` (currently UNASSIGNED until a person is named).

State dir below is `$TOKEN_ECONOMICS_STATE_DIR`, default `~/.token-economics`.

## What it means

A policy feature raised an exception. If the feature fails open (everything except budgets) the request went through unchecked and this is logged; if it fails closed see `policy_unavailable`.

## Who is affected

Requests that feature should have checked or rewritten, until fixed.

## First checks

```bash
grep feature_error ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/decisions.jsonl | tail -n 20
uv run token-economics policy show
curl -s 127.0.0.1:8787/_te/health
```

## Actions

1. Read the `detail` (exception type) and the feature name in the log line.
2. Switch the feature off while it is investigated: `uv run token-economics policy kill <feature>` (or `policy mode <feature> off`).
3. File the exception with the feature's owner; do not edit the ledger or the price book.

## Confirm recovery

No new `feature_error` lines for that feature after the kill, and `policy show` shows it off or killed.

## Escalation

Ticket the feature's owner. Page only if the feature is budgets (then it is `policy_unavailable`).

Kill switches and CLI verbs: see [README.md](README.md).
