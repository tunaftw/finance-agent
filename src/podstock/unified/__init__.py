"""Unified search layer for cross-source queries."""

from .models import Signal, Speaker, SignalType, AssetType
from .search import search_signals

__all__ = [
    "Signal",
    "Speaker",
    "SignalType",
    "AssetType",
    "search_signals",
]
