"""Pydantic models for podcast lists.

This module defines data structures for managing podcast lists,
which group podcasts for different types of analysis.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PodcastList(BaseModel):
    """A named list of podcasts for grouped analysis.

    Attributes:
        id: Unique identifier (slug format, e.g., 'broad', 'niche').
        name: Display name of the list.
        description: Optional description of the list's purpose.
        type: List type for categorization ('broad', 'niche', 'custom').
        podcast_ids: List of podcast IDs included in this list.
        created_at: When the list was created.
        active: Whether the list is active.

    Example:
        >>> lst = PodcastList(
        ...     id="favorites",
        ...     name="Mina Favoriter",
        ...     type="custom",
        ...     podcast_ids=["borspodden", "fillorkill"]
        ... )
    """

    id: str = Field(..., min_length=1, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(..., min_length=1)
    description: str | None = None
    type: Literal["broad", "niche", "custom"] = "custom"
    podcast_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    active: bool = True


class ListsFile(BaseModel):
    """Schema for the lists.json file.

    Attributes:
        version: Schema version number.
        updated_at: Last update timestamp.
        lists: List of podcast list configurations.

    Example:
        >>> file = ListsFile(lists=[
        ...     PodcastList(id="broad", name="Bred Analys", type="broad")
        ... ])
    """

    version: int = 1
    updated_at: datetime = Field(default_factory=datetime.now)
    lists: list[PodcastList] = Field(default_factory=list)
