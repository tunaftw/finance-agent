"""Custom exceptions for PodStock.

This module defines the exception hierarchy used throughout the application.
All custom exceptions inherit from PodStockError.
"""

from __future__ import annotations


class PodStockError(Exception):
    """Base exception for all PodStock errors.

    All custom exceptions in PodStock inherit from this class,
    making it easy to catch all application-specific errors.

    Example:
        >>> try:
        ...     raise PodStockError("Something went wrong")
        ... except PodStockError as e:
        ...     print(f"PodStock error: {e}")
    """

    pass


class ConfigError(PodStockError):
    """Raised when configuration is invalid or cannot be loaded.

    Examples:
        - Config file not found
        - Invalid JSON in config file
        - Missing required configuration keys
    """

    pass


class RSSError(PodStockError):
    """Raised when RSS feed operations fail.

    Examples:
        - Failed to fetch RSS feed (network error)
        - Invalid RSS XML format
        - Missing required RSS fields
    """

    pass


class DownloadError(PodStockError):
    """Raised when audio file download fails.

    Examples:
        - Network timeout during download
        - File size mismatch after download
        - Invalid audio URL
    """

    pass


class TranscribeError(PodStockError):
    """Raised when transcription fails.

    Examples:
        - Audio file not found
        - Whisper model loading failed
        - Unsupported audio format
    """

    pass


class AnalysisError(PodStockError):
    """Raised when analysis operations fail.

    Examples:
        - Failed to parse Claude response
        - Invalid recommendation format
        - Missing transcript file
    """

    pass


class StateError(PodStockError):
    """Raised when state operations fail.

    Examples:
        - State file corrupted
        - Failed to save state atomically
        - Episode not found in state
    """

    pass
