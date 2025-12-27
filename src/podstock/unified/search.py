"""Unified search API for cross-source queries."""

import json
import logging
from dataclasses import dataclass
from datetime import date
from typing import Iterator, Optional

from sqlalchemy import and_, or_

from ..db.engine import get_session
from ..db.models import UnifiedSignal
from .models import AssetType, Signal, SignalStrength, SignalType, SourceType

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result with signal and metadata."""

    signal: Signal
    source_name: str  # Human-readable source name


def search_signals(
    asset: Optional[str] = None,
    speaker: Optional[str] = None,
    signal_type: Optional[str] = None,
    source_type: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Signal]:
    """
    Search unified signals across all sources.

    Args:
        asset: Filter by asset symbol (partial match, case-insensitive)
        speaker: Filter by speaker name (partial match, case-insensitive)
        signal_type: Filter by signal type ('bullish', 'bearish', 'neutral')
        source_type: Filter by source type ('podcast', 'youtube', 'twitter')
        from_date: Filter by minimum date (inclusive)
        to_date: Filter by maximum date (inclusive)
        limit: Maximum number of results
        offset: Skip first N results (for pagination)

    Returns:
        List of Signal objects matching the criteria
    """
    with get_session() as session:
        query = session.query(UnifiedSignal)

        # Apply filters
        filters = []

        if asset:
            asset_upper = asset.upper()
            filters.append(
                or_(
                    UnifiedSignal.asset_symbol.ilike(f"%{asset_upper}%"),
                    UnifiedSignal.asset_name.ilike(f"%{asset}%"),
                )
            )

        if speaker:
            filters.append(UnifiedSignal.speaker_name.ilike(f"%{speaker}%"))

        if signal_type:
            filters.append(UnifiedSignal.signal == signal_type.lower())

        if source_type:
            filters.append(UnifiedSignal.source_type == source_type.lower())

        if from_date:
            filters.append(UnifiedSignal.content_date >= from_date.isoformat())

        if to_date:
            filters.append(UnifiedSignal.content_date <= to_date.isoformat())

        if filters:
            query = query.filter(and_(*filters))

        # Order by date descending (most recent first)
        query = query.order_by(UnifiedSignal.content_date.desc())

        # Apply pagination
        query = query.offset(offset).limit(limit)

        # Execute and convert to Signal objects
        results = []
        for row in query.all():
            try:
                signal = Signal(
                    source_type=SourceType(row.source_type),
                    source_id=row.source_id,
                    content_id=row.content_id,
                    content_date=date.fromisoformat(row.content_date),
                    asset_symbol=row.asset_symbol,
                    asset_name=row.asset_name,
                    asset_type=AssetType(row.asset_type),
                    signal=SignalType(row.signal),
                    signal_strength=SignalStrength(row.signal_strength),
                    speaker_name=row.speaker_name,
                    speaker_id=row.speaker_id,
                    quote=row.quote,
                    reasoning=row.reasoning,
                    timestamp=row.timestamp,
                    original_action=row.original_action,
                    price_levels=json.loads(row.price_levels) if row.price_levels else None,
                    yahoo_ticker=row.yahoo_ticker,
                    entry_price=row.entry_price,
                    entry_price_currency=row.entry_price_currency,
                    id=row.id,
                )
                results.append(signal)
            except (ValueError, TypeError) as e:
                logger.warning(f"Error converting signal {row.id}: {e}")

        return results


def count_signals(
    asset: Optional[str] = None,
    speaker: Optional[str] = None,
    signal_type: Optional[str] = None,
    source_type: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> int:
    """Count signals matching the criteria."""
    with get_session() as session:
        from sqlalchemy import func

        query = session.query(func.count(UnifiedSignal.id))

        filters = []

        if asset:
            asset_upper = asset.upper()
            filters.append(
                or_(
                    UnifiedSignal.asset_symbol.ilike(f"%{asset_upper}%"),
                    UnifiedSignal.asset_name.ilike(f"%{asset}%"),
                )
            )

        if speaker:
            filters.append(UnifiedSignal.speaker_name.ilike(f"%{speaker}%"))

        if signal_type:
            filters.append(UnifiedSignal.signal == signal_type.lower())

        if source_type:
            filters.append(UnifiedSignal.source_type == source_type.lower())

        if from_date:
            filters.append(UnifiedSignal.content_date >= from_date.isoformat())

        if to_date:
            filters.append(UnifiedSignal.content_date <= to_date.isoformat())

        if filters:
            query = query.filter(and_(*filters))

        return query.scalar() or 0


def get_signal_stats(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> dict:
    """
    Get aggregate statistics for signals.

    Returns:
        Dict with counts by source, signal type, and top assets
    """
    with get_session() as session:
        from sqlalchemy import func

        # Base query with optional date filter
        base_filter = []
        if from_date:
            base_filter.append(UnifiedSignal.content_date >= from_date.isoformat())
        if to_date:
            base_filter.append(UnifiedSignal.content_date <= to_date.isoformat())

        # Total count
        total_query = session.query(func.count(UnifiedSignal.id))
        if base_filter:
            total_query = total_query.filter(and_(*base_filter))
        total = total_query.scalar() or 0

        # By source type
        source_query = session.query(
            UnifiedSignal.source_type,
            func.count(UnifiedSignal.id)
        ).group_by(UnifiedSignal.source_type)
        if base_filter:
            source_query = source_query.filter(and_(*base_filter))
        by_source = dict(source_query.all())

        # By signal type
        signal_query = session.query(
            UnifiedSignal.signal,
            func.count(UnifiedSignal.id)
        ).group_by(UnifiedSignal.signal)
        if base_filter:
            signal_query = signal_query.filter(and_(*base_filter))
        by_signal = dict(signal_query.all())

        # Top assets
        asset_query = session.query(
            UnifiedSignal.asset_symbol,
            func.count(UnifiedSignal.id).label("count")
        ).group_by(UnifiedSignal.asset_symbol).order_by(
            func.count(UnifiedSignal.id).desc()
        ).limit(10)
        if base_filter:
            asset_query = asset_query.filter(and_(*base_filter))
        top_assets = [{"symbol": row[0], "count": row[1]} for row in asset_query.all()]

        # Top speakers
        speaker_query = session.query(
            UnifiedSignal.speaker_name,
            func.count(UnifiedSignal.id).label("count")
        ).group_by(UnifiedSignal.speaker_name).order_by(
            func.count(UnifiedSignal.id).desc()
        ).limit(10)
        if base_filter:
            speaker_query = speaker_query.filter(and_(*base_filter))
        top_speakers = [{"name": row[0], "count": row[1]} for row in speaker_query.all()]

        return {
            "total": total,
            "by_source": by_source,
            "by_signal": by_signal,
            "top_assets": top_assets,
            "top_speakers": top_speakers,
        }


def format_signal_output(signal: Signal, verbose: bool = False) -> str:
    """Format a signal for CLI output."""
    # Emoji for signal type
    signal_emoji = {
        SignalType.BULLISH: "+",
        SignalType.BEARISH: "-",
        SignalType.NEUTRAL: "~",
    }

    emoji = signal_emoji.get(signal.signal, "?")

    # Format date
    date_str = signal.content_date.isoformat()

    # Format entry price if available
    price_str = ""
    if signal.entry_price is not None:
        currency = signal.entry_price_currency or ""
        if signal.entry_price >= 1000:
            price_str = f" @ {signal.entry_price:,.0f} {currency}"
        elif signal.entry_price >= 1:
            price_str = f" @ {signal.entry_price:.2f} {currency}"
        else:
            price_str = f" @ {signal.entry_price:.4f} {currency}"

    # Basic output
    output = f"[{emoji}] {date_str} | {signal.asset_symbol:8}{price_str:15} | {signal.speaker_name:20} | {signal.source_type.value:8}"

    if verbose and signal.reasoning:
        # Truncate reasoning to 80 chars
        reasoning = signal.reasoning[:80] + "..." if len(signal.reasoning) > 80 else signal.reasoning
        output += f"\n    {reasoning}"

    if verbose and signal.quote:
        quote = signal.quote[:80] + "..." if len(signal.quote) > 80 else signal.quote
        output += f"\n    \"{quote}\""

    return output
