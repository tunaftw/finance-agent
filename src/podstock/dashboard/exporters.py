"""Data exporters for dashboard JSON generation."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from podstock.db.models import (
    Analysis,
    Content,
    Mention,
    Recommendation,
    RecommendationPerformance,
    Source,
)


def export_analyses(session: Session) -> list[dict[str, Any]]:
    """Export all analyses with basic metadata."""
    results = []

    # Query analyses with their content and source
    analyses = (
        session.query(Analysis, Content, Source)
        .join(Content, Analysis.content_id == Content.id)
        .join(Source, Content.source_id == Source.id)
        .order_by(Content.published_at.desc())
        .all()
    )

    for analysis, content, source in analyses:
        rec_count = (
            session.query(func.count(Recommendation.id))
            .filter(Recommendation.analysis_id == analysis.id)
            .scalar()
        )

        results.append(
            {
                "id": analysis.id,
                "content_id": content.id,
                "source_id": source.id,
                "source_name": source.name,
                "source_type": source.type,
                "trust_rating": source.trust_rating or 3,
                "title": content.title,
                "date": content.published_at[:10] if content.published_at else None,
                "sentiment": analysis.sentiment,
                "summary": analysis.summary,
                "recommendation_count": rec_count,
                "analyzed_at": analysis.analyzed_at,
                "model_used": analysis.model_used,
            }
        )

    return results


def export_recommendations(session: Session) -> list[dict[str, Any]]:
    """Export all recommendations with full details."""
    results = []

    recs = (
        session.query(Recommendation, Analysis, Content, Source)
        .join(Analysis, Recommendation.analysis_id == Analysis.id)
        .join(Content, Analysis.content_id == Content.id)
        .join(Source, Content.source_id == Source.id)
        .order_by(Content.published_at.desc())
        .all()
    )

    for rec, analysis, content, source in recs:
        # Get performance if available
        perf = (
            session.query(RecommendationPerformance)
            .filter(RecommendationPerformance.recommendation_id == rec.id)
            .first()
        )

        results.append(
            {
                "id": rec.id,
                "date": content.published_at[:10] if content.published_at else None,
                "source_id": source.id,
                "source_name": source.name,
                "source_type": source.type,
                "trust_rating": source.trust_rating or 3,
                "content_title": content.title,
                "stock_name": rec.raw_stock_name,
                "ticker": rec.raw_ticker,
                "action": rec.action,
                "confidence": rec.confidence,
                "speaker": rec.speaker,
                "speaker_role": rec.speaker_role,
                "reasoning": rec.reasoning,
                "quote": rec.quote,
                "price_target": rec.price_target,
                "time_horizon": rec.time_horizon,
                "sector": rec.sector,
                "market": rec.market,
                # Performance data
                "price_at_rec": perf.price_at_rec if perf else None,
                "return_7d": perf.return_7d if perf else None,
                "return_30d": perf.return_30d if perf else None,
                "return_90d": perf.return_90d if perf else None,
            }
        )

    return results


def export_sources(session: Session) -> list[dict[str, Any]]:
    """Export all sources with statistics."""
    results = []

    sources = session.query(Source).order_by(Source.trust_rating.desc(), Source.name).all()

    for source in sources:
        # Count content and recommendations
        content_count = session.query(func.count(Content.id)).filter(Content.source_id == source.id).scalar()

        rec_count = (
            session.query(func.count(Recommendation.id))
            .join(Analysis, Recommendation.analysis_id == Analysis.id)
            .join(Content, Analysis.content_id == Content.id)
            .filter(Content.source_id == source.id)
            .scalar()
        )

        # Action breakdown
        action_counts = (
            session.query(Recommendation.action, func.count(Recommendation.id))
            .join(Analysis, Recommendation.analysis_id == Analysis.id)
            .join(Content, Analysis.content_id == Content.id)
            .filter(Content.source_id == source.id)
            .group_by(Recommendation.action)
            .all()
        )

        results.append(
            {
                "id": source.id,
                "name": source.name,
                "type": source.type,
                "description": source.description,
                "trust_rating": source.trust_rating or 3,
                "trust_notes": source.trust_notes,
                "active": bool(source.active),
                "content_count": content_count,
                "recommendation_count": rec_count,
                "actions": dict(action_counts),
            }
        )

    return results


def export_speakers(session: Session) -> list[dict[str, Any]]:
    """Export speaker statistics."""
    results = []

    # Group recommendations by speaker
    speaker_data = defaultdict(
        lambda: {
            "total": 0,
            "actions": defaultdict(int),
            "sources": set(),
            "recommendations": [],
        }
    )

    recs = (
        session.query(Recommendation, Content, Source)
        .join(Analysis, Recommendation.analysis_id == Analysis.id)
        .join(Content, Analysis.content_id == Content.id)
        .join(Source, Content.source_id == Source.id)
        .filter(Recommendation.speaker.isnot(None))
        .all()
    )

    for rec, content, source in recs:
        speaker = rec.speaker
        speaker_data[speaker]["total"] += 1
        speaker_data[speaker]["actions"][rec.action] += 1
        speaker_data[speaker]["sources"].add(source.name)
        speaker_data[speaker]["recommendations"].append(
            {
                "id": rec.id,
                "date": content.published_at[:10] if content.published_at else None,
                "stock": rec.raw_stock_name,
                "action": rec.action,
                "confidence": rec.confidence,
            }
        )

    for speaker, data in speaker_data.items():
        results.append(
            {
                "name": speaker,
                "total_recommendations": data["total"],
                "actions": dict(data["actions"]),
                "sources": list(data["sources"]),
                "recent_recommendations": sorted(data["recommendations"], key=lambda x: x["date"] or "", reverse=True)[
                    :10
                ],
            }
        )

    # Sort by total recommendations
    results.sort(key=lambda x: x["total_recommendations"], reverse=True)

    return results


def export_tickers(session: Session) -> list[dict[str, Any]]:
    """Export per-ticker/stock data."""
    results = []

    # Group recommendations by stock name
    stock_data = defaultdict(
        lambda: {
            "recommendations": [],
            "mentions": 0,
            "sources": set(),
            "speakers": set(),
        }
    )

    recs = (
        session.query(Recommendation, Content, Source)
        .join(Analysis, Recommendation.analysis_id == Analysis.id)
        .join(Content, Analysis.content_id == Content.id)
        .join(Source, Content.source_id == Source.id)
        .all()
    )

    for rec, content, source in recs:
        stock_key = rec.raw_stock_name.lower()
        stock_data[stock_key]["name"] = rec.raw_stock_name
        stock_data[stock_key]["ticker"] = rec.raw_ticker
        stock_data[stock_key]["sources"].add(source.name)
        if rec.speaker:
            stock_data[stock_key]["speakers"].add(rec.speaker)
        stock_data[stock_key]["recommendations"].append(
            {
                "id": rec.id,
                "date": content.published_at[:10] if content.published_at else None,
                "action": rec.action,
                "confidence": rec.confidence,
                "speaker": rec.speaker,
                "source": source.name,
                "trust_rating": source.trust_rating or 3,
            }
        )

    for stock_key, data in stock_data.items():
        # Calculate action summary
        action_counts = defaultdict(int)
        for rec in data["recommendations"]:
            action_counts[rec["action"]] += 1

        results.append(
            {
                "stock_name": data.get("name", stock_key),
                "ticker": data.get("ticker"),
                "total_mentions": len(data["recommendations"]),
                "unique_sources": len(data["sources"]),
                "unique_speakers": len(data["speakers"]),
                "sources": list(data["sources"]),
                "speakers": list(data["speakers"]),
                "actions": dict(action_counts),
                "recommendations": sorted(data["recommendations"], key=lambda x: x["date"] or "", reverse=True),
            }
        )

    # Sort by total mentions
    results.sort(key=lambda x: x["total_mentions"], reverse=True)

    return results


def export_track_record(session: Session) -> dict[str, Any]:
    """Export track record statistics."""
    # Get recommendations with performance data
    recs_with_perf = (
        session.query(Recommendation, RecommendationPerformance, Content, Source)
        .join(RecommendationPerformance, Recommendation.id == RecommendationPerformance.recommendation_id)
        .join(Analysis, Recommendation.analysis_id == Analysis.id)
        .join(Content, Analysis.content_id == Content.id)
        .join(Source, Content.source_id == Source.id)
        .filter(RecommendationPerformance.return_30d.isnot(None))
        .all()
    )

    # Calculate statistics by source
    source_stats = defaultdict(
        lambda: {
            "total": 0,
            "positive_30d": 0,
            "returns_30d": [],
            "returns_90d": [],
            "by_action": defaultdict(lambda: {"total": 0, "positive": 0, "returns": []}),
        }
    )

    # Calculate by speaker
    speaker_stats = defaultdict(
        lambda: {
            "total": 0,
            "positive_30d": 0,
            "returns_30d": [],
            "sources": set(),
        }
    )

    for rec, perf, content, source in recs_with_perf:
        # Source stats
        source_stats[source.id]["name"] = source.name
        source_stats[source.id]["trust_rating"] = source.trust_rating or 3
        source_stats[source.id]["total"] += 1

        if perf.return_30d and perf.return_30d > 0:
            source_stats[source.id]["positive_30d"] += 1

        if perf.return_30d:
            source_stats[source.id]["returns_30d"].append(perf.return_30d)
            source_stats[source.id]["by_action"][rec.action]["total"] += 1
            source_stats[source.id]["by_action"][rec.action]["returns"].append(perf.return_30d)
            if perf.return_30d > 0:
                source_stats[source.id]["by_action"][rec.action]["positive"] += 1

        if perf.return_90d:
            source_stats[source.id]["returns_90d"].append(perf.return_90d)

        # Speaker stats
        if rec.speaker:
            speaker_stats[rec.speaker]["total"] += 1
            speaker_stats[rec.speaker]["sources"].add(source.name)
            if perf.return_30d:
                speaker_stats[rec.speaker]["returns_30d"].append(perf.return_30d)
                if perf.return_30d > 0:
                    speaker_stats[rec.speaker]["positive_30d"] += 1

    # Format source stats
    sources_formatted = []
    for source_id, stats in source_stats.items():
        hit_rate_30d = (stats["positive_30d"] / stats["total"] * 100) if stats["total"] > 0 else 0
        avg_return_30d = sum(stats["returns_30d"]) / len(stats["returns_30d"]) if stats["returns_30d"] else 0
        avg_return_90d = sum(stats["returns_90d"]) / len(stats["returns_90d"]) if stats["returns_90d"] else 0

        sources_formatted.append(
            {
                "source_id": source_id,
                "name": stats["name"],
                "trust_rating": stats["trust_rating"],
                "total_verified": stats["total"],
                "hit_rate_30d": round(hit_rate_30d, 1),
                "avg_return_30d": round(avg_return_30d, 2),
                "avg_return_90d": round(avg_return_90d, 2),
                "by_action": {
                    action: {
                        "total": data["total"],
                        "hit_rate": round(data["positive"] / data["total"] * 100, 1) if data["total"] > 0 else 0,
                        "avg_return": round(sum(data["returns"]) / len(data["returns"]), 2) if data["returns"] else 0,
                    }
                    for action, data in stats["by_action"].items()
                },
            }
        )

    # Format speaker stats
    speakers_formatted = []
    for speaker, stats in speaker_stats.items():
        if stats["total"] >= 3:  # Only include speakers with at least 3 verified recommendations
            hit_rate = (stats["positive_30d"] / stats["total"] * 100) if stats["total"] > 0 else 0
            avg_return = sum(stats["returns_30d"]) / len(stats["returns_30d"]) if stats["returns_30d"] else 0

            speakers_formatted.append(
                {
                    "speaker": speaker,
                    "total_verified": stats["total"],
                    "hit_rate_30d": round(hit_rate, 1),
                    "avg_return_30d": round(avg_return, 2),
                    "sources": list(stats["sources"]),
                }
            )

    # Sort by hit rate
    sources_formatted.sort(key=lambda x: x["hit_rate_30d"], reverse=True)
    speakers_formatted.sort(key=lambda x: x["hit_rate_30d"], reverse=True)

    return {
        "by_source": sources_formatted,
        "by_speaker": speakers_formatted,
        "total_verified": len(recs_with_perf),
    }


def export_watchlist(session: Session, trust_threshold: int = 4) -> list[dict[str, Any]]:
    """Export high conviction watchlist.

    Criteria:
    - confidence = 'high' AND source.trust_rating >= trust_threshold
    - OR multiple independent mentions (3+ sources mentioning same stock with buy)
    """
    results = []
    now = datetime.now()
    thirty_days_ago = (now - timedelta(days=30)).isoformat()

    # Get high confidence recommendations from trusted sources (recent)
    high_conf_recs = (
        session.query(Recommendation, Content, Source)
        .join(Analysis, Recommendation.analysis_id == Analysis.id)
        .join(Content, Analysis.content_id == Content.id)
        .join(Source, Content.source_id == Source.id)
        .filter(
            Recommendation.confidence == "high",
            Recommendation.action == "buy",
            Source.trust_rating >= trust_threshold,
            Content.published_at >= thirty_days_ago,
        )
        .order_by(Content.published_at.desc())
        .all()
    )

    seen_stocks = set()

    for rec, content, source in high_conf_recs:
        stock_key = rec.raw_stock_name.lower()
        if stock_key in seen_stocks:
            continue
        seen_stocks.add(stock_key)

        results.append(
            {
                "stock_name": rec.raw_stock_name,
                "ticker": rec.raw_ticker,
                "date": content.published_at[:10] if content.published_at else None,
                "source": source.name,
                "source_trust": source.trust_rating,
                "speaker": rec.speaker,
                "confidence": rec.confidence,
                "reasoning": rec.reasoning,
                "quote": rec.quote,
                "criteria": "high_confidence_trusted",
            }
        )

    # Find stocks with multiple independent buy recommendations (recent)
    stock_mentions = defaultdict(list)

    buy_recs = (
        session.query(Recommendation, Content, Source)
        .join(Analysis, Recommendation.analysis_id == Analysis.id)
        .join(Content, Analysis.content_id == Content.id)
        .join(Source, Content.source_id == Source.id)
        .filter(
            Recommendation.action == "buy",
            Content.published_at >= thirty_days_ago,
        )
        .all()
    )

    for rec, content, source in buy_recs:
        stock_key = rec.raw_stock_name.lower()
        stock_mentions[stock_key].append(
            {
                "source_id": source.id,
                "source_name": source.name,
                "date": content.published_at[:10] if content.published_at else None,
                "speaker": rec.speaker,
                "trust_rating": source.trust_rating or 3,
                "rec": rec,
            }
        )

    # Add stocks with 3+ independent sources
    for stock_key, mentions in stock_mentions.items():
        unique_sources = set(m["source_id"] for m in mentions)
        if len(unique_sources) >= 3 and stock_key not in seen_stocks:
            # Sort by trust rating and date
            mentions.sort(key=lambda x: (x["trust_rating"], x["date"] or ""), reverse=True)
            best = mentions[0]

            results.append(
                {
                    "stock_name": best["rec"].raw_stock_name,
                    "ticker": best["rec"].raw_ticker,
                    "date": best["date"],
                    "source": f"{len(unique_sources)} sources",
                    "source_trust": max(m["trust_rating"] for m in mentions),
                    "speaker": best["speaker"],
                    "confidence": best["rec"].confidence,
                    "reasoning": f"Mentioned as buy by {len(unique_sources)} independent sources",
                    "quote": None,
                    "criteria": "multiple_sources",
                    "sources": [m["source_name"] for m in mentions[:5]],
                }
            )

    # Sort by date
    results.sort(key=lambda x: x["date"] or "", reverse=True)

    return results
