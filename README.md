# token-economics
Layer 0 of Company OS: price every model call, budget it, and report cost per successful task

The plan is in [`plan/`](plan/README.md). Code follows [`plan/13-monorepo-layout.md`](plan/13-monorepo-layout.md).
What is built and what is not: [`docs/P0-STATUS.md`](docs/P0-STATUS.md), [`docs/P1-STATUS.md`](docs/P1-STATUS.md).

## Try it (P0: observe only, nothing is blocked or changed)

```bash
uv sync --all-packages
uv run token-economics init --tenant devx          # creates a virtual key, prints harness settings
uv run token-economics-gateway --port 8787         # pass-through gateway
# in another shell, with the settings `init` printed:
#   ANTHROPIC_BASE_URL=http://127.0.0.1:8787 claude
uv run token-economics report                      # spend per developer, cache hit, from the ledger
uv run token-economics detect --days 30            # 50-row leak coverage table from Claude Code transcripts
uv run token-economics prices --stale              # price rows that need verifying
uv run token-economics-admin                       # dashboard at http://127.0.0.1:8788

# P1: limits (all off until switched on)
uv run token-economics budget set --scope caller --match <name> --usd 20 --mode advisory
uv run token-economics policy mode budgets enforced
uv run token-economics key list
```

State lives in `~/.token-economics` (`TOKEN_ECONOMICS_STATE_DIR` to change it). No prompt or response text is stored.

## Checks

```bash
uv run ruff check . && uv run pytest -q && uv run pytest tools/tests -q
uv run python tools/check_layering.py && uv run python tools/check_surface.py && uv run python tools/check_extractable.py
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the TDD cycle and commit rules.
