"""Search functionality for Twitter data.

This module provides search capabilities over indexed tweets.
Uses pre-built JSON indexes for fast querying.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


class TweetSearch:
    """Search collected and indexed tweets.

    Provides queries by ticker, user, and date with filtering options.

    Attributes:
        data_dir: Base data directory.
        index_dir: Directory containing index files.

    Example:
        >>> search = TweetSearch(Path("data"))
        >>> results = search.search_ticker("EVO")
        >>> print(f"Found {len(results)} tweets about $EVO")
    """

    def __init__(self, data_dir: Path) -> None:
        """Initialize TweetSearch.

        Args:
            data_dir: Base data directory.
        """
        self.data_dir = Path(data_dir)
        self.index_dir = self.data_dir / "twitter" / "index"
        self._load_indexes()

    def _load_indexes(self) -> None:
        """Load all indexes into memory."""
        self.by_ticker = self._load_index("by_ticker.json")
        self.by_user = self._load_index("by_user.json")
        self.by_date = self._load_index("by_date.json")
        self.master = self._load_index("index.json")

    def _load_index(self, filename: str) -> dict:
        """Load a single index file."""
        path = self.index_dir / filename
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def reload_indexes(self) -> None:
        """Reload indexes from disk.

        Call this after building new indexes.
        """
        self._load_indexes()

    # ==========================================================================
    # Ticker-based queries
    # ==========================================================================

    def search_ticker(
        self,
        ticker: str,
        *,
        limit: int | None = None,
        source_id: str | None = None,
    ) -> list[dict]:
        """Find all tweets mentioning a stock ticker.

        Args:
            ticker: Ticker symbol (with or without $).
            limit: Maximum results to return.
            source_id: Filter by specific source.

        Returns:
            List of tweet references.

        Example:
            >>> results = search.search_ticker("$TSLA", limit=50)
        """
        ticker_clean = ticker.upper().lstrip("$")
        results = self.by_ticker.get(ticker_clean, [])

        if source_id:
            results = [r for r in results if r.get("source_id") == source_id]

        if limit:
            results = results[:limit]

        return results

    def get_ticker_history(
        self,
        ticker: str,
        days: int | None = None,
        *,
        source_id: str | None = None,
    ) -> list[dict]:
        """Get chronological tweet history for a ticker.

        Args:
            ticker: Ticker symbol.
            days: Only include tweets from last N days.
            source_id: Filter by specific source.

        Returns:
            List of tweets sorted by date (newest first).

        Example:
            >>> history = search.get_ticker_history("EVO", days=30)
        """
        tweets = self.search_ticker(ticker, source_id=source_id)

        if days:
            cutoff = datetime.now() - timedelta(days=days)
            tweets = [
                t
                for t in tweets
                if datetime.fromisoformat(t["posted_at"]) >= cutoff
            ]

        return sorted(tweets, key=lambda t: t["posted_at"], reverse=True)

    def get_top_tickers(self, n: int = 10) -> list[dict]:
        """Get most frequently mentioned tickers.

        Args:
            n: Number of top tickers to return.

        Returns:
            List of tickers with mention counts.

        Example:
            >>> top = search.get_top_tickers(20)
            >>> print(top[0])
            {'ticker': 'TSLA', 'mention_count': 156}
        """
        ticker_counts = [
            {"ticker": ticker, "mention_count": len(tweets)}
            for ticker, tweets in self.by_ticker.items()
        ]
        return sorted(ticker_counts, key=lambda x: x["mention_count"], reverse=True)[:n]

    def get_tickers_for_source(self, source_id: str) -> list[str]:
        """Get all tickers mentioned by a source.

        Args:
            source_id: Source identifier.

        Returns:
            List of unique tickers.
        """
        user_data = self.by_user.get(source_id, {})
        return user_data.get("unique_tickers", [])

    # ==========================================================================
    # User-based queries
    # ==========================================================================

    def search_user(
        self,
        source_id: str,
        *,
        limit: int | None = None,
        with_tickers_only: bool = False,
    ) -> list[dict]:
        """Find all tweets from a specific user.

        Args:
            source_id: Source identifier.
            limit: Maximum results to return.
            with_tickers_only: Only return tweets with ticker mentions.

        Returns:
            List of tweet references.

        Example:
            >>> tweets = search.search_user("vildkatten", limit=100)
        """
        user_data = self.by_user.get(source_id, {})
        tweets = user_data.get("tweets", [])

        if with_tickers_only:
            tweets = [t for t in tweets if t.get("has_tickers")]

        if limit:
            tweets = tweets[:limit]

        return tweets

    def get_user_stats(self, source_id: str) -> dict | None:
        """Get statistics for a specific user.

        Args:
            source_id: Source identifier.

        Returns:
            User statistics or None if not found.

        Example:
            >>> stats = search.get_user_stats("vildkatten")
            >>> print(stats['tweet_count'])
        """
        user_data = self.by_user.get(source_id)
        if not user_data:
            return None

        return {
            "source_id": source_id,
            "tweet_count": user_data.get("tweet_count", 0),
            "tweets_with_tickers": user_data.get("tweets_with_tickers", 0),
            "unique_tickers": user_data.get("unique_tickers", []),
            "ticker_count": len(user_data.get("unique_tickers", [])),
            "first_tweet_at": user_data.get("first_tweet_at"),
            "last_tweet_at": user_data.get("last_tweet_at"),
        }

    def get_top_sources(self, n: int = 10) -> list[dict]:
        """Get sources with most tweets.

        Args:
            n: Number of top sources to return.

        Returns:
            List of sources with tweet counts.

        Example:
            >>> top = search.get_top_sources(10)
        """
        source_counts = [
            {
                "source_id": source_id,
                "tweet_count": data.get("tweet_count", 0),
                "tweets_with_tickers": data.get("tweets_with_tickers", 0),
            }
            for source_id, data in self.by_user.items()
        ]
        return sorted(source_counts, key=lambda x: x["tweet_count"], reverse=True)[:n]

    def get_sources_mentioning_ticker(self, ticker: str) -> list[dict]:
        """Get all sources that have mentioned a ticker.

        Args:
            ticker: Ticker symbol.

        Returns:
            List of sources with mention counts.
        """
        ticker_clean = ticker.upper().lstrip("$")
        tweets = self.by_ticker.get(ticker_clean, [])

        # Count by source
        source_counts: dict[str, int] = {}
        for tweet in tweets:
            source = tweet.get("source_id")
            source_counts[source] = source_counts.get(source, 0) + 1

        return [
            {"source_id": s, "mention_count": c}
            for s, c in sorted(source_counts.items(), key=lambda x: x[1], reverse=True)
        ]

    # ==========================================================================
    # Date-based queries
    # ==========================================================================

    def search_date(self, date_str: str) -> list[dict]:
        """Find all tweets from a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format.

        Returns:
            List of tweet references.

        Example:
            >>> tweets = search.search_date("2024-12-25")
        """
        return self.by_date.get(date_str, [])

    def search_date_range(
        self,
        start_date: str,
        end_date: str | None = None,
        *,
        source_id: str | None = None,
        ticker: str | None = None,
    ) -> list[dict]:
        """Find tweets within a date range.

        Args:
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD), defaults to today.
            source_id: Filter by specific source.
            ticker: Filter by ticker mention.

        Returns:
            List of tweet references sorted by date.

        Example:
            >>> tweets = search.search_date_range("2024-12-01", "2024-12-31")
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        results = []
        for date_str, tweets in self.by_date.items():
            if start_date <= date_str <= end_date:
                for tweet in tweets:
                    if source_id and tweet.get("source_id") != source_id:
                        continue
                    if ticker:
                        ticker_clean = ticker.upper().lstrip("$")
                        if ticker_clean not in tweet.get("tickers", []):
                            continue
                    results.append(tweet)

        return sorted(results, key=lambda t: t.get("posted_at", ""), reverse=True)

    def get_recent_tweets(
        self,
        days: int = 7,
        *,
        with_tickers_only: bool = False,
        limit: int | None = None,
    ) -> list[dict]:
        """Get tweets from the last N days.

        Args:
            days: Number of days to look back.
            with_tickers_only: Only return tweets with ticker mentions.
            limit: Maximum results to return.

        Returns:
            List of recent tweets.

        Example:
            >>> recent = search.get_recent_tweets(days=7, with_tickers_only=True)
        """
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        results = self.search_date_range(start_date, end_date)

        if with_tickers_only:
            results = [r for r in results if r.get("has_tickers")]

        if limit:
            results = results[:limit]

        return results

    # ==========================================================================
    # Statistics
    # ==========================================================================

    def get_stats(self) -> dict[str, Any]:
        """Get overall statistics.

        Returns:
            Dictionary with statistics.

        Example:
            >>> stats = search.get_stats()
            >>> print(f"Total tweets: {stats['tweet_count']}")
        """
        return {
            "tweet_count": self.master.get("tweet_count", 0),
            "source_count": self.master.get("source_count", 0),
            "unique_tickers": self.master.get("unique_tickers", 0),
            "tweets_with_tickers": self.master.get("tweets_with_tickers", 0),
            "date_range": self.master.get("date_range", {}),
            "last_updated": self.master.get("last_updated"),
            "top_tickers": self.master.get("top_tickers", []),
            "top_sources": self.master.get("top_sources", []),
        }

    def has_data(self) -> bool:
        """Check if any data is indexed.

        Returns:
            True if indexes contain data.
        """
        return self.master.get("tweet_count", 0) > 0

    def is_stale(self, max_age_hours: int = 24) -> bool:
        """Check if indexes are potentially stale.

        Args:
            max_age_hours: Consider stale if older than this.

        Returns:
            True if indexes may be stale.
        """
        last_updated = self.master.get("last_updated")
        if not last_updated:
            return True

        try:
            updated_at = datetime.fromisoformat(last_updated)
            age = datetime.now() - updated_at
            return age.total_seconds() > (max_age_hours * 3600)
        except ValueError:
            return True
