"""Storage management for news data.

This module handles persisting news items, feed configs, and sync state.
News items are stored in daily JSON files for efficient storage and retrieval.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from podstock.news.models import (
    DailyNewsFile,
    FeedConfig,
    NewsItem,
    NewsStateFile,
)

if TYPE_CHECKING:
    from podstock.core.config import Config


# Maximum number of item IDs to keep for deduplication
MAX_RECENT_ITEMS = 1000


class NewsStorage:
    """Storage manager for news data.

    Handles:
    - Feed configurations and sync state (news_state.json)
    - Daily news items (items/YYYY/MM/YYYY-MM-DD.json)

    Example:
        >>> storage = NewsStorage(config)
        >>> storage.add_items([item1, item2])
        >>> items = storage.get_items_for_date(date.today())
    """

    def __init__(self, config: Config):
        """Initialize storage with configuration.

        Args:
            config: Application configuration.
        """
        self.config = config
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create required directories."""
        self.news_dir.mkdir(parents=True, exist_ok=True)
        self.items_dir.mkdir(parents=True, exist_ok=True)

    @property
    def news_dir(self) -> Path:
        """Base directory for news data."""
        return self.config.data_dir / "news"

    @property
    def items_dir(self) -> Path:
        """Directory for daily news item files."""
        return self.news_dir / "items"

    @property
    def state_file(self) -> Path:
        """Path to news_state.json."""
        return self.news_dir / "news_state.json"

    # =========================================================================
    # State Management
    # =========================================================================

    def _load_state(self) -> NewsStateFile:
        """Load state file or create empty."""
        if self.state_file.exists():
            with open(self.state_file, encoding="utf-8") as f:
                data = json.load(f)
            return NewsStateFile.model_validate(data)
        return NewsStateFile()

    def _save_state(self, state: NewsStateFile) -> None:
        """Save state file atomically."""
        state.last_updated = datetime.now()
        temp_path = self.state_file.with_suffix(".tmp")

        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(state.model_dump_json(indent=2))

        temp_path.replace(self.state_file)

    # =========================================================================
    # Feed Configuration
    # =========================================================================

    def list_feeds(self) -> list[FeedConfig]:
        """Get all configured feeds."""
        state = self._load_state()
        return list(state.feeds.values())

    def get_feed(self, feed_id: str) -> FeedConfig | None:
        """Get a feed by ID."""
        state = self._load_state()
        return state.feeds.get(feed_id)

    def add_feed(self, feed: FeedConfig) -> None:
        """Add a new feed configuration.

        Args:
            feed: Feed configuration to add.

        Raises:
            ValueError: If feed ID already exists.
        """
        state = self._load_state()

        if feed.id in state.feeds:
            raise ValueError(f"Feed '{feed.id}' already exists")

        state.feeds[feed.id] = feed
        self._save_state(state)

    def update_feed(self, feed: FeedConfig) -> None:
        """Update an existing feed configuration."""
        state = self._load_state()
        state.feeds[feed.id] = feed
        self._save_state(state)

    def remove_feed(self, feed_id: str) -> None:
        """Remove a feed configuration."""
        state = self._load_state()
        if feed_id in state.feeds:
            del state.feeds[feed_id]
            self._save_state(state)

    def update_feed_polled(self, feed_id: str, item_count: int) -> None:
        """Update last polled time and item count for a feed."""
        state = self._load_state()
        if feed_id in state.feeds:
            state.feeds[feed_id].last_polled = datetime.now()
            state.feeds[feed_id].last_item_count = item_count
            self._save_state(state)

    # =========================================================================
    # Deduplication
    # =========================================================================

    def is_duplicate(self, item_id: str) -> bool:
        """Check if an item ID has been seen recently."""
        state = self._load_state()
        return item_id in state.recent_item_ids

    def _add_to_recent(self, item_ids: list[str]) -> None:
        """Add item IDs to recent list for deduplication."""
        state = self._load_state()

        # Add new IDs
        state.recent_item_ids.extend(item_ids)

        # Trim to max size (keep most recent)
        if len(state.recent_item_ids) > MAX_RECENT_ITEMS:
            state.recent_item_ids = state.recent_item_ids[-MAX_RECENT_ITEMS:]

        self._save_state(state)

    # =========================================================================
    # News Items - Daily Files
    # =========================================================================

    def _get_daily_file_path(self, date: datetime) -> Path:
        """Get path to daily news file for a date.

        Args:
            date: The date.

        Returns:
            Path to daily file (items/YYYY/MM/YYYY-MM-DD.json).
        """
        year = date.strftime("%Y")
        month = date.strftime("%m")
        date_str = date.strftime("%Y-%m-%d")

        dir_path = self.items_dir / year / month
        dir_path.mkdir(parents=True, exist_ok=True)

        return dir_path / f"{date_str}.json"

    def _load_daily_file(self, date: datetime) -> DailyNewsFile:
        """Load daily news file or create empty."""
        path = self._get_daily_file_path(date)
        date_str = date.strftime("%Y-%m-%d")

        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return DailyNewsFile.model_validate(data)

        return DailyNewsFile(date=date_str)

    def _save_daily_file(self, date: datetime, file: DailyNewsFile) -> None:
        """Save daily news file atomically."""
        path = self._get_daily_file_path(date)
        file.item_count = len(file.items)
        temp_path = path.with_suffix(".tmp")

        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(file.model_dump_json(indent=2))

        temp_path.replace(path)

    def add_items(self, items: list[NewsItem]) -> int:
        """Add news items, storing in daily files.

        Items are deduplicated and grouped by date before saving.

        Args:
            items: List of news items to add.

        Returns:
            Number of new items added (excluding duplicates).
        """
        if not items:
            return 0

        # Filter out duplicates
        new_items = [item for item in items if not self.is_duplicate(item.id)]

        if not new_items:
            return 0

        # Group items by date
        items_by_date: dict[str, list[NewsItem]] = {}
        for item in new_items:
            date_key = item.published_at.strftime("%Y-%m-%d")
            if date_key not in items_by_date:
                items_by_date[date_key] = []
            items_by_date[date_key].append(item)

        # Save to daily files
        for date_key, date_items in items_by_date.items():
            date = datetime.strptime(date_key, "%Y-%m-%d")
            daily = self._load_daily_file(date)

            # Check for duplicates within the file
            existing_ids = {item.id for item in daily.items}
            for item in date_items:
                if item.id not in existing_ids:
                    daily.items.append(item)

            # Sort by published time (newest first)
            daily.items.sort(key=lambda x: x.published_at, reverse=True)
            self._save_daily_file(date, daily)

        # Add to recent IDs for deduplication
        self._add_to_recent([item.id for item in new_items])

        return len(new_items)

    def get_items_for_date(self, date: datetime) -> list[NewsItem]:
        """Get all news items for a specific date.

        Args:
            date: The date to get items for.

        Returns:
            List of news items, sorted by published time (newest first).
        """
        daily = self._load_daily_file(date)
        return daily.items

    def get_items_in_range(
        self,
        start_date: datetime,
        end_date: datetime,
        company_id: str | None = None,
        followed_only: bool = False,
    ) -> list[NewsItem]:
        """Get news items in a date range.

        Args:
            start_date: Start of range (inclusive).
            end_date: End of range (inclusive).
            company_id: Filter by company ID.
            followed_only: Only return items for followed companies.

        Returns:
            List of news items, sorted by published time (newest first).
        """
        items: list[NewsItem] = []
        current = start_date

        while current <= end_date:
            daily_items = self.get_items_for_date(current)
            items.extend(daily_items)
            current = datetime(
                current.year,
                current.month,
                current.day + 1 if current.day < 28 else 1,
            )
            # Simple date iteration
            from datetime import timedelta
            current = start_date + timedelta(days=(current - start_date).days + 1)
            if current > end_date:
                break

        # Apply filters
        if company_id:
            items = [
                item for item in items
                if any(m.company_id == company_id for m in item.companies)
            ]

        if followed_only:
            items = [
                item for item in items
                if any(m.is_followed for m in item.companies)
            ]

        # Sort by published time (newest first)
        items.sort(key=lambda x: x.published_at, reverse=True)

        return items

    def get_recent_items(
        self,
        hours: int = 24,
        company_id: str | None = None,
        followed_only: bool = False,
    ) -> list[NewsItem]:
        """Get recent news items.

        Args:
            hours: Number of hours to look back.
            company_id: Filter by company ID.
            followed_only: Only return items for followed companies.

        Returns:
            List of news items, sorted by published time (newest first).
        """
        from datetime import timedelta

        end_date = datetime.now()
        start_date = end_date - timedelta(hours=hours)

        # Get items from relevant daily files
        items: list[NewsItem] = []
        current = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

        while current <= end_date:
            daily_items = self.get_items_for_date(current)
            # Filter by time
            for item in daily_items:
                if start_date <= item.published_at <= end_date:
                    items.append(item)
            current += timedelta(days=1)

        # Apply filters
        if company_id:
            items = [
                item for item in items
                if any(m.company_id == company_id for m in item.companies)
            ]

        if followed_only:
            items = [
                item for item in items
                if any(m.is_followed for m in item.companies)
            ]

        # Sort by published time (newest first)
        items.sort(key=lambda x: x.published_at, reverse=True)

        return items

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> dict:
        """Get storage statistics.

        Returns:
            Dictionary with stats about feeds, items, etc.
        """
        state = self._load_state()

        # Count total items by scanning recent daily files
        from datetime import timedelta
        total_items = 0
        today = datetime.now()

        for i in range(7):  # Last 7 days
            date = today - timedelta(days=i)
            daily = self._load_daily_file(date)
            total_items += len(daily.items)

        return {
            "feeds_active": len([f for f in state.feeds.values() if f.active]),
            "feeds_total": len(state.feeds),
            "items_last_7_days": total_items,
            "recent_ids_tracked": len(state.recent_item_ids),
            "last_updated": state.last_updated.isoformat() if state.last_updated else None,
        }
