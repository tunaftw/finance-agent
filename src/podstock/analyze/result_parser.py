"""Result parsing for Claude analysis responses.

This module parses Claude's JSON responses into structured Recommendation objects.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from podstock.core.exceptions import AnalysisError
from podstock.core.models import ConfidenceLevel, Recommendation


def extract_json_from_response(response: str) -> str:
    """Extract JSON from Claude's response.

    Handles responses that may include markdown code blocks
    or extra text before/after the JSON.

    Args:
        response: Raw response text from Claude.

    Returns:
        Extracted JSON string.

    Raises:
        AnalysisError: If no valid JSON found.
    """
    # Try to find JSON in code block
    code_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    matches = re.findall(code_block_pattern, response)

    for match in matches:
        if "{" in match and "}" in match:
            return match.strip()

    # Try to find raw JSON object
    json_pattern = r"\{[\s\S]*\}"
    matches = re.findall(json_pattern, response)

    for match in matches:
        try:
            json.loads(match)
            return match
        except json.JSONDecodeError:
            continue

    raise AnalysisError("No valid JSON found in response")


def parse_confidence(value: str | None) -> ConfidenceLevel:
    """Parse confidence level string to enum.

    Args:
        value: Confidence string ("high", "medium", "low").

    Returns:
        ConfidenceLevel enum value.
    """
    if not value:
        return ConfidenceLevel.MEDIUM

    value_lower = value.lower().strip()

    if value_lower == "high":
        return ConfidenceLevel.HIGH
    elif value_lower == "low":
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.MEDIUM


def parse_recommendation(
    data: dict[str, Any],
    episode_id: str,
    index: int,
) -> Recommendation | None:
    """Parse a single recommendation from dict.

    Args:
        data: Recommendation data dict.
        episode_id: ID of the source episode.
        index: Index for generating unique ID.

    Returns:
        Recommendation object, or None if required fields missing.
    """
    # Required fields
    company_name = data.get("company_name")
    quote = data.get("quote")
    context = data.get("context")
    reasoning = data.get("reasoning")

    if not all([company_name, quote, context, reasoning]):
        return None

    # Generate ID
    rec_id = f"{episode_id}-{index:03d}"

    # Parse confidence
    confidence = parse_confidence(data.get("confidence"))

    return Recommendation(
        id=rec_id,
        episode_id=episode_id,
        company_name=company_name,
        ticker=data.get("ticker"),
        market=data.get("market"),
        host=data.get("host"),
        quote=quote,
        context=context,
        timestamp_hint=data.get("timestamp_hint"),
        time_horizon=data.get("time_horizon"),
        confidence=confidence,
        reasoning=reasoning,
        extracted_at=datetime.now(),
    )


def parse_claude_response(
    response: str,
    episode_id: str,
) -> list[Recommendation]:
    """Parse Claude's analysis response into Recommendation objects.

    Args:
        response: Raw response text from Claude.
        episode_id: ID of the analyzed episode.

    Returns:
        List of Recommendation objects.

    Raises:
        AnalysisError: If parsing fails.

    Example:
        >>> recommendations = parse_claude_response(response_text, "bp-2024-12-18")
        >>> len(recommendations) >= 0
        True
    """
    try:
        json_str = extract_json_from_response(response)
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise AnalysisError(f"Invalid JSON in response: {e}") from e

    recommendations_data = data.get("recommendations", [])

    if not isinstance(recommendations_data, list):
        raise AnalysisError("'recommendations' field must be a list")

    recommendations = []
    for i, rec_data in enumerate(recommendations_data, start=1):
        rec = parse_recommendation(rec_data, episode_id, i)
        if rec:
            recommendations.append(rec)

    return recommendations


def save_recommendations(
    recommendations: list[Recommendation],
    recommendations_dir: Path,
    podcast_id: str,
    episode_id: str,
) -> Path:
    """Save recommendations to JSON file.

    Args:
        recommendations: List of Recommendation objects.
        recommendations_dir: Base directory for recommendations.
        podcast_id: Podcast identifier.
        episode_id: Episode identifier.

    Returns:
        Path to saved file.
    """

    # Create podcast subdirectory
    podcast_dir = recommendations_dir / podcast_id
    podcast_dir.mkdir(parents=True, exist_ok=True)

    output_path = podcast_dir / f"{episode_id}.json"

    # Convert to JSON-serializable format
    data = {
        "episode_id": episode_id,
        "podcast_id": podcast_id,
        "extracted_at": datetime.now().isoformat(),
        "count": len(recommendations),
        "recommendations": [
            {
                "id": rec.id,
                "company_name": rec.company_name,
                "ticker": rec.ticker,
                "market": rec.market,
                "host": rec.host,
                "quote": rec.quote,
                "context": rec.context,
                "timestamp_hint": rec.timestamp_hint,
                "time_horizon": rec.time_horizon,
                "confidence": rec.confidence.value,
                "reasoning": rec.reasoning,
            }
            for rec in recommendations
        ],
    }

    # Atomic write
    temp_path = output_path.with_suffix(".tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

        temp_path.replace(output_path)
    except OSError as e:
        if temp_path.exists():
            temp_path.unlink()
        raise AnalysisError(f"Failed to save recommendations: {e}") from e

    return output_path


def load_recommendations(
    recommendations_dir: Path,
    podcast_id: str,
    episode_id: str,
) -> list[Recommendation]:
    """Load recommendations from JSON file.

    Args:
        recommendations_dir: Base directory for recommendations.
        podcast_id: Podcast identifier.
        episode_id: Episode identifier.

    Returns:
        List of Recommendation objects.

    Raises:
        AnalysisError: If file not found or invalid.
    """

    file_path = recommendations_dir / podcast_id / f"{episode_id}.json"

    if not file_path.exists():
        raise AnalysisError(f"Recommendations file not found: {file_path}")

    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise AnalysisError(f"Failed to load recommendations: {e}") from e

    recommendations = []
    for i, rec_data in enumerate(data.get("recommendations", []), start=1):
        rec = parse_recommendation(rec_data, episode_id, i)
        if rec:
            recommendations.append(rec)

    return recommendations
