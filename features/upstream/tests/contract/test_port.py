from importlib.metadata import entry_points

import pytest
from token_economics_contracts.ports import Upstream
from token_economics_contracts.registry import UPSTREAMS
from token_economics_feat_upstream.providers.anthropic import UPSTREAM as ANTHROPIC
from token_economics_feat_upstream.providers.openai import UPSTREAM as OPENAI


@pytest.mark.parametrize("upstream", [ANTHROPIC, OPENAI])
def test_upstream_implements_the_port(upstream):
    # Given an upstream object / When checked against the port / Then it conforms
    assert isinstance(upstream, Upstream)
    assert upstream.provider and upstream.base_url


def test_entry_points_resolve_to_the_upstream_objects():
    # Given the installed entry points / When loaded / Then each is the module-level UPSTREAM
    found = {ep.name: ep.load() for ep in entry_points(group=UPSTREAMS)}
    assert found["anthropic"] is ANTHROPIC
    assert found["openai"] is OPENAI
