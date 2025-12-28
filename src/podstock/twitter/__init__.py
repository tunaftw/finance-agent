"""Twitter/X tweet collection and analysis for PodStock.

This module provides functionality to collect, store, index, and analyze
tweets from Twitter/X accounts for investment research purposes.

Example:
    >>> from podstock.twitter import TwitterSource, Tweet, TweetSearch
    >>> source = TwitterSource(id="vildkatten", handle="vildkatten")
    >>> search = TweetSearch(data_dir)
    >>> results = search.search_ticker("EVO")
"""

from podstock.twitter.models import (
    Tweet,
    TweetActionType,
    TweetAnalysis,
    TwitterCollectionState,
    TwitterSource,
    TwitterSourcesFile,
    TwitterStateFile,
    StockMention,
    extract_hashtags,
    extract_mentions,
    extract_tickers,
)
from podstock.twitter.exceptions import (
    TwitterError,
    TwitterCollectionError,
    TwitterStateError,
    TwitterStorageError,
    TwitterSourceNotFoundError,
    TwitterParseError,
    TwitterRateLimitError,
)
from podstock.twitter.state import TwitterState, load_twitter_state
from podstock.twitter.manager import (
    load_twitter_sources,
    save_twitter_sources,
    add_twitter_source,
    remove_twitter_source,
    get_twitter_source,
    update_twitter_source,
    list_twitter_sources,
    get_source_stats,
)
from podstock.twitter.storage import TweetStorage
from podstock.twitter.index import TwitterIndexBuilder, build_twitter_indexes
from podstock.twitter.search import TweetSearch
from podstock.twitter.api_client import TwitterAPIClient, get_twitter_client
from podstock.twitter.api_collector import (
    TwitterAPICollector,
    CollectionResult,
    collect_tweets,
)
from podstock.twitter.analyze import TweetAnalyzer, analyze_source_tweets
from podstock.twitter.report import generate_twitter_report, save_twitter_report

__all__ = [
    # Models
    "TwitterSource",
    "Tweet",
    "TweetAnalysis",
    "StockMention",
    "TweetActionType",
    "TwitterCollectionState",
    "TwitterSourcesFile",
    "TwitterStateFile",
    # Utilities
    "extract_tickers",
    "extract_mentions",
    "extract_hashtags",
    # State
    "TwitterState",
    "load_twitter_state",
    # Manager
    "load_twitter_sources",
    "save_twitter_sources",
    "add_twitter_source",
    "remove_twitter_source",
    "get_twitter_source",
    "update_twitter_source",
    "list_twitter_sources",
    "get_source_stats",
    # Storage
    "TweetStorage",
    # Index
    "TwitterIndexBuilder",
    "build_twitter_indexes",
    # Search
    "TweetSearch",
    # API Client
    "TwitterAPIClient",
    "get_twitter_client",
    # API Collector
    "TwitterAPICollector",
    "CollectionResult",
    "collect_tweets",
    # Analysis
    "TweetAnalyzer",
    "analyze_source_tweets",
    # Reports
    "generate_twitter_report",
    "save_twitter_report",
    # Exceptions
    "TwitterError",
    "TwitterCollectionError",
    "TwitterStateError",
    "TwitterStorageError",
    "TwitterSourceNotFoundError",
    "TwitterParseError",
    "TwitterRateLimitError",
]
