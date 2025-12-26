"""Tweet storage using JSONL format.

This module handles persistent storage of tweets using JSON Lines (JSONL)
format. Each source has its own tweets.jsonl file for append-only writes.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterator

from podstock.twitter.exceptions import TwitterStorageError
from podstock.twitter.models import Tweet


class TweetStorage:
    """Manages persistent storage of tweets.

    Uses JSONL (JSON Lines) format for append-only, crash-safe storage.
    Each source has tweets stored in: {data_dir}/twitter/raw/{source_id}/tweets.jsonl

    Attributes:
        data_dir: Base data directory.
        raw_dir: Directory for raw tweet storage.

    Example:
        >>> storage = TweetStorage(Path("data"))
        >>> storage.save_tweet(tweet)
        >>> tweets = list(storage.load_tweets("vildkatten"))
    """

    def __init__(self, data_dir: Path) -> None:
        """Initialize TweetStorage.

        Args:
            data_dir: Base data directory.
        """
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "twitter" / "raw"

    def _get_source_dir(self, source_id: str) -> Path:
        """Get directory for a source's tweets."""
        return self.raw_dir / source_id

    def _get_tweets_file(self, source_id: str) -> Path:
        """Get path to a source's tweets.jsonl file."""
        return self._get_source_dir(source_id) / "tweets.jsonl"

    def save_tweet(self, tweet: Tweet) -> None:
        """Save a single tweet to storage.

        Appends to the JSONL file for the tweet's source.
        Creates directory if it doesn't exist.

        Args:
            tweet: Tweet to save.

        Raises:
            TwitterStorageError: If save fails.

        Example:
            >>> storage.save_tweet(tweet)
        """
        source_dir = self._get_source_dir(tweet.source_id)
        tweets_file = self._get_tweets_file(tweet.source_id)

        try:
            source_dir.mkdir(parents=True, exist_ok=True)

            # Append to JSONL file
            with open(tweets_file, "a", encoding="utf-8") as f:
                f.write(tweet.model_dump_json() + "\n")

        except OSError as e:
            raise TwitterStorageError(f"Failed to save tweet: {e}") from e

    def save_tweets(self, tweets: list[Tweet]) -> int:
        """Save multiple tweets to storage.

        Groups tweets by source and appends to respective files.

        Args:
            tweets: List of tweets to save.

        Returns:
            Number of tweets saved.

        Raises:
            TwitterStorageError: If save fails.

        Example:
            >>> saved = storage.save_tweets(tweets)
            >>> print(f"Saved {saved} tweets")
        """
        # Group by source
        by_source: dict[str, list[Tweet]] = {}
        for tweet in tweets:
            if tweet.source_id not in by_source:
                by_source[tweet.source_id] = []
            by_source[tweet.source_id].append(tweet)

        saved = 0
        for source_id, source_tweets in by_source.items():
            source_dir = self._get_source_dir(source_id)
            tweets_file = self._get_tweets_file(source_id)

            try:
                source_dir.mkdir(parents=True, exist_ok=True)

                # Append all tweets for this source
                with open(tweets_file, "a", encoding="utf-8") as f:
                    for tweet in source_tweets:
                        f.write(tweet.model_dump_json() + "\n")
                        saved += 1

            except OSError as e:
                raise TwitterStorageError(
                    f"Failed to save tweets for {source_id}: {e}"
                ) from e

        return saved

    def load_tweets(
        self,
        source_id: str,
        *,
        deduplicate: bool = True,
        limit: int | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> Iterator[Tweet]:
        """Load tweets for a source.

        Args:
            source_id: Source identifier.
            deduplicate: Remove duplicate tweets by ID.
            limit: Maximum number of tweets to return.
            since: Only tweets posted after this time.
            until: Only tweets posted before this time.

        Yields:
            Tweet objects.

        Example:
            >>> for tweet in storage.load_tweets("vildkatten", limit=100):
            ...     print(tweet.text[:50])
        """
        tweets_file = self._get_tweets_file(source_id)

        if not tweets_file.exists():
            return

        seen_ids: set[str] = set()
        count = 0

        try:
            with open(tweets_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        tweet = Tweet.model_validate_json(line)
                    except Exception:
                        # Skip invalid lines
                        continue

                    # Deduplicate
                    if deduplicate and tweet.id in seen_ids:
                        continue
                    seen_ids.add(tweet.id)

                    # Time filters
                    if since and tweet.posted_at < since:
                        continue
                    if until and tweet.posted_at > until:
                        continue

                    yield tweet
                    count += 1

                    if limit and count >= limit:
                        return

        except OSError as e:
            raise TwitterStorageError(f"Failed to read tweets: {e}") from e

    def load_all_tweets(
        self,
        *,
        deduplicate: bool = True,
        limit: int | None = None,
    ) -> Iterator[Tweet]:
        """Load tweets from all sources.

        Args:
            deduplicate: Remove duplicate tweets by ID.
            limit: Maximum total tweets to return.

        Yields:
            Tweet objects from all sources.

        Example:
            >>> all_tweets = list(storage.load_all_tweets())
        """
        if not self.raw_dir.exists():
            return

        seen_ids: set[str] = set()
        count = 0

        for source_dir in self.raw_dir.iterdir():
            if not source_dir.is_dir():
                continue

            source_id = source_dir.name
            for tweet in self.load_tweets(source_id, deduplicate=False):
                # Global deduplicate
                if deduplicate and tweet.id in seen_ids:
                    continue
                seen_ids.add(tweet.id)

                yield tweet
                count += 1

                if limit and count >= limit:
                    return

    def get_tweet_ids(self, source_id: str) -> set[str]:
        """Get all tweet IDs for a source.

        Useful for checking which tweets are already collected.

        Args:
            source_id: Source identifier.

        Returns:
            Set of tweet IDs.

        Example:
            >>> existing_ids = storage.get_tweet_ids("vildkatten")
            >>> "1234567890" in existing_ids
            True
        """
        ids: set[str] = set()
        for tweet in self.load_tweets(source_id, deduplicate=False):
            ids.add(tweet.id)
        return ids

    def get_tweet_count(self, source_id: str) -> int:
        """Get number of tweets stored for a source.

        Args:
            source_id: Source identifier.

        Returns:
            Number of unique tweets.

        Example:
            >>> storage.get_tweet_count("vildkatten")
            1523
        """
        return len(self.get_tweet_ids(source_id))

    def get_latest_tweet_id(self, source_id: str) -> str | None:
        """Get the most recent tweet ID for a source.

        Based on posted_at timestamp, not collection order.

        Args:
            source_id: Source identifier.

        Returns:
            Tweet ID or None if no tweets.

        Example:
            >>> storage.get_latest_tweet_id("vildkatten")
            '1234567890'
        """
        latest: Tweet | None = None

        for tweet in self.load_tweets(source_id):
            if latest is None or tweet.posted_at > latest.posted_at:
                latest = tweet

        return latest.id if latest else None

    def get_oldest_tweet_id(self, source_id: str) -> str | None:
        """Get the oldest tweet ID for a source.

        Based on posted_at timestamp.

        Args:
            source_id: Source identifier.

        Returns:
            Tweet ID or None if no tweets.

        Example:
            >>> storage.get_oldest_tweet_id("vildkatten")
            '0987654321'
        """
        oldest: Tweet | None = None

        for tweet in self.load_tweets(source_id):
            if oldest is None or tweet.posted_at < oldest.posted_at:
                oldest = tweet

        return oldest.id if oldest else None

    def get_sources_with_tweets(self) -> list[str]:
        """Get list of source IDs that have stored tweets.

        Returns:
            List of source IDs.

        Example:
            >>> storage.get_sources_with_tweets()
            ['vildkatten', 'borspodden', 'aktiansen']
        """
        if not self.raw_dir.exists():
            return []

        sources = []
        for source_dir in self.raw_dir.iterdir():
            if source_dir.is_dir():
                tweets_file = source_dir / "tweets.jsonl"
                if tweets_file.exists():
                    sources.append(source_dir.name)

        return sorted(sources)

    def get_storage_stats(self) -> dict:
        """Get storage statistics.

        Returns:
            Dictionary with storage stats.

        Example:
            >>> stats = storage.get_storage_stats()
            >>> stats['total_tweets']
            15234
        """
        sources = self.get_sources_with_tweets()
        total_tweets = 0
        source_counts: dict[str, int] = {}

        for source_id in sources:
            count = self.get_tweet_count(source_id)
            source_counts[source_id] = count
            total_tweets += count

        return {
            "source_count": len(sources),
            "total_tweets": total_tweets,
            "by_source": source_counts,
        }

    def delete_tweets(self, source_id: str) -> int:
        """Delete all tweets for a source.

        WARNING: This is destructive and cannot be undone.

        Args:
            source_id: Source identifier.

        Returns:
            Number of tweets deleted.

        Raises:
            TwitterStorageError: If deletion fails.
        """
        tweets_file = self._get_tweets_file(source_id)

        if not tweets_file.exists():
            return 0

        # Count before deleting
        count = self.get_tweet_count(source_id)

        try:
            tweets_file.unlink()
        except OSError as e:
            raise TwitterStorageError(f"Failed to delete tweets: {e}") from e

        return count

    def compact_storage(self, source_id: str) -> int:
        """Remove duplicate tweets from storage.

        Rewrites the JSONL file with duplicates removed.

        Args:
            source_id: Source identifier.

        Returns:
            Number of duplicates removed.

        Example:
            >>> removed = storage.compact_storage("vildkatten")
            >>> print(f"Removed {removed} duplicates")
        """
        tweets_file = self._get_tweets_file(source_id)

        if not tweets_file.exists():
            return 0

        # Load all tweets with deduplication
        tweets = list(self.load_tweets(source_id, deduplicate=True))
        original_count = sum(1 for _ in self.load_tweets(source_id, deduplicate=False))
        duplicates = original_count - len(tweets)

        if duplicates == 0:
            return 0

        # Rewrite file
        temp_file = tweets_file.with_suffix(".tmp")

        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                for tweet in tweets:
                    f.write(tweet.model_dump_json() + "\n")

            temp_file.replace(tweets_file)

        except OSError as e:
            if temp_file.exists():
                temp_file.unlink()
            raise TwitterStorageError(f"Failed to compact storage: {e}") from e

        return duplicates
