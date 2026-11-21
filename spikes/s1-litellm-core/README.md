# Spike: LiteLLM as the gateway core

Status: **not run**. Time-box: 3 days. A spike is throwaway code and is never imported.

## Question
Can LiteLLM forward Claude Code traffic untouched (every anthropic-beta value, cache_control order, OAuth passthrough) and return byte-identical responses?

## Method
Run tests/integration against a LiteLLM proxy in place of apps/gateway; compare cache-read tokens for one Claude Code session with and without it.

## Result
Not run yet. Write the result here with a date, then copy it into `plan/09-risks-and-open-questions.md` (P0 exit gate).
