"""Import podcast analyses into unified signal layer."""

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

# Default path to podcast analyses
DEFAULT_ANALYSES_PATH = Path(__file__).parent.parent.parent.parent.parent / "data" / "podcasts" / "analyses-v2"


def parse_podcast_analysis(file_path: Path) -> Iterator[Signal]:
    """
    Parse a podcast analysis JSON file and yield Signal objects.

    Args:
        file_path: Path to the JSON analysis file

    Yields:
        Signal objects for each recommendation in the file
    """
    try:
        with open(file_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to parse {file_path}: {e}")
        return

    # Extract metadata
    episode_id = data.get("episode_id", file_path.stem)
    podcast_name = data.get("podcast_name", "unknown")
    episode_date_str = data.get("date")

    if not episode_date_str:
        # Try to extract from filename (format: podcast-YYYY-MM-DD-hash.json)
        parts = file_path.stem.split("-")
        if len(parts) >= 4:
            try:
                episode_date_str = f"{parts[-4]}-{parts[-3]}-{parts[-2]}"
            except (IndexError, ValueError):
                logger.warning(f"Could not extract date from {file_path}")
                return

    try:
        episode_date = date.fromisoformat(episode_date_str)
    except (ValueError, TypeError):
        logger.warning(f"Invalid date format in {file_path}: {episode_date_str}")
        return

    # Extract source_id from podcast_name or episode_id
    source_id = episode_id.rsplit("-", 3)[0] if episode_id else podcast_name.lower().replace(" ", "")

    # Process recommendations
    recommendations = data.get("recommendations", [])

    for rec in recommendations:
        stock_name = rec.get("stock_name")
        if not stock_name:
            continue

        action = rec.get("action", "hold")
        speaker = rec.get("speaker", "unknown")
        confidence = rec.get("confidence")

        # Normalize signal
        signal_type = SignalNormalizer.normalize_podcast_action(action)
        signal_strength = SignalNormalizer.normalize_confidence(confidence)

        # Determine asset type
        ticker = rec.get("ticker") or stock_name.upper().replace(" ", "_")
        asset_type = SignalNormalizer.detect_asset_type(ticker, stock_name)

        yield Signal(
            source_type=SourceType.PODCAST,
            source_id=source_id,
            content_id=episode_id,
            content_date=episode_date,
            asset_symbol=ticker,
            asset_name=stock_name,
            asset_type=asset_type,
            signal=signal_type,
            signal_strength=signal_strength,
            speaker_name=speaker,
            quote=rec.get("quote"),
            reasoning=rec.get("reasoning"),
            timestamp=rec.get("timestamp"),
            original_action=action,
            price_levels=[rec.get("price_target")] if rec.get("price_target") else None,
        )


def import_podcast_analyses(
    analyses_path: Path | None = None,
    dry_run: bool = False,
    limit: int | None = None,
) -> dict:
    """
    Import all podcast analyses into unified_signals table.

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
            for signal in parse_podcast_analysis(file_path):
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
        logger.info(f"Inserted {inserted} podcast signals")

    return stats
