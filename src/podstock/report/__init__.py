"""Report module for PodStock.

This module provides Markdown report generation
from extracted recommendations.
"""

from __future__ import annotations

from podstock.report.markdown import (
    ReportStats,
    calculate_stats,
    generate_and_save_report,
    generate_report,
    save_report,
)

__all__ = [
    "ReportStats",
    "calculate_stats",
    "generate_and_save_report",
    "generate_report",
    "save_report",
]
