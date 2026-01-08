"""Performance tracking for recommendations.

Integrates with the prices module to calculate returns for recommendations.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import and_

from podstock.db.models import (
    Content,
    Price,
    Recommendation,
    RecommendationPerformance,
    Security,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def get_price_on_date(
    session: "Session",
    security_id: int,
    target_date: str,
    lookback_days: int = 5,
) -> float | None:
    """Get closing price for a security on or near a date.

    Args:
        session: Database session
        security_id: Security ID
        target_date: Target date (YYYY-MM-DD)
        lookback_days: Days to look back if exact date not found

    Returns:
        Close price or None if not found
    """
    # Try exact date first
    price = (
        session.query(Price)
        .filter_by(security_id=security_id, date=target_date)
        .first()
    )
    if price:
        return price.close

    # Look back a few days (for weekends/holidays)
    start_date = (
        datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=lookback_days)
    ).strftime("%Y-%m-%d")

    price = (
        session.query(Price)
        .filter(
            Price.security_id == security_id,
            Price.date >= start_date,
            Price.date <= target_date,
        )
        .order_by(Price.date.desc())
        .first()
    )

    return price.close if price else None


def calculate_return(price_at_rec: float, current_price: float) -> float:
    """Calculate percentage return."""
    if price_at_rec == 0:
        return 0.0
    return ((current_price - price_at_rec) / price_at_rec) * 100


def update_recommendation_performance(
    session: "Session",
    recommendation_id: int,
    force: bool = False,
) -> RecommendationPerformance | None:
    """Update performance data for a single recommendation.

    Args:
        session: Database session
        recommendation_id: Recommendation ID
        force: Recalculate even if already exists

    Returns:
        Updated RecommendationPerformance or None if not possible
    """
    # Get recommendation with related data
    rec = (
        session.query(Recommendation)
        .filter_by(id=recommendation_id)
        .first()
    )

    if not rec or not rec.security_id:
        return None

    # Get the recommendation date from content
    analysis = rec.analysis
    content = analysis.content if analysis else None
    if not content:
        return None

    rec_date = content.published_at
    if not rec_date:
        return None

    # Check existing performance
    perf = (
        session.query(RecommendationPerformance)
        .filter_by(recommendation_id=recommendation_id)
        .first()
    )

    if perf and not force:
        # Check if we need to update (not complete yet)
        if perf.is_complete:
            return perf

    # Get price at recommendation date
    price_at_rec = get_price_on_date(session, rec.security_id, rec_date)
    if not price_at_rec:
        return None

    # Calculate prices at different intervals
    today = datetime.now().date()
    rec_datetime = datetime.strptime(rec_date[:10], "%Y-%m-%d").date()
    days_since = (today - rec_datetime).days

    intervals = {
        "1d": 1,
        "7d": 7,
        "30d": 30,
        "90d": 90,
        "180d": 180,
        "365d": 365,
    }

    prices = {}
    returns = {}

    for interval_name, days in intervals.items():
        if days_since >= days:
            target = (rec_datetime + timedelta(days=days)).strftime("%Y-%m-%d")
            price = get_price_on_date(session, rec.security_id, target)
            if price:
                prices[interval_name] = price
                returns[interval_name] = calculate_return(price_at_rec, price)

    # Create or update performance record
    if not perf:
        perf = RecommendationPerformance(recommendation_id=recommendation_id)
        session.add(perf)

    perf.price_at_rec = price_at_rec
    perf.price_1d = prices.get("1d")
    perf.price_7d = prices.get("7d")
    perf.price_30d = prices.get("30d")
    perf.price_90d = prices.get("90d")
    perf.price_180d = prices.get("180d")
    perf.price_365d = prices.get("365d")
    perf.return_1d = returns.get("1d")
    perf.return_7d = returns.get("7d")
    perf.return_30d = returns.get("30d")
    perf.return_90d = returns.get("90d")
    perf.return_180d = returns.get("180d")
    perf.return_365d = returns.get("365d")
    perf.calculated_at = datetime.now().isoformat()
    perf.is_complete = days_since >= 365 and perf.price_365d is not None

    return perf


def update_all_performance(
    session: "Session",
    limit: int | None = None,
    force: bool = False,
) -> dict[str, int]:
    """Update performance for all recommendations with matched securities.

    Args:
        session: Database session
        limit: Max recommendations to process
        force: Recalculate even if already exists

    Returns:
        Dict with counts: updated, skipped, failed
    """
    # Get recommendations with securities that need updating
    query = (
        session.query(Recommendation.id)
        .filter(Recommendation.security_id.isnot(None))
    )

    if not force:
        # Only get those without complete performance
        query = query.outerjoin(
            RecommendationPerformance,
            Recommendation.id == RecommendationPerformance.recommendation_id,
        ).filter(
            (RecommendationPerformance.id.is_(None)) |
            (RecommendationPerformance.is_complete == 0)
        )

    if limit:
        query = query.limit(limit)

    rec_ids = [r[0] for r in query.all()]

    results = {"updated": 0, "skipped": 0, "failed": 0}

    for rec_id in rec_ids:
        try:
            perf = update_recommendation_performance(session, rec_id, force=force)
            if perf:
                results["updated"] += 1
            else:
                results["skipped"] += 1
        except Exception:
            results["failed"] += 1

    return results


def import_prices_from_tracker(
    session: "Session",
    data_dir: str | None = None,
) -> dict[str, int]:
    """Import historical prices from the prices module storage.

    This reads from the existing prices JSON files and imports them
    into the database prices table.

    Args:
        session: Database session
        data_dir: Optional data directory path

    Returns:
        Dict with counts: imported, skipped
    """
    from pathlib import Path
    from podstock.db.models import Security, Price
    import json

    if data_dir:
        prices_dir = Path(data_dir) / "prices" / "history"
    else:
        prices_dir = Path(__file__).parent.parent.parent.parent / "data" / "prices" / "history"

    if not prices_dir.exists():
        return {"imported": 0, "skipped": 0, "error": "prices directory not found"}

    results = {"imported": 0, "skipped": 0}

    # Get all securities
    securities = {s.ticker: s.id for s in session.query(Security).all()}

    for price_file in prices_dir.glob("*.json"):
        try:
            data = json.loads(price_file.read_text())
            ticker = data.get("ticker")

            if ticker not in securities:
                results["skipped"] += 1
                continue

            security_id = securities[ticker]

            for price_data in data.get("prices", []):
                date = price_data.get("date")
                if not date:
                    continue

                # Check if already exists
                existing = (
                    session.query(Price)
                    .filter_by(security_id=security_id, date=date)
                    .first()
                )
                if existing:
                    continue

                price = Price(
                    security_id=security_id,
                    date=date,
                    open=price_data.get("open"),
                    high=price_data.get("high"),
                    low=price_data.get("low"),
                    close=price_data.get("close"),
                    adj_close=price_data.get("adj_close"),
                    volume=price_data.get("volume"),
                    source="yahoo",
                )
                session.add(price)
                results["imported"] += 1

        except Exception:
            results["skipped"] += 1

    return results


def fetch_prices_from_yahoo(
    session: "Session",
    progress_callback=None,
    full_history: bool = False,
    force: bool = False,
) -> dict[str, int]:
    """Fetch historical prices from Yahoo Finance for all securities with recommendations.

    This function:
    1. Gets all unique recommendation dates per security
    2. Fetches price data from Yahoo Finance covering those dates
    3. Stores prices in the database

    Args:
        session: Database session
        progress_callback: Optional callback(current, total, ticker) for progress
        full_history: If True, download full history from 2010 instead of just rec dates
        force: If True, re-download even if prices already exist for this security

    Returns:
        Dict with counts: fetched, skipped, failed, securities_processed
    """
    from podstock.prices.clients.yahoo import YahooFinanceClient

    results = {"fetched": 0, "skipped": 0, "failed": 0, "securities_processed": 0}

    # Get all securities with recommendations
    securities = (
        session.query(Security)
        .join(Recommendation, Recommendation.security_id == Security.id)
        .distinct()
        .all()
    )

    total = len(securities)
    client = YahooFinanceClient(rate_limit_delay=0.5)

    for idx, security in enumerate(securities):
        if progress_callback:
            progress_callback(idx + 1, total, security.ticker)

        # Check if we already have prices for this security
        if not force:
            existing_count = session.query(Price).filter_by(security_id=security.id).count()
            if existing_count > 0:
                results["skipped"] += 1
                continue

        # Determine date range
        if full_history:
            # Download full history from 2010
            start_dt = datetime(2010, 1, 1)
            end_dt = datetime.now()
        else:
            # Get recommendation dates through analysis relationship
            rec_dates = []
            for rec in session.query(Recommendation).filter_by(security_id=security.id).all():
                if rec.analysis and rec.analysis.content:
                    pub_date = rec.analysis.content.published_at
                    if pub_date:
                        rec_dates.append(pub_date[:10])  # YYYY-MM-DD

            if not rec_dates:
                results["skipped"] += 1
                continue

            # Get min/max dates
            min_date = min(rec_dates)
            max_date = max(rec_dates)

            # Add buffer for performance calculations (365 days after last rec)
            try:
                start_dt = datetime.strptime(min_date, "%Y-%m-%d") - timedelta(days=5)
                end_dt = min(
                    datetime.strptime(max_date, "%Y-%m-%d") + timedelta(days=400),
                    datetime.now()
                )
            except ValueError:
                results["failed"] += 1
                continue

        # Fetch prices from Yahoo
        try:
            snapshots = client.get_price_range(security.ticker, start_dt, end_dt)

            if not snapshots:
                results["failed"] += 1
                continue

            for snap in snapshots:
                date_str = snap.timestamp.strftime("%Y-%m-%d")

                # Check if already exists (for incremental updates)
                existing = (
                    session.query(Price)
                    .filter_by(security_id=security.id, date=date_str)
                    .first()
                )
                if existing:
                    continue

                price = Price(
                    security_id=security.id,
                    date=date_str,
                    open=snap.open_price,
                    high=snap.high_price,
                    low=snap.low_price,
                    close=snap.price,
                    adj_close=snap.price,  # Yahoo adjusted close
                    volume=snap.volume,
                    source="yahoo",
                )
                session.add(price)
                results["fetched"] += 1

            results["securities_processed"] += 1

            # Commit periodically
            if (idx + 1) % 10 == 0:
                session.commit()

        except Exception:
            results["failed"] += 1
            continue

    # Final commit
    session.commit()

    return results


def update_current_prices(
    session: "Session",
    progress_callback=None,
) -> dict[str, int]:
    """Update return_current using the latest available price from local database.

    For each recommendation with performance data, calculate return from
    price_at_rec to the most recent price available in the prices table.

    Args:
        session: Database session
        progress_callback: Optional callback(current, total) for progress

    Returns:
        Dict with counts: updated, skipped
    """
    from sqlalchemy import func

    results = {"updated": 0, "skipped": 0}

    # Get all performance records with price_at_rec
    perfs = (
        session.query(RecommendationPerformance)
        .filter(RecommendationPerformance.price_at_rec.isnot(None))
        .all()
    )

    total = len(perfs)

    # Cache latest prices per security to avoid repeated queries
    latest_prices: dict[int, tuple[float, str]] = {}

    for idx, perf in enumerate(perfs):
        if progress_callback:
            progress_callback(idx + 1, total)

        rec = perf.recommendation
        if not rec or not rec.security_id:
            results["skipped"] += 1
            continue

        security_id = rec.security_id

        # Get latest price from cache or query
        if security_id not in latest_prices:
            latest = (
                session.query(Price.close, Price.date)
                .filter(Price.security_id == security_id)
                .order_by(Price.date.desc())
                .first()
            )
            if latest:
                latest_prices[security_id] = (latest.close, latest.date)
            else:
                latest_prices[security_id] = (None, None)

        price, date = latest_prices[security_id]

        if price and perf.price_at_rec:
            perf.price_current = price
            perf.price_current_date = date
            perf.return_current = calculate_return(perf.price_at_rec, price)
            results["updated"] += 1
        else:
            results["skipped"] += 1

        # Commit periodically
        if (idx + 1) % 1000 == 0:
            session.commit()

    session.commit()
    return results
