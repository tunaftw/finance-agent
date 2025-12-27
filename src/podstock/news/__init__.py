"""News module for Stockholm Stock Exchange news aggregation.

This module handles fetching and managing news from:
- Nasdaq Nordic (regulatory/MAR news)
- Swedish financial media (Di.se, etc.)
"""

from podstock.news.models import (
    CompanyMatch,
    FeedConfig,
    NewsItem,
    NewsPriority,
    NewsSource,
    NewsType,
)

__all__ = [
    "CompanyMatch",
    "FeedConfig",
    "NewsItem",
    "NewsPriority",
    "NewsSource",
    "NewsType",
]
