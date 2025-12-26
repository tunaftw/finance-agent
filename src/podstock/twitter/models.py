"""Pydantic data models for Twitter collection and analysis.

This module defines the core data structures used throughout the Twitter
collection system. All models use Pydantic for validation and serialization.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TwitterSource(BaseModel):
    """A Twitter account to collect tweets from.

    Parallels the Podcast model in core/models.py.

    Attributes:
        id: Unique identifier (lowercase handle without @).
        handle: Twitter handle (stored without @ prefix).
        display_name: User's display name on Twitter.
        bio: User's Twitter bio.
        description: Our notes about this account.
        category: Classification (analyst, fund_manager, podcast, etc.).
        language: Primary language code (default: 'sv').
        follower_count: Number of followers (snapshot).
        added_at: When the source was added.
        active: Whether to include in collection.

    Example:
        >>> source = TwitterSource(
        ...     id="vildkatten",
        ...     handle="vildkatten",
        ...     display_name="Per Ekström",
        ...     category="analyst"
        ... )
    """

    id: str = Field(..., min_length=1, pattern=r"^[a-z0-9_]+$")
    handle: str = Field(..., min_length=1)
    display_name: str | None = None
    bio: str | None = None
    description: str | None = None
    category: str | None = None
    language: str = "sv"
    follower_count: int | None = None
    added_at: datetime = Field(default_factory=datetime.now)
    active: bool = True

    @field_validator("handle")
    @classmethod
    def normalize_handle(cls, v: str) -> str:
        """Remove @ prefix if present."""
        return v.lstrip("@").lower()

    @field_validator("id", mode="before")
    @classmethod
    def normalize_id(cls, v: str) -> str:
        """Normalize ID to lowercase."""
        return v.lower()


class Tweet(BaseModel):
    """A single tweet with full metadata.

    This is the raw collected data, analogous to Episode in core/models.py.

    Attributes:
        id: Twitter's unique tweet ID.
        source_id: Which account this came from (our internal ID).
        author_handle: Tweet author's handle.
        author_display_name: Tweet author's display name.
        text: Full tweet text content.
        is_retweet: Whether this is a retweet.
        is_reply: Whether this is a reply.
        is_quote: Whether this quotes another tweet.
        quoted_tweet_id: ID of quoted tweet if applicable.
        reply_to_tweet_id: ID of tweet being replied to.
        posted_at: When the tweet was posted.
        collected_at: When we collected this tweet.
        likes: Number of likes (may be None for old tweets).
        retweets: Number of retweets.
        replies: Number of replies.
        views: Number of views (impressions).
        bookmarks: Number of bookmarks.
        has_media: Whether tweet contains images/video.
        media_urls: URLs to media attachments.
        has_links: Whether tweet contains external links.
        external_urls: External URLs in the tweet.
        mentioned_tickers: Extracted stock tickers ($TSLA, $EVO).
        mentioned_users: Mentioned @usernames.
        hashtags: Hashtags in the tweet.

    Example:
        >>> tweet = Tweet(
        ...     id="1234567890",
        ...     source_id="vildkatten",
        ...     author_handle="vildkatten",
        ...     text="Köper $EVO på dessa nivåer!",
        ...     posted_at=datetime.now(),
        ... )
    """

    id: str = Field(..., min_length=1)
    source_id: str = Field(..., min_length=1)
    author_handle: str
    author_display_name: str | None = None

    # Content
    text: str
    is_retweet: bool = False
    is_reply: bool = False
    is_quote: bool = False
    quoted_tweet_id: str | None = None
    reply_to_tweet_id: str | None = None

    # Timing
    posted_at: datetime
    collected_at: datetime = Field(default_factory=datetime.now)

    # Engagement metrics (may be None for older tweets)
    likes: int | None = None
    retweets: int | None = None
    replies: int | None = None
    views: int | None = None
    bookmarks: int | None = None

    # Media
    has_media: bool = False
    media_urls: list[str] = Field(default_factory=list)
    has_links: bool = False
    external_urls: list[str] = Field(default_factory=list)

    # Extracted entities (populated during processing)
    mentioned_tickers: list[str] = Field(default_factory=list)
    mentioned_users: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)

    def extract_entities(self) -> None:
        """Extract tickers, mentions, and hashtags from tweet text.

        Updates mentioned_tickers, mentioned_users, and hashtags in place.
        """
        # Extract tickers ($TSLA, $EVO, $HM-B)
        ticker_pattern = r"\$([A-Z]{1,5}(?:-[A-Z])?)"
        self.mentioned_tickers = list(set(re.findall(ticker_pattern, self.text.upper())))

        # Extract mentions (@username)
        mention_pattern = r"@([A-Za-z0-9_]+)"
        self.mentioned_users = list(set(re.findall(mention_pattern, self.text)))

        # Extract hashtags (#fintwit)
        hashtag_pattern = r"#([A-Za-z0-9_]+)"
        self.hashtags = list(set(re.findall(hashtag_pattern, self.text)))

        # Update flags
        self.has_links = bool(re.search(r"https?://", self.text))


class TweetActionType(str, Enum):
    """Type of stock action mentioned in tweet."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    WATCH = "watch"
    AVOID = "avoid"
    UNKNOWN = "unknown"


class StockMention(BaseModel):
    """A single stock mention within a tweet.

    Attributes:
        stock_name: Full company name.
        ticker: Stock ticker symbol.
        action: Type of recommendation (buy/sell/hold/watch/avoid).
        confidence: Confidence level of the recommendation.
        reasoning: Summary of the argument.
        price_target: Price target if mentioned.
        time_horizon: Investment time horizon.
        quote: Relevant portion of the tweet.
    """

    stock_name: str
    ticker: str | None = None
    action: TweetActionType = TweetActionType.UNKNOWN
    confidence: Literal["high", "medium", "low", "speculative"] = "low"
    reasoning: str | None = None
    price_target: str | None = None
    time_horizon: str | None = None
    quote: str


class TweetAnalysis(BaseModel):
    """LLM-extracted analysis of a tweet.

    Parallels StockRecommendation in extract/models.py.

    Attributes:
        tweet_id: ID of the analyzed tweet.
        source_id: Which source account.
        stock_mentions: List of stock mentions with analysis.
        market_sentiment: Overall market sentiment.
        is_actionable: Whether tweet contains actual recommendation.
        is_speculation: Whether this is speculation vs analysis.
        has_price_target: Whether a price target was mentioned.
        processed_at: When analysis was performed.
        model_used: LLM model used for analysis.
    """

    tweet_id: str
    source_id: str

    # Stock mentions with context
    stock_mentions: list[StockMention] = Field(default_factory=list)

    # Overall sentiment
    market_sentiment: Literal["bullish", "bearish", "neutral", "mixed"] | None = None

    # Metadata
    is_actionable: bool = False
    is_speculation: bool = False
    has_price_target: bool = False

    processed_at: datetime = Field(default_factory=datetime.now)
    model_used: str = "claude-sonnet-4-20250514"


class TwitterCollectionState(BaseModel):
    """Tracks collection progress per source.

    Parallels EpisodeStatus in core/models.py.

    Attributes:
        source_id: ID of the Twitter source.
        last_collected_at: When we last collected from this source.
        last_tweet_id: Most recent tweet ID collected.
        oldest_tweet_id: Oldest tweet ID collected.
        tweet_count: Total tweets collected.
        estimated_total_tweets: Estimated total tweets for account.
        collection_complete: Whether we've reached end of timeline.
        processed_count: Number of tweets processed/analyzed.
        last_processed_at: When we last processed tweets.
        last_error: Last error message if any.
        error_count: Total errors encountered.
        consecutive_errors: Consecutive errors (reset on success).

    Example:
        >>> state = TwitterCollectionState(source_id="vildkatten")
        >>> state.collection_complete
        False
    """

    source_id: str
    last_collected_at: datetime | None = None
    last_tweet_id: str | None = None
    oldest_tweet_id: str | None = None
    tweet_count: int = 0
    estimated_total_tweets: int | None = None
    collection_complete: bool = False
    processed_count: int = 0
    last_processed_at: datetime | None = None
    last_error: str | None = None
    error_count: int = 0
    consecutive_errors: int = 0


class TwitterSourcesFile(BaseModel):
    """Schema for twitter_sources.json file.

    Attributes:
        version: Schema version number.
        updated_at: Last update timestamp.
        sources: List of Twitter sources to follow.
    """

    version: int = 1
    updated_at: datetime = Field(default_factory=datetime.now)
    sources: list[TwitterSource] = Field(default_factory=list)


class TwitterStateFile(BaseModel):
    """Schema for twitter_state.json file.

    Attributes:
        version: Schema version number.
        last_updated: Last update timestamp.
        sources: Dictionary mapping source_id to collection state.
    """

    version: int = 1
    last_updated: datetime = Field(default_factory=datetime.now)
    sources: dict[str, TwitterCollectionState] = Field(default_factory=dict)


# Utility functions for entity extraction


def extract_tickers(text: str) -> list[str]:
    """Extract stock ticker symbols from text.

    Handles: $TSLA, $AAPL, Swedish tickers like $EVO, $HM-B

    Args:
        text: Text to extract tickers from.

    Returns:
        List of unique ticker symbols (without $).

    Example:
        >>> extract_tickers("Buying $TSLA and $AAPL today!")
        ['TSLA', 'AAPL']
    """
    pattern = r"\$([A-Z]{1,5}(?:-[A-Z])?)"
    return list(set(re.findall(pattern, text.upper())))


def extract_mentions(text: str) -> list[str]:
    """Extract @mentions from text.

    Args:
        text: Text to extract mentions from.

    Returns:
        List of unique usernames (without @).

    Example:
        >>> extract_mentions("Thanks @elonmusk for the insight!")
        ['elonmusk']
    """
    pattern = r"@([A-Za-z0-9_]+)"
    return list(set(re.findall(pattern, text)))


def extract_hashtags(text: str) -> list[str]:
    """Extract #hashtags from text.

    Args:
        text: Text to extract hashtags from.

    Returns:
        List of unique hashtags (without #).

    Example:
        >>> extract_hashtags("Great day for #fintwit #stocks")
        ['fintwit', 'stocks']
    """
    pattern = r"#([A-Za-z0-9_]+)"
    return list(set(re.findall(pattern, text)))
