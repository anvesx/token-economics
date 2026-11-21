# token-economics-feat-upstream

Send the request upstream unchanged: one file per provider.

Kind: feature. Phase: P0. May import: token-economics-contracts.

Run alone: `uv run --package token-economics-feat-upstream pytest features/upstream`

## What it does

One file per provider under `src/token_economics_feat_upstream/providers/`. Each defines `UPSTREAM`, an object implementing the `Upstream` port from contracts:

- `provider`, `base_url`: defaults `https://api.anthropic.com` and `https://api.openai.com`. Override with a constructor argument, or with the env var `TOKEN_ECONOMICS_UPSTREAM_ANTHROPIC` / `TOKEN_ECONOMICS_UPSTREAM_OPENAI`. The environment is read when the object is constructed, not later.
- `url(path, query)`: base URL, path and query joined.
- `forward_headers(headers)`: every request header unchanged (names keep their casing, values are never read, stored or logged), except hop-by-hop headers (`host`, `content-length`, `connection`, `keep-alive`, `transfer-encoding`, `te`, `upgrade`, `proxy-authorization`, `proxy-connection`) and the virtual key `x-token-economics-key`. Matching is case-insensitive. `accept-encoding` is kept, so the caller must decompress before handing a body to an adapter. A header mapping holds one value per name, so several `anthropic-beta` values travel as one comma-joined value or as the caller's repeated-header representation.
- `SECRET_HEADERS` (in each provider file, re-exported from the package): header names whose values must never be written to disk.

No network I/O happens here: the gateway sends the request.

Entry points (`token_economics.upstreams`): `anthropic`, `openai`.

## Run alone

`uv run --package token-economics-feat-upstream pytest features/upstream`

## Not built

xai, gemini, bedrock, openrouter, vercel, catalogue and oauth files (see plan/13).
