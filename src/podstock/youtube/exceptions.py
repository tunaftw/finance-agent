"""Custom exceptions for YouTube module.

This module defines YouTube-specific exceptions that may occur during
collection, extraction, or processing of transcripts.
"""

from __future__ import annotations


class YouTubeError(Exception):
    """Base exception for YouTube module errors."""

    pass


class YouTubeExtractionError(YouTubeError):
    """Error during transcript extraction from YouTube."""

    pass


class YouTubeChannelNotFoundError(YouTubeError):
    """Requested YouTube channel was not found."""

    def __init__(self, channel_id: str) -> None:
        self.channel_id = channel_id
        super().__init__(f"YouTube channel not found: {channel_id}")


class YouTubeVideoNotFoundError(YouTubeError):
    """Requested YouTube video was not found."""

    def __init__(self, video_id: str) -> None:
        self.video_id = video_id
        super().__init__(f"YouTube video not found: {video_id}")


class YouTubeTranscriptNotAvailable(YouTubeError):
    """No transcript available for the video."""

    def __init__(self, video_id: str, reason: str | None = None) -> None:
        self.video_id = video_id
        self.reason = reason
        msg = f"No transcript available for video: {video_id}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)


class YouTubeStateError(YouTubeError):
    """Error related to YouTube state file operations."""

    pass


class YouTubeStorageError(YouTubeError):
    """Error during transcript storage operations."""

    pass


class YtDlpNotFoundError(YouTubeError):
    """yt-dlp is not installed or not found in PATH."""

    def __init__(self) -> None:
        super().__init__(
            "yt-dlp is not installed. Install with: pip install yt-dlp"
        )


class YtDlpError(YouTubeExtractionError):
    """Error from yt-dlp during extraction."""

    def __init__(self, message: str, stderr: str | None = None) -> None:
        self.stderr = stderr
        full_msg = message
        if stderr:
            full_msg += f"\n{stderr}"
        super().__init__(full_msg)
