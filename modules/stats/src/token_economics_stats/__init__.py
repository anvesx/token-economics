"""Paired task-clustered bootstrap, CPS, non-inferiority and Holm correction for the eval harness."""

from .core import PairedResult, cps, geometric_sd, holm, non_inferior, paired_bootstrap, verdict

__all__ = ["PairedResult", "cps", "geometric_sd", "holm", "non_inferior", "paired_bootstrap", "verdict"]
