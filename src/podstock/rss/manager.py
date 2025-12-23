"""Podcast management for PodStock.

This module handles CRUD operations for podcast subscriptions.
Podcasts are stored in data/podcasts.json.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from podstock.core.exceptions import ConfigError, RSSError
from podstock.core.models import Podcast
from podstock.rss.parser import fetch_feed, validate_rss_url


def _generate_podcast_id(name: str) -> str:
    """Generate a slug ID from podcast name.

    Args:
        name: Podcast name.

    Returns:
        Lowercase slug (e.g., "borspodden" from "Börspodden").

    Example:
        >>> _generate_podcast_id("Börspodden")
        'borspodden'
        >>> _generate_podcast_id("Market Makers")
        'market-makers'
    """
    # Convert to lowercase
    slug = name.lower()

    # Replace Swedish characters
    replacements = {
        "å": "a",
        "ä": "a",
        "ö": "o",
        "é": "e",
        "ü": "u",
    }
    for char, replacement in replacements.items():
        slug = slug.replace(char, replacement)

    # Replace spaces and special chars with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)

    # Remove leading/trailing hyphens
    slug = slug.strip("-")

    return slug


def load_podcasts(podcasts_file: Path) -> list[Podcast]:
    """Load podcasts from file.

    Args:
        podcasts_file: Path to podcasts.json.

    Returns:
        List of Podcast objects.

    Raises:
        ConfigError: If file is invalid.

    Example:
        >>> podcasts = load_podcasts(Path("data/podcasts.json"))
        >>> len(podcasts)
        5
    """
    if not podcasts_file.exists():
        return []

    try:
        with open(podcasts_file, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in podcasts file: {e}") from e
    except OSError as e:
        raise ConfigError(f"Failed to read podcasts file: {e}") from e

    podcasts = []
    for podcast_data in data.get("podcasts", []):
        try:
            # Handle datetime fields
            if "added_at" in podcast_data and isinstance(podcast_data["added_at"], str):
                podcast_data["added_at"] = datetime.fromisoformat(
                    podcast_data["added_at"].replace("Z", "+00:00")
                )
            podcasts.append(Podcast(**podcast_data))
        except Exception as e:
            # Skip invalid entries but log
            print(f"Warning: Skipping invalid podcast entry: {e}")
            continue

    return podcasts


def save_podcasts(podcasts: list[Podcast], podcasts_file: Path) -> None:
    """Save podcasts to file atomically.

    Args:
        podcasts: List of Podcast objects to save.
        podcasts_file: Path to podcasts.json.

    Raises:
        ConfigError: If save fails.

    Example:
        >>> save_podcasts(podcasts, Path("data/podcasts.json"))
    """
    temp_path = podcasts_file.with_suffix(".tmp")

    # Convert to JSON-serializable format
    podcasts_data: list[dict[str, Any]] = []
    for podcast in podcasts:
        data = podcast.model_dump()
        # Convert HttpUrl to string
        data["rss_url"] = str(data["rss_url"])
        if data.get("website"):
            data["website"] = str(data["website"])
        # Convert datetime to ISO string
        if data.get("added_at"):
            data["added_at"] = data["added_at"].isoformat()
        podcasts_data.append(data)

    file_data = {
        "version": 1,
        "updated_at": datetime.now().isoformat(),
        "podcasts": podcasts_data,
    }

    try:
        # Ensure parent directory exists
        podcasts_file.parent.mkdir(parents=True, exist_ok=True)

        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(file_data, f, indent=2, ensure_ascii=False)
            f.write("\n")

        temp_path.replace(podcasts_file)

    except OSError as e:
        if temp_path.exists():
            temp_path.unlink()
        raise ConfigError(f"Failed to save podcasts: {e}") from e


def get_podcast(podcast_id: str, podcasts_file: Path) -> Podcast | None:
    """Get a podcast by ID.

    Args:
        podcast_id: Podcast identifier.
        podcasts_file: Path to podcasts.json.

    Returns:
        Podcast if found, None otherwise.

    Example:
        >>> podcast = get_podcast("borspodden", Path("data/podcasts.json"))
        >>> podcast.name
        'Börspodden'
    """
    podcasts = load_podcasts(podcasts_file)
    for podcast in podcasts:
        if podcast.id == podcast_id:
            return podcast
    return None


def add_podcast(
    name: str,
    rss_url: str,
    podcasts_file: Path,
    *,
    hosts: list[str] | None = None,
    description: str | None = None,
    validate_url: bool = True,
) -> Podcast:
    """Add a new podcast.

    Args:
        name: Display name of the podcast.
        rss_url: URL to the RSS feed.
        podcasts_file: Path to podcasts.json.
        hosts: Optional list of host names.
        description: Optional description.
        validate_url: Whether to validate RSS URL (default True).

    Returns:
        The newly created Podcast.

    Raises:
        RSSError: If URL validation fails.
        ConfigError: If podcast with same ID already exists.

    Example:
        >>> podcast = add_podcast("Börspodden", "https://borspodden.libsyn.com/rss", podcasts_file)
        >>> podcast.id
        'borspodden'
    """
    # Generate ID
    podcast_id = _generate_podcast_id(name)

    # Check for duplicates
    existing = get_podcast(podcast_id, podcasts_file)
    if existing:
        raise ConfigError(f"Podcast with ID '{podcast_id}' already exists")

    # Validate RSS URL
    if validate_url and not validate_rss_url(rss_url):
        raise RSSError(f"Invalid RSS feed URL: {rss_url}")

    # Create podcast
    podcast = Podcast(
        id=podcast_id,
        name=name,
        rss_url=rss_url,
        hosts=hosts or [],
        description=description,
        added_at=datetime.now(),
        active=True,
    )

    # Add to list and save
    podcasts = load_podcasts(podcasts_file)
    podcasts.append(podcast)
    save_podcasts(podcasts, podcasts_file)

    return podcast


def remove_podcast(podcast_id: str, podcasts_file: Path) -> bool:
    """Remove a podcast by ID.

    Args:
        podcast_id: Podcast identifier.
        podcasts_file: Path to podcasts.json.

    Returns:
        True if removed, False if not found.

    Example:
        >>> remove_podcast("borspodden", Path("data/podcasts.json"))
        True
    """
    podcasts = load_podcasts(podcasts_file)
    original_count = len(podcasts)

    podcasts = [p for p in podcasts if p.id != podcast_id]

    if len(podcasts) < original_count:
        save_podcasts(podcasts, podcasts_file)
        return True

    return False


def update_podcast(
    podcast_id: str,
    podcasts_file: Path,
    *,
    name: str | None = None,
    hosts: list[str] | None = None,
    description: str | None = None,
    active: bool | None = None,
) -> Podcast | None:
    """Update an existing podcast.

    Args:
        podcast_id: Podcast identifier.
        podcasts_file: Path to podcasts.json.
        name: New name (optional).
        hosts: New hosts list (optional).
        description: New description (optional).
        active: New active status (optional).

    Returns:
        Updated Podcast, or None if not found.

    Example:
        >>> podcast = update_podcast("borspodden", podcasts_file, active=False)
        >>> podcast.active
        False
    """
    podcasts = load_podcasts(podcasts_file)

    for i, podcast in enumerate(podcasts):
        if podcast.id == podcast_id:
            # Create updated podcast
            updated_data = podcast.model_dump()
            if name is not None:
                updated_data["name"] = name
            if hosts is not None:
                updated_data["hosts"] = hosts
            if description is not None:
                updated_data["description"] = description
            if active is not None:
                updated_data["active"] = active

            updated_podcast = Podcast(**updated_data)
            podcasts[i] = updated_podcast
            save_podcasts(podcasts, podcasts_file)
            return updated_podcast

    return None


def get_active_podcasts(podcasts_file: Path) -> list[Podcast]:
    """Get all active podcasts.

    Args:
        podcasts_file: Path to podcasts.json.

    Returns:
        List of active Podcast objects.

    Example:
        >>> active = get_active_podcasts(Path("data/podcasts.json"))
        >>> all(p.active for p in active)
        True
    """
    podcasts = load_podcasts(podcasts_file)
    return [p for p in podcasts if p.active]


def fetch_podcast_info(rss_url: str) -> dict[str, Any]:
    """Fetch podcast info from RSS feed.

    Useful for pre-populating podcast details when adding.

    Args:
        rss_url: URL to the RSS feed.

    Returns:
        Dict with name, description, and other info.

    Raises:
        RSSError: If fetch fails.

    Example:
        >>> info = fetch_podcast_info("https://borspodden.libsyn.com/rss")
        >>> info["name"]
        'Börspodden'
    """
    feed = fetch_feed(rss_url)

    return {
        "name": feed.feed.get("title", "Unknown"),
        "description": feed.feed.get("description") or feed.feed.get("subtitle"),
        "website": feed.feed.get("link"),
        "language": feed.feed.get("language", "sv"),
        "author": feed.feed.get("author") or feed.feed.get("itunes_author"),
        "image": feed.feed.get("image", {}).get("href"),
        "episode_count": len(feed.entries),
    }
