"""Pydantic data models for PodStock.

This module defines the core data structures used throughout the application.
All models use Pydantic for validation and serialization.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl, field_validator


class Podcast(BaseModel):
    """Represents a podcast subscription.

    Attributes:
        id: Unique identifier (slug format, e.g., 'borspodden').
        name: Display name of the podcast.
        rss_url: URL to the RSS feed.
        hosts: List of host names.
        description: Optional description of the podcast.
        language: Language code (default: 'sv').
        website: Optional website URL.
        twitter: Optional Twitter handle.
        added_at: When the podcast was added.
        active: Whether to include in processing.

    Example:
        >>> podcast = Podcast(
        ...     id="borspodden",
        ...     name="Börspodden",
        ...     rss_url="https://borspodden.libsyn.com/rss",
        ...     hosts=["Johan Isaksson", "John Skogman"]
        ... )
    """

    id: str = Field(..., min_length=1, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(..., min_length=1)
    rss_url: HttpUrl | None = None  # Optional for Apple-only podcasts
    hosts: list[str] = Field(default_factory=list)
    description: str | None = None
    language: str = "sv"
    website: HttpUrl | None = None
    twitter: str | None = None
    added_at: datetime = Field(default_factory=datetime.now)
    active: bool = True


class Episode(BaseModel):
    """Represents a podcast episode.

    Attributes:
        id: Unique identifier (e.g., 'bp-2024-12-18').
        podcast_id: ID of the parent podcast.
        title: Episode title.
        published_at: Publication date.
        audio_url: URL to the audio file.
        duration_seconds: Duration in seconds (if known).
        description: Episode description/show notes.
        guid: RSS GUID for deduplication.

    Example:
        >>> episode = Episode(
        ...     id="bp-2024-12-18",
        ...     podcast_id="borspodden",
        ...     title="Avsnitt 598 - Julspecial",
        ...     published_at=datetime(2024, 12, 18),
        ...     audio_url="https://example.com/episode.mp3"
        ... )
    """

    id: str = Field(..., min_length=1)
    podcast_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    published_at: datetime
    audio_url: HttpUrl
    duration_seconds: int | None = None
    description: str | None = None
    guid: str | None = None

    @field_validator("duration_seconds")
    @classmethod
    def duration_must_be_positive(cls, v: int | None) -> int | None:
        """Validate that duration is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("duration_seconds must be positive")
        return v


class ConfidenceLevel(str, Enum):
    """Confidence level for a recommendation."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Recommendation(BaseModel):
    """Represents a stock recommendation extracted from a podcast.

    Attributes:
        id: Unique identifier.
        episode_id: ID of the source episode.
        company_name: Full company name.
        ticker: Stock ticker symbol (if known).
        market: Stock market (e.g., 'OMX Stockholm').
        host: Who made the recommendation (if identifiable).
        quote: Exact quote from the transcript.
        context: Summary of the context.
        timestamp_hint: Approximate time in episode.
        time_horizon: Investment time horizon.
        confidence: Confidence level of the recommendation.
        reasoning: Why this is interpreted as a buy recommendation.
        extracted_at: When the recommendation was extracted.

    Example:
        >>> rec = Recommendation(
        ...     id="bp-2024-12-18-001",
        ...     episode_id="bp-2024-12-18",
        ...     company_name="Evolution Gaming",
        ...     ticker="EVO",
        ...     quote="Vi har ökat i Evolution",
        ...     context="Diskussion om Q3-rapporten",
        ...     confidence=ConfidenceLevel.HIGH,
        ...     reasoning="Explicit köputtryck"
        ... )
    """

    id: str = Field(..., min_length=1)
    episode_id: str = Field(..., min_length=1)
    company_name: str = Field(..., min_length=1)
    ticker: str | None = None
    market: str | None = None
    host: str | None = None
    quote: str = Field(..., min_length=1)
    context: str = Field(..., min_length=1)
    timestamp_hint: str | None = None
    time_horizon: str | None = None
    confidence: ConfidenceLevel
    reasoning: str = Field(..., min_length=1)
    extracted_at: datetime = Field(default_factory=datetime.now)


class EpisodeStatus(BaseModel):
    """Tracks the processing status of an episode.

    Attributes:
        episode_id: ID of the episode.
        downloaded: Whether audio has been downloaded.
        downloaded_at: When audio was downloaded.
        audio_path: Path to downloaded audio file.
        transcribed: Whether audio has been transcribed.
        transcribed_at: When transcription completed.
        transcript_path: Path to transcript file.
        transcript_source: Source of transcript ('whisper' or 'apple').
        has_timestamps: Whether transcript includes timestamps.
        analyzed: Whether transcript has been analyzed.
        analyzed_at: When analysis completed.
        recommendations_count: Number of recommendations found.

    Example:
        >>> status = EpisodeStatus(episode_id="bp-2024-12-18")
        >>> status.downloaded
        False
    """

    episode_id: str = Field(..., min_length=1)
    downloaded: bool = False
    downloaded_at: datetime | None = None
    audio_path: Path | None = None
    transcribed: bool = False
    transcribed_at: datetime | None = None
    transcript_path: Path | None = None
    transcript_source: str | None = None  # "whisper" or "apple"
    has_timestamps: bool = False
    analyzed: bool = False
    analyzed_at: datetime | None = None
    recommendations_count: int = 0

    model_config = {"arbitrary_types_allowed": True}


class PodcastsFile(BaseModel):
    """Schema for the podcasts.json file.

    Attributes:
        version: Schema version number.
        updated_at: Last update timestamp.
        podcasts: List of podcast configurations.
    """

    version: int = 1
    updated_at: datetime = Field(default_factory=datetime.now)
    podcasts: list[Podcast] = Field(default_factory=list)


class StateFile(BaseModel):
    """Schema for the state.json file.

    Attributes:
        version: Schema version number.
        last_updated: Last update timestamp.
        episodes: Dictionary mapping episode_id to EpisodeStatus.
    """

    version: int = 1
    last_updated: datetime = Field(default_factory=datetime.now)
    episodes: dict[str, EpisodeStatus] = Field(default_factory=dict)
