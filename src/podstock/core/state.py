"""State management for PodStock.

This module handles tracking the processing status of episodes.
State is persisted to data/state.json with atomic writes.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from podstock.core.exceptions import StateError
from podstock.core.models import EpisodeStatus, StateFile


class State:
    """Manages processing state for episodes.

    Tracks which episodes have been downloaded, transcribed, and analyzed.
    Provides methods to query and update status with automatic persistence.

    Attributes:
        state_file: Path to state.json file.

    Example:
        >>> state = State(Path("data/state.json"))
        >>> state.is_downloaded("bp-2024-12-18")
        False
        >>> state.mark_downloaded("bp-2024-12-18", Path("audio/bp-2024-12-18.mp3"))
        >>> state.is_downloaded("bp-2024-12-18")
        True
    """

    def __init__(self, state_file: Path) -> None:
        """Initialize State manager.

        Args:
            state_file: Path to state.json file.
        """
        self._state_file = state_file
        self._data: StateFile = self._load()

    @property
    def state_file(self) -> Path:
        """Path to the state file."""
        return self._state_file

    def _load(self) -> StateFile:
        """Load state from file or create empty state."""
        if not self._state_file.exists():
            return StateFile()

        try:
            with open(self._state_file, encoding="utf-8") as f:
                raw_data = json.load(f)
        except json.JSONDecodeError as e:
            raise StateError(f"Invalid JSON in state file: {e}") from e
        except OSError as e:
            raise StateError(f"Failed to read state file: {e}") from e

        # Parse episodes into EpisodeStatus objects
        episodes: dict[str, EpisodeStatus] = {}
        for episode_id, status_data in raw_data.get("episodes", {}).items():
            # Convert path strings back to Path objects
            if status_data.get("audio_path"):
                status_data["audio_path"] = Path(status_data["audio_path"])
            if status_data.get("transcript_path"):
                status_data["transcript_path"] = Path(status_data["transcript_path"])

            episodes[episode_id] = EpisodeStatus(episode_id=episode_id, **status_data)

        return StateFile(
            version=raw_data.get("version", 1),
            last_updated=datetime.fromisoformat(raw_data["last_updated"])
            if "last_updated" in raw_data
            else datetime.now(),
            episodes=episodes,
        )

    def save(self) -> None:
        """Save state to file atomically.

        Raises:
            StateError: If save fails.
        """
        temp_path = self._state_file.with_suffix(".tmp")

        # Convert to JSON-serializable format
        episodes_data: dict[str, Any] = {}
        for episode_id, status in self._data.episodes.items():
            status_dict = status.model_dump(exclude={"episode_id"})
            # Convert Path objects to strings
            if status_dict.get("audio_path"):
                status_dict["audio_path"] = str(status_dict["audio_path"])
            if status_dict.get("transcript_path"):
                status_dict["transcript_path"] = str(status_dict["transcript_path"])
            # Convert datetime objects to ISO strings
            for key in ["downloaded_at", "transcribed_at", "analyzed_at"]:
                if status_dict.get(key):
                    status_dict[key] = status_dict[key].isoformat()
            episodes_data[episode_id] = status_dict

        data = {
            "version": self._data.version,
            "last_updated": datetime.now().isoformat(),
            "episodes": episodes_data,
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
            raise StateError(f"Failed to save state: {e}") from e

    def _get_or_create_status(self, episode_id: str) -> EpisodeStatus:
        """Get existing status or create new one."""
        if episode_id not in self._data.episodes:
            self._data.episodes[episode_id] = EpisodeStatus(episode_id=episode_id)
        return self._data.episodes[episode_id]

    # Query methods

    def is_downloaded(self, episode_id: str) -> bool:
        """Check if episode audio has been downloaded.

        Args:
            episode_id: Episode identifier.

        Returns:
            True if downloaded, False otherwise.
        """
        status = self._data.episodes.get(episode_id)
        return status.downloaded if status else False

    def is_transcribed(self, episode_id: str) -> bool:
        """Check if episode has been transcribed.

        Args:
            episode_id: Episode identifier.

        Returns:
            True if transcribed, False otherwise.
        """
        status = self._data.episodes.get(episode_id)
        return status.transcribed if status else False

    def is_analyzed(self, episode_id: str) -> bool:
        """Check if episode has been analyzed.

        Args:
            episode_id: Episode identifier.

        Returns:
            True if analyzed, False otherwise.
        """
        status = self._data.episodes.get(episode_id)
        return status.analyzed if status else False

    def get_status(self, episode_id: str) -> EpisodeStatus | None:
        """Get full status for an episode.

        Args:
            episode_id: Episode identifier.

        Returns:
            EpisodeStatus if exists, None otherwise.
        """
        return self._data.episodes.get(episode_id)

    def get_audio_path(self, episode_id: str) -> Path | None:
        """Get path to downloaded audio file.

        Args:
            episode_id: Episode identifier.

        Returns:
            Path to audio file if downloaded, None otherwise.
        """
        status = self._data.episodes.get(episode_id)
        return status.audio_path if status else None

    def get_transcript_path(self, episode_id: str) -> Path | None:
        """Get path to transcript file.

        Args:
            episode_id: Episode identifier.

        Returns:
            Path to transcript if transcribed, None otherwise.
        """
        status = self._data.episodes.get(episode_id)
        return status.transcript_path if status else None

    # Update methods

    def mark_downloaded(self, episode_id: str, audio_path: Path) -> None:
        """Mark episode as downloaded.

        Args:
            episode_id: Episode identifier.
            audio_path: Path to the downloaded audio file.
        """
        status = self._get_or_create_status(episode_id)
        status.downloaded = True
        status.downloaded_at = datetime.now()
        status.audio_path = audio_path
        self.save()

    def mark_transcribed(
        self,
        episode_id: str,
        transcript_path: Path,
        *,
        source: str = "whisper",
        has_timestamps: bool = False,
    ) -> None:
        """Mark episode as transcribed.

        Args:
            episode_id: Episode identifier.
            transcript_path: Path to the transcript file.
            source: Transcript source ('whisper' or 'apple').
            has_timestamps: Whether transcript includes timestamps.
        """
        status = self._get_or_create_status(episode_id)
        status.transcribed = True
        status.transcribed_at = datetime.now()
        status.transcript_path = transcript_path
        status.transcript_source = source
        status.has_timestamps = has_timestamps
        self.save()

    def mark_analyzed(self, episode_id: str, recommendations_count: int) -> None:
        """Mark episode as analyzed.

        Args:
            episode_id: Episode identifier.
            recommendations_count: Number of recommendations extracted.
        """
        status = self._get_or_create_status(episode_id)
        status.analyzed = True
        status.analyzed_at = datetime.now()
        status.recommendations_count = recommendations_count
        self.save()

    # Bulk query methods

    def get_all_episodes(self) -> dict[str, EpisodeStatus]:
        """Get all episode statuses.

        Returns:
            Dictionary mapping episode_id to EpisodeStatus.
        """
        return self._data.episodes.copy()

    def get_pending_transcription(self) -> list[str]:
        """Get episode IDs that are downloaded but not transcribed.

        Returns:
            List of episode IDs ready for transcription.
        """
        return [
            episode_id
            for episode_id, status in self._data.episodes.items()
            if status.downloaded and not status.transcribed
        ]

    def get_pending_analysis(self) -> list[str]:
        """Get episode IDs that are transcribed but not analyzed.

        Returns:
            List of episode IDs ready for analysis.
        """
        return [
            episode_id
            for episode_id, status in self._data.episodes.items()
            if status.transcribed and not status.analyzed
        ]


def load_state(state_file: Path) -> State:
    """Load state from file.

    Convenience function to create a State instance.

    Args:
        state_file: Path to state.json file.

    Returns:
        Initialized State manager.

    Raises:
        StateError: If state file is corrupted.
    """
    return State(state_file)
