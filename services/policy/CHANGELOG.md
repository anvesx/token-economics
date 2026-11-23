# Changelog: token-economics-svc-policy

## Unreleased

- Loads only the features the policy switches on, one at a time: a broken feature package shows as a problem and breaks only itself.
- `rewrite`: enforced rewriters change the body in policy order, advisory ones log `would_rewrite`; each gets its own copy and a failing one is skipped.

## 0.1.0

- First version (P0).
