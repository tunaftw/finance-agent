"""Pydantic data models for YouTube transcript collection.

This module defines the core data structures used throughout the YouTube
collection system. All models use Pydantic for validation and serialization.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class YouTubeChannel(BaseModel):
    """A YouTube channel to collect transcripts from.

    Parallels TwitterSource and Podcast models.

    Attributes:
        id: Unique identifier (slug format, e.g., 'technicalroundup').
        channel_id: YouTube's channel ID (starts with UC...).
        handle: YouTube handle (e.g., @TechnicalRoundup).
        name: Display name of the channel.
        description: Our notes about this channel.
        category: Classification (crypto, finance, tech, etc.).
        language: Primary language code (default: 'en').
        subscriber_count: Number of subscribers (snapshot).
        video_count: Number of videos on channel.
        added_at: When the channel was added.
        active: Whether to include in collection.

    Example:
        >>> channel = YouTubeChannel(
        ...     id="technicalroundup",
        ...     channel_id="UC...",
        ...     handle="@TechnicalRoundup",
        ...     name="Technical Roundup",
        ...     category="crypto"
        ... )
    """

    id: str = Field(..., min_length=1, pattern=r"^[a-z0-9_-]+$")
    channel_id: str | None = None  # YouTube's UC... ID (optional, may not be available)
    handle: str | None = None  # @handle format
    name: str = Field(..., min_length=1)
    description: str | None = None
    category: str | None = None  # crypto, finance, tech, etc.
    language: str = "en"
    subscriber_count: int | None = None
    video_count: int | None = None
    added_at: datetime = Field(default_factory=datetime.now)
    active: bool = True

    @field_validator("id", mode="before")
    @classmethod
    def normalize_id(cls, v: str) -> str:
        """Normalize ID to lowercase."""
        return v.lower().replace(" ", "-")

    @field_validator("handle")
    @classmethod
    def normalize_handle(cls, v: str | None) -> str | None:
        """Ensure handle starts with @."""
        if v is None:
            return None
        if not v.startswith("@"):
            return f"@{v}"
        return v


class YouTubeVideo(BaseModel):
    """A single YouTube video with metadata.

    Parallels Episode and Tweet models.

    Attributes:
        id: YouTube's video ID (11 characters).
        channel_id: Our internal channel ID (slug).
        youtube_channel_id: YouTube's channel ID (UC...).
        title: Video title.
        description: Video description.
        published_at: When the video was published.
        duration_seconds: Video duration in seconds.
        view_count: Number of views.
        like_count: Number of likes.
        has_transcript: Whether a transcript was found.
        transcript_language: Language of the transcript.
        transcript_type: Type of transcript (auto/manual/none).
        mentioned_cryptos: Extracted crypto symbols ($BTC, $ETH).
        collected_at: When we collected this video.

    Example:
        >>> video = YouTubeVideo(
        ...     id="dQw4w9WgXcQ",
        ...     channel_id="technicalroundup",
        ...     youtube_channel_id="UC...",
        ...     title="Bitcoin Analysis 2025",
        ...     published_at=datetime.now(),
        ... )
    """

    id: str = Field(..., min_length=11, max_length=11)
    channel_id: str = Field(..., min_length=1)  # Our internal slug
    youtube_channel_id: str | None = None  # YouTube's UC... ID
    title: str = Field(..., min_length=1)
    description: str | None = None
    published_at: datetime
    duration_seconds: int | None = None
    view_count: int | None = None
    like_count: int | None = None

    # Transcript info
    has_transcript: bool = False
    transcript_language: str | None = None
    transcript_type: Literal["auto", "manual", "none"] = "none"

    # Extracted entities
    mentioned_cryptos: list[str] = Field(default_factory=list)

    collected_at: datetime = Field(default_factory=datetime.now)

    def extract_crypto_mentions(self, text: str | None = None) -> list[str]:
        """Extract crypto symbols from text.

        Looks for $BTC, $ETH, etc. and common crypto names.

        Args:
            text: Text to search. If None, uses title + description.

        Returns:
            List of unique crypto symbols found.
        """
        if text is None:
            text = f"{self.title} {self.description or ''}"

        # Extract $SYMBOL patterns
        ticker_pattern = r"\$([A-Z]{2,10})"
        tickers = set(re.findall(ticker_pattern, text.upper()))

        # Common crypto names to symbols
        crypto_names = {
            "bitcoin": "BTC",
            "ethereum": "ETH",
            "solana": "SOL",
            "cardano": "ADA",
            "ripple": "XRP",
            "dogecoin": "DOGE",
            "polkadot": "DOT",
            "avalanche": "AVAX",
            "chainlink": "LINK",
            "polygon": "MATIC",
        }

        text_lower = text.lower()
        for name, symbol in crypto_names.items():
            if name in text_lower:
                tickers.add(symbol)

        self.mentioned_cryptos = sorted(tickers)
        return self.mentioned_cryptos


class TranscriptSegment(BaseModel):
    """A timestamped segment of transcript.

    Attributes:
        start: Start time in seconds.
        end: End time in seconds.
        text: Text content of the segment.
    """

    start: float
    end: float
    text: str


class VideoTranscript(BaseModel):
    """Full transcript for a YouTube video.

    Attributes:
        video_id: YouTube video ID.
        channel_id: Our internal channel ID.
        language: Language of the transcript.
        text: Full transcript text (no timestamps).
        segments: List of timestamped segments.
        word_count: Total word count.
        duration_seconds: Duration covered by transcript.
        transcript_type: Whether auto-generated or manual.
        extracted_at: When the transcript was extracted.

    Example:
        >>> transcript = VideoTranscript(
        ...     video_id="dQw4w9WgXcQ",
        ...     channel_id="technicalroundup",
        ...     language="en",
        ...     text="Hello and welcome to...",
        ...     word_count=1500,
        ... )
    """

    video_id: str = Field(..., min_length=11, max_length=11)
    channel_id: str = Field(..., min_length=1)
    language: str = "en"
    text: str = ""
    segments: list[TranscriptSegment] = Field(default_factory=list)
    word_count: int = 0
    duration_seconds: float | None = None
    transcript_type: Literal["auto", "manual"] = "auto"
    extracted_at: datetime = Field(default_factory=datetime.now)

    def calculate_word_count(self) -> int:
        """Calculate and update word count from text."""
        self.word_count = len(self.text.split())
        return self.word_count


class YouTubeCollectionState(BaseModel):
    """Tracks collection progress per channel.

    Parallels TwitterCollectionState.

    Attributes:
        channel_id: Our internal channel ID.
        last_collected_at: When we last collected from this channel.
        last_video_id: Most recent video ID collected.
        oldest_video_id: Oldest video ID collected.
        videos_collected: Total videos collected.
        videos_with_transcripts: Videos that had transcripts.
        oldest_video_date: Date of oldest video collected.
        newest_video_date: Date of newest video collected.
        collection_complete: Whether we've collected all videos.
        last_error: Last error message if any.
        error_count: Total errors encountered.

    Example:
        >>> state = YouTubeCollectionState(channel_id="technicalroundup")
        >>> state.collection_complete
        False
    """

    channel_id: str
    last_collected_at: datetime | None = None
    last_video_id: str | None = None
    oldest_video_id: str | None = None
    videos_collected: int = 0
    videos_with_transcripts: int = 0
    oldest_video_date: datetime | None = None
    newest_video_date: datetime | None = None
    collection_complete: bool = False
    last_error: str | None = None
    error_count: int = 0


class YouTubeChannelsFile(BaseModel):
    """Schema for youtube_channels.json file.

    Attributes:
        version: Schema version number.
        updated_at: Last update timestamp.
        channels: List of YouTube channels to collect from.
    """

    version: int = 1
    updated_at: datetime = Field(default_factory=datetime.now)
    channels: list[YouTubeChannel] = Field(default_factory=list)


class YouTubeStateFile(BaseModel):
    """Schema for youtube_state.json file.

    Attributes:
        version: Schema version number.
        last_updated: Last update timestamp.
        channels: Dictionary mapping channel_id to collection state.
    """

    version: int = 1
    last_updated: datetime = Field(default_factory=datetime.now)
    channels: dict[str, YouTubeCollectionState] = Field(default_factory=dict)


# Utility functions


def extract_video_id(url: str) -> str | None:
    """Extract video ID from a YouTube URL.

    Handles various URL formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID

    Args:
        url: YouTube URL.

    Returns:
        Video ID (11 characters) or None if not found.

    Example:
        >>> extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        'dQw4w9WgXcQ'
    """
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",  # Just the ID
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def extract_channel_id(url: str) -> str | None:
    """Extract channel ID or handle from a YouTube URL.

    Handles various URL formats:
    - https://www.youtube.com/channel/UC...
    - https://www.youtube.com/@handle
    - https://www.youtube.com/c/ChannelName

    Args:
        url: YouTube channel URL.

    Returns:
        Channel ID or handle, or None if not found.

    Example:
        >>> extract_channel_id("https://www.youtube.com/@TechnicalRoundup")
        '@TechnicalRoundup'
    """
    patterns = [
        r"youtube\.com/channel/(UC[a-zA-Z0-9_-]+)",  # Channel ID
        r"youtube\.com/(@[a-zA-Z0-9_-]+)",  # Handle
        r"youtube\.com/c/([a-zA-Z0-9_-]+)",  # Custom URL
        r"youtube\.com/user/([a-zA-Z0-9_-]+)",  # Legacy user URL
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None
