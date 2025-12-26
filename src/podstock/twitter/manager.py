"""Twitter source management.

This module handles CRUD operations for Twitter sources (accounts to follow).
Sources are persisted to data/twitter_sources.json.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from podstock.twitter.exceptions import TwitterError, TwitterSourceNotFoundError
from podstock.twitter.models import TwitterSource, TwitterSourcesFile


def load_twitter_sources(sources_file: Path) -> list[TwitterSource]:
    """Load Twitter sources from file.

    Args:
        sources_file: Path to twitter_sources.json.

    Returns:
        List of TwitterSource objects.

    Raises:
        TwitterError: If file is corrupted.

    Example:
        >>> sources = load_twitter_sources(Path("data/twitter_sources.json"))
        >>> len(sources)
        5
    """
    if not sources_file.exists():
        return []

    try:
        with open(sources_file, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise TwitterError(f"Invalid JSON in sources file: {e}") from e
    except OSError as e:
        raise TwitterError(f"Failed to read sources file: {e}") from e

    sources = []
    for source_data in data.get("sources", []):
        # Convert ISO string to datetime
        if source_data.get("added_at"):
            source_data["added_at"] = datetime.fromisoformat(source_data["added_at"])
        sources.append(TwitterSource(**source_data))

    return sources


def save_twitter_sources(sources: list[TwitterSource], sources_file: Path) -> None:
    """Save Twitter sources to file atomically.

    Args:
        sources: List of TwitterSource objects.
        sources_file: Path to twitter_sources.json.

    Raises:
        TwitterError: If save fails.

    Example:
        >>> sources = [TwitterSource(id="test", handle="test")]
        >>> save_twitter_sources(sources, Path("data/twitter_sources.json"))
    """
    temp_path = sources_file.with_suffix(".tmp")

    # Convert to JSON-serializable format
    sources_data = []
    for source in sources:
        source_dict = source.model_dump()
        # Convert datetime to ISO string
        if source_dict.get("added_at"):
            source_dict["added_at"] = source_dict["added_at"].isoformat()
        sources_data.append(source_dict)

    data = {
        "version": 1,
        "updated_at": datetime.now().isoformat(),
        "sources": sources_data,
    }

    try:
        # Ensure parent directory exists
        sources_file.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file first
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

        # Atomic rename
        temp_path.replace(sources_file)

    except OSError as e:
        if temp_path.exists():
            temp_path.unlink()
        raise TwitterError(f"Failed to save sources: {e}") from e


def add_twitter_source(
    handle: str,
    sources_file: Path,
    *,
    display_name: str | None = None,
    category: str | None = None,
    description: str | None = None,
    language: str = "sv",
) -> TwitterSource:
    """Add a new Twitter source.

    Args:
        handle: Twitter handle (with or without @).
        sources_file: Path to twitter_sources.json.
        display_name: User's display name.
        category: Classification (analyst, fund_manager, etc.).
        description: Our notes about this account.
        language: Primary language (default: 'sv').

    Returns:
        The created TwitterSource.

    Raises:
        TwitterError: If source already exists or save fails.

    Example:
        >>> source = add_twitter_source(
        ...     handle="@vildkatten",
        ...     sources_file=Path("data/twitter_sources.json"),
        ...     category="analyst"
        ... )
        >>> source.id
        'vildkatten'
    """
    # Normalize handle
    normalized_handle = handle.lstrip("@").lower()
    source_id = normalized_handle

    # Load existing sources
    sources = load_twitter_sources(sources_file)

    # Check for duplicates
    existing_ids = {s.id for s in sources}
    if source_id in existing_ids:
        raise TwitterError(f"Source already exists: {source_id}")

    # Create new source
    source = TwitterSource(
        id=source_id,
        handle=normalized_handle,
        display_name=display_name,
        category=category,
        description=description,
        language=language,
        added_at=datetime.now(),
        active=True,
    )

    # Add and save
    sources.append(source)
    save_twitter_sources(sources, sources_file)

    return source


def remove_twitter_source(source_id: str, sources_file: Path) -> TwitterSource:
    """Remove a Twitter source.

    Args:
        source_id: ID of the source to remove.
        sources_file: Path to twitter_sources.json.

    Returns:
        The removed TwitterSource.

    Raises:
        TwitterSourceNotFoundError: If source doesn't exist.

    Example:
        >>> removed = remove_twitter_source("vildkatten", sources_file)
        >>> removed.handle
        'vildkatten'
    """
    sources = load_twitter_sources(sources_file)

    # Find source
    source_to_remove = None
    for i, source in enumerate(sources):
        if source.id == source_id:
            source_to_remove = sources.pop(i)
            break

    if source_to_remove is None:
        raise TwitterSourceNotFoundError(source_id)

    save_twitter_sources(sources, sources_file)
    return source_to_remove


def get_twitter_source(source_id: str, sources_file: Path) -> TwitterSource:
    """Get a Twitter source by ID.

    Args:
        source_id: ID of the source.
        sources_file: Path to twitter_sources.json.

    Returns:
        The TwitterSource.

    Raises:
        TwitterSourceNotFoundError: If source doesn't exist.

    Example:
        >>> source = get_twitter_source("vildkatten", sources_file)
        >>> source.handle
        'vildkatten'
    """
    sources = load_twitter_sources(sources_file)

    for source in sources:
        if source.id == source_id:
            return source

    raise TwitterSourceNotFoundError(source_id)


def update_twitter_source(
    source_id: str,
    sources_file: Path,
    **updates: Any,
) -> TwitterSource:
    """Update a Twitter source.

    Args:
        source_id: ID of the source to update.
        sources_file: Path to twitter_sources.json.
        **updates: Fields to update.

    Returns:
        The updated TwitterSource.

    Raises:
        TwitterSourceNotFoundError: If source doesn't exist.

    Example:
        >>> source = update_twitter_source(
        ...     "vildkatten",
        ...     sources_file,
        ...     category="fund_manager",
        ...     description="Updated description"
        ... )
    """
    sources = load_twitter_sources(sources_file)

    # Find and update source
    for i, source in enumerate(sources):
        if source.id == source_id:
            # Create updated source
            source_dict = source.model_dump()
            source_dict.update(updates)
            sources[i] = TwitterSource(**source_dict)
            save_twitter_sources(sources, sources_file)
            return sources[i]

    raise TwitterSourceNotFoundError(source_id)


def set_source_active(
    source_id: str, sources_file: Path, active: bool = True
) -> TwitterSource:
    """Activate or deactivate a Twitter source.

    Args:
        source_id: ID of the source.
        sources_file: Path to twitter_sources.json.
        active: Whether source should be active.

    Returns:
        The updated TwitterSource.

    Raises:
        TwitterSourceNotFoundError: If source doesn't exist.
    """
    return update_twitter_source(source_id, sources_file, active=active)


def list_twitter_sources(
    sources_file: Path,
    *,
    active_only: bool = False,
    category: str | None = None,
) -> list[TwitterSource]:
    """List Twitter sources with optional filtering.

    Args:
        sources_file: Path to twitter_sources.json.
        active_only: Only return active sources.
        category: Filter by category.

    Returns:
        List of matching TwitterSource objects.

    Example:
        >>> sources = list_twitter_sources(sources_file, active_only=True)
        >>> len(sources)
        5
    """
    sources = load_twitter_sources(sources_file)

    if active_only:
        sources = [s for s in sources if s.active]

    if category:
        sources = [s for s in sources if s.category == category]

    return sources


def get_source_stats(sources_file: Path) -> dict[str, Any]:
    """Get statistics about Twitter sources.

    Args:
        sources_file: Path to twitter_sources.json.

    Returns:
        Dictionary with statistics.

    Example:
        >>> stats = get_source_stats(sources_file)
        >>> stats['total']
        10
    """
    sources = load_twitter_sources(sources_file)

    # Count by category
    categories: dict[str, int] = {}
    for source in sources:
        cat = source.category or "uncategorized"
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "total": len(sources),
        "active": sum(1 for s in sources if s.active),
        "inactive": sum(1 for s in sources if not s.active),
        "by_category": categories,
    }
