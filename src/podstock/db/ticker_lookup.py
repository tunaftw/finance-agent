"""Security ticker lookup and resolution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import func

from podstock.db.models import PendingSecurity, Recommendation, Security, SecurityAlias

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


# Ticker suffix to exchange/market mapping
SUFFIX_MAP = {
    ".ST": ("OMX", "sweden", "SEK"),
    ".CO": ("OMX", "denmark", "DKK"),
    ".HE": ("OMX", "finland", "EUR"),
    ".OL": ("OSE", "norway", "NOK"),
    ".L": ("LSE", "europe", "GBP"),
    "-USD": ("CRYPTO", "crypto", "USD"),
}


def parse_ticker_suffix(ticker: str) -> tuple[str, str, str]:
    """Parse ticker suffix to determine exchange and market.

    Args:
        ticker: Ticker symbol like 'EVO.ST' or 'AAPL'

    Returns:
        Tuple of (exchange, market, currency)
    """
    for suffix, (exchange, market, currency) in SUFFIX_MAP.items():
        if ticker.endswith(suffix):
            return exchange, market, currency

    # Default: USA
    return "NYSE", "usa", "USD"


def get_or_create_security(
    session: "Session",
    ticker: str,
    name: str,
    exchange: str | None = None,
    market: str | None = None,
    currency: str | None = None,
    asset_type: str = "stock",
) -> tuple[Security, bool]:
    """Get existing security or create new one.

    Args:
        session: Database session
        ticker: Ticker symbol
        name: Company name
        exchange: Exchange code (optional, auto-detected from ticker)
        market: Market region (optional, auto-detected)
        currency: Currency code (optional, auto-detected)
        asset_type: 'stock' or 'crypto'

    Returns:
        Tuple of (Security, was_created)
    """
    # Auto-detect from ticker suffix if not provided
    if exchange is None or market is None or currency is None:
        auto_exchange, auto_market, auto_currency = parse_ticker_suffix(ticker)
        exchange = exchange or auto_exchange
        market = market or auto_market
        currency = currency or auto_currency

    # Check for existing security
    existing = session.query(Security).filter_by(ticker=ticker, exchange=exchange).first()

    if existing:
        return existing, False

    # Create new security
    security = Security(
        ticker=ticker,
        name=name,
        exchange=exchange,
        market=market,
        currency=currency,
        asset_type=asset_type,
    )
    session.add(security)
    session.flush()  # Get the ID

    return security, True


def add_alias(
    session: "Session",
    security_id: int,
    alias: str,
    alias_type: str = "name",
) -> bool:
    """Add an alias for a security.

    Args:
        session: Database session
        security_id: ID of the security
        alias: Alias string (will be lowercased)
        alias_type: Type of alias ('name', 'ticker_variant', 'twitter')

    Returns:
        True if alias was created, False if it already exists
    """
    alias_lower = alias.lower().strip()

    # Check if alias already exists
    existing = session.query(SecurityAlias).filter(
        func.lower(SecurityAlias.alias) == alias_lower
    ).first()

    if existing:
        return False

    security_alias = SecurityAlias(
        security_id=security_id,
        alias=alias_lower,
        alias_type=alias_type,
    )
    session.add(security_alias)
    return True


def resolve_security(
    session: "Session",
    name: str,
    ticker: str | None = None,
) -> Security | None:
    """Try to resolve a stock name/ticker to a Security.

    Lookup order:
    1. Exact ticker match
    2. Ticker with common suffixes (.ST, .CO, .HE, .OL, -USD)
    3. Exact name match (case-insensitive)
    4. Alias match (case-insensitive)

    Args:
        session: Database session
        name: Stock name from recommendation
        ticker: Optional ticker from recommendation

    Returns:
        Security if found, None otherwise
    """
    name_lower = name.lower().strip()

    # 1. Try ticker match first (exact)
    if ticker:
        ticker_upper = ticker.upper()
        security = session.query(Security).filter(
            func.upper(Security.ticker) == ticker_upper
        ).first()
        if security:
            return security

        # 2. Try ticker with common suffixes
        suffixes = [".ST", ".CO", ".HE", ".OL", ".L", "-USD"]
        for suffix in suffixes:
            security = session.query(Security).filter(
                func.upper(Security.ticker) == ticker_upper + suffix
            ).first()
            if security:
                return security

    # 3. Try exact name match
    security = session.query(Security).filter(
        func.lower(Security.name) == name_lower
    ).first()
    if security:
        return security

    # 4. Try alias match
    alias = session.query(SecurityAlias).filter(
        func.lower(SecurityAlias.alias) == name_lower
    ).first()
    if alias:
        return alias.security

    return None


def seed_from_ticker_mapping(
    session: "Session",
    mapping_path: Path,
) -> dict[str, int]:
    """Seed securities from ticker_mapping.json.

    Args:
        session: Database session
        mapping_path: Path to ticker_mapping.json

    Returns:
        Dict with counts: securities_created, securities_updated, aliases_created
    """
    data = json.loads(mapping_path.read_text())

    result = {
        "securities_created": 0,
        "securities_updated": 0,
        "aliases_created": 0,
    }

    # Get crypto symbols for asset_type detection
    crypto_symbols = set(data.get("crypto_symbols", []))

    # Track which securities we've created to avoid duplicates
    ticker_to_security: dict[str, Security] = {}

    # Process main mappings: name -> ticker
    for name, ticker in data.get("mappings", {}).items():
        # Determine asset type
        asset_type = "crypto" if ticker in crypto_symbols else "stock"

        # Get or create the security
        if ticker not in ticker_to_security:
            security, was_created = get_or_create_security(
                session,
                ticker=ticker,
                name=name,
                asset_type=asset_type,
            )
            ticker_to_security[ticker] = security

            if was_created:
                result["securities_created"] += 1
            else:
                result["securities_updated"] += 1
        else:
            security = ticker_to_security[ticker]

        # Add name as alias if different from canonical name
        if name.lower() != security.name.lower():
            if add_alias(session, security.id, name):
                result["aliases_created"] += 1

    # Process explicit aliases
    for alias, canonical_name in data.get("aliases", {}).items():
        # Find the security by canonical name
        security = session.query(Security).filter(
            func.lower(Security.name) == canonical_name.lower()
        ).first()

        if security:
            if add_alias(session, security.id, alias):
                result["aliases_created"] += 1

    return result


def link_recommendations_to_securities(
    session: "Session",
    progress_callback=None,
) -> dict[str, int]:
    """Link unlinked recommendations to securities.

    For each recommendation without a security_id:
    1. Try to resolve using raw_stock_name and raw_ticker
    2. If resolved, update security_id
    3. If not resolved, track for pending_securities

    Args:
        session: Database session
        progress_callback: Optional callback(current, total) for progress

    Returns:
        Dict with counts: linked, pending, skipped
    """
    result = {
        "linked": 0,
        "pending": 0,
        "skipped": 0,
    }

    # Get all recommendations without security_id
    recs = (
        session.query(Recommendation)
        .filter(Recommendation.security_id.is_(None))
        .all()
    )

    total = len(recs)

    # Track pending to add at end (avoid duplicate key issues during loop)
    pending_to_add: dict[tuple[str, str | None], dict] = {}

    for idx, rec in enumerate(recs):
        if progress_callback:
            progress_callback(idx + 1, total)

        # Skip if no name
        if not rec.raw_stock_name:
            result["skipped"] += 1
            continue

        # Try to resolve
        security = resolve_security(session, rec.raw_stock_name, rec.raw_ticker)

        if security:
            rec.security_id = security.id
            result["linked"] += 1
        else:
            # Track for pending (aggregate by name+ticker)
            key = (rec.raw_stock_name, rec.raw_ticker)
            if key not in pending_to_add:
                pending_to_add[key] = {
                    "raw_name": rec.raw_stock_name,
                    "raw_ticker": rec.raw_ticker,
                    "context": rec.reasoning[:200] if rec.reasoning else None,
                    "count": 0,
                }
            pending_to_add[key]["count"] += 1
            result["pending"] += 1

        # Commit periodically
        if (idx + 1) % 500 == 0:
            session.commit()

    # Now add/update pending securities
    for key, data in pending_to_add.items():
        existing = (
            session.query(PendingSecurity)
            .filter(
                PendingSecurity.raw_name == data["raw_name"],
                PendingSecurity.raw_ticker == data["raw_ticker"],
            )
            .first()
        )

        if existing:
            existing.occurrence_count += data["count"]
        else:
            pending = PendingSecurity(
                raw_name=data["raw_name"],
                raw_ticker=data["raw_ticker"],
                context=data["context"],
                occurrence_count=data["count"],
            )
            session.add(pending)

    session.commit()
    return result


def _create_or_update_pending(
    session: "Session",
    raw_name: str,
    raw_ticker: str | None,
    context: str | None = None,
) -> PendingSecurity | None:
    """Create or update a pending security entry.

    Args:
        session: Database session
        raw_name: Raw stock name
        raw_ticker: Raw ticker (may be None)
        context: Context/reasoning for the recommendation

    Returns:
        The pending security entry or None if skipped
    """
    # Check if already exists - use exact match for raw_name since unique constraint is case-sensitive
    existing = (
        session.query(PendingSecurity)
        .filter(
            PendingSecurity.raw_name == raw_name,
            PendingSecurity.raw_ticker == raw_ticker,
        )
        .first()
    )

    if existing:
        existing.occurrence_count += 1
        return existing

    # Also check case-insensitive to avoid near-duplicates
    existing_similar = (
        session.query(PendingSecurity)
        .filter(
            func.lower(PendingSecurity.raw_name) == raw_name.lower(),
            PendingSecurity.raw_ticker == raw_ticker,
        )
        .first()
    )

    if existing_similar:
        existing_similar.occurrence_count += 1
        return existing_similar

    # Create new
    try:
        pending = PendingSecurity(
            raw_name=raw_name,
            raw_ticker=raw_ticker,
            context=context,
            occurrence_count=1,
        )
        session.add(pending)
        session.flush()
        return pending
    except Exception:
        # Unique constraint violation - another thread/process created it
        session.rollback()
        return None
