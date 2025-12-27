"""RSS feed fetching and parsing for news.

This module handles fetching RSS feeds from various news sources
and converting them to NewsItem objects.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import feedparser
import requests

from podstock.news.models import (
    FeedConfig,
    NewsItem,
    NewsPriority,
    NewsSource,
    NewsType,
)

if TYPE_CHECKING:
    from podstock.news.matcher import CompanyMatcher
    from podstock.news.storage import NewsStorage


# Default timeout for RSS fetches
DEFAULT_TIMEOUT = 30


class FeedManager:
    """Manager for fetching and processing RSS feeds.

    Example:
        >>> manager = FeedManager(storage, matcher)
        >>> new_count = manager.sync_all()
        >>> print(f"Added {new_count} new items")
    """

    def __init__(
        self,
        storage: NewsStorage,
        matcher: CompanyMatcher | None = None,
    ):
        """Initialize feed manager.

        Args:
            storage: News storage instance.
            matcher: Company matcher for linking news to companies.
        """
        self.storage = storage
        self.matcher = matcher

    def fetch_feed(
        self,
        url: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> feedparser.FeedParserDict:
        """Fetch and parse an RSS feed.

        Args:
            url: URL to the RSS feed.
            timeout: Request timeout in seconds.

        Returns:
            Parsed feed object from feedparser.

        Raises:
            ValueError: If fetch or parse fails.
        """
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
        except requests.Timeout as e:
            raise ValueError(f"Timeout fetching RSS feed: {url}") from e
        except requests.RequestException as e:
            raise ValueError(f"Failed to fetch RSS feed: {e}") from e

        # Check for parsing errors
        if feed.bozo and feed.bozo_exception:
            exc_type = type(feed.bozo_exception).__name__
            if exc_type not in ("CharacterEncodingOverride", "CharacterEncodingUnknown"):
                raise ValueError(f"Failed to parse RSS feed: {feed.bozo_exception}")

        return feed

    def _parse_published_date(self, entry: Any) -> datetime:
        """Parse publication date from RSS entry."""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                return datetime(*entry.published_parsed[:6])
            except (TypeError, ValueError):
                pass

        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                return datetime(*entry.updated_parsed[:6])
            except (TypeError, ValueError):
                pass

        return datetime.now()

    def _parse_entry(
        self,
        entry: Any,
        feed_config: FeedConfig,
    ) -> NewsItem | None:
        """Parse a single RSS entry into a NewsItem.

        Args:
            entry: feedparser entry object.
            feed_config: Configuration for this feed.

        Returns:
            NewsItem object, or None if essential data missing.
        """
        # Required: title
        title = getattr(entry, "title", None)
        if not title:
            return None

        # Required: link
        link = getattr(entry, "link", None)
        if not link:
            return None

        # Parse publication date
        published_at = self._parse_published_date(entry)

        # Generate ID
        item_id = NewsItem.generate_id(feed_config.source, published_at, title)

        # Optional: summary
        summary = getattr(entry, "summary", None) or getattr(entry, "description", None)
        if summary:
            # Clean up HTML and truncate
            import re
            summary = re.sub(r"<[^>]+>", "", summary)
            summary = summary[:500] if len(summary) > 500 else summary

        # Optional: categories
        categories = []
        if hasattr(entry, "tags"):
            categories = [tag.get("term", "") for tag in entry.tags if tag.get("term")]

        # Optional: guid
        guid = getattr(entry, "id", None) or getattr(entry, "guid", None)

        item = NewsItem(
            id=item_id,
            title=title,
            summary=summary,
            content_url=link,
            news_type=feed_config.news_type,
            source=feed_config.source,
            source_feed=feed_config.url,
            published_at=published_at,
            raw_guid=guid,
            raw_categories=categories,
        )

        # Match companies if matcher available
        if self.matcher:
            matches = self.matcher.match_news_item(item)
            item.companies = matches
            if matches:
                item.primary_company_id = matches[0].company_id
            item.priority = self._calculate_priority(item)

        return item

    def _calculate_priority(self, item: NewsItem) -> NewsPriority:
        """Calculate priority based on news type and company following."""
        has_followed = any(m.is_followed for m in item.companies)

        if item.news_type == NewsType.REGULATORY:
            return NewsPriority.HIGH if has_followed else NewsPriority.MEDIUM
        else:
            return NewsPriority.MEDIUM if has_followed else NewsPriority.LOW

    def sync_feed(self, feed_config: FeedConfig) -> int:
        """Sync a single feed.

        Args:
            feed_config: Feed configuration to sync.

        Returns:
            Number of new items added.
        """
        if not feed_config.active:
            return 0

        try:
            feed = self.fetch_feed(feed_config.url)
        except ValueError as e:
            print(f"Error fetching {feed_config.name}: {e}")
            return 0

        items: list[NewsItem] = []
        for entry in feed.entries:
            item = self._parse_entry(entry, feed_config)
            if item:
                items.append(item)

        # Add items to storage
        new_count = self.storage.add_items(items)

        # Update feed last polled
        self.storage.update_feed_polled(feed_config.id, len(items))

        return new_count

    def sync_all(self) -> int:
        """Sync all active feeds.

        Returns:
            Total number of new items added.
        """
        feeds = self.storage.list_feeds()
        total_new = 0

        for feed in feeds:
            if feed.active:
                new_count = self.sync_feed(feed)
                total_new += new_count

        return total_new

    def sync_by_id(self, feed_id: str) -> int:
        """Sync a specific feed by ID.

        Args:
            feed_id: ID of the feed to sync.

        Returns:
            Number of new items added.

        Raises:
            ValueError: If feed not found.
        """
        feed = self.storage.get_feed(feed_id)
        if not feed:
            raise ValueError(f"Feed '{feed_id}' not found")

        return self.sync_feed(feed)
