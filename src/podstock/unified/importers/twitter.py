"""Import Twitter analyses into unified signal layer."""

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

# Default path to Twitter analyses
DEFAULT_ANALYSES_PATH = Path(__file__).parent.parent.parent.parent.parent / "data" / "twitter" / "analyses"


def parse_twitter_analysis(file_path: Path) -> Iterator[Signal]:
    """
    Parse a Twitter analysis JSON file and yield Signal objects.

    Args:
        file_path: Path to the JSON analysis file

    Yields:
        Signal objects for each mention in the file (crypto, stock, recommendations)
    """
    # Skip non-analysis files
    if not file_path.name.endswith("-analysis.json"):
        return

    try:
        with open(file_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to parse {file_path}: {e}")
        return

    # Extract metadata
    source_id = data.get("source_id", file_path.stem.replace("-analysis", ""))
    analyzed_at = data.get("analyzed_at", "")

    # Try to get date from analyzed_at or current_positioning
    analysis_date = None
    if analyzed_at:
        try:
            analysis_date = date.fromisoformat(analyzed_at[:10])
        except (ValueError, TypeError):
            pass

    if not analysis_date:
        # Try current_positioning.as_of
        current_pos = data.get("current_positioning", {})
        if current_pos.get("as_of"):
            try:
                analysis_date = date.fromisoformat(current_pos["as_of"])
            except (ValueError, TypeError):
                pass

    if not analysis_date:
        # Default to today
        analysis_date = date.today()

    # Get profile info for speaker name
    profile = data.get("profile_summary", {})
    speaker_name = profile.get("name", source_id)

    # Collect all mentions from different fields
    all_mentions = []

    # 1. crypto_mentions (format: asset, ticker, action)
    for mention in data.get("crypto_mentions", []):
        all_mentions.append({
            "asset_name": mention.get("asset"),
            "ticker": mention.get("ticker"),
            "action": mention.get("action", "neutral"),
            "confidence": mention.get("confidence"),
            "reasoning": mention.get("reasoning"),
            "quotes": mention.get("quotes", []),
            "key_levels": mention.get("key_levels"),
            "asset_type_hint": "crypto",
        })

    # 2. stock_mentions (format: stock_name, ticker, action)
    for mention in data.get("stock_mentions", []):
        all_mentions.append({
            "asset_name": mention.get("stock_name"),
            "ticker": mention.get("ticker"),
            "action": mention.get("action", "neutral"),
            "confidence": mention.get("confidence"),
            "reasoning": mention.get("reasoning"),
            "quotes": mention.get("quotes", []),
            "key_levels": mention.get("valuation_notes"),
            "asset_type_hint": "stock",
        })

    # 3. recommendations (format: name, ticker, signal, date)
    for rec in data.get("recommendations", []):
        # Try to parse individual recommendation date
        rec_date = None
        if rec.get("date"):
            try:
                rec_date = date.fromisoformat(rec["date"][:10])
            except (ValueError, TypeError):
                pass

        all_mentions.append({
            "asset_name": rec.get("name"),
            "ticker": rec.get("ticker"),
            "action": rec.get("signal", rec.get("action", "neutral")),
            "confidence": rec.get("confidence"),
            "reasoning": rec.get("reasoning") or rec.get("thesis"),
            "quotes": rec.get("quotes", []),
            "key_levels": rec.get("valuation"),
            "asset_type_hint": "stock",
            "date": rec_date,  # Individual tweet date
        })

    # 4. core_holdings (format: name, ticker, signal, with nested recommendations)
    for holding in data.get("core_holdings", []):
        # Process each recommendation within the holding to get individual dates
        recommendations = holding.get("recommendations", [])
        if recommendations:
            for rec in recommendations:
                rec_date = None
                if rec.get("date"):
                    try:
                        rec_date = date.fromisoformat(rec["date"][:10])
                    except (ValueError, TypeError):
                        pass

                all_mentions.append({
                    "asset_name": holding.get("name"),
                    "ticker": holding.get("ticker"),
                    "action": rec.get("signal", holding.get("signal", "buy")),
                    "confidence": "high",
                    "reasoning": rec.get("reasoning") or rec.get("text"),
                    "quotes": [rec.get("text")] if rec.get("text") else [],
                    "key_levels": None,
                    "asset_type_hint": "stock",
                    "date": rec_date,
                })
        else:
            # Fallback: if no recommendations, create a signal for the holding itself
            all_mentions.append({
                "asset_name": holding.get("name"),
                "ticker": holding.get("ticker"),
                "action": holding.get("signal", "buy"),
                "confidence": "high",
                "reasoning": holding.get("thesis") or holding.get("reasoning") or holding.get("notes"),
                "quotes": [],
                "key_levels": None,
                "asset_type_hint": "stock",
            })

    # 5. other_positions (same format as core_holdings, with nested recommendations)
    for position in data.get("other_positions", []):
        recommendations = position.get("recommendations", [])
        if recommendations:
            for rec in recommendations:
                rec_date = None
                if rec.get("date"):
                    try:
                        rec_date = date.fromisoformat(rec["date"][:10])
                    except (ValueError, TypeError):
                        pass

                all_mentions.append({
                    "asset_name": position.get("name"),
                    "ticker": position.get("ticker"),
                    "action": rec.get("signal", position.get("signal", "neutral")),
                    "confidence": position.get("confidence", "medium"),
                    "reasoning": rec.get("reasoning") or rec.get("text"),
                    "quotes": [rec.get("text")] if rec.get("text") else [],
                    "key_levels": None,
                    "asset_type_hint": "stock",
                    "date": rec_date,
                })
        else:
            all_mentions.append({
                "asset_name": position.get("name"),
                "ticker": position.get("ticker"),
                "action": position.get("signal", "neutral"),
                "confidence": position.get("confidence", "medium"),
                "reasoning": position.get("thesis") or position.get("reasoning") or position.get("notes"),
                "quotes": [],
                "key_levels": None,
                "asset_type_hint": "stock",
            })

    # 6. negative_mentions (with nested recommendations)
    for mention in data.get("negative_mentions", []):
        recommendations = mention.get("recommendations", [])
        if recommendations:
            for rec in recommendations:
                rec_date = None
                if rec.get("date"):
                    try:
                        rec_date = date.fromisoformat(rec["date"][:10])
                    except (ValueError, TypeError):
                        pass

                all_mentions.append({
                    "asset_name": mention.get("name"),
                    "ticker": mention.get("ticker"),
                    "action": rec.get("signal", mention.get("signal", "avoid")),
                    "confidence": mention.get("confidence", "medium"),
                    "reasoning": rec.get("reasoning") or rec.get("text"),
                    "quotes": [rec.get("text")] if rec.get("text") else [],
                    "key_levels": None,
                    "asset_type_hint": "stock",
                    "date": rec_date,
                })
        else:
            all_mentions.append({
                "asset_name": mention.get("name"),
                "ticker": mention.get("ticker"),
                "action": mention.get("signal", "avoid"),
                "confidence": mention.get("confidence", "medium"),
                "reasoning": mention.get("reasoning") or mention.get("notes"),
                "quotes": [],
                "key_levels": None,
                "asset_type_hint": "stock",
            })

    # Process all mentions
    for mention in all_mentions:
        asset_name = mention.get("asset_name")
        ticker = mention.get("ticker", asset_name)

        if not asset_name:
            continue

        action = mention.get("action", "neutral")
        confidence = mention.get("confidence")
        reasoning = mention.get("reasoning")

        # Get quotes as a combined string
        quotes = mention.get("quotes", [])
        quote_text = " | ".join(quotes[:2]) if quotes else None  # Limit to first 2 quotes

        # Normalize signal
        signal_type = SignalNormalizer.normalize_podcast_action(action)  # Same mapping works
        signal_strength = SignalNormalizer.normalize_confidence(confidence)

        # Determine asset type
        if mention.get("asset_type_hint") == "crypto":
            asset_type = AssetType.CRYPTO
        else:
            asset_type = SignalNormalizer.detect_asset_type(ticker or "", asset_name)

        # Parse key levels if present
        key_levels = mention.get("key_levels")
        price_levels = None
        if key_levels:
            price_levels = [key_levels]

        # Use individual mention date if available, otherwise fall back to analysis date
        mention_date = mention.get("date") or analysis_date

        yield Signal(
            source_type=SourceType.TWITTER,
            source_id=source_id,
            content_id=f"{source_id}-{mention_date.isoformat()}",  # Include date for uniqueness
            content_date=mention_date,
            asset_symbol=ticker or asset_name.upper(),
            asset_name=asset_name,
            asset_type=asset_type,
            signal=signal_type,
            signal_strength=signal_strength,
            speaker_name=speaker_name,
            quote=quote_text,
            reasoning=reasoning,
            timestamp=None,
            original_action=action,
            price_levels=price_levels,
        )


def import_twitter_analyses(
    analyses_path: Path | None = None,
    dry_run: bool = False,
    limit: int | None = None,
) -> dict:
    """
    Import all Twitter analyses into unified_signals table.

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

    # Find all analysis JSON files
    json_files = sorted(analyses_path.glob("*-analysis.json"))

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
            for signal in parse_twitter_analysis(file_path):
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
        logger.info(f"Inserted {inserted} Twitter signals")

    return stats
