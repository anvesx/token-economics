import json
from decimal import Decimal

from token_economics_contracts import SERVICES, Attempt, EvalHarness, load
from token_economics_svc_eval import create, report_markdown


def _spec(**extra: object) -> dict[str, object]:
    return {
        "name": "t",
        "tasks": "x",
        "baseline": "baseline",
        "arms": {"baseline": {}, "a": {}, "b": {}},
        "bound": {"success_pp": 5},
        "n_boot": 300,
        **extra,
    }


def _attempts() -> list[Attempt]:
    out = []
    for i in range(30):
        for s in range(2):
            out.append(Attempt(task_id=f"t{i}", arm="baseline", seed=s, success=True, cost_usd=Decimal(2 + i % 3)))
            out.append(Attempt(task_id=f"t{i}", arm="a", seed=s, success=True, cost_usd=Decimal(1 + i % 3) / 2))
            out.append(Attempt(task_id=f"t{i}", arm="b", seed=s, success=True, cost_usd=Decimal(2 + i % 3)))
    return out


def test_analyse_gives_arm_summaries_and_holm_adjusted_verdicts_that_serialise() -> None:
    # Given a cheaper arm and an identical arm against one baseline
    result = create().analyse(_attempts(), _spec())
    # Then the cheaper arm wins, the identical one does not, and the whole result is JSON
    assert result["comparisons"]["a"]["verdict"] == "win" and result["comparisons"]["b"]["verdict"] == "no_win"
    assert result["comparisons"]["a"]["adjusted_p"] >= result["comparisons"]["a"]["p_value"]
    assert result["arms"]["baseline"]["failed_waste_share"] == 0.0
    assert result["arms"]["baseline"]["median_cost_geometric_sd"] == 1.0
    json.dumps(result)
    assert "win" in report_markdown(result)


def test_the_selftest_on_a_known_no_op_reports_no_difference() -> None:
    # Given the P2 gate: two arms from one distribution
    for seed in range(3):
        out = create().selftest(seed)
        # Then it passes: no win, and 1 is inside the ratio interval
        assert out["passed"], out
        assert out["ratio_ci"][0] <= 1 <= out["ratio_ci"][1]


def test_the_harness_is_registered_as_the_eval_service() -> None:
    harness = load(SERVICES, "eval")()
    assert isinstance(harness, EvalHarness)
