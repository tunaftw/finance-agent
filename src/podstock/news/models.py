"""Pydantic data models for news aggregation.

This module defines the core data structures for fetching, storing,
and managing news from Stockholm Stock Exchange and financial media.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class NewsType(str, Enum):
    """Type of news item."""

    REGULATORY = "regulatory"  # MAR, insider, earnings announcements
    EDITORIAL = "editorial"  # Media articles, analysis
    PRESS_RELEASE = "press_release"  # Company press releases


class NewsSource(str, Enum):
    """Source of the news."""

    NASDAQ_NORDIC = "nasdaq_nordic"
    GLOBENEWSWIRE = "globenewswire"
    DI_SE = "di_se"
    CISION = "cision"
    OTHER = "other"


class NewsPriority(str, Enum):
    """Priority level for news items based on company following and type."""

    HIGH = "high"  # Followed company + regulatory
    MEDIUM = "medium"  # Followed + editorial OR unfollowed + regulatory
    LOW = "low"  # Unfollowed + editorial


class CompanyMatch(BaseModel):
    """A matched company reference in a news item.

    Attributes:
        company_id: Reference to Company.id from filings system.
        ticker: Stock ticker symbol if matched.
        isin: ISIN code if matched.
        match_type: How the match was made (ticker, isin, name).
        match_confidence: Confidence score 0.0-1.0.
        is_followed: True if company is in tracked companies list.
    """

    company_id: str
    ticker: str | None = None
    isin: str | None = None
    match_type: str = "ticker"  # "ticker", "isin", "name_exact", "name_fuzzy"
    match_confidence: float = 1.0
    is_followed: bool = False


class NewsItem(BaseModel):
    """A single news item from RSS feeds.

    Attributes:
        id: Unique identifier (format: "{source}-{date}-{hash}").
        title: News headline.
        summary: Brief summary or first paragraph.
        content_url: Link to full article.
        news_type: Type of news (regulatory, editorial, press_release).
        source: Source of the news.
        source_feed: Actual feed URL used.
        published_at: When the news was published.
        fetched_at: When we fetched this item.
        companies: List of matched companies.
        primary_company_id: Main company if identifiable.
        priority: Computed priority based on following and type.
        raw_guid: Original RSS GUID.
        raw_categories: Original RSS categories.

    Example:
        >>> item = NewsItem(
        ...     id="nasdaq-2024-12-27-a1b2",
        ...     title="Evolution AB: Quarterly Report Q4 2024",
        ...     content_url="https://...",
        ...     news_type=NewsType.REGULATORY,
        ...     source=NewsSource.NASDAQ_NORDIC,
        ...     source_feed="https://api.news.eu.nasdaq.com/...",
        ...     published_at=datetime.now(),
        ... )
    """

    id: str = Field(..., min_length=1)

    # Content
    title: str
    summary: str | None = None
    content_url: str

    # Classification
    news_type: NewsType
    source: NewsSource
    source_feed: str

    # Timing
    published_at: datetime
    fetched_at: datetime = Field(default_factory=datetime.now)

    # Company matching
    companies: list[CompanyMatch] = Field(default_factory=list)
    primary_company_id: str | None = None

    # Priority (computed)
    priority: NewsPriority = NewsPriority.LOW

    # Raw data
    raw_guid: str | None = None
    raw_categories: list[str] = Field(default_factory=list)

    @classmethod
    def generate_id(cls, source: NewsSource, published: datetime, title: str) -> str:
        """Generate a unique news item ID.

        Format: {source}-{date}-{hash}
        Example: nasdaq-2024-12-27-a1b2

        Args:
            source: News source.
            published: Publication date.
            title: News title (used for hash).

        Returns:
            Unique news item ID string.
        """
        date_str = published.strftime("%Y-%m-%d")
        title_hash = hex(abs(hash(title)))[-4:]
        return f"{source.value}-{date_str}-{title_hash}"


class FeedConfig(BaseModel):
    """Configuration for an RSS feed.

    Attributes:
        id: Unique identifier (e.g., "nasdaq-main", "di-se").
        name: Human-readable name.
        url: RSS feed URL.
        news_type: Type of news from this feed.
        source: Source identifier.
        active: Whether to include in sync operations.
        polling_interval_seconds: How often to poll (default 5 min).
        last_polled: When we last fetched this feed.
        last_item_count: Number of items in last fetch.
    """

    id: str = Field(..., min_length=1)
    name: str
    url: str
    news_type: NewsType
    source: NewsSource
    active: bool = True
    polling_interval_seconds: int = 300  # 5 min default
    last_polled: datetime | None = None
    last_item_count: int = 0


class NewsStateFile(BaseModel):
    """Schema for news_state.json - tracking sync state.

    Attributes:
        version: Schema version number.
        last_updated: Last state update timestamp.
        feeds: Dictionary mapping feed_id to FeedConfig.
        recent_item_ids: Last N item IDs for deduplication.
    """

    version: int = 1
    last_updated: datetime = Field(default_factory=datetime.now)
    feeds: dict[str, FeedConfig] = Field(default_factory=dict)
    recent_item_ids: list[str] = Field(default_factory=list)  # Last 1000 for dedup


class DailyNewsFile(BaseModel):
    """Schema for daily news files (e.g., items/2024/12/2024-12-27.json).

    Attributes:
        date: The date this file covers.
        items: List of news items for this day.
        item_count: Number of items.
    """

    date: str  # YYYY-MM-DD
    items: list[NewsItem] = Field(default_factory=list)
    item_count: int = 0
