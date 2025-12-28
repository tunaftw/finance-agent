"""Generate markdown reports from Twitter analysis.

This module creates readable reports from TweetAnalysis data,
summarizing stock mentions, signals, and sentiment.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from podstock.twitter.models import TweetActionType, TweetAnalysis


def generate_twitter_report(
    analyses: list[TweetAnalysis],
    source_id: str,
    include_raw_quotes: bool = True,
) -> str:
    """Generate a markdown report from tweet analyses.

    Args:
        analyses: List of TweetAnalysis objects.
        source_id: Twitter source identifier.
        include_raw_quotes: Whether to include tweet quotes.

    Returns:
        Markdown formatted report.
    """
    lines: list[str] = []

    # Header
    lines.append(f"# Twitter-analys: @{source_id}")
    lines.append(f"*Genererad: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append("")

    # Summary stats
    total_mentions = sum(len(a.stock_mentions) for a in analyses)
    actionable = sum(1 for a in analyses if a.is_actionable)

    # Count by action
    action_counts: dict[str, int] = defaultdict(int)
    for analysis in analyses:
        for mention in analysis.stock_mentions:
            action_counts[mention.action.value] += 1

    # Count by ticker
    ticker_mentions: dict[str, list[dict]] = defaultdict(list)
    for analysis in analyses:
        for mention in analysis.stock_mentions:
            ticker = mention.ticker or mention.stock_name
            ticker_mentions[ticker].append({
                "analysis": analysis,
                "mention": mention,
            })

    lines.append("## Sammanfattning")
    lines.append("")
    lines.append(f"- **Analyserade tweets:** {len(analyses)}")
    lines.append(f"- **Aktie-omnämnanden:** {total_mentions}")
    lines.append(f"- **Actionable signals:** {actionable}")
    lines.append(f"- **Unika tickers:** {len(ticker_mentions)}")
    lines.append("")

    # Action breakdown
    if action_counts:
        lines.append("### Signaler per typ")
        lines.append("")
        lines.append("| Signal | Antal |")
        lines.append("|--------|-------|")
        for action in ["buy", "sell", "hold", "watch", "avoid", "unknown"]:
            if action in action_counts:
                emoji = _action_emoji(action)
                lines.append(f"| {emoji} {action.upper()} | {action_counts[action]} |")
        lines.append("")

    # Per ticker analysis
    lines.append("## Analys per aktie")
    lines.append("")

    # Sort by number of mentions
    sorted_tickers = sorted(
        ticker_mentions.items(),
        key=lambda x: len(x[1]),
        reverse=True,
    )

    for ticker, mentions in sorted_tickers:
        lines.append(f"### {ticker}")
        lines.append("")
        lines.append(f"*{len(mentions)} omnämnanden*")
        lines.append("")

        for item in mentions:
            analysis = item["analysis"]
            mention = item["mention"]

            # Date and action
            emoji = _action_emoji(mention.action.value)
            date = analysis.processed_at.strftime("%Y-%m-%d") if analysis.processed_at else "Unknown"
            confidence = mention.confidence or "?"

            lines.append(f"**{date}** - {emoji} {mention.action.value.upper()} ({confidence})")

            if mention.reasoning:
                lines.append(f"> {mention.reasoning}")

            if include_raw_quotes and mention.quote:
                lines.append(f"")
                lines.append(f"*\"{mention.quote[:200]}{'...' if len(mention.quote) > 200 else ''}\"*")

            lines.append("")

    # Timeline
    lines.append("## Tidslinje")
    lines.append("")

    # Sort analyses by date
    sorted_analyses = sorted(
        [a for a in analyses if a.stock_mentions],
        key=lambda a: a.processed_at or datetime.min,
        reverse=True,
    )

    for analysis in sorted_analyses[:20]:  # Last 20
        date = analysis.processed_at.strftime("%Y-%m-%d") if analysis.processed_at else "?"
        sentiment = analysis.market_sentiment or "?"

        for mention in analysis.stock_mentions:
            emoji = _action_emoji(mention.action.value)
            ticker = mention.ticker or mention.stock_name
            lines.append(
                f"- **{date}** | {emoji} {ticker} | {mention.action.value} | Sentiment: {sentiment}"
            )

    lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Analyserat med Claude. Källa: @{source_id}*")

    return "\n".join(lines)


def save_twitter_report(
    analyses: list[TweetAnalysis],
    output_dir: Path,
    source_id: str,
) -> Path:
    """Save a Twitter analysis report to file.

    Args:
        analyses: List of analyses.
        output_dir: Directory to save to.
        source_id: Source identifier.

    Returns:
        Path to saved report.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = generate_twitter_report(analyses, source_id)

    filename = f"{source_id}-twitter-rapport-{datetime.now().strftime('%Y%m%d')}.md"
    output_path = output_dir / filename

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    return output_path


def _action_emoji(action: str) -> str:
    """Get emoji for action type."""
    return {
        "buy": "🟢",
        "sell": "🔴",
        "hold": "🟡",
        "watch": "👀",
        "avoid": "⛔",
        "unknown": "❓",
    }.get(action.lower(), "❓")
