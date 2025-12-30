"""Evolution tracking across multiple filings.

This module synthesizes analysis from multiple filings to track:
- Promise delivery and CEO credibility
- Tone trajectory over time
- Financial trends (margin, growth, debt)
- Guidance accuracy
- Theme evolution

The output is a FilingEvolution model that can be used for:
- Investment thesis generation
- Dashboard visualization
- CEO credibility scoring
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from podstock.filings.models import (
    CEOLetterTone,
    ConfidenceLevel,
    EvolutionSignals,
    FilingEvolution,
    FilingType,
    FinancialTrend,
    FinancialTrendPoint,
    GuidanceAccuracyRecord,
    PromiseStatus,
    ThemeEvolution,
    ToneDataPoint,
    TrackedPromise,
    WatchItem,
)


def load_analyses(company_id: str, data_dir: Path) -> list[dict]:
    """Load all analysis JSON files for a company.

    Args:
        company_id: Company identifier (e.g., "getinge")
        data_dir: Base data directory (e.g., Path("data"))

    Returns:
        List of analysis dicts, sorted by period (oldest first)
    """
    analysis_dir = data_dir / "filings" / "analysis" / company_id
    if not analysis_dir.exists():
        return []

    analyses = []
    for json_file in analysis_dir.glob("*.json"):
        if json_file.name == "evolution.json":
            continue  # Skip the evolution output file

        with open(json_file, encoding="utf-8") as f:
            analysis = json.load(f)
            analyses.append(analysis)

    # Sort by period: annual reports first within a year, then quarters
    def sort_key(a: dict) -> tuple:
        year = a.get("fiscal_year", 0)
        quarter = a.get("fiscal_quarter") or 0
        filing_type = a.get("filing_type", "")
        # Annual = 0, Q1=1, Q2=2, Q3=3, Q4=4
        type_order = 0 if filing_type == "annual" else quarter
        return (year, type_order)

    return sorted(analyses, key=sort_key)


def get_period_label(analysis: dict) -> str:
    """Generate a human-readable period label.

    Examples: "Annual 2024", "Q2 2025", "Q3 2025"
    """
    year = analysis.get("fiscal_year", 0)
    quarter = analysis.get("fiscal_quarter")
    filing_type = analysis.get("filing_type", "")

    if filing_type == "annual" or quarter is None:
        return f"Annual {year}"
    return f"Q{quarter} {year}"


def track_promises(analyses: list[dict]) -> list[TrackedPromise]:
    """Extract and track promises across filings.

    Identifies promises made in CEO letters and tracks their status
    across subsequent filings.

    Args:
        analyses: List of filing analyses, sorted chronologically

    Returns:
        List of TrackedPromise objects with status updates
    """
    tracked: dict[str, TrackedPromise] = {}  # key = normalized promise text

    for analysis in analyses:
        filing_id = analysis.get("filing_id", "unknown")
        ceo_letter = analysis.get("ceo_letter", {})
        promises = ceo_letter.get("promises", [])

        for p in promises:
            statement = p.get("statement", "")
            if not statement:
                continue

            # Create a normalized key for matching
            # Simple normalization: lowercase, strip punctuation
            key = statement.lower().strip()
            key = "".join(c for c in key if c.isalnum() or c.isspace())
            key = " ".join(key.split())[:100]  # First 100 chars

            metric = p.get("metric", "")
            target = p.get("target", "")

            if key not in tracked:
                # New promise
                tracked[key] = TrackedPromise(
                    promise=statement,
                    metric=metric if metric else None,
                    target=target if target else None,
                    made_in=filing_id,
                    current_status=PromiseStatus.ON_TRACK,
                    mentions=[filing_id],
                )
            else:
                # Update existing promise
                existing = tracked[key]
                if filing_id not in existing.mentions:
                    existing.mentions.append(filing_id)

    # Update promise statuses based on evidence
    # Try to match with financial data and guidance updates
    for key, promise in tracked.items():
        evidence, status = _evaluate_promise_evidence(promise, analyses)
        promise.evidence = evidence
        promise.current_status = status

    return list(tracked.values())


def _evaluate_promise_evidence(promise: TrackedPromise, analyses: list[dict]) -> tuple[str, PromiseStatus]:
    """Evaluate promise status and build evidence string.

    Args:
        promise: The promise to evaluate
        analyses: All filing analyses

    Returns:
        Tuple of (evidence_string, status)
    """
    metric = promise.metric or ""
    target = promise.target or ""

    # Try to find quantified updates for this metric
    for analysis in reversed(analyses):  # Check most recent first
        # Check guidance updates
        guidance = analysis.get("guidance", {}) or {}
        targets = guidance.get("targets", []) or []
        period = get_period_label(analysis)

        for t in targets:
            t_metric = t.get("metric", "").lower()
            t_value = t.get("value", "")
            vs_previous = t.get("vs_previous", "")

            # Try to match metric names
            if metric.lower() in t_metric or t_metric in metric.lower():
                if vs_previous:
                    return f"{t_value} ({vs_previous}) - {period}", PromiseStatus.ON_TRACK
                elif t_value:
                    return f"Target: {t_value} - {period}", PromiseStatus.ON_TRACK

        # Check financial metrics for relevant data
        metrics = analysis.get("financial_metrics", {}) or {}
        period_data = analysis.get("period_data", {}) or {}

        # Match common metric types
        if "growth" in metric.lower() or "organic" in metric.lower():
            growth = metrics.get("revenue_growth_organic") or period_data.get("organic_growth")
            if growth is not None:
                growth_pct = growth * 100
                return f"Organic growth: {growth_pct:.1f}% in {period}", PromiseStatus.ON_TRACK

        if "margin" in metric.lower() or "ebita" in metric.lower():
            margin = metrics.get("ebita_margin_adjusted") or period_data.get("ebita_margin_adjusted")
            if margin is not None:
                margin_pct = margin * 100
                return f"EBITA margin: {margin_pct:.1f}% in {period}", PromiseStatus.ON_TRACK

        if "eps" in metric.lower() or "earnings" in metric.lower():
            eps = metrics.get("eps_adjusted") or metrics.get("eps")
            if eps is not None:
                return f"EPS: {eps:.2f} SEK in {period}", PromiseStatus.ON_TRACK

        if "debt" in metric.lower() or "leverage" in metric.lower():
            leverage = metrics.get("net_debt_to_ebitda")
            if leverage is not None:
                return f"Net debt/EBITDA: {leverage:.1f}x in {period}", PromiseStatus.ON_TRACK

    # Fallback to mention-based evidence
    num_mentions = len(promise.mentions)
    if num_mentions >= 3:
        latest = promise.mentions[-1]
        return f"Reiterated in {num_mentions} filings (latest: {latest})", PromiseStatus.ON_TRACK
    elif num_mentions == 2:
        return f"Mentioned in {num_mentions} filings", PromiseStatus.ON_TRACK
    elif num_mentions == 1:
        return "Only mentioned once - tracking", PromiseStatus.UNKNOWN
    else:
        return "No updates found", PromiseStatus.UNKNOWN


def build_tone_trajectory(analyses: list[dict]) -> list[ToneDataPoint]:
    """Build tone trajectory from CEO letters.

    Args:
        analyses: List of filing analyses, sorted chronologically

    Returns:
        List of ToneDataPoint objects with reasoning and key quotes
    """
    trajectory = []

    for analysis in analyses:
        ceo_letter = analysis.get("ceo_letter", {})
        tone_str = ceo_letter.get("tone", "")
        confidence_str = ceo_letter.get("confidence_level", "")

        if not tone_str:
            continue

        # Map string to enum
        try:
            tone = CEOLetterTone(tone_str)
        except ValueError:
            tone = CEOLetterTone.NEUTRAL

        try:
            confidence = ConfidenceLevel(confidence_str)
        except ValueError:
            confidence = ConfidenceLevel.MEDIUM

        period = get_period_label(analysis)

        # Extract key quote (first available)
        key_quotes = ceo_letter.get("key_quotes", []) or []
        key_quote = None
        if key_quotes:
            first_quote = key_quotes[0]
            # Handle both string and dict formats
            if isinstance(first_quote, str):
                key_quote = first_quote
            elif isinstance(first_quote, dict):
                key_quote = first_quote.get("quote", "")

        # Build reasoning from context
        reasoning = _build_tone_reasoning(analysis, tone, confidence)

        trajectory.append(
            ToneDataPoint(
                period=period,
                tone=tone,
                confidence=confidence,
                reasoning=reasoning,
                key_quote=key_quote,
            )
        )

    return trajectory


def _build_tone_reasoning(analysis: dict, tone: CEOLetterTone, confidence: ConfidenceLevel) -> str:
    """Build reasoning explaining why the tone was rated this way.

    Args:
        analysis: Filing analysis dict
        tone: The classified tone
        confidence: Confidence level

    Returns:
        Human-readable reasoning string
    """
    parts = []

    # Financial context
    metrics = analysis.get("financial_metrics", {}) or {}
    period_data = analysis.get("period_data", {}) or {}

    organic_growth = metrics.get("revenue_growth_organic") or period_data.get("organic_growth")
    if organic_growth is not None:
        growth_pct = organic_growth * 100
        if growth_pct > 5:
            parts.append(f"Strong growth ({growth_pct:.1f}%)")
        elif growth_pct > 0:
            parts.append(f"Modest growth ({growth_pct:.1f}%)")
        else:
            parts.append(f"Negative growth ({growth_pct:.1f}%)")

    ebita_margin = metrics.get("ebita_margin_adjusted") or period_data.get("ebita_margin_adjusted")
    if ebita_margin is not None:
        margin_pct = ebita_margin * 100
        if margin_pct > 15:
            parts.append(f"healthy margins ({margin_pct:.1f}%)")
        elif margin_pct > 10:
            parts.append(f"moderate margins ({margin_pct:.1f}%)")
        else:
            parts.append(f"margin pressure ({margin_pct:.1f}%)")

    # Challenges acknowledged
    ceo_letter = analysis.get("ceo_letter", {}) or {}
    challenges = ceo_letter.get("challenges", []) or []
    if challenges:
        parts.append(f"acknowledged {len(challenges)} challenges")

    # Honesty signals
    honesty_signals = ceo_letter.get("honesty_signals", []) or []
    if honesty_signals:
        parts.append("transparent communication")

    # Confidence language
    confidence_str = confidence.value if hasattr(confidence, "value") else str(confidence)
    if confidence_str == "high":
        parts.append("confident language")
    elif confidence_str == "low":
        parts.append("cautious language")

    if not parts:
        return f"Tone: {tone.value}"

    return "; ".join(parts)


def build_financial_trends(analyses: list[dict]) -> dict[str, FinancialTrend]:
    """Build financial trends from metrics.

    Tracks: revenue_growth, ebita_margin, net_debt_to_ebitda, eps

    Args:
        analyses: List of filing analyses, sorted chronologically

    Returns:
        Dict mapping metric name to FinancialTrend
    """
    trends: dict[str, list[FinancialTrendPoint]] = {
        "organic_growth": [],
        "ebita_margin": [],
        "net_debt_to_ebitda": [],
        "eps": [],
    }

    for analysis in analyses:
        period = get_period_label(analysis)
        metrics = analysis.get("financial_metrics", {}) or {}
        period_data = analysis.get("period_data", {}) or {}

        # Organic growth
        organic = metrics.get("revenue_growth_organic") or period_data.get(
            "organic_growth"
        )
        if organic is not None:
            trends["organic_growth"].append(
                FinancialTrendPoint(period=period, value=organic * 100)
            )

        # EBITA margin
        ebita_margin = metrics.get("ebita_margin_adjusted") or period_data.get(
            "ebita_margin_adjusted"
        )
        if ebita_margin is not None:
            trends["ebita_margin"].append(
                FinancialTrendPoint(period=period, value=ebita_margin * 100)
            )

        # Net debt / EBITDA
        leverage = metrics.get("net_debt_to_ebitda")
        if leverage is not None:
            trends["net_debt_to_ebitda"].append(
                FinancialTrendPoint(period=period, value=leverage)
            )

        # EPS
        eps = metrics.get("eps_adjusted") or metrics.get("eps")
        if eps is not None:
            trends["eps"].append(FinancialTrendPoint(period=period, value=eps))

    # Convert to FinancialTrend objects with trajectory calculation
    result = {}
    for metric, points in trends.items():
        if len(points) < 2:
            trajectory = "stable"
        else:
            first_val = points[0].value
            last_val = points[-1].value
            change_pct = (
                ((last_val - first_val) / abs(first_val) * 100)
                if first_val != 0
                else 0
            )
            if change_pct > 5:
                trajectory = "improving"
            elif change_pct < -5:
                trajectory = "declining"
            else:
                trajectory = "stable"

        result[metric] = FinancialTrend(
            metric=metric,
            values=points,
            trajectory=trajectory,
        )

    return result


def calculate_guidance_accuracy(analyses: list[dict]) -> list[GuidanceAccuracyRecord]:
    """Calculate guidance accuracy by comparing guidance vs actuals.

    Compares guidance given in one period to actual results in subsequent periods.

    Args:
        analyses: List of filing analyses, sorted chronologically

    Returns:
        List of GuidanceAccuracyRecord objects
    """
    records = []

    # Track guidance from each filing
    guidance_given: list[tuple[int, str, str, str]] = []  # (year, metric, target, filing_id)

    for analysis in analyses:
        guidance = analysis.get("guidance", {}) or {}
        targets = guidance.get("targets", []) or []
        year = analysis.get("fiscal_year", 0)

        for t in targets:
            metric = t.get("metric", "")
            value = t.get("value", "")
            period = t.get("period", "")

            if metric and value:
                # Store for later comparison
                target_year = year  # Simplified: assume guidance is for current/next year
                if "2025" in period:
                    target_year = 2025
                elif "2024" in period:
                    target_year = 2024
                elif "2026" in period:
                    target_year = 2026

                guidance_given.append(
                    (target_year, metric, value, analysis.get("filing_id", ""))
                )

    # TODO: Compare against actual results from later filings
    # For now, return empty list - would need actual vs guided comparison
    return records


def track_theme_evolution(analyses: list[dict]) -> list[ThemeEvolution]:
    """Track how themes evolve across filings.

    Args:
        analyses: List of filing analyses, sorted chronologically

    Returns:
        List of ThemeEvolution objects
    """
    theme_counts: dict[str, list[tuple[str, int]]] = {}  # theme -> [(period, emphasis)]

    emphasis_map = {"high": 3, "medium": 2, "low": 1}

    for analysis in analyses:
        period = get_period_label(analysis)
        ceo_letter = analysis.get("ceo_letter", {})
        themes = ceo_letter.get("themes", [])

        for t in themes:
            topic = t.get("topic", "")
            emphasis_str = t.get("emphasis", "medium")
            emphasis = emphasis_map.get(emphasis_str, 2)

            if topic:
                if topic not in theme_counts:
                    theme_counts[topic] = []
                theme_counts[topic].append((period, emphasis))

    # Analyze trends
    evolutions = []
    for theme, data in theme_counts.items():
        if len(data) < 2:
            trend = "stable"
            interpretation = "Only mentioned once"
        else:
            first_emphasis = data[0][1]
            last_emphasis = data[-1][1]

            if last_emphasis > first_emphasis:
                trend = "increasing"
                interpretation = f"Emphasis growing from {data[0][0]} to {data[-1][0]}"
            elif last_emphasis < first_emphasis:
                trend = "decreasing"
                interpretation = f"Emphasis declining from {data[0][0]} to {data[-1][0]}"
            else:
                trend = "stable"
                interpretation = f"Consistent emphasis across {len(data)} periods"

        evolutions.append(
            ThemeEvolution(
                theme=theme,
                trend=trend,
                interpretation=interpretation,
            )
        )

    return evolutions


def generate_signals(
    analyses: list[dict],
    promises: list[TrackedPromise],
    tone_trajectory: list[ToneDataPoint],
    financial_trends: dict[str, FinancialTrend],
) -> EvolutionSignals:
    """Generate green/red/watch signals from evolution data.

    Args:
        analyses: List of filing analyses
        promises: Tracked promises
        tone_trajectory: Tone over time
        financial_trends: Financial metric trends

    Returns:
        EvolutionSignals with green_flags, red_flags, watch_items
    """
    green_flags = []
    red_flags = []
    watch_items = []

    # Promise tracking signals
    met_promises = sum(1 for p in promises if p.current_status == PromiseStatus.MET)
    missed_promises = sum(
        1 for p in promises if p.current_status == PromiseStatus.MISSED
    )

    if met_promises > 0:
        green_flags.append(f"{met_promises} promises met")
    if missed_promises > 0:
        red_flags.append(f"{missed_promises} promises missed")

    # Tone trajectory signals
    if len(tone_trajectory) >= 2:
        recent_tones = [t.tone for t in tone_trajectory[-2:]]
        if all(
            t in (CEOLetterTone.OPTIMISTIC, CEOLetterTone.CAUTIOUSLY_OPTIMISTIC)
            for t in recent_tones
        ):
            green_flags.append("Consistent positive tone in recent communications")
        elif any(t == CEOLetterTone.DEFENSIVE for t in recent_tones):
            red_flags.append("Defensive tone detected in recent communication")
        elif any(t == CEOLetterTone.CAUTIOUS for t in recent_tones):
            watch_items.append(
                WatchItem(
                    description="CEO tone becoming more cautious",
                    severity="medium",
                    category="communication",
                    source_filing=analyses[-1].get("filing_id", "recent"),
                    change="new",
                )
            )

    # Financial trend signals
    margin_trend = financial_trends.get("ebita_margin")
    if margin_trend:
        if margin_trend.trajectory == "improving":
            green_flags.append("EBITA margin trending upward")
        elif margin_trend.trajectory == "declining":
            red_flags.append("EBITA margin trending downward")

    growth_trend = financial_trends.get("organic_growth")
    if growth_trend:
        if growth_trend.trajectory == "improving":
            green_flags.append("Organic growth accelerating")
        elif growth_trend.trajectory == "declining":
            watch_items.append(
                WatchItem(
                    description="Organic growth decelerating",
                    severity="medium",
                    category="financial",
                    source_filing=analyses[-1].get("filing_id", "recent") if analyses else "",
                    change="new",
                )
            )

    leverage_trend = financial_trends.get("net_debt_to_ebitda")
    if leverage_trend and leverage_trend.values:
        latest_leverage = leverage_trend.values[-1].value
        if latest_leverage > 2.5:
            red_flags.append(f"High leverage: {latest_leverage:.1f}x Net Debt/EBITDA")
        elif latest_leverage < 1.5:
            green_flags.append(f"Conservative leverage: {latest_leverage:.1f}x")

    # Extract ALL risks with change indicators from recent filings
    # User preference: show all risks, not just escalated ones
    for analysis in analyses[-2:]:  # Check recent filings
        risk_factors = analysis.get("risk_factors", {}) or {}
        risks = risk_factors.get("risks", []) or []
        filing_id = analysis.get("filing_id", "unknown")
        period = get_period_label(analysis)

        for risk in risks:
            risk_desc = risk.get("risk", "")
            if not risk_desc:
                continue

            # Skip boilerplate risks
            if risk.get("is_boilerplate", False):
                continue

            severity = risk.get("severity", "medium")
            category = risk.get("category", "unknown")
            change = risk.get("change", "unchanged")

            watch_items.append(
                WatchItem(
                    description=risk_desc,
                    severity=severity,
                    category=category,
                    source_filing=filing_id,
                    change=change,
                )
            )

    # Guidance signals
    for analysis in analyses[-2:]:
        guidance = analysis.get("guidance", {}) or {}
        direction = guidance.get("overall_direction", "")
        if direction == "raised":
            green_flags.append(f"Guidance raised in {get_period_label(analysis)}")
        elif direction == "lowered":
            red_flags.append(f"Guidance lowered in {get_period_label(analysis)}")

    return EvolutionSignals(
        green_flags=green_flags,
        red_flags=red_flags,
        watch_items=watch_items,
    )


def synthesize_evolution(company_id: str, data_dir: Path) -> FilingEvolution:
    """Synthesize evolution from all available analyses.

    This is the main entry point for evolution tracking.

    Args:
        company_id: Company identifier (e.g., "getinge")
        data_dir: Base data directory (e.g., Path("data"))

    Returns:
        FilingEvolution model with complete synthesis
    """
    analyses = load_analyses(company_id, data_dir)

    if not analyses:
        return FilingEvolution(
            company_id=company_id,
            filings_analyzed=[],
        )

    # Extract filing IDs
    filing_ids = [a.get("filing_id", "unknown") for a in analyses]

    # Run all extraction functions
    promises = track_promises(analyses)
    tone_trajectory = build_tone_trajectory(analyses)
    financial_trends = build_financial_trends(analyses)
    guidance_accuracy = calculate_guidance_accuracy(analyses)
    theme_evolution = track_theme_evolution(analyses)

    # Generate signals
    signals = generate_signals(analyses, promises, tone_trajectory, financial_trends)

    return FilingEvolution(
        company_id=company_id,
        last_updated=datetime.now(),
        filings_analyzed=filing_ids,
        promise_tracker=promises,
        tone_trajectory=tone_trajectory,
        theme_evolution=theme_evolution,
        financial_trends=financial_trends,
        guidance_accuracy=guidance_accuracy,
        signals=signals,
    )


def save_evolution(evolution: FilingEvolution, data_dir: Path) -> Path:
    """Save evolution to JSON file.

    Args:
        evolution: FilingEvolution to save
        data_dir: Base data directory

    Returns:
        Path to saved file
    """
    output_dir = data_dir / "filings" / "analysis" / evolution.company_id
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "evolution.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            evolution.model_dump(mode="json"),
            f,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    return output_path


def load_evolution(company_id: str, data_dir: Path) -> FilingEvolution | None:
    """Load existing evolution from JSON file.

    Args:
        company_id: Company identifier
        data_dir: Base data directory

    Returns:
        FilingEvolution if exists, else None
    """
    path = data_dir / "filings" / "analysis" / company_id / "evolution.json"

    if not path.exists():
        return None

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    return FilingEvolution.model_validate(data)
