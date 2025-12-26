"""Storage utilities for YouTube transcripts and metadata.

This module handles saving and loading YouTube videos and transcripts
using JSONL format for metadata and plain text for transcripts.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from podstock.youtube.exceptions import YouTubeStorageError
from podstock.youtube.models import (
    VideoTranscript,
    YouTubeVideo,
)


class YouTubeStorage:
    """Handles storage of YouTube videos and transcripts.

    Storage structure:
        data/youtube/
            channels.json           - Channel configurations
            youtube_state.json      - Collection state
            transcripts/
                {channel_slug}/
                    videos.jsonl    - Video metadata
                    {video_id}.txt  - Plain text transcript
                    {video_id}.json - Structured transcript with timestamps

    Example:
        >>> storage = YouTubeStorage(data_dir=Path("data"))
        >>> storage.save_transcript(transcript)
        >>> loaded = storage.load_transcript("technicalroundup", "dQw4w9WgXcQ")
    """

    def __init__(self, data_dir: Path) -> None:
        """Initialize storage.

        Args:
            data_dir: Base data directory.
        """
        self.data_dir = data_dir
        self.youtube_dir = data_dir / "youtube"
        self.transcripts_dir = self.youtube_dir / "transcripts"

        # Create directories
        self.youtube_dir.mkdir(parents=True, exist_ok=True)
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)

    def _get_channel_dir(self, channel_id: str) -> Path:
        """Get directory for a channel's transcripts."""
        channel_dir = self.transcripts_dir / channel_id
        channel_dir.mkdir(parents=True, exist_ok=True)
        return channel_dir

    def _get_videos_file(self, channel_id: str) -> Path:
        """Get path to videos.jsonl for a channel."""
        return self._get_channel_dir(channel_id) / "videos.jsonl"

    def save_video(self, video: YouTubeVideo) -> None:
        """Save video metadata to JSONL file.

        Args:
            video: Video to save.
        """
        videos_file = self._get_videos_file(video.channel_id)

        # Load existing videos to check for duplicates
        existing = self.load_videos(video.channel_id)
        existing_ids = {v.id for v in existing}

        if video.id in existing_ids:
            # Update existing entry
            existing = [v if v.id != video.id else video for v in existing]
            self._write_videos(video.channel_id, existing)
        else:
            # Append new video
            with open(videos_file, "a", encoding="utf-8") as f:
                f.write(video.model_dump_json() + "\n")

    def save_videos(self, videos: list[YouTubeVideo]) -> int:
        """Save multiple videos, avoiding duplicates.

        Args:
            videos: List of videos to save.

        Returns:
            Number of new videos saved.
        """
        if not videos:
            return 0

        channel_id = videos[0].channel_id

        # Load existing
        existing = self.load_videos(channel_id)
        existing_ids = {v.id for v in existing}

        # Find new videos
        new_videos = [v for v in videos if v.id not in existing_ids]

        if new_videos:
            videos_file = self._get_videos_file(channel_id)
            with open(videos_file, "a", encoding="utf-8") as f:
                for video in new_videos:
                    f.write(video.model_dump_json() + "\n")

        return len(new_videos)

    def _write_videos(self, channel_id: str, videos: list[YouTubeVideo]) -> None:
        """Rewrite entire videos file."""
        videos_file = self._get_videos_file(channel_id)

        # Write atomically
        tmp_file = videos_file.with_suffix(".tmp")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                for video in videos:
                    f.write(video.model_dump_json() + "\n")
            tmp_file.rename(videos_file)
        except Exception as e:
            if tmp_file.exists():
                tmp_file.unlink()
            raise YouTubeStorageError(f"Failed to write videos: {e}")

    def load_videos(self, channel_id: str) -> list[YouTubeVideo]:
        """Load all videos for a channel.

        Args:
            channel_id: Channel ID (our internal slug).

        Returns:
            List of YouTubeVideo objects.
        """
        videos_file = self._get_videos_file(channel_id)

        if not videos_file.exists():
            return []

        videos = []
        with open(videos_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        videos.append(YouTubeVideo.model_validate(data))
                    except (json.JSONDecodeError, ValueError):
                        continue

        return videos

    def get_video(self, channel_id: str, video_id: str) -> YouTubeVideo | None:
        """Get a specific video by ID.

        Args:
            channel_id: Channel ID.
            video_id: YouTube video ID.

        Returns:
            YouTubeVideo or None if not found.
        """
        videos = self.load_videos(channel_id)
        for video in videos:
            if video.id == video_id:
                return video
        return None

    def save_transcript(self, transcript: VideoTranscript) -> Path:
        """Save a transcript to disk.

        Creates both:
        - {video_id}.txt - Plain text transcript
        - {video_id}.json - Full transcript with timestamps

        Args:
            transcript: Transcript to save.

        Returns:
            Path to the plain text file.
        """
        channel_dir = self._get_channel_dir(transcript.channel_id)

        # Save plain text
        txt_file = channel_dir / f"{transcript.video_id}.txt"
        header = self._build_transcript_header(transcript)
        txt_file.write_text(
            header + "\n\n" + transcript.text,
            encoding="utf-8",
        )

        # Save JSON with timestamps
        json_file = channel_dir / f"{transcript.video_id}.json"
        json_file.write_text(
            transcript.model_dump_json(indent=2),
            encoding="utf-8",
        )

        # Update video record to show it has transcript
        video = self.get_video(transcript.channel_id, transcript.video_id)
        if video:
            video.has_transcript = True
            video.transcript_language = transcript.language
            video.transcript_type = transcript.transcript_type
            self.save_video(video)

        return txt_file

    def _build_transcript_header(self, transcript: VideoTranscript) -> str:
        """Build header for plain text transcript file."""
        lines = [
            "=" * 60,
            f"Video: {transcript.video_id}",
            f"Channel: {transcript.channel_id}",
            f"source: youtube-{transcript.transcript_type}",
            f"language: {transcript.language}",
            f"word_count: {transcript.word_count}",
            f"has_timestamps: {len(transcript.segments) > 0}",
            f"extracted_at: {transcript.extracted_at.isoformat()}",
            "=" * 60,
        ]
        return "\n".join(lines)

    def load_transcript(
        self,
        channel_id: str,
        video_id: str,
        with_segments: bool = False,
    ) -> VideoTranscript | None:
        """Load a transcript from disk.

        Args:
            channel_id: Channel ID.
            video_id: YouTube video ID.
            with_segments: If True, load from JSON (includes timestamps).

        Returns:
            VideoTranscript or None if not found.
        """
        channel_dir = self._get_channel_dir(channel_id)

        if with_segments:
            json_file = channel_dir / f"{video_id}.json"
            if json_file.exists():
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                    return VideoTranscript.model_validate(data)
                except (json.JSONDecodeError, ValueError):
                    return None
        else:
            txt_file = channel_dir / f"{video_id}.txt"
            if txt_file.exists():
                content = txt_file.read_text(encoding="utf-8")
                # Parse header and extract text
                parts = content.split("=" * 60)
                if len(parts) >= 3:
                    text = parts[2].strip()
                    return VideoTranscript(
                        video_id=video_id,
                        channel_id=channel_id,
                        text=text,
                        word_count=len(text.split()),
                    )

        return None

    def has_transcript(self, channel_id: str, video_id: str) -> bool:
        """Check if a transcript exists for a video.

        Args:
            channel_id: Channel ID.
            video_id: YouTube video ID.

        Returns:
            True if transcript file exists.
        """
        channel_dir = self._get_channel_dir(channel_id)
        txt_file = channel_dir / f"{video_id}.txt"
        return txt_file.exists()

    def list_transcripts(self, channel_id: str) -> list[str]:
        """List all video IDs with transcripts for a channel.

        Args:
            channel_id: Channel ID.

        Returns:
            List of video IDs.
        """
        channel_dir = self._get_channel_dir(channel_id)
        if not channel_dir.exists():
            return []

        return [
            f.stem
            for f in channel_dir.glob("*.txt")
            if f.stem != "videos"  # Exclude videos.jsonl
        ]

    def get_transcript_path(self, channel_id: str, video_id: str) -> Path | None:
        """Get path to a transcript file.

        Args:
            channel_id: Channel ID.
            video_id: Video ID.

        Returns:
            Path to txt file or None if not exists.
        """
        channel_dir = self._get_channel_dir(channel_id)
        txt_file = channel_dir / f"{video_id}.txt"
        return txt_file if txt_file.exists() else None

    def get_stats(self, channel_id: str | None = None) -> dict:
        """Get storage statistics.

        Args:
            channel_id: Optional channel to get stats for.

        Returns:
            Dictionary with statistics.
        """
        if channel_id:
            videos = self.load_videos(channel_id)
            transcripts = self.list_transcripts(channel_id)
            return {
                "channel_id": channel_id,
                "total_videos": len(videos),
                "videos_with_transcripts": len(transcripts),
                "transcript_coverage": len(transcripts) / len(videos) if videos else 0,
            }
        else:
            # All channels
            stats = {
                "total_channels": 0,
                "total_videos": 0,
                "total_transcripts": 0,
            }

            for channel_dir in self.transcripts_dir.iterdir():
                if channel_dir.is_dir():
                    stats["total_channels"] += 1
                    stats["total_videos"] += len(self.load_videos(channel_dir.name))
                    stats["total_transcripts"] += len(self.list_transcripts(channel_dir.name))

            return stats
