"""RSS feed parsing for PodStock.

This module handles fetching and parsing podcast RSS feeds.
Supports common formats from Libsyn, Acast, and other podcast hosts.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import feedparser
import requests

from podstock.core.exceptions import RSSError
from podstock.core.models import Episode

# Default timeout for RSS fetches
DEFAULT_TIMEOUT = 30


def fetch_feed(url: str, timeout: int = DEFAULT_TIMEOUT) -> feedparser.FeedParserDict:
    """Fetch and parse an RSS feed.

    Args:
        url: URL to the RSS feed.
        timeout: Request timeout in seconds.

    Returns:
        Parsed feed object from feedparser.

    Raises:
        RSSError: If fetch or parse fails.

    Example:
        >>> feed = fetch_feed("https://borspodden.libsyn.com/rss")
        >>> feed.feed.title
        'Börspodden'
    """
    try:
        # Use requests for better timeout handling, then parse
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except requests.Timeout as e:
        raise RSSError(f"Timeout fetching RSS feed: {url}") from e
    except requests.RequestException as e:
        raise RSSError(f"Failed to fetch RSS feed: {e}") from e

    # Check for parsing errors
    if feed.bozo and feed.bozo_exception:
        # Some bozo exceptions are recoverable (e.g., CharacterEncodingOverride)
        # Only raise for serious parsing errors
        exc_type = type(feed.bozo_exception).__name__
        if exc_type not in ("CharacterEncodingOverride", "CharacterEncodingUnknown"):
            raise RSSError(f"Failed to parse RSS feed: {feed.bozo_exception}")

    if not feed.entries:
        raise RSSError(f"RSS feed has no entries: {url}")

    return feed


def _generate_episode_id(podcast_id: str, published: datetime, title: str) -> str:
    """Generate a unique episode ID.

    Format: {podcast_id}-{date}-{hash}
    Example: borspodden-2024-12-18-a1b2

    Args:
        podcast_id: ID of the podcast.
        published: Publication date.
        title: Episode title (used for hash).

    Returns:
        Unique episode ID string.

    Note:
        Uses MD5 hash for consistency with apple.py module.
        This ensures the same episode gets the same ID regardless
        of whether it comes from RSS or Apple Podcasts.
    """
    date_str = published.strftime("%Y-%m-%d")
    # Use MD5 hash (same as apple.py) for cross-source consistency
    title_hash = hashlib.md5(title.encode()).hexdigest()[:4]
    return f"{podcast_id}-{date_str}-{title_hash}"


def _extract_audio_url(entry: Any) -> str | None:
    """Extract audio URL from RSS entry.

    Checks enclosures and media content for audio files.

    Args:
        entry: feedparser entry object.

    Returns:
        Audio URL if found, None otherwise.
    """
    # Check enclosures (standard RSS)
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enclosure in entry.enclosures:
            if enclosure.get("type", "").startswith("audio/"):
                return enclosure.get("href") or enclosure.get("url")
            # Some feeds don't specify type correctly
            url = enclosure.get("href") or enclosure.get("url", "")
            if url.endswith((".mp3", ".m4a", ".wav", ".ogg")):
                return url

    # Check media:content (iTunes/media RSS)
    if hasattr(entry, "media_content") and entry.media_content:
        for media in entry.media_content:
            if media.get("type", "").startswith("audio/"):
                return media.get("url")

    # Check links
    if hasattr(entry, "links"):
        for link in entry.links:
            if link.get("type", "").startswith("audio/"):
                return link.get("href")
            href = link.get("href", "")
            if href.endswith((".mp3", ".m4a", ".wav", ".ogg")):
                return href

    return None


def _parse_duration(duration_str: str | None) -> int | None:
    """Parse duration string to seconds.

    Handles formats:
    - "HH:MM:SS"
    - "MM:SS"
    - "3600" (seconds)

    Args:
        duration_str: Duration string from RSS.

    Returns:
        Duration in seconds, or None if unparseable.
    """
    if not duration_str:
        return None

    duration_str = duration_str.strip()

    # Try as integer seconds
    try:
        return int(duration_str)
    except ValueError:
        pass

    # Try as HH:MM:SS or MM:SS
    parts = duration_str.split(":")
    try:
        if len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
    except ValueError:
        pass

    return None


def _parse_published_date(entry: Any) -> datetime:
    """Parse publication date from RSS entry.

    Args:
        entry: feedparser entry object.

    Returns:
        Publication datetime, or current time if unparseable.
    """
    # feedparser normalizes dates to published_parsed
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:6])
        except (TypeError, ValueError):
            pass

    # Try updated_parsed as fallback
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            return datetime(*entry.updated_parsed[:6])
        except (TypeError, ValueError):
            pass

    # Last resort: current time
    return datetime.now()


def parse_episode(entry: Any, podcast_id: str) -> Episode | None:
    """Parse a single RSS entry into an Episode.

    Args:
        entry: feedparser entry object.
        podcast_id: ID of the parent podcast.

    Returns:
        Episode object, or None if essential data missing.

    Example:
        >>> episode = parse_episode(feed.entries[0], "borspodden")
        >>> episode.title
        'Avsnitt 598 - Julspecial'
    """
    # Required: title
    title = getattr(entry, "title", None)
    if not title:
        return None

    # Required: audio URL
    audio_url = _extract_audio_url(entry)
    if not audio_url:
        return None

    # Parse publication date
    published_at = _parse_published_date(entry)

    # Generate episode ID
    episode_id = _generate_episode_id(podcast_id, published_at, title)

    # Optional fields
    duration_str = getattr(entry, "itunes_duration", None)
    duration = _parse_duration(duration_str)

    description = getattr(entry, "summary", None) or getattr(entry, "description", None)

    guid = getattr(entry, "id", None) or getattr(entry, "guid", None)

    return Episode(
        id=episode_id,
        podcast_id=podcast_id,
        title=title,
        published_at=published_at,
        audio_url=audio_url,
        duration_seconds=duration,
        description=description,
        guid=guid,
    )


def get_all_episodes(url: str, podcast_id: str, timeout: int = DEFAULT_TIMEOUT) -> list[Episode]:
    """Fetch and parse all episodes from an RSS feed.

    Args:
        url: URL to the RSS feed.
        podcast_id: ID of the podcast.
        timeout: Request timeout in seconds.

    Returns:
        List of Episode objects, sorted by date (newest first).

    Raises:
        RSSError: If fetch or parse fails.

    Example:
        >>> episodes = get_all_episodes("https://borspodden.libsyn.com/rss", "borspodden")
        >>> len(episodes)
        150
    """
    feed = fetch_feed(url, timeout)

    episodes = []
    for entry in feed.entries:
        episode = parse_episode(entry, podcast_id)
        if episode:
            episodes.append(episode)

    # Sort by publication date (newest first)
    episodes.sort(key=lambda e: e.published_at, reverse=True)

    return episodes


def get_latest_episodes(
    url: str, podcast_id: str, n: int = 10, timeout: int = DEFAULT_TIMEOUT
) -> list[Episode]:
    """Fetch the latest N episodes from an RSS feed.

    Args:
        url: URL to the RSS feed.
        podcast_id: ID of the podcast.
        n: Number of episodes to return.
        timeout: Request timeout in seconds.

    Returns:
        List of up to N Episode objects, sorted by date (newest first).

    Raises:
        RSSError: If fetch or parse fails.

    Example:
        >>> episodes = get_latest_episodes("https://borspodden.libsyn.com/rss", "borspodden", n=5)
        >>> len(episodes) <= 5
        True
    """
    episodes = get_all_episodes(url, podcast_id, timeout)
    return episodes[:n]


def validate_rss_url(url: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
    """Validate that a URL points to a valid RSS feed.

    Args:
        url: URL to validate.
        timeout: Request timeout in seconds.

    Returns:
        True if valid RSS feed, False otherwise.

    Example:
        >>> validate_rss_url("https://borspodden.libsyn.com/rss")
        True
        >>> validate_rss_url("https://example.com/not-rss")
        False
    """
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False

        feed = fetch_feed(url, timeout)
        return bool(feed.entries)
    except (RSSError, Exception):
        return False
