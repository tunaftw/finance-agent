"""Pydantic models for podcast sync operations.

This module defines data structures for tracking sync progress and results.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EpisodeSyncResult(BaseModel):
    """Result of syncing a single episode.

    Attributes:
        episode_id: Unique episode identifier.
        podcast_id: Parent podcast identifier.
        title: Episode title.
        published_at: Episode publication date.
        status: Sync status ('synced', 'skipped', 'failed').
        transcript_source: Source used for transcription ('apple' or 'whisper').
        error: Error message if failed.

    Example:
        >>> result = EpisodeSyncResult(
        ...     episode_id="bp-2024-12-18-abc1",
        ...     podcast_id="borspodden",
        ...     title="Avsnitt 600",
        ...     published_at=datetime(2024, 12, 18),
        ...     status="synced",
        ...     transcript_source="apple"
        ... )
    """

    episode_id: str
    podcast_id: str
    title: str
    published_at: datetime
    status: Literal["synced", "skipped", "failed"]
    transcript_source: Literal["apple", "whisper"] | None = None
    error: str | None = None


class SyncSummary(BaseModel):
    """Summary of a sync operation.

    Attributes:
        started_at: When sync started.
        completed_at: When sync completed.
        podcasts_checked: Number of podcasts processed.
        new_episodes: Number of new episodes found.
        transcribed: Number of episodes transcribed.
        failed: Number of episodes that failed.
        errors: List of error messages.
        episodes: List of individual episode results.

    Example:
        >>> summary = SyncSummary(started_at=datetime.now())
        >>> summary.new_episodes
        0
    """

    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
    podcasts_checked: int = 0
    new_episodes: int = 0
    transcribed: int = 0
    failed: int = 0
    errors: list[str] = Field(default_factory=list)
    episodes: list[EpisodeSyncResult] = Field(default_factory=list)

    def add_result(self, result: EpisodeSyncResult) -> None:
        """Add an episode result to the summary."""
        self.episodes.append(result)

        if result.status == "synced":
            self.new_episodes += 1
            self.transcribed += 1
        elif result.status == "failed":
            self.failed += 1
            if result.error:
                self.errors.append(f"{result.episode_id}: {result.error}")

    def finish(self) -> None:
        """Mark the sync as complete."""
        self.completed_at = datetime.now()
