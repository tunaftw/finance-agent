"""Data exporters for dashboard JSON generation."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
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


# --- NEW EXPORTERS FOR SOURCE-SPECIFIC TABS ---


def export_podcasts(data_dir: Path) -> dict[str, Any]:
    """Export podcast episodes directly from analysis JSON files.

    Args:
        data_dir: Path to the data directory (e.g., /data/)

    Returns:
        Dict with episodes, sources, and stock_mentions
    """
    analyses_dir = data_dir / "podcasts" / "analyses"

    if not analyses_dir.exists():
        return {"episodes": [], "sources": [], "stock_mentions": []}

    episodes = []
    sources_map: dict[str, dict] = {}
    stock_mentions_map: dict[str, list] = defaultdict(list)

    # Read all analysis JSON files
    for json_file in sorted(analyses_dir.glob("*.json"), reverse=True):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            continue

        # Extract podcast_id from episode_id (e.g., "aktiepodden-2024-12-20-cff4" -> "aktiepodden")
        episode_id = data.get("episode_id", json_file.stem)
        parts = episode_id.rsplit("-", 3)
        podcast_id = parts[0] if len(parts) >= 4 else episode_id.split("-")[0]

        podcast_name = data.get("podcast_name", podcast_id.replace("-", " ").title())

        # Build episode entry
        episode = {
            "id": episode_id,
            "podcast_id": podcast_id,
            "podcast_name": podcast_name,
            "episode_title": data.get("episode_title", ""),
            "episode_number": data.get("episode_number"),
            "date": data.get("date", ""),
            "hosts": data.get("hosts", []),
            "guests": data.get("guests", []),
            "main_topics": data.get("main_topics", []),
            "stocks_discussed": data.get("stocks_discussed", []),
            "recommendation_count": len(data.get("recommendations", [])),
            "market_sentiment": data.get("market_sentiment", ""),
            "summary": data.get("summary", ""),
            "key_takeaways": data.get("key_takeaways", []),
            "recommendations": [
                {
                    "stock_name": rec.get("stock_name", ""),
                    "ticker": rec.get("ticker"),
                    "action": rec.get("action", ""),
                    "confidence": rec.get("confidence", ""),
                    "speaker": rec.get("speaker", ""),
                    "speaker_role": rec.get("speaker_role", ""),
                    "reasoning": rec.get("reasoning", ""),
                    "quote": rec.get("quote", ""),
                    "price_target": rec.get("price_target"),
                    "time_horizon": rec.get("time_horizon"),
                }
                for rec in data.get("recommendations", [])
            ],
        }
        episodes.append(episode)

        # Track source stats
        if podcast_id not in sources_map:
            sources_map[podcast_id] = {
                "id": podcast_id,
                "name": podcast_name,
                "episode_count": 0,
                "recommendation_count": 0,
            }
        sources_map[podcast_id]["episode_count"] += 1
        sources_map[podcast_id]["recommendation_count"] += len(data.get("recommendations", []))

        # Track stock mentions for company search
        for stock in data.get("stocks_discussed", []):
            stock_key = stock.lower()
            stock_mentions_map[stock_key].append({
                "stock_name": stock,
                "episode_id": episode_id,
                "date": data.get("date", ""),
                "podcast_name": podcast_name,
            })

    # Build stock mentions list
    stock_mentions = []
    for stock_key, mentions in stock_mentions_map.items():
        if mentions:
            stock_mentions.append({
                "stock_name": mentions[0]["stock_name"],
                "mention_count": len(mentions),
                "episodes": sorted(mentions, key=lambda x: x["date"] or "", reverse=True),
            })

    # Sort by mention count
    stock_mentions.sort(key=lambda x: x["mention_count"], reverse=True)

    return {
        "episodes": episodes,
        "sources": sorted(sources_map.values(), key=lambda x: x["name"]),
        "stock_mentions": stock_mentions,
    }


def export_twitter(data_dir: Path) -> dict[str, Any]:
    """Export Twitter tweets and analyses.

    Args:
        data_dir: Path to the data directory (e.g., /data/)

    Returns:
        Dict with tweets, users, and stock_mentions
    """
    twitter_dir = data_dir / "twitter"
    raw_dir = twitter_dir / "raw"
    analyses_dir = twitter_dir / "analyses"

    if not raw_dir.exists():
        return {"tweets": [], "users": [], "stock_mentions": []}

    tweets = []
    users_map: dict[str, dict] = {}
    stock_mentions_map: dict[str, dict] = defaultdict(lambda: {"user_mentions": defaultdict(int)})

    # Load analyses indexed by tweet_id
    analyses_by_tweet: dict[str, dict] = {}
    if analyses_dir.exists():
        for analysis_file in analyses_dir.glob("*-tweet-analyses.json"):
            try:
                with open(analysis_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for analysis in data.get("analyses", []):
                        tweet_id = analysis.get("tweet_id")
                        if tweet_id:
                            analyses_by_tweet[tweet_id] = analysis
            except (json.JSONDecodeError, IOError):
                continue

    # Process each user's tweets
    for user_dir in raw_dir.iterdir():
        if not user_dir.is_dir():
            continue

        user_id = user_dir.name
        tweets_file = user_dir / "tweets.jsonl"

        if not tweets_file.exists():
            continue

        user_tweets = []
        actionable_count = 0

        try:
            with open(tweets_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        tweet_data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    tweet_id = str(tweet_data.get("id", ""))

                    # Get analysis if available
                    analysis = analyses_by_tweet.get(tweet_id, {})
                    stock_mentions = analysis.get("stock_mentions", [])
                    is_actionable = analysis.get("is_actionable", False)

                    if is_actionable:
                        actionable_count += 1

                    # Extract date from posted_at
                    posted_at = tweet_data.get("posted_at", "")
                    date = posted_at[:10] if posted_at else ""

                    tweet = {
                        "id": tweet_id,
                        "user_id": user_id,
                        "user_handle": f"@{tweet_data.get('author_handle', user_id)}",
                        "text": tweet_data.get("text", ""),
                        "date": date,
                        "posted_at": posted_at,
                        "likes": tweet_data.get("likes", 0) or 0,
                        "views": tweet_data.get("views", 0) or 0,
                        "is_reply": tweet_data.get("is_reply", False),
                        "is_retweet": tweet_data.get("is_retweet", False),
                        "stock_mentions": [
                            {
                                "stock_name": m.get("stock_name", ""),
                                "ticker": m.get("ticker", ""),
                                "action": m.get("action", ""),
                                "confidence": m.get("confidence", ""),
                                "reasoning": m.get("reasoning", ""),
                            }
                            for m in stock_mentions
                        ],
                        "market_sentiment": analysis.get("market_sentiment", ""),
                        "is_actionable": is_actionable,
                    }
                    user_tweets.append(tweet)

                    # Track stock mentions for cross-reference
                    for mention in stock_mentions:
                        stock_name = mention.get("stock_name", "")
                        if stock_name:
                            stock_key = stock_name.lower()
                            stock_mentions_map[stock_key]["stock_name"] = stock_name
                            stock_mentions_map[stock_key]["ticker"] = mention.get("ticker", "")
                            stock_mentions_map[stock_key]["user_mentions"][user_id] += 1

        except IOError:
            continue

        # Add user stats
        if user_tweets:
            users_map[user_id] = {
                "id": user_id,
                "handle": f"@{user_id}",
                "tweet_count": len(user_tweets),
                "actionable_count": actionable_count,
            }
            tweets.extend(user_tweets)

    # Sort tweets by date (newest first)
    tweets.sort(key=lambda x: x["posted_at"] or "", reverse=True)

    # Build stock mentions for cross-reference
    stock_mentions = []
    for stock_key, data in stock_mentions_map.items():
        user_mentions = [
            {"user_id": uid, "count": count}
            for uid, count in data["user_mentions"].items()
        ]
        user_mentions.sort(key=lambda x: x["count"], reverse=True)

        stock_mentions.append({
            "stock_name": data.get("stock_name", stock_key),
            "ticker": data.get("ticker", ""),
            "total_mentions": sum(m["count"] for m in user_mentions),
            "unique_users": len(user_mentions),
            "user_mentions": user_mentions,
        })

    # Sort by total mentions
    stock_mentions.sort(key=lambda x: x["total_mentions"], reverse=True)

    return {
        "tweets": tweets,
        "users": sorted(users_map.values(), key=lambda x: x["actionable_count"], reverse=True),
        "stock_mentions": stock_mentions,
    }


def export_youtube(data_dir: Path) -> dict[str, Any]:
    """Export YouTube videos from raw JSON files and analyses.

    Args:
        data_dir: Path to the data directory (e.g., /data/)

    Returns:
        Dict with videos, channels, and stock_mentions
    """
    youtube_dir = data_dir / "youtube"
    raw_dir = youtube_dir / "raw"
    analyses_dir = youtube_dir / "analyses"
    sources_file = youtube_dir / "sources.json"

    if not raw_dir.exists():
        return {"videos": [], "channels": [], "stock_mentions": []}

    videos = []
    channels_map: dict[str, dict] = {}
    stock_mentions_map: dict[str, list] = defaultdict(list)

    # Load channel info
    channel_info = {}
    if sources_file.exists():
        try:
            with open(sources_file, "r", encoding="utf-8") as f:
                sources_data = json.load(f)
                for ch in sources_data.get("channels", []):
                    channel_info[ch["id"]] = ch
        except (json.JSONDecodeError, IOError):
            pass

    # Load analyses indexed by video_id (source_id in analysis files)
    analyses_by_video: dict[str, dict] = {}
    if analyses_dir.exists():
        for analysis_file in analyses_dir.glob("*.json"):
            try:
                with open(analysis_file, "r", encoding="utf-8") as f:
                    analysis = json.load(f)
                    video_id = analysis.get("source_id", analysis_file.stem)
                    analyses_by_video[video_id] = analysis
            except (json.JSONDecodeError, IOError):
                continue

    # Process each channel's videos
    for channel_dir in raw_dir.iterdir():
        if not channel_dir.is_dir():
            continue

        channel_id = channel_dir.name
        ch_info = channel_info.get(channel_id, {})
        channel_name = ch_info.get("name", channel_id.replace("-", " ").title())

        channel_videos = []

        for video_file in channel_dir.glob("*.json"):
            try:
                with open(video_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue

            video_id = data.get("video_id", video_file.stem)

            # Get analysis data if available
            analysis = analyses_by_video.get(video_id, {})

            # Extract date - prefer analysis date, then raw, then file mtime
            date = analysis.get("date", "")
            if not date:
                published_at = data.get("published_at", "")
                date = published_at[:10] if published_at else ""
            if not date:
                try:
                    mtime = video_file.stat().st_mtime
                    date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                except Exception:
                    pass

            # Get title - fall back to extracting from transcript or video_id
            title = data.get("title", "")
            if not title:
                # Try to extract a meaningful title from transcript start
                text = data.get("text", "")
                if text:
                    # Take first 100 chars, clean up
                    snippet = text[:100].replace("\n", " ").strip()
                    title = f"{snippet}..." if len(text) > 100 else snippet
                else:
                    title = f"Video {video_id}"

            # Get channel name from analysis if available
            if analysis.get("channel_or_podcast"):
                channel_name = analysis["channel_or_podcast"]

            # Get stocks discussed from analysis or raw
            stocks_discussed = analysis.get("assets_discussed", []) or data.get("stocks_discussed", [])

            # Build recommendations from analysis mentions
            mentions = analysis.get("mentions", [])
            recommendations = [
                {
                    "stock_name": m.get("asset_name", ""),
                    "ticker": m.get("asset_symbol", ""),
                    "action": _sentiment_to_action(m.get("sentiment", "")),
                    "sentiment": m.get("sentiment", ""),
                    "confidence": m.get("confidence", ""),
                    "speaker": m.get("speaker", ""),
                    "reasoning": m.get("reasoning", ""),
                    "quote": m.get("quote", ""),
                    "price_target": m.get("price_target"),
                    "time_horizon": m.get("time_horizon"),
                }
                for m in mentions
            ]

            video = {
                "id": video_id,
                "channel_id": channel_id,
                "channel_name": channel_name,
                "title": title,
                "date": date,
                "duration_seconds": data.get("duration_seconds"),
                "category": ch_info.get("category", ""),
                "speakers": analysis.get("speakers", []),
                "main_topics": analysis.get("main_topics", []),
                "summary": analysis.get("summary", "") or data.get("summary", ""),
                "key_takeaways": analysis.get("key_takeaways", []),
                "overall_sentiment": analysis.get("overall_market_sentiment", ""),
                "stocks_discussed": stocks_discussed,
                "recommendation_count": len(recommendations),
                "recommendations": recommendations,
            }
            channel_videos.append(video)

            # Track stock mentions
            for stock in stocks_discussed:
                stock_key = stock.lower() if isinstance(stock, str) else str(stock).lower()
                stock_mentions_map[stock_key].append({
                    "stock_name": stock if isinstance(stock, str) else str(stock),
                    "video_id": video_id,
                    "date": date,
                    "channel_name": channel_name,
                })

        # Add channel stats
        if channel_videos:
            rec_count = sum(v["recommendation_count"] for v in channel_videos)
            channels_map[channel_id] = {
                "id": channel_id,
                "name": channel_name,
                "video_count": len(channel_videos),
                "recommendation_count": rec_count,
                "category": ch_info.get("category", ""),
            }
            videos.extend(channel_videos)

    # Sort videos by date (newest first)
    videos.sort(key=lambda x: x["date"] or "", reverse=True)

    # Build stock mentions
    stock_mentions = []
    for stock_key, mentions in stock_mentions_map.items():
        if mentions:
            stock_mentions.append({
                "stock_name": mentions[0]["stock_name"],
                "mention_count": len(mentions),
                "videos": sorted(mentions, key=lambda x: x["date"] or "", reverse=True),
            })

    stock_mentions.sort(key=lambda x: x["mention_count"], reverse=True)

    return {
        "videos": videos,
        "channels": sorted(channels_map.values(), key=lambda x: x["name"]),
        "stock_mentions": stock_mentions,
    }


def _sentiment_to_action(sentiment: str) -> str:
    """Convert sentiment to action for display."""
    mapping = {
        "bullish": "buy",
        "bearish": "sell",
        "neutral": "hold",
    }
    return mapping.get(sentiment.lower(), sentiment)


# --- EXISTING DATABASE EXPORTERS ---


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
