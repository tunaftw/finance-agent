"""State management for Twitter collection.

This module handles tracking the collection and processing status of Twitter
sources. State is persisted to data/twitter_state.json with atomic writes.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from podstock.twitter.exceptions import TwitterStateError
from podstock.twitter.models import CollectionRun, TwitterCollectionState, TwitterStateFile


class TwitterState:
    """Manages collection and processing state for Twitter sources.

    Tracks which sources have been collected, how many tweets, and processing
    progress. Provides methods to query and update status with automatic
    persistence using atomic writes.

    Attributes:
        state_file: Path to twitter_state.json file.

    Example:
        >>> state = TwitterState(Path("data/twitter_state.json"))
        >>> state.get_tweet_count("vildkatten")
        0
        >>> state.mark_collected("vildkatten", "1234567890", 150)
        >>> state.get_tweet_count("vildkatten")
        150
    """

    def __init__(self, state_file: Path) -> None:
        """Initialize TwitterState manager.

        Args:
            state_file: Path to twitter_state.json file.
        """
        self._state_file = state_file
        self._data: TwitterStateFile = self._load()

    @property
    def state_file(self) -> Path:
        """Path to the state file."""
        return self._state_file

    def _load(self) -> TwitterStateFile:
        """Load state from file or create empty state."""
        if not self._state_file.exists():
            return TwitterStateFile()

        try:
            with open(self._state_file, encoding="utf-8") as f:
                raw_data = json.load(f)
        except json.JSONDecodeError as e:
            raise TwitterStateError(f"Invalid JSON in twitter state file: {e}") from e
        except OSError as e:
            raise TwitterStateError(f"Failed to read twitter state file: {e}") from e

        # Parse sources into TwitterCollectionState objects
        sources: dict[str, TwitterCollectionState] = {}
        for source_id, state_data in raw_data.get("sources", {}).items():
            # Convert ISO strings to datetime
            for key in ["last_collected_at", "last_processed_at"]:
                if state_data.get(key):
                    state_data[key] = datetime.fromisoformat(state_data[key])

            # Parse collection_history
            if "collection_history" in state_data:
                history = []
                for run_data in state_data["collection_history"]:
                    if run_data.get("collected_at"):
                        run_data["collected_at"] = datetime.fromisoformat(run_data["collected_at"])
                    history.append(CollectionRun(**run_data))
                state_data["collection_history"] = history

            sources[source_id] = TwitterCollectionState(
                source_id=source_id, **state_data
            )

        return TwitterStateFile(
            version=raw_data.get("version", 1),
            last_updated=datetime.fromisoformat(raw_data["last_updated"])
            if "last_updated" in raw_data
            else datetime.now(),
            sources=sources,
        )

    def save(self) -> None:
        """Save state to file atomically.

        Uses temp file + rename pattern for crash safety.

        Raises:
            TwitterStateError: If save fails.
        """
        temp_path = self._state_file.with_suffix(".tmp")

        # Convert to JSON-serializable format
        sources_data: dict[str, Any] = {}
        for source_id, state in self._data.sources.items():
            state_dict = state.model_dump(exclude={"source_id"})
            # Convert datetime objects to ISO strings
            for key in ["last_collected_at", "last_processed_at"]:
                if state_dict.get(key):
                    state_dict[key] = state_dict[key].isoformat()

            # Serialize collection_history
            if "collection_history" in state_dict:
                serialized_history = []
                for run in state_dict["collection_history"]:
                    if run.get("collected_at"):
                        run["collected_at"] = run["collected_at"].isoformat()
                    serialized_history.append(run)
                state_dict["collection_history"] = serialized_history

            sources_data[source_id] = state_dict

        data = {
            "version": self._data.version,
            "last_updated": datetime.now().isoformat(),
            "sources": sources_data,
        }

        try:
            # Ensure parent directory exists
            self._state_file.parent.mkdir(parents=True, exist_ok=True)

            # Write to temp file first
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")

            # Atomic rename
            temp_path.replace(self._state_file)

        except OSError as e:
            if temp_path.exists():
                temp_path.unlink()
            raise TwitterStateError(f"Failed to save twitter state: {e}") from e

    def _get_or_create_state(self, source_id: str) -> TwitterCollectionState:
        """Get existing state or create new one."""
        if source_id not in self._data.sources:
            self._data.sources[source_id] = TwitterCollectionState(source_id=source_id)
        return self._data.sources[source_id]

    # ==========================================================================
    # Query methods
    # ==========================================================================

    def get_state(self, source_id: str) -> TwitterCollectionState | None:
        """Get full state for a source.

        Args:
            source_id: Source identifier.

        Returns:
            TwitterCollectionState if exists, None otherwise.
        """
        return self._data.sources.get(source_id)

    def get_or_create_state(self, source_id: str) -> TwitterCollectionState:
        """Get existing state or create new one.

        Args:
            source_id: Source identifier.

        Returns:
            TwitterCollectionState (existing or newly created).
        """
        return self._get_or_create_state(source_id)

    def get_tweet_count(self, source_id: str) -> int:
        """Get number of tweets collected for a source.

        Args:
            source_id: Source identifier.

        Returns:
            Number of tweets collected.
        """
        state = self._data.sources.get(source_id)
        return state.tweet_count if state else 0

    def is_collection_complete(self, source_id: str) -> bool:
        """Check if collection has reached end of timeline.

        Args:
            source_id: Source identifier.

        Returns:
            True if collection complete, False otherwise.
        """
        state = self._data.sources.get(source_id)
        return state.collection_complete if state else False

    def get_last_tweet_id(self, source_id: str) -> str | None:
        """Get the most recent tweet ID collected.

        Args:
            source_id: Source identifier.

        Returns:
            Tweet ID if any collected, None otherwise.
        """
        state = self._data.sources.get(source_id)
        return state.last_tweet_id if state else None

    def get_oldest_tweet_id(self, source_id: str) -> str | None:
        """Get the oldest tweet ID collected.

        Args:
            source_id: Source identifier.

        Returns:
            Tweet ID if any collected, None otherwise.
        """
        state = self._data.sources.get(source_id)
        return state.oldest_tweet_id if state else None

    # ==========================================================================
    # Update methods
    # ==========================================================================

    def mark_collected(
        self,
        source_id: str,
        last_tweet_id: str,
        tweet_count: int,
        oldest_tweet_id: str | None = None,
        collection_complete: bool = False,
        # Collection run parameters - ALWAYS pass these when collecting
        tweets_added: int = 0,
        requested_since: str | None = None,  # YYYY-MM-DD
        requested_until: str | None = None,  # YYYY-MM-DD
        collection_method: str = "last_tweets",
    ) -> None:
        """Mark source as having been collected.

        IMPORTANT: This method automatically logs the collection run to history.
        Always pass tweets_added, requested_since, requested_until when collecting
        to maintain accurate history for auditing.

        Args:
            source_id: Source identifier.
            last_tweet_id: Most recent tweet ID collected.
            tweet_count: Total tweets now collected.
            oldest_tweet_id: Oldest tweet ID if known.
            collection_complete: Whether timeline end was reached.
            tweets_added: Number of NEW tweets added in this run.
            requested_since: Date filter used (YYYY-MM-DD), None if not filtered.
            requested_until: Date filter used (YYYY-MM-DD), None if not filtered.
            collection_method: 'advanced_search' or 'last_tweets'.
        """
        state = self._get_or_create_state(source_id)
        state.last_collected_at = datetime.now()
        state.last_tweet_id = last_tweet_id
        state.tweet_count = tweet_count
        state.consecutive_errors = 0

        if oldest_tweet_id:
            state.oldest_tweet_id = oldest_tweet_id
        if collection_complete:
            state.collection_complete = True

        # Always log collection run to history (even if 0 tweets added)
        collection_run = CollectionRun(
            collected_at=datetime.now(),
            requested_since=requested_since,
            requested_until=requested_until,
            tweets_added=tweets_added,
            method=collection_method,
        )
        state.collection_history.append(collection_run)

        self.save()

    def mark_processed(
        self,
        source_id: str,
        processed_count: int,
    ) -> None:
        """Mark tweets as processed.

        Args:
            source_id: Source identifier.
            processed_count: Total tweets now processed.
        """
        state = self._get_or_create_state(source_id)
        state.processed_count = processed_count
        state.last_processed_at = datetime.now()
        self.save()

    def mark_error(self, source_id: str, error: str) -> None:
        """Record an error for a source.

        Args:
            source_id: Source identifier.
            error: Error message.
        """
        state = self._get_or_create_state(source_id)
        state.last_error = error
        state.error_count += 1
        state.consecutive_errors += 1
        self.save()

    def clear_errors(self, source_id: str) -> None:
        """Clear error state for a source.

        Args:
            source_id: Source identifier.
        """
        state = self._get_or_create_state(source_id)
        state.last_error = None
        state.consecutive_errors = 0
        self.save()

    def update_tweet_count(self, source_id: str, new_tweets: int) -> None:
        """Increment tweet count after collection.

        Args:
            source_id: Source identifier.
            new_tweets: Number of new tweets collected.
        """
        state = self._get_or_create_state(source_id)
        state.tweet_count += new_tweets
        state.last_collected_at = datetime.now()
        self.save()

    # ==========================================================================
    # Bulk query methods
    # ==========================================================================

    def get_all_states(self) -> dict[str, TwitterCollectionState]:
        """Get all source states.

        Returns:
            Dictionary mapping source_id to TwitterCollectionState.
        """
        return self._data.sources.copy()

    def get_pending_collection(self) -> list[str]:
        """Get sources that haven't been fully collected.

        Returns:
            List of source IDs that need more collection.
        """
        return [
            source_id
            for source_id, state in self._data.sources.items()
            if not state.collection_complete
        ]

    def get_pending_processing(self) -> list[str]:
        """Get sources with unprocessed tweets.

        Returns:
            List of source IDs with tweets awaiting processing.
        """
        return [
            source_id
            for source_id, state in self._data.sources.items()
            if state.processed_count < state.tweet_count
        ]

    def get_sources_with_errors(self) -> list[str]:
        """Get sources that have encountered errors.

        Returns:
            List of source IDs with errors.
        """
        return [
            source_id
            for source_id, state in self._data.sources.items()
            if state.error_count > 0
        ]

    def get_total_tweet_count(self) -> int:
        """Get total tweets collected across all sources.

        Returns:
            Total tweet count.
        """
        return sum(state.tweet_count for state in self._data.sources.values())

    def get_stats(self) -> dict[str, Any]:
        """Get overall statistics.

        Returns:
            Dictionary with statistics.
        """
        states = self._data.sources.values()
        return {
            "source_count": len(self._data.sources),
            "total_tweets": sum(s.tweet_count for s in states),
            "total_processed": sum(s.processed_count for s in states),
            "complete_sources": sum(1 for s in states if s.collection_complete),
            "sources_with_errors": sum(1 for s in states if s.error_count > 0),
            "last_updated": self._data.last_updated.isoformat(),
        }


def load_twitter_state(state_file: Path) -> TwitterState:
    """Load Twitter state from file.

    Convenience function to create a TwitterState instance.

    Args:
        state_file: Path to twitter_state.json file.

    Returns:
        Initialized TwitterState manager.

    Raises:
        TwitterStateError: If state file is corrupted.
    """
    return TwitterState(state_file)
