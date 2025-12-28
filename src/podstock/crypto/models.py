"""Pydantic data models for crypto sentiment analysis.

This module defines crypto-specific data structures that are separate
from the stock recommendation models, designed for tracking bullish/bearish
sentiment over time and verifying predictions.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class CryptoAsset(str, Enum):
    """Common crypto assets."""

    BTC = "BTC"
    ETH = "ETH"
    SOL = "SOL"
    XRP = "XRP"
    ADA = "ADA"
    DOGE = "DOGE"
    DOT = "DOT"
    AVAX = "AVAX"
    LINK = "LINK"
    MATIC = "MATIC"
    OTHER = "OTHER"


class SentimentLevel(str, Enum):
    """Sentiment classification levels."""

    VERY_BULLISH = "very_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    VERY_BEARISH = "very_bearish"

    @property
    def score(self) -> float:
        """Get numeric score for sentiment (-1 to +1)."""
        scores = {
            SentimentLevel.VERY_BULLISH: 1.0,
            SentimentLevel.BULLISH: 0.5,
            SentimentLevel.NEUTRAL: 0.0,
            SentimentLevel.BEARISH: -0.5,
            SentimentLevel.VERY_BEARISH: -1.0,
        }
        return scores[self]


class CryptoMention(BaseModel):
    """A single crypto mention with sentiment analysis.

    This is the crypto equivalent of StockRecommendation, but designed
    specifically for crypto assets with bullish/bearish sentiment tracking.

    Attributes:
        asset_name: Full name (Bitcoin, Ethereum, etc.).
        asset_symbol: Ticker symbol (BTC, ETH, SOL).
        asset_type: Type of asset (coin, token, stablecoin, etc.).
        sentiment: Sentiment level from very_bullish to very_bearish.
        confidence: Confidence in the sentiment classification.
        speaker: Name of the speaker if identifiable.
        timestamp: Timestamp in transcript (if available).
        quote: Exact quote supporting the sentiment (max 150 words).
        reasoning: Analysis of why this sentiment was assigned.
        price_prediction: Verbal price prediction if made.
        price_target: Numeric price target if specified.
        price_target_currency: Currency for price target.
        time_horizon: Time horizon for prediction.
        market_cap_awareness: Whether speaker showed market cap knowledge.
        mentioned_catalysts: Catalysts mentioned (ETF, halving, etc.).
        risk_factors_mentioned: Risks mentioned.

    Example:
        >>> mention = CryptoMention(
        ...     asset_name="Bitcoin",
        ...     asset_symbol="BTC",
        ...     sentiment=SentimentLevel.VERY_BULLISH,
        ...     confidence="high",
        ...     quote="I think we're going to 150K by end of 2025",
        ...     reasoning="Speaker is accumulating and gives specific target",
        ... )
    """

    # Asset identification
    asset_name: str = Field(..., min_length=1)
    asset_symbol: str = Field(..., min_length=1, max_length=10)
    asset_type: Literal["coin", "token", "stablecoin", "nft", "defi"] = "coin"

    # Sentiment analysis
    sentiment: SentimentLevel
    confidence: Literal["high", "medium", "low", "speculative"]

    # Context
    speaker: str | None = None
    timestamp: str | None = None  # Format: "HH:MM:SS" or "MM:SS"
    quote: str = Field(..., min_length=1, max_length=500)
    reasoning: str = Field(..., min_length=1)

    # Predictions (if made)
    price_prediction: str | None = None  # Verbal description
    price_target: float | None = None  # Numeric value
    price_target_currency: str = "USD"
    time_horizon: str | None = None  # "1 week", "Q1 2025", "end of year", etc.

    # Market context
    market_cap_awareness: bool = False
    mentioned_catalysts: list[str] = Field(default_factory=list)
    risk_factors_mentioned: list[str] = Field(default_factory=list)


class CryptoSentimentAnalysis(BaseModel):
    """Complete crypto sentiment analysis for a video/episode.

    Parallels EpisodeAnalysis in extract/models.py but focused on
    crypto sentiment rather than stock recommendations.

    Attributes:
        source_id: Video or episode ID.
        source_type: Type of source (youtube, podcast, twitter).
        channel_or_podcast: Name of channel/podcast.
        title: Episode/video title.
        date: Publication date (ISO format).
        speakers: List of speakers/hosts.
        main_topics: Main topics discussed (max 5).
        assets_discussed: All crypto assets mentioned.
        mentions: Detailed crypto mentions with sentiment.
        overall_market_sentiment: Overall crypto market sentiment.
        bitcoin_dominance_view: View on BTC dominance trend.
        alt_season_prediction: Whether alt season is predicted.
        summary: 3-5 sentence summary.
        key_takeaways: 3-5 bullet points.
        transcript_word_count: Word count of source transcript.
        has_timestamps: Whether transcript had timestamps.
        processed_at: When analysis was performed.
        model_used: LLM model used.

    Example:
        >>> analysis = CryptoSentimentAnalysis(
        ...     source_id="dQw4w9WgXcQ",
        ...     source_type="youtube",
        ...     channel_or_podcast="Technical Roundup",
        ...     date="2025-01-15",
        ...     overall_market_sentiment=SentimentLevel.BULLISH,
        ...     mentions=[...],
        ... )
    """

    # Source identification
    source_id: str = Field(..., min_length=1)
    source_type: Literal["youtube", "podcast", "twitter"]
    channel_or_podcast: str = Field(..., min_length=1)
    title: str | None = None
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")

    # Participants
    speakers: list[str] = Field(default_factory=list)

    # Content
    main_topics: list[str] = Field(default_factory=list, max_length=5)
    assets_discussed: list[str] = Field(default_factory=list)
    mentions: list[CryptoMention] = Field(default_factory=list)

    # Overall sentiment
    overall_market_sentiment: SentimentLevel
    bitcoin_dominance_view: Literal[
        "increasing", "decreasing", "stable", "not_discussed"
    ] = "not_discussed"
    alt_season_prediction: bool | None = None

    # Summary
    summary: str = Field(default="", min_length=0)
    key_takeaways: list[str] = Field(default_factory=list)

    # Metadata
    transcript_word_count: int = 0
    has_timestamps: bool = False
    processed_at: datetime = Field(default_factory=datetime.now)
    model_used: str = "claude-sonnet-4-20250514"

    def get_sentiment_score(self) -> float:
        """Calculate average sentiment score from all mentions.

        Returns:
            Average sentiment score (-1 to +1).
        """
        if not self.mentions:
            return self.overall_market_sentiment.score

        scores = [m.sentiment.score for m in self.mentions]
        return sum(scores) / len(scores)

    def get_asset_sentiment(self, symbol: str) -> SentimentLevel | None:
        """Get sentiment for a specific asset.

        Args:
            symbol: Asset symbol (BTC, ETH, etc.).

        Returns:
            Most confident sentiment for the asset, or None.
        """
        symbol = symbol.upper()
        relevant = [m for m in self.mentions if m.asset_symbol.upper() == symbol]

        if not relevant:
            return None

        # Return highest confidence one
        confidence_order = ["high", "medium", "low", "speculative"]
        for conf in confidence_order:
            for mention in relevant:
                if mention.confidence == conf:
                    return mention.sentiment

        return relevant[0].sentiment


class PricePrediction(BaseModel):
    """A tracked price prediction for later verification.

    Records predictions made in content so they can be verified
    against actual price movements.

    Attributes:
        prediction_id: Unique ID for this prediction.
        source_id: Source video/episode ID.
        source_type: Type of source.
        source_name: Channel/podcast name.
        asset_symbol: Crypto asset symbol.
        predicted_at: When prediction was made.
        prediction_text: Original prediction text.
        target_price: Numeric target if specified.
        target_currency: Currency for target.
        direction: Predicted direction.
        time_horizon: Time horizon for prediction.
        deadline: When prediction should be verified.
        price_at_prediction: Price when prediction was made.
        verified_at: When prediction was verified.
        actual_price: Actual price at verification.
        prediction_correct: Whether prediction was correct.
        price_change_percent: Percentage price change.
        speaker: Who made the prediction.

    Example:
        >>> prediction = PricePrediction(
        ...     prediction_id="pred_12345",
        ...     source_id="dQw4w9WgXcQ",
        ...     source_type="youtube",
        ...     asset_symbol="BTC",
        ...     direction="up",
        ...     target_price=150000,
        ...     deadline=datetime(2025, 12, 31),
        ... )
    """

    prediction_id: str = Field(..., min_length=1)
    source_id: str = Field(..., min_length=1)
    source_type: Literal["youtube", "podcast", "twitter"]
    source_name: str = Field(default="")
    asset_symbol: str = Field(..., min_length=1)

    # The prediction
    predicted_at: datetime
    prediction_text: str = Field(..., min_length=1)
    target_price: float | None = None
    target_currency: str = "USD"
    direction: Literal["up", "down", "sideways"]
    time_horizon: str | None = None
    deadline: datetime | None = None  # When to verify

    # Price at prediction time
    price_at_prediction: float

    # Verification (filled in later)
    verified_at: datetime | None = None
    actual_price: float | None = None
    prediction_correct: bool | None = None
    price_change_percent: float | None = None

    # Speaker
    speaker: str | None = None

    def is_verifiable(self) -> bool:
        """Check if prediction can be verified.

        Returns:
            True if deadline has passed and not yet verified.
        """
        if self.verified_at is not None:
            return False
        if self.deadline is None:
            return False
        return datetime.now() >= self.deadline


class AggregatedSentiment(BaseModel):
    """Aggregated sentiment over a time period for an asset.

    Used for time-series analysis and bias tracking.

    Attributes:
        asset_symbol: Crypto asset symbol.
        period_start: Start of aggregation period.
        period_end: End of aggregation period.
        total_mentions: Total mentions in period.
        bullish_count: Number of bullish mentions.
        bearish_count: Number of bearish mentions.
        neutral_count: Number of neutral mentions.
        sentiment_score: Average sentiment score (-1 to +1).
        confidence_weighted_score: Confidence-weighted sentiment.
        source_count: Number of unique sources.
        sources: List of source IDs.
        predictions_made: Number of predictions in period.
        predictions_verified: Number of verified predictions.
        prediction_accuracy: Accuracy of verified predictions.

    Example:
        >>> agg = AggregatedSentiment(
        ...     asset_symbol="BTC",
        ...     period_start=datetime(2025, 1, 1),
        ...     period_end=datetime(2025, 1, 31),
        ...     total_mentions=45,
        ...     bullish_count=30,
        ...     bearish_count=5,
        ...     neutral_count=10,
        ...     sentiment_score=0.55,
        ... )
    """

    asset_symbol: str = Field(..., min_length=1)
    period_start: datetime
    period_end: datetime

    # Counts
    total_mentions: int = 0
    bullish_count: int = 0  # very_bullish + bullish
    bearish_count: int = 0  # very_bearish + bearish
    neutral_count: int = 0

    # Weighted sentiment (-1 to +1)
    sentiment_score: float = 0.0
    confidence_weighted_score: float = 0.0

    # Sources
    source_count: int = 0
    sources: list[str] = Field(default_factory=list)

    # Predictions
    predictions_made: int = 0
    predictions_verified: int = 0
    prediction_accuracy: float | None = None

    @property
    def is_bullish(self) -> bool:
        """Check if overall sentiment is bullish."""
        return self.sentiment_score > 0.1

    @property
    def is_bearish(self) -> bool:
        """Check if overall sentiment is bearish."""
        return self.sentiment_score < -0.1

    @property
    def period_days(self) -> int:
        """Get number of days in period."""
        return (self.period_end - self.period_start).days


class BiasMetrics(BaseModel):
    """Bias metrics for a specific source over time.

    Tracks how consistently bullish/bearish a source is.

    Attributes:
        source_id: Source channel/podcast ID.
        source_name: Display name.
        period_start: Start of analysis period.
        period_end: End of analysis period.
        overall_bias: Overall bias score (-1 to +1).
        consistency: How consistent their sentiment is (0 to 1).
        btc_bias: Specific bias toward Bitcoin.
        alt_bias: Bias toward altcoins.
        prediction_count: Total predictions made.
        verified_predictions: Verified predictions.
        accuracy: Prediction accuracy if verified.
        most_mentioned_assets: Top 5 most mentioned assets.
        sentiment_trend: Recent trend (bullish/bearish/stable).

    Example:
        >>> metrics = BiasMetrics(
        ...     source_id="technicalroundup",
        ...     source_name="Technical Roundup",
        ...     overall_bias=0.65,
        ...     consistency=0.8,
        ...     accuracy=0.55,
        ... )
    """

    source_id: str = Field(..., min_length=1)
    source_name: str = Field(default="")
    period_start: datetime
    period_end: datetime

    # Bias scores
    overall_bias: float = Field(ge=-1.0, le=1.0)  # -1 = very bearish, +1 = very bullish
    consistency: float = Field(ge=0.0, le=1.0)  # How consistent over time
    btc_bias: float = Field(default=0.0, ge=-1.0, le=1.0)
    alt_bias: float = Field(default=0.0, ge=-1.0, le=1.0)

    # Predictions
    prediction_count: int = 0
    verified_predictions: int = 0
    accuracy: float | None = None

    # Asset coverage
    most_mentioned_assets: list[str] = Field(default_factory=list)

    # Trend
    sentiment_trend: Literal["bullish", "bearish", "stable"] = "stable"

    @property
    def bias_label(self) -> str:
        """Get human-readable bias label."""
        if self.overall_bias > 0.6:
            return "Very Bullish"
        elif self.overall_bias > 0.2:
            return "Bullish"
        elif self.overall_bias > -0.2:
            return "Neutral"
        elif self.overall_bias > -0.6:
            return "Bearish"
        else:
            return "Very Bearish"
