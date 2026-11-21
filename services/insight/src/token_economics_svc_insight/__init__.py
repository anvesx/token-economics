"""Attribution, baseline report and the leak detectors in alert mode."""

from pathlib import Path as _Path

from .baseline import BaselineReport, DeveloperBaseline, baseline, baseline_markdown
from .dashboard import (
    DashboardSummary,
    DayTotals,
    GroupTotals,
    RecentRequest,
    SessionTotals,
    TokenTotals,
    dashboard_summary,
)
from .detectors import HermesDetectors, coverage_markdown
from .sessions import SessionViews, open_session_views

__all__ = [
    "BaselineReport",
    "DashboardSummary",
    "DayTotals",
    "DeveloperBaseline",
    "GroupTotals",
    "HermesDetectors",
    "RecentRequest",
    "SessionTotals",
    "SessionViews",
    "TokenTotals",
    "baseline",
    "baseline_markdown",
    "coverage_markdown",
    "dashboard_summary",
    "open_detectors",
    "open_session_views",
]


def open_detectors(transcripts_root: str, state_dir: str, prompt_check: bool = False) -> HermesDetectors:
    """Factory registered as `token_economics.services` / `detectors`. Prompt check is off unless asked for."""
    return HermesDetectors(_Path(transcripts_root), _Path(state_dir), prompt_check=prompt_check)
