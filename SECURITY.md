# Security

## Reporting a problem

Email **security@devxlabs.ai** (placeholder address: to be confirmed before this repo is shared outside the team). Please do not open a public issue for a vulnerability. Say what you found, how to reproduce it, and what it could reach. We aim to reply within three working days.

## What the system stores

- **No prompt or response content by default.** The ledger keeps metadata only: token counts by bucket, model, price row, time, tenant, key and task ids. Storing content is a per-tenant opt-in with a retention limit (`token_economics_redaction`).
- **Secrets are never logged.** API keys, OAuth tokens and provider admin keys are never written to logs, the ledger, traces or error messages. OAuth tokens are forwarded to the provider and not stored.
- Test fixtures must be synthetic or redacted. CI runs a secret scan (gitleaks) on every pull request.

## Handling reports

We confirm the report, fix it on a private branch, release the fix, then publish a short note in `CHANGELOG.md` naming the affected package and version.
