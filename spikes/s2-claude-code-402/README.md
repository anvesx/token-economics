# Spike: Claude Code against a 402

Status: **not run**. Time-box: 3 days. A spike is throwaway code and is never imported.

## Question
What does Claude Code do when the gateway answers 402 or 429 for an exhausted budget: retry, stop, show the message?

## Method
Point Claude Code at a stub that returns 402 and then 429 with a JSON error body; record retries, backoff and what the user sees, for interactive and claude -p.

## Result
Not run yet. Write the result here with a date, then copy it into `plan/09-risks-and-open-questions.md` (P0 exit gate).
