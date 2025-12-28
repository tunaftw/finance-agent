"""Common database queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import and_, func, or_

from podstock.db.models import (
    Analysis,
    Content,
    Recommendation,
    Security,
    Source,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass
class RecommendationResult:
    """Result from recommendation search."""

    id: int
    stock_name: str
    ticker: str | None
    action: str
    confidence: str | None
    speaker: str | None
    reasoning: str | None
    date: str
    source_id: str
    source_name: str
    content_title: str | None


def search_recommendations(
    session: "Session",
    stock: str | None = None,
    ticker: str | None = None,
    action: str | None = None,
    since: str | None = None,
    speaker: str | None = None,
    source_id: str | None = None,
    limit: int = 20,
) -> list[RecommendationResult]:
    """Search recommendations with various filters.

    Args:
        session: Database session
        stock: Stock name (partial match)
        ticker: Ticker symbol
        action: Action type (buy, sell, hold, watch, avoid)
        since: Date string (YYYY-MM-DD)
        speaker: Speaker name (partial match)
        source_id: Source ID filter
        limit: Maximum results

    Returns:
        List of RecommendationResult
    """
    query = (
        session.query(
            Recommendation,
            Content.published_at,
            Content.title,
            Source.id,
            Source.name,
            Security.ticker,
        )
        .join(Analysis, Recommendation.analysis_id == Analysis.id)
        .join(Content, Analysis.content_id == Content.id)
        .join(Source, Content.source_id == Source.id)
        .outerjoin(Security, Recommendation.security_id == Security.id)
    )

    # Apply filters
    if stock:
        query = query.filter(
            or_(
                Recommendation.raw_stock_name.ilike(f"%{stock}%"),
                Security.name.ilike(f"%{stock}%"),
            )
        )

    if ticker:
        query = query.filter(
            or_(
                Recommendation.raw_ticker.ilike(f"%{ticker}%"),
                Security.ticker.ilike(f"%{ticker}%"),
            )
        )

    if action:
        query = query.filter(Recommendation.action == action.lower())

    if since:
        query = query.filter(Content.published_at >= since)

    if speaker:
        query = query.filter(Recommendation.speaker.ilike(f"%{speaker}%"))

    if source_id:
        query = query.filter(Source.id == source_id)

    # Order by date descending
    query = query.order_by(Content.published_at.desc()).limit(limit)

    results = []
    for rec, published_at, title, src_id, src_name, sec_ticker in query.all():
        results.append(
            RecommendationResult(
                id=rec.id,
                stock_name=rec.raw_stock_name,
                ticker=sec_ticker or rec.raw_ticker,
                action=rec.action,
                confidence=rec.confidence,
                speaker=rec.speaker,
                reasoning=rec.reasoning,
                date=published_at,
                source_id=src_id,
                source_name=src_name,
                content_title=title,
            )
        )

    return results


def get_top_stocks(
    session: "Session",
    days: int = 30,
    action: str | None = None,
    limit: int = 10,
) -> list[tuple[str, str | None, int, dict[str, int]]]:
    """Get most mentioned/recommended stocks.

    Args:
        session: Database session
        days: Lookback period
        action: Filter by action type
        limit: Maximum results

    Returns:
        List of (stock_name, ticker, count, action_breakdown)
    """
    since = (datetime.now() - timedelta(days=days)).date().isoformat()

    query = (
        session.query(
            Recommendation.raw_stock_name,
            Security.ticker,
            Recommendation.action,
            func.count(Recommendation.id).label("count"),
        )
        .join(Analysis, Recommendation.analysis_id == Analysis.id)
        .join(Content, Analysis.content_id == Content.id)
        .outerjoin(Security, Recommendation.security_id == Security.id)
        .filter(Content.published_at >= since)
    )

    if action:
        query = query.filter(Recommendation.action == action.lower())

    query = query.group_by(
        Recommendation.raw_stock_name,
        Security.ticker,
        Recommendation.action,
    )

    # Aggregate by stock
    stock_data: dict[str, dict] = {}
    for name, ticker, act, count in query.all():
        key = name.lower()
        if key not in stock_data:
            stock_data[key] = {
                "name": name,
                "ticker": ticker,
                "total": 0,
                "actions": {},
            }
        stock_data[key]["total"] += count
        stock_data[key]["actions"][act] = stock_data[key]["actions"].get(act, 0) + count
        if ticker and not stock_data[key]["ticker"]:
            stock_data[key]["ticker"] = ticker

    # Sort by total and return top N
    sorted_stocks = sorted(stock_data.values(), key=lambda x: x["total"], reverse=True)

    return [
        (s["name"], s["ticker"], s["total"], s["actions"]) for s in sorted_stocks[:limit]
    ]


def get_recent_by_source(
    session: "Session",
    source_id: str,
    limit: int = 10,
) -> list[dict]:
    """Get recent content with analysis for a source.

    Args:
        session: Database session
        source_id: Source ID
        limit: Maximum results

    Returns:
        List of content dictionaries with analysis summary
    """
    query = (
        session.query(Content, Analysis)
        .join(Analysis, Content.id == Analysis.content_id)
        .filter(Content.source_id == source_id)
        .order_by(Content.published_at.desc())
        .limit(limit)
    )

    results = []
    for content, analysis in query.all():
        rec_count = (
            session.query(func.count(Recommendation.id))
            .filter(Recommendation.analysis_id == analysis.id)
            .scalar()
        )

        results.append(
            {
                "id": content.id,
                "title": content.title,
                "date": content.published_at,
                "summary": analysis.summary,
                "sentiment": analysis.sentiment,
                "recommendations": rec_count,
            }
        )

    return results


def get_speaker_stats(
    session: "Session",
    days: int = 90,
    limit: int = 20,
) -> list[dict]:
    """Get statistics by speaker.

    Args:
        session: Database session
        days: Lookback period
        limit: Maximum speakers

    Returns:
        List of speaker statistics
    """
    since = (datetime.now() - timedelta(days=days)).date().isoformat()

    query = (
        session.query(
            Recommendation.speaker,
            Recommendation.action,
            func.count(Recommendation.id).label("count"),
        )
        .join(Analysis, Recommendation.analysis_id == Analysis.id)
        .join(Content, Analysis.content_id == Content.id)
        .filter(
            Content.published_at >= since,
            Recommendation.speaker.isnot(None),
        )
        .group_by(Recommendation.speaker, Recommendation.action)
    )

    # Aggregate by speaker
    speaker_data: dict[str, dict] = {}
    for speaker, action, count in query.all():
        if not speaker:
            continue
        if speaker not in speaker_data:
            speaker_data[speaker] = {"name": speaker, "total": 0, "actions": {}}
        speaker_data[speaker]["total"] += count
        speaker_data[speaker]["actions"][action] = count

    # Sort by total
    sorted_speakers = sorted(speaker_data.values(), key=lambda x: x["total"], reverse=True)

    return sorted_speakers[:limit]


def get_unmatched_securities(
    session: "Session",
    limit: int = 50,
) -> list[tuple[str, str | None, int]]:
    """Get recommendations without matched securities.

    Args:
        session: Database session
        limit: Maximum results

    Returns:
        List of (stock_name, ticker, count)
    """
    query = (
        session.query(
            Recommendation.raw_stock_name,
            Recommendation.raw_ticker,
            func.count(Recommendation.id).label("count"),
        )
        .filter(Recommendation.security_id.is_(None))
        .group_by(Recommendation.raw_stock_name, Recommendation.raw_ticker)
        .order_by(func.count(Recommendation.id).desc())
        .limit(limit)
    )

    return [(name, ticker, count) for name, ticker, count in query.all()]
