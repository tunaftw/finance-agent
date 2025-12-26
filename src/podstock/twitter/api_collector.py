"""Twitter API collector with storage and state integration.

This module coordinates tweet collection via twitterapi.io with
the existing storage and state management systems.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from podstock.twitter.api_client import TwitterAPIClient
from podstock.twitter.exceptions import TwitterCollectionError, TwitterRateLimitError
from podstock.twitter.manager import load_twitter_sources
from podstock.twitter.models import Tweet
from podstock.twitter.state import TwitterState
from podstock.twitter.storage import TweetStorage


@dataclass
class CollectionResult:
    """Result of a tweet collection operation.

    Attributes:
        source_id: Source identifier.
        tweets_collected: Number of new tweets collected.
        total_tweets: Total tweets now stored.
        oldest_id: Oldest tweet ID collected.
        newest_id: Newest tweet ID collected.
        is_complete: Whether we reached end of timeline.
        error: Error message if collection failed.
    """

    source_id: str
    tweets_collected: int = 0
    total_tweets: int = 0
    oldest_id: str | None = None
    newest_id: str | None = None
    is_complete: bool = False
    error: str | None = None

    @property
    def success(self) -> bool:
        """Whether collection succeeded."""
        return self.error is None


class TwitterAPICollector:
    """Coordinates tweet collection with storage and state.

    Uses TwitterAPIClient to fetch tweets and integrates with
    TweetStorage and TwitterState for persistence and tracking.

    Attributes:
        client: Twitter API client.
        storage: Tweet storage manager.
        state: Collection state manager.
        sources_file: Path to twitter_sources.json.

    Example:
        >>> collector = TwitterAPICollector(api_key="key", data_dir=Path("data"))
        >>> result = collector.collect_source("vildkatten", max_tweets=500)
        >>> print(f"Collected {result.tweets_collected} new tweets")
    """

    def __init__(
        self,
        api_key: str | None = None,
        data_dir: Path | None = None,
    ) -> None:
        """Initialize the collector.

        Args:
            api_key: API key for twitterapi.io. If not provided,
                reads from TWITTER_API_KEY environment variable.
            data_dir: Base data directory. Defaults to 'data'.
        """
        self.data_dir = Path(data_dir or "data")
        self.client = TwitterAPIClient(api_key=api_key)
        self.storage = TweetStorage(self.data_dir)
        self.state = TwitterState(self.data_dir / "twitter_state.json")
        self.sources_file = self.data_dir / "twitter_sources.json"

    def collect_source(
        self,
        source_id: str,
        max_tweets: int = 500,
        include_replies: bool = False,
        incremental: bool = True,
    ) -> CollectionResult:
        """Collect tweets from a single source.

        Args:
            source_id: Source identifier (username).
            max_tweets: Maximum tweets to collect.
            include_replies: Whether to include replies.
            incremental: If True, only fetch tweets newer than last collection.

        Returns:
            CollectionResult with collection statistics.

        Example:
            >>> result = collector.collect_source("vildkatten", max_tweets=100)
            >>> if result.success:
            ...     print(f"Got {result.tweets_collected} tweets")
        """
        result = CollectionResult(source_id=source_id)

        # Get existing state
        source_state = self.state.get_or_create_state(source_id)
        existing_ids = self.storage.get_tweet_ids(source_id)

        # Determine since_id for incremental collection
        since_id = source_state.last_tweet_id if incremental else None

        try:
            tweets = self.client.collect_user_tweets(
                username=source_id,
                max_tweets=max_tweets,
                since_id=since_id,
                include_replies=include_replies,
            )
        except TwitterRateLimitError as e:
            result.error = f"Rate limited: {e}"
            self.state.mark_error(source_id, result.error)
            return result
        except TwitterCollectionError as e:
            result.error = str(e)
            self.state.mark_error(source_id, result.error)
            return result

        if not tweets:
            result.is_complete = True
            return result

        # Filter out duplicates
        new_tweets = [t for t in tweets if t.id not in existing_ids]

        if new_tweets:
            # Save new tweets
            saved = self.storage.save_tweets(new_tweets)
            result.tweets_collected = saved

            # Update result
            result.newest_id = new_tweets[0].id
            result.oldest_id = new_tweets[-1].id

        # Check if we reached end of timeline
        result.is_complete = len(tweets) < max_tweets

        # Update total count
        result.total_tweets = len(existing_ids) + result.tweets_collected

        # Update state
        if new_tweets:
            self.state.mark_collected(
                source_id=source_id,
                last_tweet_id=result.newest_id or source_state.last_tweet_id or "",
                tweet_count=result.total_tweets,
                oldest_tweet_id=result.oldest_id,
                collection_complete=result.is_complete,
            )
        elif result.is_complete:
            # Mark complete even if no new tweets
            current_state = self.state.get_state(source_id)
            if current_state:
                self.state.mark_collected(
                    source_id=source_id,
                    last_tweet_id=current_state.last_tweet_id or "",
                    tweet_count=current_state.tweet_count,
                    collection_complete=True,
                )

        return result

    def collect_all_sources(
        self,
        max_per_source: int = 500,
        include_replies: bool = False,
        active_only: bool = True,
    ) -> dict[str, CollectionResult]:
        """Collect tweets from all configured sources.

        Args:
            max_per_source: Maximum tweets per source.
            include_replies: Whether to include replies.
            active_only: Only collect from active sources.

        Returns:
            Dictionary mapping source_id to CollectionResult.

        Example:
            >>> results = collector.collect_all_sources(max_per_source=100)
            >>> for source_id, result in results.items():
            ...     print(f"{source_id}: {result.tweets_collected} new tweets")
        """
        results: dict[str, CollectionResult] = {}

        try:
            sources = load_twitter_sources(self.sources_file)
        except Exception as e:
            # Return empty if sources file doesn't exist
            return results

        for source in sources:
            if active_only and not source.active:
                continue

            result = self.collect_source(
                source_id=source.id,
                max_tweets=max_per_source,
                include_replies=include_replies,
            )
            results[source.id] = result

        return results

    def get_collection_stats(self) -> dict:
        """Get overall collection statistics.

        Returns:
            Dictionary with collection stats.
        """
        storage_stats = self.storage.get_storage_stats()
        state_stats = self.state.get_stats()

        return {
            "sources": storage_stats["source_count"],
            "total_tweets": storage_stats["total_tweets"],
            "by_source": storage_stats["by_source"],
            "processed": state_stats["total_processed"],
            "complete_sources": state_stats["complete_sources"],
            "sources_with_errors": state_stats["sources_with_errors"],
        }


def collect_tweets(
    source_id: str,
    max_tweets: int = 500,
    api_key: str | None = None,
    data_dir: Path | None = None,
) -> CollectionResult:
    """Convenience function to collect tweets from a source.

    Args:
        source_id: Source identifier (username).
        max_tweets: Maximum tweets to collect.
        api_key: API key (optional, uses env var).
        data_dir: Data directory (optional, uses 'data').

    Returns:
        CollectionResult with statistics.

    Example:
        >>> result = collect_tweets("vildkatten", max_tweets=100)
        >>> print(f"Collected {result.tweets_collected} tweets")
    """
    collector = TwitterAPICollector(api_key=api_key, data_dir=data_dir)
    return collector.collect_source(source_id, max_tweets=max_tweets)
