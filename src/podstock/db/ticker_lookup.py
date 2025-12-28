"""Security ticker lookup and resolution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import func

from podstock.db.models import Security, SecurityAlias

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
    2. Exact name match (case-insensitive)
    3. Alias match (case-insensitive)

    Args:
        session: Database session
        name: Stock name from recommendation
        ticker: Optional ticker from recommendation

    Returns:
        Security if found, None otherwise
    """
    name_lower = name.lower().strip()

    # 1. Try ticker match first
    if ticker:
        security = session.query(Security).filter(
            func.lower(Security.ticker) == ticker.lower()
        ).first()
        if security:
            return security

    # 2. Try exact name match
    security = session.query(Security).filter(
        func.lower(Security.name) == name_lower
    ).first()
    if security:
        return security

    # 3. Try alias match
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
