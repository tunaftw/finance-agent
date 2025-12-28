"""YouTube channel management.

This module provides CRUD operations for YouTube channels,
similar to the podcast manager in rss/manager.py.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from podstock.youtube.exceptions import (
    YouTubeChannelNotFoundError,
    YouTubeStorageError,
)
from podstock.youtube.extractor import YouTubeExtractor
from podstock.youtube.models import (
    YouTubeChannel,
    YouTubeChannelsFile,
    extract_channel_id,
)


class YouTubeChannelManager:
    """Manages YouTube channel configurations.

    Handles adding, removing, listing, and updating YouTube channels.

    Example:
        >>> manager = YouTubeChannelManager(data_dir=Path("data"))
        >>> channel = manager.add_channel(
        ...     "https://www.youtube.com/@TechnicalRoundup",
        ...     category="crypto"
        ... )
        >>> print(f"Added: {channel.name}")
    """

    def __init__(self, data_dir: Path) -> None:
        """Initialize channel manager.

        Args:
            data_dir: Base data directory.
        """
        self.data_dir = data_dir
        self.youtube_dir = data_dir / "youtube"
        self.channels_file = self.youtube_dir / "sources.json"  # Renamed from channels.json

        # Create directory
        self.youtube_dir.mkdir(parents=True, exist_ok=True)

    def _load_channels_file(self) -> YouTubeChannelsFile:
        """Load channels file from disk."""
        if self.channels_file.exists():
            try:
                data = json.loads(self.channels_file.read_text(encoding="utf-8"))
                return YouTubeChannelsFile.model_validate(data)
            except (json.JSONDecodeError, ValueError):
                return YouTubeChannelsFile()
        return YouTubeChannelsFile()

    def _save_channels_file(self, channels_file: YouTubeChannelsFile) -> None:
        """Save channels file to disk (atomic write)."""
        channels_file.updated_at = datetime.now()

        tmp_file = self.channels_file.with_suffix(".tmp")
        try:
            tmp_file.write_text(
                channels_file.model_dump_json(indent=2),
                encoding="utf-8",
            )
            tmp_file.rename(self.channels_file)
        except Exception as e:
            if tmp_file.exists():
                tmp_file.unlink()
            raise YouTubeStorageError(f"Failed to save channels: {e}")

    def list_channels(self, active_only: bool = False) -> list[YouTubeChannel]:
        """List all configured channels.

        Args:
            active_only: If True, only return active channels.

        Returns:
            List of YouTubeChannel objects.
        """
        channels_file = self._load_channels_file()
        channels = channels_file.channels

        if active_only:
            channels = [c for c in channels if c.active]

        return channels

    def get_channel(self, channel_id: str) -> YouTubeChannel:
        """Get a channel by ID.

        Args:
            channel_id: Channel ID (our internal slug).

        Returns:
            YouTubeChannel object.

        Raises:
            YouTubeChannelNotFoundError: If channel not found.
        """
        channels = self.list_channels()
        for channel in channels:
            if channel.id == channel_id:
                return channel

        raise YouTubeChannelNotFoundError(channel_id)

    def add_channel(
        self,
        channel_url: str,
        category: str | None = None,
        description: str | None = None,
        language: str = "en",
    ) -> YouTubeChannel:
        """Add a new YouTube channel.

        Fetches channel metadata from YouTube and saves configuration.

        Args:
            channel_url: Full YouTube channel URL.
            category: Category (crypto, finance, tech, etc.).
            description: Our notes about this channel.
            language: Primary language code.

        Returns:
            Created YouTubeChannel object.

        Raises:
            YouTubeStorageError: If channel already exists or save fails.
        """
        # Extract channel info using yt-dlp
        try:
            extractor = YouTubeExtractor(self.data_dir)
            channel = extractor.get_channel_info(channel_url)

            if channel is None:
                # Create basic channel from URL
                handle = extract_channel_id(channel_url)
                if handle:
                    slug_id = handle.lstrip("@").lower()
                else:
                    slug_id = "unknown-channel"

                channel = YouTubeChannel(
                    id=slug_id,
                    channel_id=None,
                    handle=handle,
                    name=slug_id.replace("-", " ").title(),
                    language=language,
                )

        except Exception:
            # Fallback: create basic channel from URL
            handle = extract_channel_id(channel_url)
            if handle:
                slug_id = handle.lstrip("@").lower()
            else:
                slug_id = "unknown-channel"

            channel = YouTubeChannel(
                id=slug_id,
                channel_id=None,
                handle=handle,
                name=slug_id.replace("-", " ").title(),
                language=language,
            )

        # Apply overrides
        if category:
            channel.category = category
        if description:
            channel.description = description
        channel.language = language

        # Check for duplicates
        channels_file = self._load_channels_file()
        existing_ids = {c.id for c in channels_file.channels}

        if channel.id in existing_ids:
            raise YouTubeStorageError(f"Channel already exists: {channel.id}")

        # Save
        channels_file.channels.append(channel)
        self._save_channels_file(channels_file)

        return channel

    def add_channel_manual(
        self,
        channel_id: str,
        youtube_channel_id: str,
        name: str,
        handle: str | None = None,
        category: str | None = None,
        description: str | None = None,
        language: str = "en",
    ) -> YouTubeChannel:
        """Add a channel with manual configuration.

        Use this when auto-detection fails or you want to specify details.

        Args:
            channel_id: Our internal slug ID.
            youtube_channel_id: YouTube's UC... channel ID.
            name: Display name.
            handle: YouTube handle (@name).
            category: Category classification.
            description: Notes about this channel.
            language: Primary language.

        Returns:
            Created YouTubeChannel object.

        Raises:
            YouTubeStorageError: If channel already exists.
        """
        # Check for duplicates
        channels_file = self._load_channels_file()
        existing_ids = {c.id for c in channels_file.channels}

        if channel_id in existing_ids:
            raise YouTubeStorageError(f"Channel already exists: {channel_id}")

        channel = YouTubeChannel(
            id=channel_id,
            channel_id=youtube_channel_id,
            handle=handle,
            name=name,
            category=category,
            description=description,
            language=language,
        )

        channels_file.channels.append(channel)
        self._save_channels_file(channels_file)

        return channel

    def update_channel(
        self,
        channel_id: str,
        **updates: str | int | bool | None,
    ) -> YouTubeChannel:
        """Update a channel's configuration.

        Args:
            channel_id: Channel ID to update.
            **updates: Fields to update (name, category, description, etc.).

        Returns:
            Updated YouTubeChannel object.

        Raises:
            YouTubeChannelNotFoundError: If channel not found.
        """
        channels_file = self._load_channels_file()

        found = False
        for i, channel in enumerate(channels_file.channels):
            if channel.id == channel_id:
                # Apply updates
                channel_dict = channel.model_dump()
                for key, value in updates.items():
                    if hasattr(channel, key):
                        channel_dict[key] = value

                channels_file.channels[i] = YouTubeChannel.model_validate(channel_dict)
                found = True
                break

        if not found:
            raise YouTubeChannelNotFoundError(channel_id)

        self._save_channels_file(channels_file)
        return channels_file.channels[i]

    def remove_channel(self, channel_id: str) -> bool:
        """Remove a channel.

        Note: Does not delete collected transcripts.

        Args:
            channel_id: Channel ID to remove.

        Returns:
            True if removed, False if not found.
        """
        channels_file = self._load_channels_file()
        original_count = len(channels_file.channels)

        channels_file.channels = [
            c for c in channels_file.channels
            if c.id != channel_id
        ]

        if len(channels_file.channels) < original_count:
            self._save_channels_file(channels_file)
            return True

        return False

    def set_active(self, channel_id: str, active: bool) -> YouTubeChannel:
        """Enable or disable a channel.

        Args:
            channel_id: Channel ID.
            active: Whether to activate or deactivate.

        Returns:
            Updated channel.

        Raises:
            YouTubeChannelNotFoundError: If channel not found.
        """
        return self.update_channel(channel_id, active=active)

    def get_channel_url(self, channel: YouTubeChannel) -> str:
        """Get the YouTube URL for a channel.

        Args:
            channel: Channel object.

        Returns:
            Best available URL for the channel.
        """
        if channel.handle:
            return f"https://www.youtube.com/{channel.handle}"
        elif channel.channel_id:
            return f"https://www.youtube.com/channel/{channel.channel_id}"
        else:
            return f"https://www.youtube.com/@{channel.id}"
