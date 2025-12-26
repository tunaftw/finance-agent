"""Data models for price tracking and recommendation verification.

This module defines the core data structures for tracking prices at
recommendation time and verifying them against actual price movements.

Models
------
AssetType : Enum
    Type of financial asset (STOCK or CRYPTO).

PriceSnapshot : BaseModel
    A point-in-time price observation with OHLCV data.
    Fields: symbol, price, currency, timestamp, source, open/high/low/volume

TrackedRecommendation : BaseModel
    A recommendation linked to price tracking data.
    Fields: tracking_id, source_type, source_id, source_name, asset_type,
            asset_name, symbol, market, action, speaker, recommendation_date,
            price_target, entry_price, verification_intervals, verifications
    Methods: get_latest_verification(), get_verification_at_interval(),
             is_verified_at(), pending_intervals(), current_return()

VerificationResult : BaseModel
    Price verification at a specific time interval.
    Fields: interval_months, verified_at, price_snapshot, absolute_return,
            percentage_return, direction_correct, target_reached

AccuracyStats : BaseModel
    Aggregated accuracy statistics for recommendations.
    Fields: total_recommendations, verified_recommendations, correct_direction,
            incorrect_direction, direction_accuracy, average/median/best/worst_return
    Properties: hit_rate (human-readable string)

ImportResult : BaseModel
    Result of importing recommendations from extractions.
    Fields: imported, skipped, failed, errors, imported_ids
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    """Type of financial asset."""

    STOCK = "stock"
    CRYPTO = "crypto"


class PriceSnapshot(BaseModel):
    """A point-in-time price observation.

    Attributes:
        symbol: Ticker symbol (e.g., EVO.ST, BTC).
        price: Price value.
        currency: Currency code (SEK, USD).
        timestamp: When the price was recorded.
        source: Data source (yahoo, coingecko).
        open_price: Opening price (optional).
        high_price: High price (optional).
        low_price: Low price (optional).
        volume: Trading volume (optional).

    Example:
        >>> snapshot = PriceSnapshot(
        ...     symbol="EVO.ST",
        ...     price=1234.50,
        ...     currency="SEK",
        ...     timestamp=datetime.now(),
        ...     source="yahoo",
        ... )
    """

    symbol: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    timestamp: datetime
    source: Literal["yahoo", "coingecko"]

    # Optional OHLCV data
    open_price: float | None = None
    high_price: float | None = None
    low_price: float | None = None
    volume: int | None = None


class VerificationResult(BaseModel):
    """Price verification at a specific time interval.

    Captures the price at a certain interval after the recommendation
    and calculates the return.

    Attributes:
        interval_months: Months since recommendation (0 = today).
        verified_at: When verification was performed.
        price_snapshot: The price data at verification.
        absolute_return: Price change in currency units.
        percentage_return: Percentage change.
        direction_correct: Whether price moved as predicted.
        target_reached: Whether price target was reached (if applicable).

    Example:
        >>> result = VerificationResult(
        ...     interval_months=6,
        ...     verified_at=datetime.now(),
        ...     price_snapshot=snapshot,
        ...     absolute_return=150.0,
        ...     percentage_return=12.5,
        ...     direction_correct=True,
        ... )
    """

    interval_months: int = Field(..., ge=0)
    verified_at: datetime
    price_snapshot: PriceSnapshot

    # Calculated returns
    absolute_return: float
    percentage_return: float

    # Accuracy assessment
    direction_correct: bool | None = None
    target_reached: bool | None = None


class TrackedRecommendation(BaseModel):
    """A recommendation linked to price tracking data.

    This is the central model that connects a recommendation from any source
    (podcast, Twitter, YouTube) to its price verification history.

    Attributes:
        tracking_id: Unique identifier for this tracking entry.
        source_type: Type of source (podcast, twitter, youtube).
        source_id: Identifier of the source (episode_id, tweet_id, video_id).
        source_name: Human-readable source name (podcast name, handle).
        asset_type: Whether this is a stock or crypto asset.
        asset_name: Full asset name (e.g., "Evolution Gaming").
        symbol: Ticker symbol (e.g., "EVO.ST").
        market: Market classification (sweden, us, europe).
        action: Recommendation action (buy, sell, hold, watch, avoid).
        speaker: Who made the recommendation.
        recommendation_date: When the recommendation was made.
        price_target: Target price if mentioned.
        price_target_currency: Currency for price target.
        entry_price: Price at time of recommendation.
        verification_intervals: Intervals to verify (in months).
        verifications: List of verification results.
        created_at: When tracking was created.
        updated_at: When tracking was last updated.

    Example:
        >>> rec = TrackedRecommendation(
        ...     tracking_id="fillorkill-2024-01-15-evo",
        ...     source_type="podcast",
        ...     source_id="fillorkill-2024-01-15-abcd",
        ...     source_name="Fill or Kill",
        ...     asset_type=AssetType.STOCK,
        ...     asset_name="Evolution",
        ...     symbol="EVO.ST",
        ...     action="buy",
        ...     recommendation_date=datetime(2024, 1, 15),
        ... )
    """

    tracking_id: str = Field(..., min_length=1)
    source_type: Literal["podcast", "twitter", "youtube"]
    source_id: str = Field(..., min_length=1)
    source_name: str = Field(..., min_length=1)

    # Asset identification
    asset_type: AssetType
    asset_name: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    market: str | None = None

    # Recommendation details
    action: Literal["buy", "sell", "hold", "watch", "avoid"]
    speaker: str | None = None
    recommendation_date: datetime

    # Price targets
    price_target: float | None = None
    price_target_currency: str = "SEK"

    # Entry price (at recommendation time)
    entry_price: PriceSnapshot | None = None

    # Verification schedule
    verification_intervals: list[int] = Field(default_factory=lambda: [1, 3, 6, 12])
    verifications: list[VerificationResult] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def get_latest_verification(self) -> VerificationResult | None:
        """Get the most recent verification result.

        Returns:
            Most recent VerificationResult or None if no verifications.
        """
        if not self.verifications:
            return None
        return max(self.verifications, key=lambda v: v.verified_at)

    def get_verification_at_interval(self, months: int) -> VerificationResult | None:
        """Get verification result for a specific interval.

        Args:
            months: The interval in months to look up.

        Returns:
            VerificationResult for that interval or None.
        """
        for v in self.verifications:
            if v.interval_months == months:
                return v
        return None

    def is_verified_at(self, months: int) -> bool:
        """Check if verified at a specific interval.

        Args:
            months: The interval in months.

        Returns:
            True if verified at that interval.
        """
        return self.get_verification_at_interval(months) is not None

    def pending_intervals(self) -> list[int]:
        """Get intervals that haven't been verified yet.

        Returns:
            List of interval months not yet verified.
        """
        verified = {v.interval_months for v in self.verifications}
        return [i for i in self.verification_intervals if i not in verified]

    def current_return(self) -> float | None:
        """Get the current percentage return if verified today.

        Returns:
            Percentage return or None if no today verification.
        """
        today_result = self.get_verification_at_interval(0)
        if today_result:
            return today_result.percentage_return
        return None


class AccuracyStats(BaseModel):
    """Aggregated accuracy statistics for recommendations.

    Attributes:
        total_recommendations: Total number of recommendations.
        verified_recommendations: Number with at least one verification.
        correct_direction: Number where direction was correct.
        incorrect_direction: Number where direction was wrong.
        direction_accuracy: Percentage of correct directions.
        average_return: Average percentage return.
        median_return: Median percentage return.
        best_return: Best percentage return.
        worst_return: Worst percentage return.
        by_action: Breakdown by action type.
        by_speaker: Breakdown by speaker.
        by_source: Breakdown by source.

    Example:
        >>> stats = AccuracyStats(
        ...     total_recommendations=100,
        ...     verified_recommendations=80,
        ...     correct_direction=52,
        ...     incorrect_direction=28,
        ...     direction_accuracy=0.65,
        ...     average_return=8.5,
        ... )
    """

    total_recommendations: int = 0
    verified_recommendations: int = 0
    correct_direction: int = 0
    incorrect_direction: int = 0
    direction_accuracy: float | None = None

    # Return statistics
    average_return: float | None = None
    median_return: float | None = None
    best_return: float | None = None
    worst_return: float | None = None

    # Breakdowns
    by_action: dict[str, "AccuracyStats"] = Field(default_factory=dict)
    by_speaker: dict[str, "AccuracyStats"] = Field(default_factory=dict)
    by_source: dict[str, "AccuracyStats"] = Field(default_factory=dict)

    @property
    def hit_rate(self) -> str:
        """Get human-readable hit rate.

        Returns:
            Hit rate as "X/Y (Z%)" format.
        """
        if self.direction_accuracy is None:
            return "N/A"
        return (
            f"{self.correct_direction}/{self.verified_recommendations} "
            f"({self.direction_accuracy * 100:.1f}%)"
        )


class ImportResult(BaseModel):
    """Result of importing recommendations from extractions.

    Attributes:
        imported: Number of successfully imported recommendations.
        skipped: Number skipped (already exists or filtered out).
        failed: Number that failed to import (missing ticker, price error).
        errors: List of error messages for failed imports.
        imported_ids: List of tracking IDs for imported recommendations.

    Example:
        >>> result = ImportResult(imported=25, skipped=5, failed=2)
        >>> print(f"Imported {result.imported} recommendations")
    """

    imported: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = Field(default_factory=list)
    imported_ids: list[str] = Field(default_factory=list)
