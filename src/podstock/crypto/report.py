"""Crypto sentiment report generation.

This module generates markdown reports for crypto sentiment analysis,
including bias tracking, prediction accuracy, and trend visualization.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from podstock.crypto.aggregator import SentimentAggregator
from podstock.crypto.models import (
    AggregatedSentiment,
    BiasMetrics,
    CryptoSentimentAnalysis,
)
from podstock.crypto.price_tracker import PriceTracker


def generate_crypto_sentiment_report(
    analysis: CryptoSentimentAnalysis,
    include_quotes: bool = True,
) -> str:
    """Generate markdown report for a single analysis.

    Args:
        analysis: CryptoSentimentAnalysis to report on.
        include_quotes: Whether to include quotes.

    Returns:
        Markdown formatted report.
    """
    lines = [
        f"# Crypto Sentiment Analysis",
        "",
        f"**Source:** {analysis.channel_or_podcast}",
        f"**Date:** {analysis.date}",
        f"**Type:** {analysis.source_type}",
    ]

    if analysis.title:
        lines.append(f"**Title:** {analysis.title}")

    lines.extend([
        "",
        f"## Overall Sentiment: {analysis.overall_market_sentiment.value.replace('_', ' ').title()}",
        "",
    ])

    if analysis.summary:
        lines.extend([
            "### Summary",
            "",
            analysis.summary,
            "",
        ])

    if analysis.key_takeaways:
        lines.extend([
            "### Key Takeaways",
            "",
        ])
        for takeaway in analysis.key_takeaways:
            lines.append(f"- {takeaway}")
        lines.append("")

    # Assets discussed
    if analysis.assets_discussed:
        lines.extend([
            "### Assets Discussed",
            "",
            ", ".join(analysis.assets_discussed),
            "",
        ])

    # Detailed mentions
    if analysis.mentions:
        lines.extend([
            "### Detailed Sentiment Analysis",
            "",
        ])

        for mention in analysis.mentions:
            emoji = _get_sentiment_emoji(mention.sentiment.value)
            lines.extend([
                f"#### {mention.asset_symbol} - {emoji} {mention.sentiment.value.replace('_', ' ').title()}",
                "",
                f"**Confidence:** {mention.confidence}",
            ])

            if mention.speaker:
                lines.append(f"**Speaker:** {mention.speaker}")

            if mention.timestamp:
                lines.append(f"**Timestamp:** {mention.timestamp}")

            if include_quotes:
                lines.extend([
                    "",
                    f"> {mention.quote}",
                ])

            lines.extend([
                "",
                f"**Reasoning:** {mention.reasoning}",
            ])

            if mention.price_target:
                lines.append(f"**Price Target:** ${mention.price_target:,.0f} {mention.price_target_currency}")

            if mention.time_horizon:
                lines.append(f"**Time Horizon:** {mention.time_horizon}")

            if mention.mentioned_catalysts:
                lines.append(f"**Catalysts:** {', '.join(mention.mentioned_catalysts)}")

            if mention.risk_factors_mentioned:
                lines.append(f"**Risk Factors:** {', '.join(mention.risk_factors_mentioned)}")

            lines.append("")

    # Metadata
    lines.extend([
        "---",
        "",
        f"*Processed: {analysis.processed_at.strftime('%Y-%m-%d %H:%M')}*",
        f"*Model: {analysis.model_used}*",
        f"*Word Count: {analysis.transcript_word_count:,}*",
    ])

    return "\n".join(lines)


def generate_bias_tracking_report(
    metrics: BiasMetrics,
    aggregated_data: list[AggregatedSentiment] | None = None,
) -> str:
    """Generate markdown report for bias tracking.

    Args:
        metrics: BiasMetrics for the source.
        aggregated_data: Optional aggregated sentiment data.

    Returns:
        Markdown formatted report.
    """
    lines = [
        f"# Bias Tracking Report: {metrics.source_name or metrics.source_id}",
        "",
        f"**Period:** {metrics.period_start.strftime('%Y-%m-%d')} to {metrics.period_end.strftime('%Y-%m-%d')}",
        "",
        "## Overall Metrics",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Overall Bias | {metrics.bias_label} ({metrics.overall_bias:+.2f}) |",
        f"| Consistency | {metrics.consistency:.1%} |",
        f"| BTC Bias | {metrics.btc_bias:+.2f} |",
        f"| Altcoin Bias | {metrics.alt_bias:+.2f} |",
        f"| Trend | {metrics.sentiment_trend.title()} |",
        "",
    ]

    # Interpretation
    lines.extend([
        "## Interpretation",
        "",
    ])

    if metrics.overall_bias > 0.3:
        lines.append(f"This source shows a **bullish bias** ({metrics.overall_bias:+.2f}) in their crypto coverage.")
    elif metrics.overall_bias < -0.3:
        lines.append(f"This source shows a **bearish bias** ({metrics.overall_bias:+.2f}) in their crypto coverage.")
    else:
        lines.append("This source maintains a **relatively neutral stance** in their crypto coverage.")

    if metrics.consistency > 0.7:
        lines.append("Their views are **highly consistent** over time.")
    elif metrics.consistency < 0.4:
        lines.append("Their views **vary significantly** from episode to episode.")

    lines.append("")

    # Most mentioned assets
    if metrics.most_mentioned_assets:
        lines.extend([
            "## Most Discussed Assets",
            "",
        ])
        for i, asset in enumerate(metrics.most_mentioned_assets, 1):
            lines.append(f"{i}. {asset}")
        lines.append("")

    # Prediction accuracy if available
    if metrics.verified_predictions > 0:
        lines.extend([
            "## Prediction Track Record",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Predictions | {metrics.prediction_count} |",
            f"| Verified | {metrics.verified_predictions} |",
            f"| Accuracy | {metrics.accuracy:.1%} |" if metrics.accuracy else "| Accuracy | N/A |",
            "",
        ])

    # Aggregated data visualization
    if aggregated_data:
        lines.extend([
            "## Sentiment Over Time",
            "",
            "| Period | Sentiment | Mentions | Bullish | Bearish |",
            "|--------|-----------|----------|---------|---------|",
        ])

        for agg in aggregated_data[-12:]:  # Last 12 periods
            period_str = agg.period_start.strftime("%Y-%m-%d")
            sentiment_str = f"{agg.sentiment_score:+.2f}"
            lines.append(
                f"| {period_str} | {sentiment_str} | {agg.total_mentions} | {agg.bullish_count} | {agg.bearish_count} |"
            )

        lines.append("")

    # Footer
    lines.extend([
        "---",
        "",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
    ])

    return "\n".join(lines)


def generate_prediction_accuracy_report(
    tracker: PriceTracker,
    source_filter: str | None = None,
) -> str:
    """Generate report on prediction accuracy.

    Args:
        tracker: PriceTracker instance.
        source_filter: Optional source ID to filter by.

    Returns:
        Markdown formatted report.
    """
    stats = tracker.get_accuracy_stats(source_id=source_filter)
    summary = tracker.get_prediction_summary()

    lines = [
        "# Crypto Prediction Accuracy Report",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Predictions | {summary['total_predictions']} |",
        f"| Pending | {summary['pending']} |",
        f"| Due for Verification | {summary['due_for_verification']} |",
        f"| Verified | {summary['verified']} |",
    ]

    if summary['accuracy'] is not None:
        lines.append(f"| Overall Accuracy | {summary['accuracy']:.1%} |")

    lines.append("")

    # Accuracy by asset
    if stats.get("by_asset"):
        lines.extend([
            "## Accuracy by Asset",
            "",
            "| Asset | Correct | Total | Accuracy |",
            "|-------|---------|-------|----------|",
        ])

        for asset, data in sorted(stats["by_asset"].items()):
            acc_str = f"{data['accuracy']:.1%}" if data['accuracy'] else "N/A"
            lines.append(f"| {asset} | {data['correct']} | {data['total']} | {acc_str} |")

        lines.append("")

    # Accuracy by direction
    if stats.get("by_direction"):
        lines.extend([
            "## Accuracy by Direction",
            "",
            "| Direction | Correct | Total | Accuracy |",
            "|-----------|---------|-------|----------|",
        ])

        for direction, data in stats["by_direction"].items():
            acc_str = f"{data['accuracy']:.1%}" if data['accuracy'] else "N/A"
            lines.append(f"| {direction.title()} | {data['correct']} | {data['total']} | {acc_str} |")

        lines.append("")

    # Assets tracked
    if summary.get("assets_tracked"):
        lines.extend([
            "## Assets Tracked",
            "",
            ", ".join(summary["assets_tracked"]),
            "",
        ])

    # Sources tracked
    if summary.get("sources_tracked"):
        lines.extend([
            "## Sources Tracked",
            "",
        ])
        for source in summary["sources_tracked"]:
            lines.append(f"- {source}")
        lines.append("")

    return "\n".join(lines)


def generate_multi_source_comparison(
    aggregator: SentimentAggregator,
    source_ids: list[str],
    asset: str = "BTC",
    days: int = 30,
) -> str:
    """Generate comparison report across multiple sources.

    Args:
        aggregator: SentimentAggregator instance.
        source_ids: List of source IDs to compare.
        asset: Asset to compare sentiment on.
        days: Days to analyze.

    Returns:
        Markdown formatted comparison report.
    """
    lines = [
        f"# {asset} Sentiment Comparison",
        "",
        f"**Period:** Last {days} days",
        f"**Asset:** {asset}",
        "",
        "## Source Comparison",
        "",
        "| Source | Bias | Consistency | Trend |",
        "|--------|------|-------------|-------|",
    ]

    for source_id in source_ids:
        metrics = aggregator.calculate_bias_metrics(source_id, lookback_days=days)
        lines.append(
            f"| {source_id} | {metrics.overall_bias:+.2f} | {metrics.consistency:.1%} | {metrics.sentiment_trend} |"
        )

    lines.append("")

    # Overall market view
    all_analyses = aggregator.load_analyses()
    if all_analyses:
        btc_mentions = []
        for analysis in all_analyses:
            for mention in analysis.mentions:
                if mention.asset_symbol.upper() == asset.upper():
                    btc_mentions.append(mention)

        if btc_mentions:
            avg_score = sum(m.sentiment.score for m in btc_mentions) / len(btc_mentions)
            bullish = sum(1 for m in btc_mentions if m.sentiment.score > 0)
            bearish = sum(1 for m in btc_mentions if m.sentiment.score < 0)

            lines.extend([
                "## Aggregate View",
                "",
                f"- **Average Sentiment:** {avg_score:+.2f}",
                f"- **Total Mentions:** {len(btc_mentions)}",
                f"- **Bullish Mentions:** {bullish}",
                f"- **Bearish Mentions:** {bearish}",
                "",
            ])

    return "\n".join(lines)


def _get_sentiment_emoji(sentiment: str) -> str:
    """Get emoji for sentiment level.

    Args:
        sentiment: Sentiment string.

    Returns:
        Appropriate emoji.
    """
    emoji_map = {
        "very_bullish": "🚀",
        "bullish": "📈",
        "neutral": "➡️",
        "bearish": "📉",
        "very_bearish": "💀",
    }
    return emoji_map.get(sentiment, "❓")


class CryptoReportGenerator:
    """High-level report generator combining all report types.

    Example:
        >>> generator = CryptoReportGenerator(data_dir=Path("data"))
        >>> report = generator.generate_source_report("technicalroundup", days=90)
    """

    def __init__(self, data_dir: Path) -> None:
        """Initialize report generator.

        Args:
            data_dir: Base data directory.
        """
        self.data_dir = data_dir
        self.aggregator = SentimentAggregator(data_dir)
        self.tracker = PriceTracker(data_dir)
        self.reports_dir = data_dir / "reports" / "crypto"

        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_source_report(
        self,
        source_id: str,
        source_name: str = "",
        days: int = 90,
        save: bool = True,
    ) -> str:
        """Generate comprehensive report for a source.

        Args:
            source_id: Source ID.
            source_name: Display name.
            days: Days to analyze.
            save: Whether to save to file.

        Returns:
            Markdown report content.
        """
        # Calculate metrics
        metrics = self.aggregator.calculate_bias_metrics(
            source_id,
            source_name=source_name,
            lookback_days=days,
        )

        # Get aggregated data
        aggregated = self.aggregator.aggregate_by_period(
            "BTC",  # Default to BTC
            period="week",
            lookback_days=days,
        )

        # Generate report
        report = generate_bias_tracking_report(metrics, aggregated)

        if save:
            filename = f"{source_id}-crypto-report-{datetime.now().strftime('%Y%m%d')}.md"
            file_path = self.reports_dir / filename
            file_path.write_text(report, encoding="utf-8")

        return report

    def generate_prediction_report(self, save: bool = True) -> str:
        """Generate prediction accuracy report.

        Args:
            save: Whether to save to file.

        Returns:
            Markdown report content.
        """
        report = generate_prediction_accuracy_report(self.tracker)

        if save:
            filename = f"predictions-{datetime.now().strftime('%Y%m%d')}.md"
            file_path = self.reports_dir / filename
            file_path.write_text(report, encoding="utf-8")

        return report
