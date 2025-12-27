"""Enrich unified signals with entry prices from Yahoo Finance."""

import logging
from datetime import datetime
from pathlib import Path

from ..db.engine import get_session
from ..db.models import UnifiedSignal
from ..prices.clients.yahoo import YahooFinanceClient
from ..prices.ticker_mapping import TickerMapper
from .models import AssetType

logger = logging.getLogger(__name__)

# Default path to ticker mapping
DEFAULT_MAPPING_PATH = Path(__file__).parent.parent.parent.parent / "data" / "prices" / "ticker_mapping.json"


def enrich_signals_with_prices(
    since: str | None = None,
    dry_run: bool = False,
    limit: int | None = None,
    mapping_path: Path | None = None,
) -> dict:
    """
    Enrich unified signals with entry prices from Yahoo Finance.

    Args:
        since: Only enrich signals from this date onwards (ISO format)
        dry_run: If True, don't update database
        limit: Maximum number of signals to process
        mapping_path: Path to ticker mapping JSON file

    Returns:
        Dict with enrichment statistics
    """
    if mapping_path is None:
        mapping_path = DEFAULT_MAPPING_PATH

    ticker_mapper = TickerMapper(mapping_path)
    yahoo_client = YahooFinanceClient(rate_limit_delay=0.3)

    stats = {
        "total_signals": 0,
        "already_enriched": 0,
        "enriched": 0,
        "no_ticker": 0,
        "no_price": 0,
        "errors": 0,
    }

    with get_session() as session:
        # Build query
        query = session.query(UnifiedSignal).filter(
            UnifiedSignal.entry_price.is_(None)
        )

        if since:
            query = query.filter(UnifiedSignal.content_date >= since)

        query = query.order_by(UnifiedSignal.content_date.desc())

        if limit:
            query = query.limit(limit)

        signals = query.all()
        stats["total_signals"] = len(signals)

        logger.info(f"Processing {len(signals)} signals without entry prices")

        for i, signal in enumerate(signals, 1):
            if signal.entry_price is not None:
                stats["already_enriched"] += 1
                continue

            # Resolve Yahoo ticker
            yahoo_ticker = _resolve_yahoo_ticker(
                signal.asset_symbol,
                signal.asset_name,
                signal.asset_type,
                ticker_mapper,
            )

            if not yahoo_ticker:
                stats["no_ticker"] += 1
                if i <= 10:  # Only log first 10
                    logger.debug(f"No ticker for: {signal.asset_name} ({signal.asset_symbol})")
                continue

            # Fetch historical price
            try:
                signal_date = datetime.fromisoformat(signal.content_date)
                price_snapshot = yahoo_client.get_historical_price(yahoo_ticker, signal_date)

                if price_snapshot is None:
                    stats["no_price"] += 1
                    if i <= 10:
                        logger.debug(f"No price for {yahoo_ticker} on {signal.content_date}")
                    continue

                if not dry_run:
                    signal.yahoo_ticker = yahoo_ticker
                    signal.entry_price = price_snapshot.price
                    signal.entry_price_currency = price_snapshot.currency

                stats["enriched"] += 1

                if i % 50 == 0:
                    logger.info(f"Processed {i}/{len(signals)} signals...")
                    if not dry_run:
                        session.commit()

            except Exception as e:
                stats["errors"] += 1
                logger.warning(f"Error enriching {signal.id}: {e}")

        if not dry_run:
            session.commit()

    logger.info(
        f"Enrichment complete: {stats['enriched']} enriched, "
        f"{stats['no_ticker']} no ticker, {stats['no_price']} no price"
    )

    return stats


def _resolve_yahoo_ticker(
    asset_symbol: str,
    asset_name: str,
    asset_type: str,
    ticker_mapper: TickerMapper,
) -> str | None:
    """
    Resolve an asset to its Yahoo Finance ticker.

    Args:
        asset_symbol: The asset symbol (e.g., "BTC", "EVO")
        asset_name: The asset name (e.g., "Bitcoin", "Evolution")
        asset_type: The asset type (e.g., "crypto", "stock")
        ticker_mapper: TickerMapper instance for stock lookups

    Returns:
        Yahoo Finance ticker or None if not found
    """
    # Crypto name to Yahoo symbol mapping
    CRYPTO_SYMBOLS = {
        "BITCOIN": "BTC",
        "ETHEREUM": "ETH",
        "LITECOIN": "LTC",
        "RIPPLE": "XRP",
        "CARDANO": "ADA",
        "POLKADOT": "DOT",
        "DOGECOIN": "DOGE",
        "SOLANA": "SOL",
        "CHAINLINK": "LINK",
        "AVALANCHE": "AVAX",
        "POLYGON": "MATIC",
        "ALGORAND": "ALGO",
        "STELLAR": "XLM",
        "COSMOS": "ATOM",
    }

    # Handle crypto
    if asset_type == AssetType.CRYPTO.value or asset_type == "crypto":
        symbol = asset_symbol.upper()
        # Map full names to ticker symbols
        if symbol in CRYPTO_SYMBOLS:
            symbol = CRYPTO_SYMBOLS[symbol]
        # Skip non-tradeable crypto references
        if symbol in ("STABLECOINS", "COIN", "COINSHARES", "ARCANE_CRYPTO"):
            return None
        # Standard crypto suffix
        return f"{symbol}-USD"

    # Try to map stock using ticker_mapper
    # First try asset_name (more descriptive)
    yahoo_ticker = ticker_mapper.lookup(asset_name, fuzzy_threshold=85)
    if yahoo_ticker:
        return yahoo_ticker

    # Then try asset_symbol
    yahoo_ticker = ticker_mapper.lookup(asset_symbol, fuzzy_threshold=85)
    if yahoo_ticker:
        return yahoo_ticker

    # Try common patterns for Swedish stocks
    if not "." in asset_symbol and not "-" in asset_symbol:
        # Try with .ST suffix
        swedish_ticker = f"{asset_symbol.upper()}.ST"
        # We could validate this with Yahoo, but for speed we skip
        # The price fetch will fail if it's invalid
        return None  # Don't guess, require mapping

    return None


def get_enrichment_coverage(since: str | None = None) -> dict:
    """
    Get statistics about price enrichment coverage.

    Args:
        since: Only check signals from this date onwards

    Returns:
        Dict with coverage statistics
    """
    with get_session() as session:
        query = session.query(UnifiedSignal)

        if since:
            query = query.filter(UnifiedSignal.content_date >= since)

        total = query.count()
        enriched = query.filter(UnifiedSignal.entry_price.is_not(None)).count()

        # Group by asset_type
        from sqlalchemy import func
        type_stats = (
            query.with_entities(
                UnifiedSignal.asset_type,
                func.count(UnifiedSignal.id).label("total"),
                func.count(UnifiedSignal.entry_price).label("enriched"),
            )
            .group_by(UnifiedSignal.asset_type)
            .all()
        )

        return {
            "total_signals": total,
            "enriched_signals": enriched,
            "coverage_percent": round(100 * enriched / total, 1) if total > 0 else 0,
            "by_asset_type": {
                row[0]: {"total": row[1], "enriched": row[2]}
                for row in type_stats
            },
        }
