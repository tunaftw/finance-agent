"""Build and maintain search indexes for tweets.

This module creates pre-built JSON indexes for efficient tweet searching.
Indexes are stored in data/twitter/index/.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from podstock.twitter.models import Tweet
from podstock.twitter.storage import TweetStorage


class TwitterIndexBuilder:
    """Builds search indexes from collected tweets.

    Creates indexes for efficient querying by:
    - Ticker symbol ($TSLA, $EVO)
    - User/source
    - Date

    Attributes:
        data_dir: Base data directory.
        index_dir: Directory for index files.

    Example:
        >>> builder = TwitterIndexBuilder(Path("data"))
        >>> stats = builder.build_all()
        >>> print(stats['tweet_count'])
    """

    def __init__(self, data_dir: Path) -> None:
        """Initialize TwitterIndexBuilder.

        Args:
            data_dir: Base data directory.
        """
        self.data_dir = Path(data_dir)
        self.index_dir = self.data_dir / "twitter" / "index"
        self._storage = TweetStorage(data_dir)

    def _ensure_index_dir(self) -> None:
        """Ensure index directory exists."""
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def _save_index(self, filename: str, data: dict) -> None:
        """Save index with atomic write.

        Args:
            filename: Index filename.
            data: Index data.
        """
        self._ensure_index_dir()
        path = self.index_dir / filename
        temp_path = path.with_suffix(".tmp")

        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

        temp_path.replace(path)

    def _load_all_tweets(self) -> list[Tweet]:
        """Load all tweets for indexing."""
        tweets = []
        for tweet in self._storage.load_all_tweets():
            # Extract entities if not already done
            if not tweet.mentioned_tickers:
                tweet.extract_entities()
            tweets.append(tweet)
        return tweets

    def build_ticker_index(self, tweets: list[Tweet] | None = None) -> dict:
        """Build index: ticker -> list of tweet references.

        Args:
            tweets: Pre-loaded tweets or None to load all.

        Returns:
            Ticker index dictionary.

        Example:
            >>> index = builder.build_ticker_index()
            >>> len(index['TSLA'])
            42
        """
        if tweets is None:
            tweets = self._load_all_tweets()

        index: dict[str, list[dict]] = defaultdict(list)

        for tweet in tweets:
            for ticker in tweet.mentioned_tickers:
                index[ticker].append(
                    {
                        "tweet_id": tweet.id,
                        "source_id": tweet.source_id,
                        "author": tweet.author_handle,
                        "posted_at": tweet.posted_at.isoformat(),
                        "text_preview": tweet.text[:150],
                        "likes": tweet.likes,
                        "retweets": tweet.retweets,
                    }
                )

        # Sort each ticker's tweets by date (newest first)
        for ticker in index:
            index[ticker].sort(key=lambda x: x["posted_at"], reverse=True)

        return dict(index)

    def build_user_index(self, tweets: list[Tweet] | None = None) -> dict:
        """Build index: source_id -> tweet metadata.

        Args:
            tweets: Pre-loaded tweets or None to load all.

        Returns:
            User index dictionary.

        Example:
            >>> index = builder.build_user_index()
            >>> index['vildkatten']['tweet_count']
            1523
        """
        if tweets is None:
            tweets = self._load_all_tweets()

        index: dict[str, dict] = defaultdict(
            lambda: {
                "tweet_count": 0,
                "tweets_with_tickers": 0,
                "unique_tickers": set(),
                "first_tweet_at": None,
                "last_tweet_at": None,
                "tweets": [],
            }
        )

        for tweet in tweets:
            entry = index[tweet.source_id]
            entry["tweet_count"] += 1

            if tweet.mentioned_tickers:
                entry["tweets_with_tickers"] += 1
                entry["unique_tickers"].update(tweet.mentioned_tickers)

            # Track date range
            posted = tweet.posted_at.isoformat()
            if entry["first_tweet_at"] is None or posted < entry["first_tweet_at"]:
                entry["first_tweet_at"] = posted
            if entry["last_tweet_at"] is None or posted > entry["last_tweet_at"]:
                entry["last_tweet_at"] = posted

            # Store tweet reference
            entry["tweets"].append(
                {
                    "tweet_id": tweet.id,
                    "posted_at": posted,
                    "has_tickers": len(tweet.mentioned_tickers) > 0,
                    "tickers": tweet.mentioned_tickers,
                }
            )

        # Convert sets to lists for JSON serialization
        result = {}
        for source_id, data in index.items():
            data["unique_tickers"] = sorted(data["unique_tickers"])
            # Sort tweets by date (newest first)
            data["tweets"].sort(key=lambda x: x["posted_at"], reverse=True)
            result[source_id] = data

        return result

    def build_date_index(self, tweets: list[Tweet] | None = None) -> dict:
        """Build index: date -> list of tweet references.

        Args:
            tweets: Pre-loaded tweets or None to load all.

        Returns:
            Date index dictionary.

        Example:
            >>> index = builder.build_date_index()
            >>> len(index['2024-12-25'])
            15
        """
        if tweets is None:
            tweets = self._load_all_tweets()

        index: dict[str, list[dict]] = defaultdict(list)

        for tweet in tweets:
            date_str = tweet.posted_at.strftime("%Y-%m-%d")
            index[date_str].append(
                {
                    "tweet_id": tweet.id,
                    "source_id": tweet.source_id,
                    "author": tweet.author_handle,
                    "posted_at": tweet.posted_at.isoformat(),
                    "has_tickers": len(tweet.mentioned_tickers) > 0,
                    "tickers": tweet.mentioned_tickers,
                }
            )

        # Sort each date's tweets by time (newest first)
        for date_str in index:
            index[date_str].sort(key=lambda x: x["posted_at"], reverse=True)

        return dict(index)

    def build_master_index(self, tweets: list[Tweet]) -> dict:
        """Build master index with overall statistics.

        Args:
            tweets: All tweets to index.

        Returns:
            Master index dictionary.
        """
        # Collect all tickers
        all_tickers: set[str] = set()
        tweets_with_tickers = 0

        for tweet in tweets:
            if tweet.mentioned_tickers:
                tweets_with_tickers += 1
                all_tickers.update(tweet.mentioned_tickers)

        # Get date range
        if tweets:
            dates = [t.posted_at for t in tweets]
            earliest = min(dates).isoformat()
            latest = max(dates).isoformat()
        else:
            earliest = None
            latest = None

        # Count by source
        by_source: dict[str, int] = defaultdict(int)
        for tweet in tweets:
            by_source[tweet.source_id] += 1

        return {
            "version": 1,
            "last_updated": datetime.now().isoformat(),
            "tweet_count": len(tweets),
            "source_count": len(by_source),
            "unique_tickers": len(all_tickers),
            "tweets_with_tickers": tweets_with_tickers,
            "date_range": {
                "earliest": earliest,
                "latest": latest,
            },
            "top_tickers": self._get_top_tickers(tweets, 20),
            "top_sources": self._get_top_sources(tweets, 10),
        }

    def _get_top_tickers(self, tweets: list[Tweet], n: int) -> list[dict]:
        """Get most mentioned tickers."""
        counts: dict[str, int] = defaultdict(int)
        for tweet in tweets:
            for ticker in tweet.mentioned_tickers:
                counts[ticker] += 1

        sorted_tickers = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]
        return [{"ticker": t, "mention_count": c} for t, c in sorted_tickers]

    def _get_top_sources(self, tweets: list[Tweet], n: int) -> list[dict]:
        """Get sources with most tweets."""
        counts: dict[str, int] = defaultdict(int)
        for tweet in tweets:
            counts[tweet.source_id] += 1

        sorted_sources = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]
        return [{"source_id": s, "tweet_count": c} for s, c in sorted_sources]

    def build_all(self) -> dict:
        """Build all indexes from raw tweets.

        Returns:
            Master index statistics.

        Example:
            >>> stats = builder.build_all()
            >>> print(f"Indexed {stats['tweet_count']} tweets")
        """
        # Load all tweets once
        tweets = self._load_all_tweets()

        # Build all indexes
        ticker_index = self.build_ticker_index(tweets)
        user_index = self.build_user_index(tweets)
        date_index = self.build_date_index(tweets)
        master_index = self.build_master_index(tweets)

        # Save all indexes
        self._save_index("by_ticker.json", ticker_index)
        self._save_index("by_user.json", user_index)
        self._save_index("by_date.json", date_index)
        self._save_index("index.json", master_index)

        return master_index

    def get_index_stats(self) -> dict[str, Any] | None:
        """Get statistics from existing master index.

        Returns:
            Index statistics or None if not built.
        """
        index_path = self.index_dir / "index.json"
        if not index_path.exists():
            return None

        with open(index_path, encoding="utf-8") as f:
            return json.load(f)

    def is_index_stale(self) -> bool:
        """Check if indexes need rebuilding.

        Compares storage stats with index stats.

        Returns:
            True if indexes are stale.
        """
        index_stats = self.get_index_stats()
        if index_stats is None:
            return True

        storage_stats = self._storage.get_storage_stats()

        # Compare tweet counts
        if storage_stats["total_tweets"] != index_stats.get("tweet_count", 0):
            return True

        return False


def build_twitter_indexes(data_dir: Path) -> dict:
    """Convenience function to build all indexes.

    Args:
        data_dir: Base data directory.

    Returns:
        Master index statistics.

    Example:
        >>> stats = build_twitter_indexes(Path("data"))
    """
    builder = TwitterIndexBuilder(data_dir)
    return builder.build_all()
