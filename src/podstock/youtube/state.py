"""State management for YouTube collection.

This module tracks the collection progress for each YouTube channel,
similar to the Twitter state tracking.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from podstock.youtube.exceptions import YouTubeStateError
from podstock.youtube.models import (
    YouTubeCollectionState,
    YouTubeStateFile,
)


class YouTubeState:
    """Manages YouTube collection state.

    Tracks which videos have been collected and transcribed for each channel.

    Example:
        >>> state = YouTubeState(data_dir=Path("data"))
        >>> channel_state = state.get_channel_state("technicalroundup")
        >>> print(f"Collected: {channel_state.videos_collected}")
    """

    def __init__(self, data_dir: Path) -> None:
        """Initialize state manager.

        Args:
            data_dir: Base data directory.
        """
        self.data_dir = data_dir
        self.youtube_dir = data_dir / "youtube"
        self.state_file = self.youtube_dir / "youtube_state.json"

        # Create directory
        self.youtube_dir.mkdir(parents=True, exist_ok=True)

    def _load_state_file(self) -> YouTubeStateFile:
        """Load state file from disk."""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                return YouTubeStateFile.model_validate(data)
            except (json.JSONDecodeError, ValueError):
                return YouTubeStateFile()
        return YouTubeStateFile()

    def _save_state_file(self, state_file: YouTubeStateFile) -> None:
        """Save state file to disk (atomic write)."""
        state_file.last_updated = datetime.now()

        tmp_file = self.state_file.with_suffix(".tmp")
        try:
            tmp_file.write_text(
                state_file.model_dump_json(indent=2),
                encoding="utf-8",
            )
            tmp_file.rename(self.state_file)
        except Exception as e:
            if tmp_file.exists():
                tmp_file.unlink()
            raise YouTubeStateError(f"Failed to save state: {e}")

    def get_channel_state(self, channel_id: str) -> YouTubeCollectionState:
        """Get collection state for a channel.

        Args:
            channel_id: Channel ID.

        Returns:
            YouTubeCollectionState (creates new if not exists).
        """
        state_file = self._load_state_file()

        if channel_id not in state_file.channels:
            state_file.channels[channel_id] = YouTubeCollectionState(
                channel_id=channel_id
            )
            self._save_state_file(state_file)

        return state_file.channels[channel_id]

    def update_channel_state(
        self,
        channel_id: str,
        **updates: int | str | bool | datetime | None,
    ) -> YouTubeCollectionState:
        """Update collection state for a channel.

        Args:
            channel_id: Channel ID.
            **updates: Fields to update.

        Returns:
            Updated state.
        """
        state_file = self._load_state_file()

        if channel_id not in state_file.channels:
            state_file.channels[channel_id] = YouTubeCollectionState(
                channel_id=channel_id
            )

        state = state_file.channels[channel_id]
        state_dict = state.model_dump()

        for key, value in updates.items():
            if hasattr(state, key):
                state_dict[key] = value

        state_file.channels[channel_id] = YouTubeCollectionState.model_validate(state_dict)
        self._save_state_file(state_file)

        return state_file.channels[channel_id]

    def mark_collected(
        self,
        channel_id: str,
        videos_collected: int,
        videos_with_transcripts: int,
        newest_date: datetime | None = None,
        oldest_date: datetime | None = None,
        last_video_id: str | None = None,
        oldest_video_id: str | None = None,
    ) -> YouTubeCollectionState:
        """Mark a collection batch as complete.

        Args:
            channel_id: Channel ID.
            videos_collected: Total videos collected.
            videos_with_transcripts: Videos that had transcripts.
            newest_date: Date of newest video.
            oldest_date: Date of oldest video.
            last_video_id: ID of most recent video.
            oldest_video_id: ID of oldest video.

        Returns:
            Updated state.
        """
        updates: dict = {
            "last_collected_at": datetime.now(),
            "videos_collected": videos_collected,
            "videos_with_transcripts": videos_with_transcripts,
        }

        if newest_date:
            updates["newest_video_date"] = newest_date
        if oldest_date:
            updates["oldest_video_date"] = oldest_date
        if last_video_id:
            updates["last_video_id"] = last_video_id
        if oldest_video_id:
            updates["oldest_video_id"] = oldest_video_id

        return self.update_channel_state(channel_id, **updates)

    def mark_collection_complete(self, channel_id: str) -> YouTubeCollectionState:
        """Mark that all videos have been collected for a channel.

        Args:
            channel_id: Channel ID.

        Returns:
            Updated state.
        """
        return self.update_channel_state(
            channel_id,
            collection_complete=True,
            last_collected_at=datetime.now(),
        )

    def record_error(
        self,
        channel_id: str,
        error_message: str,
    ) -> YouTubeCollectionState:
        """Record an error during collection.

        Args:
            channel_id: Channel ID.
            error_message: Error message.

        Returns:
            Updated state.
        """
        state = self.get_channel_state(channel_id)

        return self.update_channel_state(
            channel_id,
            last_error=error_message,
            error_count=state.error_count + 1,
        )

    def clear_errors(self, channel_id: str) -> YouTubeCollectionState:
        """Clear error status for a channel.

        Args:
            channel_id: Channel ID.

        Returns:
            Updated state.
        """
        return self.update_channel_state(
            channel_id,
            last_error=None,
            error_count=0,
        )

    def reset_channel_state(self, channel_id: str) -> YouTubeCollectionState:
        """Reset collection state for a channel.

        Args:
            channel_id: Channel ID.

        Returns:
            Fresh state.
        """
        state_file = self._load_state_file()
        state_file.channels[channel_id] = YouTubeCollectionState(
            channel_id=channel_id
        )
        self._save_state_file(state_file)
        return state_file.channels[channel_id]

    def get_all_states(self) -> dict[str, YouTubeCollectionState]:
        """Get collection state for all channels.

        Returns:
            Dictionary mapping channel_id to state.
        """
        state_file = self._load_state_file()
        return state_file.channels

    def get_summary(self) -> dict:
        """Get summary statistics across all channels.

        Returns:
            Dictionary with summary stats.
        """
        states = self.get_all_states()

        total_videos = sum(s.videos_collected for s in states.values())
        total_transcripts = sum(s.videos_with_transcripts for s in states.values())
        complete_channels = sum(1 for s in states.values() if s.collection_complete)
        channels_with_errors = sum(1 for s in states.values() if s.last_error)

        return {
            "total_channels": len(states),
            "complete_channels": complete_channels,
            "total_videos_collected": total_videos,
            "total_transcripts": total_transcripts,
            "channels_with_errors": channels_with_errors,
        }
