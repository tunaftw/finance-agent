"""Markdown report generation for PodStock.

This module generates readable Markdown reports from recommendations.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from podstock.core.models import ConfidenceLevel, Recommendation


@dataclass
class ReportStats:
    """Statistics for a recommendations report.

    Attributes:
        total_recommendations: Total number of recommendations.
        by_podcast: Count per podcast.
        by_company: Count per company.
        by_confidence: Count per confidence level.
        date_range: Tuple of (earliest, latest) dates.
    """

    total_recommendations: int
    by_podcast: dict[str, int]
    by_company: dict[str, int]
    by_confidence: dict[str, int]
    date_range: tuple[datetime | None, datetime | None]


def calculate_stats(recommendations: list[Recommendation]) -> ReportStats:
    """Calculate statistics from recommendations.

    Args:
        recommendations: List of Recommendation objects.

    Returns:
        ReportStats with aggregated data.

    Example:
        >>> stats = calculate_stats(recommendations)
        >>> stats.total_recommendations
        5
    """
    by_podcast: dict[str, int] = defaultdict(int)
    by_company: dict[str, int] = defaultdict(int)
    by_confidence: dict[str, int] = defaultdict(int)

    earliest: datetime | None = None
    latest: datetime | None = None

    for rec in recommendations:
        # Extract podcast_id from episode_id (e.g., "bp-2024-12-18-a1b2" -> "bp")
        # Actually, we have episode_id, need to track by podcast somehow
        # For now, use first part of episode_id
        parts = rec.episode_id.split("-")
        podcast_id = parts[0] if parts else "unknown"
        by_podcast[podcast_id] += 1

        by_company[rec.company_name] += 1
        by_confidence[rec.confidence.value] += 1

        if earliest is None or rec.extracted_at < earliest:
            earliest = rec.extracted_at
        if latest is None or rec.extracted_at > latest:
            latest = rec.extracted_at

    return ReportStats(
        total_recommendations=len(recommendations),
        by_podcast=dict(by_podcast),
        by_company=dict(by_company),
        by_confidence=dict(by_confidence),
        date_range=(earliest, latest),
    )


def _format_confidence_badge(confidence: ConfidenceLevel) -> str:
    """Format confidence level as emoji badge."""
    badges = {
        ConfidenceLevel.HIGH: "🟢 High",
        ConfidenceLevel.MEDIUM: "🟡 Medium",
        ConfidenceLevel.LOW: "🔴 Low",
    }
    return badges.get(confidence, "⚪ Unknown")


def _group_by_podcast(
    recommendations: list[Recommendation],
) -> dict[str, list[Recommendation]]:
    """Group recommendations by podcast ID."""
    groups: dict[str, list[Recommendation]] = defaultdict(list)

    for rec in recommendations:
        # Extract podcast from episode_id
        # Assuming episode_id format: "{podcast_id}-{date}-{hash}"
        parts = rec.episode_id.rsplit("-", 2)
        podcast_id = parts[0] if len(parts) >= 3 else rec.episode_id.split("-")[0]
        groups[podcast_id].append(rec)

    return dict(groups)


def generate_report(
    recommendations: list[Recommendation],
    *,
    title: str = "PodStock Recommendations Report",
    include_stats: bool = True,
    group_by_podcast: bool = True,
) -> str:
    """Generate a Markdown report from recommendations.

    Args:
        recommendations: List of Recommendation objects.
        title: Report title.
        include_stats: Whether to include statistics section.
        group_by_podcast: Whether to group by podcast.

    Returns:
        Markdown formatted report string.

    Example:
        >>> report = generate_report(recommendations)
        >>> "# PodStock" in report
        True
    """
    lines: list[str] = []

    # Header
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append("")

    if not recommendations:
        lines.append("No recommendations found.")
        return "\n".join(lines)

    # Statistics
    if include_stats:
        stats = calculate_stats(recommendations)
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total recommendations:** {stats.total_recommendations}")
        lines.append(f"- **Companies mentioned:** {len(stats.by_company)}")
        lines.append(f"- **Podcasts:** {len(stats.by_podcast)}")
        lines.append("")

        # Confidence breakdown
        lines.append("### Confidence Breakdown")
        lines.append("")
        lines.append("| Level | Count |")
        lines.append("|-------|-------|")
        for level in ["high", "medium", "low"]:
            count = stats.by_confidence.get(level, 0)
            lines.append(f"| {level.capitalize()} | {count} |")
        lines.append("")

        # Top companies
        if stats.by_company:
            lines.append("### Most Mentioned Companies")
            lines.append("")
            sorted_companies = sorted(
                stats.by_company.items(), key=lambda x: x[1], reverse=True
            )[:10]
            for company, count in sorted_companies:
                lines.append(f"- **{company}**: {count} mentions")
            lines.append("")

    # Recommendations
    lines.append("---")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")

    if group_by_podcast:
        grouped = _group_by_podcast(recommendations)

        for podcast_id, podcast_recs in sorted(grouped.items()):
            lines.append(f"### {podcast_id.upper()}")
            lines.append("")

            # Sort by date (from episode_id)
            podcast_recs.sort(key=lambda r: r.episode_id, reverse=True)

            for rec in podcast_recs:
                lines.extend(_format_recommendation(rec))
                lines.append("")
    else:
        # Sort by extracted_at
        sorted_recs = sorted(recommendations, key=lambda r: r.extracted_at, reverse=True)

        for rec in sorted_recs:
            lines.extend(_format_recommendation(rec))
            lines.append("")

    return "\n".join(lines)


def _format_recommendation(rec: Recommendation) -> list[str]:
    """Format a single recommendation as Markdown."""
    lines: list[str] = []

    # Company header with ticker
    header = f"#### {rec.company_name}"
    if rec.ticker:
        header += f" ({rec.ticker})"
    lines.append(header)
    lines.append("")

    # Metadata
    confidence_badge = _format_confidence_badge(rec.confidence)
    lines.append(f"**Confidence:** {confidence_badge}")

    if rec.host:
        lines.append(f"**Host:** {rec.host}")

    if rec.time_horizon:
        lines.append(f"**Time Horizon:** {rec.time_horizon}")

    if rec.market:
        lines.append(f"**Market:** {rec.market}")

    lines.append(f"**Episode:** {rec.episode_id}")
    lines.append("")

    # Quote
    lines.append(f"> {rec.quote}")
    lines.append("")

    # Context and reasoning
    lines.append(f"**Context:** {rec.context}")
    lines.append("")
    lines.append(f"**Reasoning:** {rec.reasoning}")

    return lines


def save_report(
    report: str,
    output_path: Path,
) -> Path:
    """Save report to file.

    Args:
        report: Markdown report string.
        output_path: Path to save report.

    Returns:
        Path to saved file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write
    temp_path = output_path.with_suffix(".tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(report)

        temp_path.replace(output_path)
    except OSError:
        if temp_path.exists():
            temp_path.unlink()
        raise

    return output_path


def generate_and_save_report(
    recommendations: list[Recommendation],
    reports_dir: Path,
    *,
    filename: str | None = None,
) -> Path:
    """Generate and save a report.

    Args:
        recommendations: List of Recommendation objects.
        reports_dir: Directory to save report.
        filename: Optional filename (default: report_{date}.md).

    Returns:
        Path to saved report.

    Example:
        >>> path = generate_and_save_report(recommendations, Path("reports"))
        >>> path.exists()
        True
    """
    report = generate_report(recommendations)

    if filename is None:
        filename = f"report_{datetime.now().strftime('%Y-%m-%d')}.md"

    output_path = reports_dir / filename

    return save_report(report, output_path)
