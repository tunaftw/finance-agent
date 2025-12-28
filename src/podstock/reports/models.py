"""Pydantic models for report generation.

This module defines data structures for configuring and
storing report data.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class SummaryConfig(BaseModel):
    """Configuration for summary report generation.

    Attributes:
        start_date: Start of reporting period (inclusive).
        end_date: End of reporting period (inclusive).
        list_id: ID of podcast list to use ('broad' or 'niche').
        report_type: Type of report ('broad' or 'detailed').
        output_path: Optional custom output path.

    Example:
        >>> config = SummaryConfig(
        ...     start_date=datetime(2025, 12, 20),
        ...     end_date=datetime(2025, 12, 26),
        ...     list_id="broad",
        ...     report_type="broad"
        ... )
    """

    start_date: datetime
    end_date: datetime
    list_id: str = "broad"
    report_type: Literal["broad", "detailed"] = "broad"
    output_path: Path | None = None


class EpisodeData(BaseModel):
    """Episode data for report generation.

    Attributes:
        episode_id: Unique episode identifier.
        podcast_id: Parent podcast identifier.
        podcast_name: Display name of podcast.
        title: Episode title.
        published_at: Publication date.
        transcript_available: Whether transcript exists.

    Example:
        >>> ep = EpisodeData(
        ...     episode_id="bp-2024-12-18",
        ...     podcast_id="borspodden",
        ...     podcast_name="Börspodden",
        ...     title="Avsnitt 600",
        ...     published_at=datetime(2024, 12, 18)
        ... )
    """

    episode_id: str
    podcast_id: str
    podcast_name: str
    title: str
    published_at: datetime
    transcript_available: bool = True


class RecommendationData(BaseModel):
    """Recommendation data for report generation.

    Attributes:
        episode_id: Source episode.
        podcast_name: Podcast display name.
        stock: Stock name/ticker.
        action: Recommendation action (buy/sell/hold/watch/avoid).
        speaker: Who made the recommendation.
        reasoning: Brief reasoning.
        quote: Original quote if available.
        date: Recommendation date.

    Example:
        >>> rec = RecommendationData(
        ...     episode_id="bp-2024-12-18",
        ...     podcast_name="Börspodden",
        ...     stock="Evolution",
        ...     action="buy",
        ...     speaker="Johan Isaksson",
        ...     reasoning="Stark Q3-rapport"
        ... )
    """

    episode_id: str
    podcast_name: str
    stock: str
    action: str
    speaker: str | None = None
    reasoning: str | None = None
    quote: str | None = None
    date: str | None = None


class ReportData(BaseModel):
    """Complete data for report generation.

    Attributes:
        period: Human-readable period description.
        start_date: Start date.
        end_date: End date.
        list_id: Podcast list used.
        list_name: Display name of list.
        podcasts: List of podcast names included.
        episodes: List of episode data.
        recommendations: List of recommendations.
        generated_at: When this data was prepared.

    Example:
        >>> data = ReportData(
        ...     period="2025-12-20 till 2025-12-26",
        ...     start_date=datetime(2025, 12, 20),
        ...     end_date=datetime(2025, 12, 26),
        ...     list_id="broad",
        ...     list_name="Bred Analys",
        ...     podcasts=["Börspodden", "Fill or Kill"]
        ... )
    """

    period: str
    start_date: datetime
    end_date: datetime
    list_id: str
    list_name: str
    podcasts: list[str] = Field(default_factory=list)
    episodes: list[EpisodeData] = Field(default_factory=list)
    recommendations: list[RecommendationData] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)
