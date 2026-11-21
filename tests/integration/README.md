# Integration tests

End-to-end replay through `apps/gateway`: a fake provider and the gateway each run on a real local port. Fixtures are
built from the documented Anthropic stream format with synthetic text. They are not recordings of live traffic; record
and scrub real traces before relying on these for the P0 exit gate.

Run: `uv run pytest tests/integration -q`
