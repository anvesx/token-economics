# Changelog: token-economics-app-gateway

## Unreleased

- Shadow runs: when the rollout service samples a request, a mirror goes through the candidate policy in `<state>/shadow/policy.json` to the provider; its row goes to `<state>/shadow/ledger.sqlite` only, its response is discarded and no budget is touched.
- Sends the policy engine's rewritten body upstream, with a fresh content length. Compressed bodies are never rewritten; any failure sends the original bytes.

## 0.1.0

- First version (P0).
