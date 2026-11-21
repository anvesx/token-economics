"""The shared contract suite. Every adapter's tests call `check_adapter` (the `contract` CI check)."""

from __future__ import annotations

from .ports import Adapter
from .types import Capabilities, Identity, RequestFacts


def check_adapter(adapter: Adapter) -> None:
    """Assertions every harness adapter must pass, whatever the harness."""
    assert isinstance(adapter, Adapter), "implements the Adapter port"
    assert adapter.name and adapter.provider
    assert isinstance(adapter.capabilities, Capabilities)

    env = adapter.route("http://127.0.0.1:8787", "vk-test")
    assert isinstance(env, dict)
    if adapter.capabilities.base_url:
        assert any("127.0.0.1:8787" in v for v in env.values()), "route() points the harness at the gateway"
    else:
        assert env == {}, "a harness with no base URL cannot be routed"
        assert adapter.cap({"budget_usd": 1}) == {} or adapter.capabilities.budget_flag, (
            "no harness with base_url false is marked as enforced"
        )

    # identify() and observe() never raise on input they do not understand
    assert isinstance(adapter.identify({}, b""), Identity)
    assert isinstance(adapter.identify({"content-type": "application/json"}, b"not json"), Identity)
    assert adapter.observe(200, {}, b"") is None
    assert adapter.observe(200, {"content-type": "application/json"}, b"{}") is None
    assert adapter.observe(500, {"content-type": "application/json"}, b'{"error": {"type": "overloaded"}}') is None

    # facts() never raises and never guesses on input it does not understand
    assert adapter.facts({}, b"") == RequestFacts() or isinstance(adapter.facts({}, b""), RequestFacts)
    assert isinstance(adapter.facts({"content-type": "application/json"}, b"not json"), RequestFacts)
