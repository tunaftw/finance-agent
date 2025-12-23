"""Core module for PodStock.

This module provides the fundamental building blocks:
- Data models (Podcast, Episode, Recommendation, etc.)
- Configuration management
- State management
- Custom exceptions
"""

from __future__ import annotations

from podstock.core.config import Config, load_config, save_config
from podstock.core.exceptions import (
    AnalysisError,
    ConfigError,
    DownloadError,
    PodStockError,
    RSSError,
    StateError,
    TranscribeError,
)
from podstock.core.models import (
    ConfidenceLevel,
    Episode,
    EpisodeStatus,
    Podcast,
    PodcastsFile,
    Recommendation,
    StateFile,
)
from podstock.core.state import State, load_state

__all__ = [
    # Config
    "Config",
    "load_config",
    "save_config",
    # Exceptions
    "AnalysisError",
    "ConfigError",
    "DownloadError",
    "PodStockError",
    "RSSError",
    "StateError",
    "TranscribeError",
    # Models
    "ConfidenceLevel",
    "Episode",
    "EpisodeStatus",
    "Podcast",
    "PodcastsFile",
    "Recommendation",
    "StateFile",
    # State
    "State",
    "load_state",
]
