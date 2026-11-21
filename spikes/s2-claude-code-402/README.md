# Spike: Claude Code against a 402

Status: **run once, 2026-11-21**, Claude Code 2.1.330, `claude -p "hi"`, subscription login, through the local gateway
with a one-cent enforced budget. Interactive mode and long sessions were not tried.

## Question
What does Claude Code do when the gateway answers 402 or 429 for an exhausted budget: retry, stop, show the message?

## Result
| Gateway answer | Time to fail | Exit | What the user sees |
|---|---|---|---|
| 429, `rate_limit_error`, `x-should-retry: false` | 2.3 s | 1 | `API Error: Server is temporarily limiting requests (not your usage limit) · <gateway message>` |
| 402, `billing_error`, `x-should-retry: false` | 4.0 s | 1 | `API Error: 402 <gateway message>` |

Neither retried in a loop. 402 shows the message without a misleading prefix, so budgets default to 402 (ADR 0002).
Not tested: behaviour without `x-should-retry: false`, mid-session in interactive mode, a sub-agent hitting the limit.

Also seen: the worst-case reservation for "hi" on Sonnet 5.5 was about $1.60, because Claude Code sends a large
`max_tokens`. A budget smaller than that refuses every request.
