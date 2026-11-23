"""Paired task-clustered bootstrap, CPS, non-inferiority and Holm correction for the eval harness."""

from .core import (
    PairedResult,
    cps,
    geometric_sd,
    holm,
    mean_diff_interval,
    mean_interval,
    non_inferior,
    paired_bootstrap,
    two_proportion_p,
    verdict,
)

__all__ = [
    "PairedResult",
    "cps",
    "geometric_sd",
    "holm",
    "mean_diff_interval",
    "mean_interval",
    "non_inferior",
    "paired_bootstrap",
    "two_proportion_p",
    "verdict",
]
