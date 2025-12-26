"""List management operations for PodStock.

This module provides CRUD operations for podcast lists,
allowing users to create, read, update, and delete lists
that group podcasts for different types of analysis.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from podstock.core.exceptions import PodStockError
from podstock.lists.models import ListsFile, PodcastList


class ListError(PodStockError):
    """Error related to list operations."""

    pass


class ListManager:
    """Manages podcast lists.

    Provides CRUD operations for podcast lists, which are used
    to group podcasts for broad or detailed analysis.

    Attributes:
        lists_file: Path to lists.json file.

    Example:
        >>> manager = ListManager(Path("data/lists.json"))
        >>> manager.create_list("favorites", "Mina Favoriter", "custom")
        >>> manager.add_podcast_to_list("favorites", "borspodden")
    """

    def __init__(self, lists_file: Path) -> None:
        """Initialize ListManager.

        Args:
            lists_file: Path to lists.json file.
        """
        self._lists_file = lists_file
        self._data: ListsFile = self._load()

    @property
    def lists_file(self) -> Path:
        """Path to the lists file."""
        return self._lists_file

    def _load(self) -> ListsFile:
        """Load lists from file or create with defaults."""
        if not self._lists_file.exists():
            return self._create_default_lists()

        try:
            with open(self._lists_file, encoding="utf-8") as f:
                raw_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ListError(f"Invalid JSON in lists file: {e}") from e
        except OSError as e:
            raise ListError(f"Failed to read lists file: {e}") from e

        # Parse lists into PodcastList objects
        lists: list[PodcastList] = []
        for list_data in raw_data.get("lists", []):
            # Convert datetime strings
            if "created_at" in list_data and isinstance(list_data["created_at"], str):
                list_data["created_at"] = datetime.fromisoformat(list_data["created_at"])
            lists.append(PodcastList(**list_data))

        return ListsFile(
            version=raw_data.get("version", 1),
            updated_at=datetime.fromisoformat(raw_data["updated_at"])
            if "updated_at" in raw_data
            else datetime.now(),
            lists=lists,
        )

    def _create_default_lists(self) -> ListsFile:
        """Create default broad and niche lists."""
        now = datetime.now()
        return ListsFile(
            version=1,
            updated_at=now,
            lists=[
                PodcastList(
                    id="broad",
                    name="Bred Analys",
                    description="Alla podcasts för övergripande marknadsöversikt",
                    type="broad",
                    podcast_ids=[],
                    created_at=now,
                    active=True,
                ),
                PodcastList(
                    id="niche",
                    name="Detaljerad Analys",
                    description="Utvalda podcasts för djupanalys",
                    type="niche",
                    podcast_ids=[],
                    created_at=now,
                    active=True,
                ),
            ],
        )

    def save(self) -> None:
        """Save lists to file atomically.

        Raises:
            ListError: If save fails.
        """
        temp_path = self._lists_file.with_suffix(".tmp")

        # Convert to JSON-serializable format
        lists_data: list[dict] = []
        for lst in self._data.lists:
            lst_dict = lst.model_dump()
            # Convert datetime to ISO string
            if lst_dict.get("created_at"):
                lst_dict["created_at"] = lst_dict["created_at"].isoformat()
            lists_data.append(lst_dict)

        data = {
            "version": self._data.version,
            "updated_at": datetime.now().isoformat(),
            "lists": lists_data,
        }

        try:
            # Ensure parent directory exists
            self._lists_file.parent.mkdir(parents=True, exist_ok=True)

            # Write to temp file first
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")

            # Atomic rename
            temp_path.replace(self._lists_file)

        except OSError as e:
            if temp_path.exists():
                temp_path.unlink()
            raise ListError(f"Failed to save lists: {e}") from e

    # Query methods

    def get_all_lists(self) -> list[PodcastList]:
        """Get all podcast lists.

        Returns:
            List of all PodcastList objects.
        """
        return self._data.lists.copy()

    def get_list(self, list_id: str) -> PodcastList | None:
        """Get a specific list by ID.

        Args:
            list_id: List identifier.

        Returns:
            PodcastList if found, None otherwise.
        """
        for lst in self._data.lists:
            if lst.id == list_id:
                return lst
        return None

    def get_list_by_type(self, list_type: Literal["broad", "niche", "custom"]) -> PodcastList | None:
        """Get the first list of a specific type.

        Args:
            list_type: Type of list to find.

        Returns:
            First matching PodcastList, or None if not found.
        """
        for lst in self._data.lists:
            if lst.type == list_type:
                return lst
        return None

    def list_exists(self, list_id: str) -> bool:
        """Check if a list exists.

        Args:
            list_id: List identifier.

        Returns:
            True if list exists, False otherwise.
        """
        return self.get_list(list_id) is not None

    # Mutation methods

    def create_list(
        self,
        list_id: str,
        name: str,
        list_type: Literal["broad", "niche", "custom"] = "custom",
        description: str | None = None,
    ) -> PodcastList:
        """Create a new podcast list.

        Args:
            list_id: Unique identifier for the list (slug format).
            name: Display name for the list.
            list_type: Type of list (broad, niche, custom).
            description: Optional description.

        Returns:
            The created PodcastList.

        Raises:
            ListError: If list with same ID already exists.
        """
        if self.list_exists(list_id):
            raise ListError(f"List '{list_id}' already exists")

        new_list = PodcastList(
            id=list_id,
            name=name,
            description=description,
            type=list_type,
            podcast_ids=[],
            created_at=datetime.now(),
            active=True,
        )

        self._data.lists.append(new_list)
        self.save()

        return new_list

    def delete_list(self, list_id: str) -> bool:
        """Delete a podcast list.

        Args:
            list_id: List identifier.

        Returns:
            True if list was deleted, False if not found.

        Raises:
            ListError: If trying to delete a protected default list.
        """
        # Protect default lists
        if list_id in ("broad", "niche"):
            raise ListError(f"Cannot delete default list '{list_id}'")

        for i, lst in enumerate(self._data.lists):
            if lst.id == list_id:
                self._data.lists.pop(i)
                self.save()
                return True

        return False

    def add_podcast_to_list(self, list_id: str, podcast_id: str) -> bool:
        """Add a podcast to a list.

        Args:
            list_id: List identifier.
            podcast_id: Podcast identifier to add.

        Returns:
            True if added, False if podcast was already in list.

        Raises:
            ListError: If list doesn't exist.
        """
        lst = self.get_list(list_id)
        if lst is None:
            raise ListError(f"List '{list_id}' not found")

        if podcast_id in lst.podcast_ids:
            return False

        lst.podcast_ids.append(podcast_id)
        self.save()
        return True

    def remove_podcast_from_list(self, list_id: str, podcast_id: str) -> bool:
        """Remove a podcast from a list.

        Args:
            list_id: List identifier.
            podcast_id: Podcast identifier to remove.

        Returns:
            True if removed, False if podcast wasn't in list.

        Raises:
            ListError: If list doesn't exist.
        """
        lst = self.get_list(list_id)
        if lst is None:
            raise ListError(f"List '{list_id}' not found")

        if podcast_id not in lst.podcast_ids:
            return False

        lst.podcast_ids.remove(podcast_id)
        self.save()
        return True

    def get_podcasts_in_list(self, list_id: str) -> list[str]:
        """Get all podcast IDs in a list.

        Args:
            list_id: List identifier.

        Returns:
            List of podcast IDs.

        Raises:
            ListError: If list doesn't exist.
        """
        lst = self.get_list(list_id)
        if lst is None:
            raise ListError(f"List '{list_id}' not found")

        return lst.podcast_ids.copy()


def load_lists(lists_file: Path) -> ListManager:
    """Load lists from file.

    Convenience function to create a ListManager instance.

    Args:
        lists_file: Path to lists.json file.

    Returns:
        Initialized ListManager.

    Raises:
        ListError: If lists file is corrupted.
    """
    return ListManager(lists_file)
