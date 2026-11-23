import math
import random
from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st
from token_economics_contracts import Attempt
from token_economics_stats import cps, geometric_sd, holm, non_inferior, paired_bootstrap, verdict


def _att(task: str, arm: str, success: bool, cost: str, seed: int = 0, repo: str = "") -> Attempt:
    return Attempt(task_id=task, arm=arm, seed=seed, success=success, cost_usd=Decimal(cost), repo=repo)


def _paired(n: int, cost_cand: str = "1", success_cand: bool = True, rng_seed: int = 1) -> list[Attempt]:
    rng = random.Random(rng_seed)
    out = []
    for i in range(n):
        cost = str(rng.randint(5, 20) / 10)
        out.append(_att(f"t{i}", "base", True, cost))
        out.append(_att(f"t{i}", "cand", success_cand, str(Decimal(cost) * Decimal(cost_cand))))
    return out


def test_cps_counts_failed_spend_and_is_none_without_a_success() -> None:
    # Given one success and one failure
    rows = [_att("a", "x", True, "1.00"), _att("b", "x", False, "3.00")]
    # When CPS is computed Then the failed spend is in the numerator
    assert cps(rows) == Decimal("4.00")
    assert cps([_att("a", "x", False, "1")]) is None


def test_identical_arms_report_no_difference() -> None:
    # Given a candidate arm whose attempts equal the baseline's
    rows = []
    for i in range(30):
        ok = i % 4 != 0
        rows += [_att(f"t{i}", "base", ok, str(1 + i % 5)), _att(f"t{i}", "cand", ok, str(1 + i % 5))]
    # When compared
    r = paired_bootstrap(rows, "base", "cand", n_boot=500)
    # Then the ratio interval contains 1 and it is not a win
    assert r.ratio_ci is not None and r.ratio_ci[0] <= 1 <= r.ratio_ci[1]
    assert verdict(r, 5, 0.05)[0] != "win"


@given(st.lists(st.tuples(st.booleans(), st.integers(1, 50)), min_size=3, max_size=15), st.integers(0, 5))
@settings(max_examples=30, deadline=None)
def test_identical_arms_are_never_a_win_for_any_data(cells: list[tuple[bool, int]], seed: int) -> None:
    # Given any per-task outcomes copied to both arms
    rows = []
    for i, (ok, cents) in enumerate(cells):
        rows += [_att(f"t{i}", "a", ok, f"{cents}.00"), _att(f"t{i}", "b", ok, f"{cents}.00")]
    # When compared Then there is no win, and when the CI exists it contains 1
    r = paired_bootstrap(rows, "a", "b", n_boot=200, seed=seed)
    assert verdict(r, 5, 0.05)[0] != "win"
    if r.ratio_ci:
        assert r.ratio_ci[0] <= 1 <= r.ratio_ci[1]


def test_halved_cost_with_the_same_success_is_a_win() -> None:
    # Given a candidate that costs half and succeeds as often
    r = paired_bootstrap(_paired(40, cost_cand="0.5"), "base", "cand", n_boot=1000)
    # Then the verdict is a win
    assert r.ratio is not None and abs(r.ratio - 0.5) < 1e-9
    assert verdict(r, 5, 0.05)[0] == "win"


def test_much_lower_success_fails_the_success_bound_even_when_cheaper() -> None:
    # Given a candidate that is cheaper but succeeds on far fewer tasks
    rows = []
    for i in range(60):
        rows.append(_att(f"t{i}", "base", True, "2"))
        rows.append(_att(f"t{i}", "cand", i % 3 == 0, "1"))
    r = paired_bootstrap(rows, "base", "cand", n_boot=500)
    # Then non-inferiority is not shown
    assert not non_inferior(r, 5)
    assert verdict(r, 5, 0.05)[0] == "fails_success_bound"


def test_only_tasks_present_in_both_arms_are_paired() -> None:
    rows = _paired(10) + [_att("only-base", "base", True, "1")]
    r = paired_bootstrap(rows, "base", "cand", n_boot=50)
    assert r.n_clusters == 10 and r.attempts_base == 10


def test_resamples_without_a_success_are_dropped_and_counted() -> None:
    # Given a baseline with a single success among many tasks
    rows = []
    for i in range(10):
        rows += [_att(f"t{i}", "base", i == 0, "1"), _att(f"t{i}", "cand", True, "1")]
    r = paired_bootstrap(rows, "base", "cand", n_boot=300)
    assert r.dropped_resamples > 0 and r.unstable
    assert verdict(r, 100, 0.05)[0] == "no_win"


def test_repo_clustering_groups_tasks_of_one_repo() -> None:
    rows = []
    for i in range(6):
        rows += [_att(f"t{i}", "base", True, "1", repo=f"r{i % 2}"), _att(f"t{i}", "cand", True, "1", repo=f"r{i % 2}")]
    assert paired_bootstrap(rows, "base", "cand", n_boot=50, cluster="repo").n_clusters == 2


def test_the_same_seed_gives_the_same_result() -> None:
    rows = _paired(25, cost_cand="0.9")
    assert paired_bootstrap(rows, "base", "cand", n_boot=300, seed=4) == paired_bootstrap(
        rows, "base", "cand", n_boot=300, seed=4
    )


def test_holm_adjusts_known_values() -> None:
    # Given p-values 0.01, 0.04, 0.03 at alpha 0.05
    out = holm({"a": 0.01, "b": 0.04, "c": 0.03}, 0.05)
    # Then adjusted p are 0.03, 0.06, 0.06 and only a is rejected
    assert out["a"][0] == 0.03 and out["a"][1]
    assert abs(out["b"][0] - 0.06) < 1e-12 and not out["b"][1]
    assert abs(out["c"][0] - 0.06) < 1e-12 and not out["c"][1]


def test_geometric_sd_is_one_without_spread() -> None:
    assert geometric_sd([2, 2, 2]) == 1.0
    assert abs(geometric_sd([1, 100]) - math.exp(math.log(100) / math.sqrt(2))) < 1e-9
    assert geometric_sd([1.0]) == 1.0


def test_mean_interval_brackets_the_mean_and_is_the_same_for_the_same_seed() -> None:
    from token_economics_stats import mean_interval

    # Given a sample with a known mean
    values = [float(i % 10) for i in range(100)]
    # When the interval is drawn twice with one seed
    a, b = mean_interval(values, seed=3), mean_interval(values, seed=3)
    # Then it is identical, brackets the mean, and an empty sample has none
    assert a == b and a is not None and a[0] < 4.5 < a[1]
    assert mean_interval([]) is None
