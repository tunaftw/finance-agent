"""PodStock Database Module.

This module provides SQLite database functionality for querying
analyzed podcast episodes, tweets, and stock recommendations.

Usage:
    from podstock.db import get_engine, init_db, get_session

    # Initialize database
    engine = get_engine()
    init_db(engine)

    # Query data
    with get_session() as session:
        recommendations = session.query(Recommendation).filter_by(action='buy').all()

    # Load data
    from podstock.db import PodcastLoader
    loader = PodcastLoader()
    with get_session() as session:
        result = loader.load(json_path, session)

    # Search
    from podstock.db import search_recommendations
    with get_session() as session:
        results = search_recommendations(session, stock="Evolution")
"""

from podstock.db.engine import get_engine, get_session, init_db
from podstock.db.loader import BaseLoader, LoadResult, PodcastLoader, TwitterLoader
from podstock.db.models import (
    Analysis,
    Content,
    KeyTakeaway,
    LoadLog,
    Mention,
    PendingSecurity,
    Price,
    Recommendation,
    RecommendationPerformance,
    Security,
    SecurityAlias,
    SecurityRelation,
    Source,
)
from podstock.db.queries import (
    RecommendationResult,
    get_recent_by_source,
    get_speaker_stats,
    get_top_stocks,
    get_unmatched_securities,
    search_recommendations,
)
from podstock.db.ticker_lookup import (
    add_alias,
    get_or_create_security,
    resolve_security,
    seed_from_ticker_mapping,
)
from podstock.db.performance import (
    update_recommendation_performance,
    update_all_performance,
    import_prices_from_tracker,
)

__all__ = [
    # Engine
    "get_engine",
    "get_session",
    "init_db",
    # Models
    "Source",
    "Content",
    "Analysis",
    "Security",
    "SecurityAlias",
    "SecurityRelation",
    "PendingSecurity",
    "Recommendation",
    "Mention",
    "KeyTakeaway",
    "Price",
    "RecommendationPerformance",
    "LoadLog",
    # Loaders
    "BaseLoader",
    "PodcastLoader",
    "TwitterLoader",
    "LoadResult",
    # Queries
    "search_recommendations",
    "get_top_stocks",
    "get_recent_by_source",
    "get_speaker_stats",
    "get_unmatched_securities",
    "RecommendationResult",
    # Ticker lookup
    "resolve_security",
    "get_or_create_security",
    "add_alias",
    "seed_from_ticker_mapping",
    # Performance
    "update_recommendation_performance",
    "update_all_performance",
    "import_prices_from_tracker",
]
