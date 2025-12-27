"""Import YouTube crypto analyses into unified signal layer."""

import json
import logging
from datetime import date
from pathlib import Path
from typing import Iterator

from ...db.engine import get_session
from ...db.models import UnifiedSignal
from ..models import (
    AssetType,
    Signal,
    SignalNormalizer,
    SignalStrength,
    SignalType,
    SourceType,
)

logger = logging.getLogger(__name__)

# Default path to YouTube crypto analyses
DEFAULT_ANALYSES_PATH = Path(__file__).parent.parent.parent.parent.parent / "data" / "crypto" / "technicalroundup-analysis"


def parse_youtube_analysis(file_path: Path) -> Iterator[Signal]:
    """
    Parse a YouTube crypto analysis JSON file and yield Signal objects.

    Args:
        file_path: Path to the JSON analysis file

    Yields:
        Signal objects for each mention in the file
    """
    try:
        with open(file_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to parse {file_path}: {e}")
        return

    # Extract metadata
    video_id = data.get("source_id", file_path.stem)
    channel = data.get("channel", "unknown")
    date_str = data.get("date")

    if not date_str:
        logger.warning(f"No date in {file_path}")
        return

    try:
        video_date = date.fromisoformat(date_str)
    except (ValueError, TypeError):
        logger.warning(f"Invalid date format in {file_path}: {date_str}")
        return

    # Source ID from channel name
    source_id = channel.lower().replace(" ", "")

    # Process mentions
    mentions = data.get("mentions", [])

    for mention in mentions:
        asset_symbol = mention.get("asset_symbol")
        asset_name = mention.get("asset_name", asset_symbol)

        if not asset_symbol:
            continue

        sentiment = mention.get("sentiment") or "neutral"
        speaker = mention.get("speaker") or "unknown"
        confidence = mention.get("confidence")

        # Normalize signal
        signal_type = SignalNormalizer.normalize_youtube_sentiment(sentiment)
        signal_strength = SignalNormalizer.normalize_confidence(confidence)

        # Price levels
        price_levels = mention.get("price_levels")

        yield Signal(
            source_type=SourceType.YOUTUBE,
            source_id=source_id,
            content_id=video_id,
            content_date=video_date,
            asset_symbol=asset_symbol,
            asset_name=asset_name,
            asset_type=AssetType.CRYPTO,  # YouTube analyses are crypto-focused
            signal=signal_type,
            signal_strength=signal_strength,
            speaker_name=speaker,
            quote=mention.get("quote"),
            reasoning=mention.get("context"),
            timestamp=None,  # YouTube analyses don't have timestamps
            original_action=sentiment,
            price_levels=price_levels,
        )

    # Also process trading_ideas if present
    trading_ideas = data.get("trading_ideas", [])

    for idea in trading_ideas:
        asset = idea.get("asset")
        if not asset:
            continue

        direction = idea.get("direction", "").lower()
        speaker = idea.get("speaker", "unknown")

        # Map direction to signal
        if direction in ("long", "buy"):
            signal_type = SignalType.BULLISH
        elif direction in ("short", "sell"):
            signal_type = SignalType.BEARISH
        else:
            signal_type = SignalType.NEUTRAL

        # Build reasoning from trade details
        reasoning_parts = []
        if idea.get("entry"):
            reasoning_parts.append(f"Entry: {idea['entry']}")
        if idea.get("target"):
            reasoning_parts.append(f"Target: {idea['target']}")
        if idea.get("stop"):
            reasoning_parts.append(f"Stop: {idea['stop']}")

        reasoning = " | ".join(reasoning_parts) if reasoning_parts else None

        yield Signal(
            source_type=SourceType.YOUTUBE,
            source_id=source_id,
            content_id=video_id,
            content_date=video_date,
            asset_symbol=asset,
            asset_name=asset,
            asset_type=AssetType.CRYPTO,
            signal=signal_type,
            signal_strength=SignalStrength.STRONG,  # Trading ideas are concrete
            speaker_name=speaker,
            quote=None,
            reasoning=reasoning,
            timestamp=None,
            original_action=direction,
            price_levels=[idea.get("entry"), idea.get("target")] if idea.get("entry") else None,
        )


def import_youtube_analyses(
    analyses_path: Path | None = None,
    dry_run: bool = False,
    limit: int | None = None,
) -> dict:
    """
    Import all YouTube crypto analyses into unified_signals table.

    Args:
        analyses_path: Path to directory containing analysis JSON files
        dry_run: If True, don't write to database
        limit: Maximum number of files to process (for testing)

    Returns:
        Dict with import statistics
    """
    if analyses_path is None:
        analyses_path = DEFAULT_ANALYSES_PATH

    if not analyses_path.exists():
        logger.error(f"Analyses path not found: {analyses_path}")
        return {"error": f"Path not found: {analyses_path}"}

    # Find all JSON files
    json_files = sorted(analyses_path.glob("*.json"))

    if limit:
        json_files = json_files[:limit]

    stats = {
        "files_processed": 0,
        "signals_created": 0,
        "signals_skipped": 0,
        "errors": 0,
    }

    signals_to_insert = []

    for file_path in json_files:
        try:
            for signal in parse_youtube_analysis(file_path):
                signals_to_insert.append(signal)
                stats["signals_created"] += 1

            stats["files_processed"] += 1

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            stats["errors"] += 1

    if dry_run:
        logger.info(f"Dry run: would insert {len(signals_to_insert)} signals")
        return stats

    # Insert into database
    with get_session() as session:
        # Get existing signal IDs to avoid duplicates
        existing_ids = set(
            row[0] for row in session.query(UnifiedSignal.id).all()
        )

        # Also track IDs we're about to insert (to handle duplicates in same batch)
        batch_ids = set()

        inserted = 0
        for signal in signals_to_insert:
            if signal.id in existing_ids or signal.id in batch_ids:
                stats["signals_skipped"] += 1
                stats["signals_created"] -= 1
                continue

            batch_ids.add(signal.id)

            db_signal = UnifiedSignal(
                id=signal.id,
                source_type=signal.source_type.value,
                source_id=signal.source_id,
                content_id=signal.content_id,
                content_date=signal.content_date.isoformat(),
                asset_symbol=signal.asset_symbol,
                asset_name=signal.asset_name,
                asset_type=signal.asset_type.value,
                signal=signal.signal.value,
                signal_strength=signal.signal_strength.value,
                original_action=signal.original_action,
                speaker_name=signal.speaker_name,
                quote=signal.quote,
                reasoning=signal.reasoning,
                timestamp=signal.timestamp,
                price_levels=json.dumps(signal.price_levels) if signal.price_levels else None,
            )
            session.add(db_signal)
            inserted += 1

        session.commit()
        logger.info(f"Inserted {inserted} YouTube signals")

    return stats
