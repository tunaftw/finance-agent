"""Investment thesis generation from evolution analysis.

This module generates investment verdicts (GREEN/YELLOW/RED) based on:
- CEO credibility scoring
- Financial trend analysis
- Promise tracking
- Risk signal synthesis

The thesis aligns with the user's investment philosophy principles:
#1 Profitability path - EBIT margin trending positive
#6 Intelligent fanatics - CEO delivers on promises
#7 Recurring revenue - Organic growth focus
#12 Bad quarter momentum - Trajectory monitoring
#15 Net debt - Leverage assessment
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from podstock.filings.models import (
    CEOLetterTone,
    FilingEvolution,
    InvestmentThesis,
    InvestmentVerdict,
    PromiseStatus,
)


def calculate_ceo_credibility_score(evolution: FilingEvolution) -> tuple[float, dict[str, float]]:
    """Calculate CEO credibility score from evolution data.

    Formula (0-100):
    - Promise delivery rate: 40%
    - Guidance accuracy: 30%
    - Tone consistency: 20%
    - Challenge attribution: 10%

    Args:
        evolution: FilingEvolution with tracked promises, tone, etc.

    Returns:
        Tuple of (total_score, breakdown_dict)
    """
    breakdown = {}

    # 1. Promise delivery rate (40%)
    promises = evolution.promise_tracker
    if promises:
        met = sum(1 for p in promises if p.current_status == PromiseStatus.MET)
        on_track = sum(1 for p in promises if p.current_status == PromiseStatus.ON_TRACK)
        missed = sum(1 for p in promises if p.current_status == PromiseStatus.MISSED)
        total_tracked = met + on_track + missed

        if total_tracked > 0:
            # Met = 100%, on_track = 75%, missed = 0%
            promise_score = (met * 100 + on_track * 75) / total_tracked
        else:
            promise_score = 50  # No trackable promises = neutral
    else:
        promise_score = 50  # No promises = neutral

    breakdown["promise_delivery"] = promise_score
    promise_contribution = promise_score * 0.40

    # 2. Guidance accuracy (30%)
    if evolution.accuracy_rate is not None:
        guidance_score = evolution.accuracy_rate * 100
    else:
        # Estimate from guidance direction in signals
        guidance_score = 50  # Neutral when no accuracy data
        # Boost if guidance maintained/raised, penalize if lowered
        for flag in evolution.signals.green_flags:
            if "guidance raised" in flag.lower():
                guidance_score = 75
                break
        for flag in evolution.signals.red_flags:
            if "guidance lowered" in flag.lower():
                guidance_score = 25
                break

    breakdown["guidance_accuracy"] = guidance_score
    guidance_contribution = guidance_score * 0.30

    # 3. Tone consistency (20%)
    tone_trajectory = evolution.tone_trajectory
    if len(tone_trajectory) >= 2:
        # Check for consistent positive tone
        positive_tones = {CEOLetterTone.OPTIMISTIC, CEOLetterTone.CAUTIOUSLY_OPTIMISTIC}
        negative_tones = {CEOLetterTone.DEFENSIVE, CEOLetterTone.CAUTIOUS}

        recent_positive = sum(1 for t in tone_trajectory[-3:] if t.tone in positive_tones)
        recent_negative = sum(1 for t in tone_trajectory[-3:] if t.tone in negative_tones)
        recent_count = min(3, len(tone_trajectory))

        if recent_positive == recent_count:
            tone_score = 90
        elif recent_positive > recent_negative:
            tone_score = 70
        elif recent_positive == recent_negative:
            tone_score = 50
        else:
            tone_score = 30
    else:
        tone_score = 50  # Not enough data

    breakdown["tone_consistency"] = tone_score
    tone_contribution = tone_score * 0.20

    # 4. Challenge attribution (10%)
    # Prefer management that takes accountability vs. blames external factors
    # This requires analyzing the underlying filings - simplified heuristic for now
    # Look at signals for hints
    attribution_score = 50  # Neutral default

    for flag in evolution.signals.green_flags:
        if "account" in flag.lower() or "responsibility" in flag.lower():
            attribution_score = 80
            break

    for flag in evolution.signals.red_flags:
        if "blame" in flag.lower() or "defensive" in flag.lower():
            attribution_score = 30
            break

    breakdown["challenge_attribution"] = attribution_score
    attribution_contribution = attribution_score * 0.10

    # Total score
    total_score = (
        promise_contribution +
        guidance_contribution +
        tone_contribution +
        attribution_contribution
    )

    return total_score, breakdown


def assess_trends(evolution: FilingEvolution) -> dict[str, str]:
    """Assess financial and tone trends.

    Returns:
        Dict with trend assessments for tone, margin, growth, leverage
    """
    trends = {}

    # Tone trend
    tone_trajectory = evolution.tone_trajectory
    if len(tone_trajectory) >= 2:
        positive_tones = {CEOLetterTone.OPTIMISTIC, CEOLetterTone.CAUTIOUSLY_OPTIMISTIC}
        first_positive = tone_trajectory[0].tone in positive_tones
        last_positive = tone_trajectory[-1].tone in positive_tones

        if not first_positive and last_positive:
            trends["tone"] = "improving"
        elif first_positive and not last_positive:
            trends["tone"] = "declining"
        else:
            trends["tone"] = "stable"
    else:
        trends["tone"] = "insufficient_data"

    # Margin trend
    margin_data = evolution.financial_trends.get("ebita_margin")
    if margin_data:
        trends["margin"] = margin_data.trajectory
    else:
        trends["margin"] = "insufficient_data"

    # Growth trend
    growth_data = evolution.financial_trends.get("organic_growth")
    if growth_data:
        trends["growth"] = growth_data.trajectory
    else:
        trends["growth"] = "insufficient_data"

    # Leverage assessment
    leverage_data = evolution.financial_trends.get("net_debt_to_ebitda")
    if leverage_data and leverage_data.values:
        latest = leverage_data.values[-1].value
        if latest < 1.5:
            trends["leverage"] = "healthy"
        elif latest < 2.5:
            trends["leverage"] = "elevated"
        else:
            trends["leverage"] = "concerning"
    else:
        trends["leverage"] = "insufficient_data"

    return trends


def count_promises(evolution: FilingEvolution) -> dict[str, int]:
    """Count promises by status.

    Returns:
        Dict with counts for met, missed, pending
    """
    met = sum(1 for p in evolution.promise_tracker if p.current_status == PromiseStatus.MET)
    missed = sum(1 for p in evolution.promise_tracker if p.current_status == PromiseStatus.MISSED)
    on_track = sum(1 for p in evolution.promise_tracker if p.current_status == PromiseStatus.ON_TRACK)
    unknown = sum(1 for p in evolution.promise_tracker if p.current_status == PromiseStatus.UNKNOWN)

    return {
        "met": met,
        "missed": missed,
        "pending": on_track + unknown,
    }


def determine_verdict(
    credibility_score: float,
    trends: dict[str, str],
    signals: dict[str, list[str]],
) -> tuple[InvestmentVerdict, str]:
    """Determine investment verdict based on analysis.

    Args:
        credibility_score: CEO credibility score (0-100)
        trends: Trend assessments
        signals: Green/red/watch signals

    Returns:
        Tuple of (verdict, reasoning)
    """
    green_count = len(signals.get("green", []))
    red_count = len(signals.get("red", []))

    reasons = []

    # High credibility + positive trends + few red flags = GREEN
    if credibility_score >= 70:
        reasons.append(f"Strong CEO credibility ({credibility_score:.0f}/100)")
        if red_count == 0:
            if trends.get("margin") == "improving" or trends.get("growth") == "improving":
                reasons.append("Positive financial trends")
                return InvestmentVerdict.GREEN, "; ".join(reasons)
            elif green_count >= 2:
                return InvestmentVerdict.GREEN, "; ".join(reasons)

    # Any significant red flags or concerning leverage = RED
    if red_count >= 2:
        reasons.append(f"{red_count} red flags detected")
        return InvestmentVerdict.RED, "; ".join(reasons)

    if trends.get("leverage") == "concerning":
        reasons.append("High leverage concerning")
        return InvestmentVerdict.RED, "; ".join(reasons)

    if credibility_score < 40:
        reasons.append(f"Low CEO credibility ({credibility_score:.0f}/100)")
        return InvestmentVerdict.RED, "; ".join(reasons)

    # Low credibility or declining trends = RED
    if trends.get("margin") == "declining" and trends.get("growth") == "declining":
        reasons.append("Both margin and growth declining")
        return InvestmentVerdict.RED, "; ".join(reasons)

    # Everything else = YELLOW
    if credibility_score >= 60:
        reasons.append(f"Moderate CEO credibility ({credibility_score:.0f}/100)")
    else:
        reasons.append(f"Mixed CEO credibility signals ({credibility_score:.0f}/100)")

    if red_count > 0:
        reasons.append(f"{red_count} watch items")

    if green_count > red_count:
        reasons.append("More positive than negative signals")

    return InvestmentVerdict.YELLOW, "; ".join(reasons) if reasons else "Mixed signals require monitoring"


def assess_philosophy_alignment(evolution: FilingEvolution, trends: dict[str, str]) -> dict[str, str]:
    """Assess alignment with user's investment philosophy principles.

    Key principles tracked:
    #1 Profitability path
    #6 Intelligent fanatics
    #7 Recurring revenue
    #12 Bad quarter momentum
    #15 Net debt

    Returns:
        Dict mapping principle to assessment
    """
    alignment = {}

    # #1 Profitability path - EBIT margin trend
    margin_trend = trends.get("margin", "insufficient_data")
    if margin_trend == "improving":
        alignment["profitability_path"] = "POSITIVE: Margin improving"
    elif margin_trend == "declining":
        alignment["profitability_path"] = "NEGATIVE: Margin declining"
    else:
        alignment["profitability_path"] = "NEUTRAL: Margin stable"

    # #6 Intelligent fanatics - Promise delivery
    promises = count_promises(evolution)
    if promises["met"] > promises["missed"]:
        alignment["intelligent_fanatics"] = f"POSITIVE: {promises['met']} met vs {promises['missed']} missed"
    elif promises["missed"] > promises["met"]:
        alignment["intelligent_fanatics"] = f"NEGATIVE: {promises['missed']} missed vs {promises['met']} met"
    else:
        alignment["intelligent_fanatics"] = f"NEUTRAL: Tracking {promises['pending']} promises"

    # #7 Recurring revenue - Organic growth focus
    growth_trend = trends.get("growth", "insufficient_data")
    if growth_trend == "improving":
        alignment["recurring_revenue"] = "POSITIVE: Organic growth accelerating"
    elif growth_trend == "declining":
        alignment["recurring_revenue"] = "NEGATIVE: Organic growth slowing"
    else:
        alignment["recurring_revenue"] = "NEUTRAL: Growth stable"

    # #12 Bad quarter momentum - Look for consecutive declines
    tone_trajectory = evolution.tone_trajectory
    if len(tone_trajectory) >= 2:
        last_two = [t.tone for t in tone_trajectory[-2:]]
        negative_tones = {CEOLetterTone.DEFENSIVE, CEOLetterTone.CAUTIOUS}
        if all(t in negative_tones for t in last_two):
            alignment["momentum"] = "WARNING: Consecutive cautious quarters"
        elif last_two[-1] in negative_tones:
            alignment["momentum"] = "WATCH: Recent quarter cautious"
        else:
            alignment["momentum"] = "POSITIVE: Healthy momentum"
    else:
        alignment["momentum"] = "NEUTRAL: Insufficient history"

    # #15 Net debt - Leverage assessment
    leverage = trends.get("leverage", "insufficient_data")
    if leverage == "healthy":
        alignment["net_debt"] = "POSITIVE: Conservative leverage"
    elif leverage == "concerning":
        alignment["net_debt"] = "NEGATIVE: High leverage"
    elif leverage == "elevated":
        alignment["net_debt"] = "WATCH: Elevated leverage"
    else:
        alignment["net_debt"] = "NEUTRAL: No data"

    return alignment


def generate_thesis(evolution: FilingEvolution) -> InvestmentThesis:
    """Generate investment thesis from evolution analysis.

    This is the main entry point for thesis generation.

    Args:
        evolution: FilingEvolution with complete analysis

    Returns:
        InvestmentThesis with verdict, scores, and signals
    """
    # Calculate credibility
    credibility_score, credibility_breakdown = calculate_ceo_credibility_score(evolution)

    # Assess trends
    trends = assess_trends(evolution)

    # Count promises
    promise_counts = count_promises(evolution)

    # Get signals from evolution
    signals = {
        "green": evolution.signals.green_flags,
        "red": evolution.signals.red_flags,
        "watch": evolution.signals.watch_items,
    }

    # Determine verdict
    verdict, reasoning = determine_verdict(credibility_score, trends, signals)

    # Assess philosophy alignment
    philosophy = assess_philosophy_alignment(evolution, trends)

    return InvestmentThesis(
        company_id=evolution.company_id,
        generated_at=datetime.now(),
        verdict=verdict,
        verdict_reasoning=reasoning,
        ceo_credibility_score=credibility_score,
        credibility_breakdown=credibility_breakdown,
        green_flags=evolution.signals.green_flags,
        red_flags=evolution.signals.red_flags,
        watch_items=evolution.signals.watch_items,
        tone_trend=trends.get("tone", "stable"),
        margin_trend=trends.get("margin", "stable"),
        growth_trend=trends.get("growth", "stable"),
        leverage_assessment=trends.get("leverage", "healthy"),
        promises_met=promise_counts["met"],
        promises_missed=promise_counts["missed"],
        promises_pending=promise_counts["pending"],
        philosophy_alignment=philosophy,
    )


def save_thesis(thesis: InvestmentThesis, data_dir: Path) -> Path:
    """Save thesis to JSON file.

    Args:
        thesis: InvestmentThesis to save
        data_dir: Base data directory

    Returns:
        Path to saved file
    """
    output_dir = data_dir / "filings" / "analysis" / thesis.company_id
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "thesis.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            thesis.model_dump(mode="json"),
            f,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    return output_path


def load_thesis(company_id: str, data_dir: Path) -> InvestmentThesis | None:
    """Load existing thesis from JSON file.

    Args:
        company_id: Company identifier
        data_dir: Base data directory

    Returns:
        InvestmentThesis if exists, else None
    """
    path = data_dir / "filings" / "analysis" / company_id / "thesis.json"

    if not path.exists():
        return None

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    return InvestmentThesis.model_validate(data)
