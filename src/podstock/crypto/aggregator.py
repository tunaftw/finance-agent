"""Crypto sentiment aggregation and time-series analysis.

This module provides functionality for aggregating sentiment data
over time periods and calculating bias metrics.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from podstock.crypto.models import (
    AggregatedSentiment,
    BiasMetrics,
    CryptoSentimentAnalysis,
    SentimentLevel,
)


class SentimentAggregator:
    """Aggregates crypto sentiment data for time-series analysis.

    Provides methods for:
    - Aggregating sentiment by time period (day/week/month)
    - Calculating bias metrics for sources
    - Tracking sentiment trends over time

    Example:
        >>> aggregator = SentimentAggregator(data_dir=Path("data"))
        >>> weekly = aggregator.aggregate_by_period("BTC", period="week")
        >>> for agg in weekly:
        ...     print(f"{agg.period_start}: {agg.sentiment_score:.2f}")
    """

    def __init__(self, data_dir: Path) -> None:
        """Initialize aggregator.

        Args:
            data_dir: Base data directory.
        """
        self.data_dir = data_dir
        self.crypto_dir = data_dir / "crypto"
        self.analyses_dir = self.crypto_dir / "analyses"
        self.aggregated_dir = self.crypto_dir / "aggregated"

        # Create directories
        self.analyses_dir.mkdir(parents=True, exist_ok=True)
        self.aggregated_dir.mkdir(parents=True, exist_ok=True)

    def load_analyses(
        self,
        source_type: str | None = None,
        source_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[CryptoSentimentAnalysis]:
        """Load analyses from disk with optional filters.

        Args:
            source_type: Filter by source type (youtube, podcast, twitter).
            source_id: Filter by specific source ID.
            since: Only analyses after this date.
            until: Only analyses before this date.

        Returns:
            List of matching analyses.
        """
        analyses = []

        # Look in source type subdirectories
        search_dirs = []
        if source_type:
            type_dir = self.analyses_dir / source_type
            if type_dir.exists():
                search_dirs.append(type_dir)
        else:
            for subdir in self.analyses_dir.iterdir():
                if subdir.is_dir():
                    search_dirs.append(subdir)

        for search_dir in search_dirs:
            for json_file in search_dir.glob("*.json"):
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                    analysis = CryptoSentimentAnalysis.model_validate(data)

                    # Apply filters
                    if source_id and analysis.source_id != source_id:
                        continue

                    analysis_date = datetime.strptime(analysis.date, "%Y-%m-%d")
                    if since and analysis_date < since:
                        continue
                    if until and analysis_date > until:
                        continue

                    analyses.append(analysis)

                except (json.JSONDecodeError, ValueError):
                    continue

        # Sort by date
        analyses.sort(key=lambda a: a.date)
        return analyses

    def save_analysis(self, analysis: CryptoSentimentAnalysis) -> Path:
        """Save an analysis to disk.

        Args:
            analysis: Analysis to save.

        Returns:
            Path to saved file.
        """
        type_dir = self.analyses_dir / analysis.source_type
        type_dir.mkdir(parents=True, exist_ok=True)

        file_path = type_dir / f"{analysis.source_id}.json"
        file_path.write_text(
            analysis.model_dump_json(indent=2),
            encoding="utf-8",
        )

        return file_path

    def aggregate_by_period(
        self,
        asset: str,
        period: Literal["day", "week", "month"] = "week",
        lookback_days: int = 180,
        source_type: str | None = None,
    ) -> list[AggregatedSentiment]:
        """Aggregate sentiment for an asset by time period.

        Args:
            asset: Crypto symbol (BTC, ETH, etc.).
            period: Aggregation period.
            lookback_days: How far back to look.
            source_type: Filter by source type.

        Returns:
            List of aggregated sentiment by period.
        """
        since = datetime.now() - timedelta(days=lookback_days)
        analyses = self.load_analyses(source_type=source_type, since=since)

        # Group mentions by period
        period_data: dict[str, list] = defaultdict(list)

        for analysis in analyses:
            analysis_date = datetime.strptime(analysis.date, "%Y-%m-%d")
            period_key = self._get_period_key(analysis_date, period)

            for mention in analysis.mentions:
                if mention.asset_symbol.upper() == asset.upper():
                    period_data[period_key].append({
                        "mention": mention,
                        "source_id": analysis.source_id,
                    })

        # Aggregate each period
        aggregated = []
        for period_key, mentions_data in sorted(period_data.items()):
            start, end = self._parse_period_key(period_key, period)

            # Count sentiments
            bullish_count = sum(
                1 for m in mentions_data
                if m["mention"].sentiment in [SentimentLevel.BULLISH, SentimentLevel.VERY_BULLISH]
            )
            bearish_count = sum(
                1 for m in mentions_data
                if m["mention"].sentiment in [SentimentLevel.BEARISH, SentimentLevel.VERY_BEARISH]
            )
            neutral_count = sum(
                1 for m in mentions_data
                if m["mention"].sentiment == SentimentLevel.NEUTRAL
            )

            # Calculate sentiment scores
            scores = [m["mention"].sentiment.score for m in mentions_data]
            avg_score = sum(scores) / len(scores) if scores else 0.0

            # Confidence-weighted score
            confidence_weights = {
                "high": 1.0,
                "medium": 0.7,
                "low": 0.4,
                "speculative": 0.2,
            }
            weighted_scores = [
                m["mention"].sentiment.score * confidence_weights.get(m["mention"].confidence, 0.5)
                for m in mentions_data
            ]
            weighted_avg = sum(weighted_scores) / len(weighted_scores) if weighted_scores else 0.0

            # Unique sources
            sources = list(set(m["source_id"] for m in mentions_data))

            agg = AggregatedSentiment(
                asset_symbol=asset.upper(),
                period_start=start,
                period_end=end,
                total_mentions=len(mentions_data),
                bullish_count=bullish_count,
                bearish_count=bearish_count,
                neutral_count=neutral_count,
                sentiment_score=avg_score,
                confidence_weighted_score=weighted_avg,
                source_count=len(sources),
                sources=sources,
            )

            aggregated.append(agg)

        return aggregated

    def _get_period_key(self, date: datetime, period: str) -> str:
        """Get period key for a date.

        Args:
            date: Date to get key for.
            period: Period type (day/week/month).

        Returns:
            Period key string.
        """
        if period == "day":
            return date.strftime("%Y-%m-%d")
        elif period == "week":
            # ISO week
            return date.strftime("%Y-W%W")
        else:  # month
            return date.strftime("%Y-%m")

    def _parse_period_key(
        self,
        key: str,
        period: str,
    ) -> tuple[datetime, datetime]:
        """Parse period key to start/end dates.

        Args:
            key: Period key.
            period: Period type.

        Returns:
            Tuple of (start_date, end_date).
        """
        if period == "day":
            start = datetime.strptime(key, "%Y-%m-%d")
            end = start + timedelta(days=1)
        elif period == "week":
            # Parse ISO week
            year, week = key.split("-W")
            start = datetime.strptime(f"{year} {week} 1", "%Y %W %w")
            end = start + timedelta(days=7)
        else:  # month
            start = datetime.strptime(key + "-01", "%Y-%m-%d")
            # End of month
            if start.month == 12:
                end = datetime(start.year + 1, 1, 1)
            else:
                end = datetime(start.year, start.month + 1, 1)

        return start, end

    def calculate_bias_metrics(
        self,
        source_id: str,
        source_name: str = "",
        lookback_days: int = 90,
    ) -> BiasMetrics:
        """Calculate bias metrics for a specific source.

        Args:
            source_id: Source ID to analyze.
            source_name: Display name for source.
            lookback_days: Days to look back.

        Returns:
            BiasMetrics for the source.
        """
        since = datetime.now() - timedelta(days=lookback_days)
        analyses = self.load_analyses(source_id=source_id, since=since)

        if not analyses:
            return BiasMetrics(
                source_id=source_id,
                source_name=source_name,
                period_start=since,
                period_end=datetime.now(),
                overall_bias=0.0,
                consistency=0.0,
            )

        # Collect all mentions
        all_mentions = []
        btc_mentions = []
        alt_mentions = []

        for analysis in analyses:
            for mention in analysis.mentions:
                all_mentions.append(mention)
                if mention.asset_symbol.upper() == "BTC":
                    btc_mentions.append(mention)
                else:
                    alt_mentions.append(mention)

        # Calculate overall bias
        scores = [m.sentiment.score for m in all_mentions]
        overall_bias = sum(scores) / len(scores) if scores else 0.0

        # Calculate BTC bias
        btc_scores = [m.sentiment.score for m in btc_mentions]
        btc_bias = sum(btc_scores) / len(btc_scores) if btc_scores else 0.0

        # Calculate alt bias
        alt_scores = [m.sentiment.score for m in alt_mentions]
        alt_bias = sum(alt_scores) / len(alt_scores) if alt_scores else 0.0

        # Calculate consistency (low variance = high consistency)
        if len(scores) > 1:
            mean = overall_bias
            variance = sum((s - mean) ** 2 for s in scores) / len(scores)
            # Convert variance to consistency (0-1 scale)
            # Max variance for range [-1, 1] is 1
            consistency = max(0, 1 - variance)
        else:
            consistency = 1.0

        # Get most mentioned assets
        asset_counts: dict[str, int] = defaultdict(int)
        for mention in all_mentions:
            asset_counts[mention.asset_symbol.upper()] += 1
        most_mentioned = sorted(
            asset_counts.keys(),
            key=lambda x: asset_counts[x],
            reverse=True,
        )[:5]

        # Determine trend (compare recent to older)
        if len(analyses) >= 2:
            mid = len(analyses) // 2
            older_analyses = analyses[:mid]
            newer_analyses = analyses[mid:]

            older_scores = []
            for a in older_analyses:
                older_scores.extend(m.sentiment.score for m in a.mentions)

            newer_scores = []
            for a in newer_analyses:
                newer_scores.extend(m.sentiment.score for m in a.mentions)

            older_avg = sum(older_scores) / len(older_scores) if older_scores else 0
            newer_avg = sum(newer_scores) / len(newer_scores) if newer_scores else 0

            if newer_avg > older_avg + 0.1:
                trend = "bullish"
            elif newer_avg < older_avg - 0.1:
                trend = "bearish"
            else:
                trend = "stable"
        else:
            trend = "stable"

        return BiasMetrics(
            source_id=source_id,
            source_name=source_name or source_id,
            period_start=since,
            period_end=datetime.now(),
            overall_bias=overall_bias,
            consistency=consistency,
            btc_bias=btc_bias,
            alt_bias=alt_bias,
            most_mentioned_assets=most_mentioned,
            sentiment_trend=trend,
        )

    def get_trend_data(
        self,
        asset: str,
        days: int = 30,
    ) -> dict:
        """Get sentiment trend data for visualization.

        Args:
            asset: Crypto symbol.
            days: Number of days to analyze.

        Returns:
            Dictionary with trend data.
        """
        weekly = self.aggregate_by_period(asset, period="week", lookback_days=days)

        return {
            "asset": asset.upper(),
            "period_days": days,
            "data_points": len(weekly),
            "periods": [
                {
                    "start": agg.period_start.isoformat(),
                    "end": agg.period_end.isoformat(),
                    "sentiment_score": agg.sentiment_score,
                    "mentions": agg.total_mentions,
                    "bullish": agg.bullish_count,
                    "bearish": agg.bearish_count,
                }
                for agg in weekly
            ],
            "average_sentiment": (
                sum(a.sentiment_score for a in weekly) / len(weekly)
                if weekly else 0
            ),
            "total_mentions": sum(a.total_mentions for a in weekly),
        }

    def save_aggregated_data(
        self,
        aggregated: list[AggregatedSentiment],
        asset: str,
        period: str,
    ) -> Path:
        """Save aggregated data to disk.

        Args:
            aggregated: List of aggregated sentiment.
            asset: Asset symbol.
            period: Period type.

        Returns:
            Path to saved file.
        """
        filename = f"{asset.lower()}_{period}.json"
        file_path = self.aggregated_dir / filename

        data = {
            "asset": asset.upper(),
            "period": period,
            "generated_at": datetime.now().isoformat(),
            "data": [agg.model_dump() for agg in aggregated],
        }

        file_path.write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8",
        )

        return file_path
