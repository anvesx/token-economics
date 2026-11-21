import pytest
from token_economics_contracts.testing import check_adapter
from token_economics_feat_harness_adapters.providers.claude_code import ADAPTER as CLAUDE_CODE
from token_economics_feat_harness_adapters.providers.codex import ADAPTER as CODEX
from token_economics_feat_harness_adapters.providers.sdk import ADAPTER as SDK


@pytest.mark.parametrize("adapter", [CLAUDE_CODE, SDK, CODEX], ids=lambda a: a.name)
def test_adapter_passes_the_shared_contract_suite(adapter):
    # Given an adapter / When the contract suite runs / Then it passes
    check_adapter(adapter)
