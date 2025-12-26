"""Custom exceptions for Twitter module.

This module defines Twitter-specific exceptions that may occur during
collection, storage, or processing of tweets.
"""

from __future__ import annotations


class TwitterError(Exception):
    """Base exception for Twitter module errors."""

    pass


class TwitterCollectionError(TwitterError):
    """Error during tweet collection from Twitter/X."""

    pass


class TwitterStateError(TwitterError):
    """Error related to Twitter state file operations."""

    pass


class TwitterStorageError(TwitterError):
    """Error during tweet storage operations."""

    pass


class TwitterSourceNotFoundError(TwitterError):
    """Requested Twitter source was not found."""

    def __init__(self, source_id: str) -> None:
        self.source_id = source_id
        super().__init__(f"Twitter source not found: {source_id}")


class TwitterParseError(TwitterError):
    """Error parsing tweet data from DOM or API response."""

    pass


class TwitterRateLimitError(TwitterCollectionError):
    """Twitter rate limit was hit during collection."""

    def __init__(self, retry_after: int | None = None) -> None:
        self.retry_after = retry_after
        msg = "Twitter rate limit exceeded"
        if retry_after:
            msg += f", retry after {retry_after} seconds"
        super().__init__(msg)
