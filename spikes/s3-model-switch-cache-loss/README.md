# Spike: Cache loss on a model switch

Status: **not run**. Time-box: 3 days. A spike is throwaway code and is never imported.

## Question
How many tokens are rewritten when a session changes model mid-conversation?

## Method
From the ledger: for sessions with two models, compare cache_write tokens on the first call after the switch with the session's running cache_read. Hermes row 16 gives a transcript-side estimate to compare.

## Result
Not run yet. Write the result here with a date, then copy it into `plan/09-risks-and-open-questions.md` (P0 exit gate).
