# token-economics-svc-rollout

Shadow runs on mirrored traffic with write isolation; later canary, kill-switch and rollback.

Kind: service. Phase: P2. May import: token-economics-contracts, token-economics-stats.

Run alone: `uv run --package token-economics-svc-rollout pytest services/rollout`
