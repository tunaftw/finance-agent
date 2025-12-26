"""YouTube transcript extraction using yt-dlp.

This module provides functionality to extract auto-generated and manual
transcripts from YouTube videos using yt-dlp.

Usage:
    from podstock.youtube.extractor import YouTubeExtractor

    extractor = YouTubeExtractor(data_dir=Path("data"))
    transcript = extractor.extract_transcript("dQw4w9WgXcQ")
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from podstock.youtube.exceptions import (
    YouTubeExtractionError,
    YouTubeTranscriptNotAvailable,
    YtDlpError,
    YtDlpNotFoundError,
)
from podstock.youtube.models import (
    TranscriptSegment,
    VideoTranscript,
    YouTubeChannel,
    YouTubeVideo,
    extract_channel_id,
)


class YouTubeExtractor:
    """Extract transcripts from YouTube using yt-dlp.

    This class wraps yt-dlp to extract auto-generated and manual
    subtitles from YouTube videos. It handles VTT parsing, channel
    listing, and video metadata extraction.

    Attributes:
        data_dir: Base directory for data storage.
        cache_dir: Directory for temporary files.
        preferred_languages: Languages to prefer for transcripts.

    Example:
        >>> extractor = YouTubeExtractor(data_dir=Path("data"))
        >>> transcript = extractor.extract_transcript("dQw4w9WgXcQ")
        >>> print(f"Got {transcript.word_count} words")
    """

    def __init__(
        self,
        data_dir: Path,
        preferred_languages: list[str] | None = None,
    ) -> None:
        """Initialize the extractor.

        Args:
            data_dir: Base directory for data storage.
            preferred_languages: Languages to prefer (default: ["en", "sv"]).

        Raises:
            YtDlpNotFoundError: If yt-dlp is not installed.
        """
        self.data_dir = data_dir
        self.cache_dir = data_dir / "youtube" / "cache"
        self.preferred_languages = preferred_languages or ["en", "sv"]

        # Verify yt-dlp is installed
        if not self._check_ytdlp():
            raise YtDlpNotFoundError()

        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _check_ytdlp(self) -> bool:
        """Check if yt-dlp is installed."""
        return shutil.which("yt-dlp") is not None

    def _run_ytdlp(
        self,
        args: list[str],
        timeout: int = 300,
        check_exit_code: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run yt-dlp with given arguments.

        Args:
            args: Command line arguments for yt-dlp.
            timeout: Timeout in seconds.
            check_exit_code: Whether to raise on non-zero exit code.

        Returns:
            Completed process result.

        Raises:
            YtDlpError: If yt-dlp fails (when check_exit_code=True).
        """
        cmd = ["yt-dlp"] + args

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if check_exit_code and result.returncode != 0:
                # Check for common errors
                if "Video unavailable" in result.stderr:
                    raise YouTubeExtractionError("Video is unavailable")
                if "Private video" in result.stderr:
                    raise YouTubeExtractionError("Video is private")

                raise YtDlpError(
                    f"yt-dlp failed with code {result.returncode}",
                    stderr=result.stderr,
                )

            return result

        except subprocess.TimeoutExpired:
            raise YtDlpError(f"yt-dlp timed out after {timeout} seconds")
        except FileNotFoundError:
            raise YtDlpNotFoundError()

    def get_video_info(self, video_id: str) -> YouTubeVideo | None:
        """Get metadata for a single video.

        Args:
            video_id: YouTube video ID (11 characters).

        Returns:
            YouTubeVideo with metadata, or None if not found.

        Raises:
            YtDlpError: If extraction fails.
        """
        url = f"https://www.youtube.com/watch?v={video_id}"

        result = self._run_ytdlp([
            "--dump-json",
            "--no-download",
            url,
        ])

        try:
            data = json.loads(result.stdout)
            return self._parse_video_info(data, channel_id="unknown")
        except json.JSONDecodeError:
            return None

    def _parse_video_info(
        self,
        data: dict[str, Any],
        channel_id: str,
    ) -> YouTubeVideo:
        """Parse video info from yt-dlp JSON output.

        Args:
            data: JSON data from yt-dlp.
            channel_id: Our internal channel ID.

        Returns:
            Parsed YouTubeVideo object.
        """
        # Parse upload date (format: YYYYMMDD)
        upload_date = data.get("upload_date", "")
        if upload_date and len(upload_date) == 8:
            published_at = datetime.strptime(upload_date, "%Y%m%d")
        else:
            published_at = datetime.now()

        # Check for subtitles
        has_transcript = False
        transcript_type = "none"
        transcript_language = None

        subtitles = data.get("subtitles", {})
        auto_captions = data.get("automatic_captions", {})

        # Check manual subtitles first
        for lang in self.preferred_languages:
            if lang in subtitles:
                has_transcript = True
                transcript_type = "manual"
                transcript_language = lang
                break

        # Fall back to auto-captions
        if not has_transcript:
            for lang in self.preferred_languages:
                if lang in auto_captions:
                    has_transcript = True
                    transcript_type = "auto"
                    transcript_language = lang
                    break

        video = YouTubeVideo(
            id=data.get("id", ""),
            channel_id=channel_id,
            youtube_channel_id=data.get("channel_id"),
            title=data.get("title", "Unknown"),
            description=data.get("description"),
            published_at=published_at,
            duration_seconds=data.get("duration"),
            view_count=data.get("view_count"),
            like_count=data.get("like_count"),
            has_transcript=has_transcript,
            transcript_language=transcript_language,
            transcript_type=transcript_type,
        )

        # Extract crypto mentions from title/description
        video.extract_crypto_mentions()

        return video

    def get_channel_videos(
        self,
        channel_url: str,
        channel_id: str,
        max_videos: int | None = None,
        since: datetime | None = None,
    ) -> list[YouTubeVideo]:
        """List all videos from a YouTube channel.

        Args:
            channel_url: Full YouTube channel URL.
            channel_id: Our internal channel ID (slug).
            max_videos: Maximum number of videos to fetch.
            since: Only fetch videos published after this date.

        Returns:
            List of YouTubeVideo objects.

        Raises:
            YtDlpError: If extraction fails.
        """
        args = [
            "--flat-playlist",
            "--dump-json",
            "--no-download",
        ]

        if max_videos:
            args.extend(["--playlist-end", str(max_videos)])

        # Add date filter if specified
        if since:
            date_str = since.strftime("%Y%m%d")
            args.extend(["--dateafter", date_str])

        # Get videos tab URL
        videos_url = channel_url.rstrip("/") + "/videos"
        args.append(videos_url)

        result = self._run_ytdlp(args, timeout=600)

        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                video = self._parse_playlist_entry(data, channel_id)
                if video:
                    videos.append(video)
            except json.JSONDecodeError:
                continue

        return videos

    def _parse_playlist_entry(
        self,
        data: dict[str, Any],
        channel_id: str,
    ) -> YouTubeVideo | None:
        """Parse a playlist entry from flat-playlist output.

        Args:
            data: JSON data for one video.
            channel_id: Our internal channel ID.

        Returns:
            YouTubeVideo or None if parsing fails.
        """
        video_id = data.get("id")
        if not video_id or len(video_id) != 11:
            return None

        # Parse upload date
        upload_date = data.get("upload_date", "")
        if upload_date and len(upload_date) == 8:
            published_at = datetime.strptime(upload_date, "%Y%m%d")
        else:
            # Estimate from timestamp if available
            timestamp = data.get("timestamp")
            if timestamp:
                published_at = datetime.fromtimestamp(timestamp)
            else:
                published_at = datetime.now()

        return YouTubeVideo(
            id=video_id,
            channel_id=channel_id,
            youtube_channel_id=data.get("channel_id"),
            title=data.get("title", "Unknown"),
            description=data.get("description"),
            published_at=published_at,
            duration_seconds=data.get("duration"),
            view_count=data.get("view_count"),
            like_count=data.get("like_count"),
            has_transcript=False,  # Need to check individually
            transcript_type="none",
        )

    def extract_transcript(
        self,
        video_id: str,
        channel_id: str = "unknown",
        prefer_auto: bool = True,
    ) -> VideoTranscript:
        """Extract transcript for a YouTube video.

        Downloads the best available transcript (auto-generated or manual)
        and parses it into segments.

        Args:
            video_id: YouTube video ID (11 characters).
            channel_id: Our internal channel ID.
            prefer_auto: Whether to prefer auto-generated (usually better for speech).

        Returns:
            VideoTranscript with full text and segments.

        Raises:
            YouTubeTranscriptNotAvailable: If no transcript exists.
            YtDlpError: If extraction fails.
        """
        url = f"https://www.youtube.com/watch?v={video_id}"

        with tempfile.TemporaryDirectory() as tmpdir:
            output_template = str(Path(tmpdir) / "%(id)s.%(ext)s")

            # Build language preference string
            lang_pref = ",".join(self.preferred_languages)

            # Try with both auto and manual subs to maximize chances
            args = [
                "--skip-download",
                "--write-auto-sub",
                "--write-sub",
                "--sub-lang", lang_pref,
                "--sub-format", "vtt",
                "--convert-subs", "vtt",
                "-o", output_template,
                url,
            ]

            # yt-dlp may return non-zero even when subtitles are downloaded
            # (e.g., when some requested languages aren't available)
            # So we don't check exit code and just verify files were created
            self._run_ytdlp(args, check_exit_code=False)

            # Find the downloaded VTT file
            vtt_files = list(Path(tmpdir).glob("*.vtt"))
            if not vtt_files:
                raise YouTubeTranscriptNotAvailable(
                    video_id, "No subtitles available"
                )

            vtt_file = vtt_files[0]
            vtt_content = vtt_file.read_text(encoding="utf-8")

            # Parse VTT content
            segments = self._parse_vtt(vtt_content)

            # Detect language from filename
            language = "en"
            for lang in self.preferred_languages:
                if f".{lang}." in vtt_file.name:
                    language = lang
                    break

            # Determine transcript type
            transcript_type = "auto" if ".auto." in vtt_file.name or prefer_auto else "manual"

            # Build full text
            full_text = " ".join(seg.text for seg in segments)
            full_text = self._clean_transcript_text(full_text)

            # Calculate duration
            duration = segments[-1].end if segments else None

            transcript = VideoTranscript(
                video_id=video_id,
                channel_id=channel_id,
                language=language,
                text=full_text,
                segments=segments,
                duration_seconds=duration,
                transcript_type=transcript_type,
            )
            transcript.calculate_word_count()

            return transcript

    def _parse_vtt(self, content: str) -> list[TranscriptSegment]:
        """Parse VTT subtitle content into segments.

        Args:
            content: Raw VTT file content.

        Returns:
            List of TranscriptSegment objects.
        """
        segments = []

        # VTT timestamp pattern: 00:00:00.000 --> 00:00:05.000
        timestamp_pattern = r"(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})"

        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Look for timestamp line
            match = re.match(timestamp_pattern, line)
            if match:
                start_str, end_str = match.groups()
                start = self._parse_timestamp(start_str)
                end = self._parse_timestamp(end_str)

                # Collect text lines until empty line
                text_lines = []
                i += 1
                while i < len(lines) and lines[i].strip():
                    text_line = lines[i].strip()
                    # Remove VTT tags like <c> </c>
                    text_line = re.sub(r"<[^>]+>", "", text_line)
                    if text_line:
                        text_lines.append(text_line)
                    i += 1

                if text_lines:
                    text = " ".join(text_lines)
                    segments.append(TranscriptSegment(
                        start=start,
                        end=end,
                        text=text,
                    ))
            else:
                i += 1

        return segments

    def _parse_timestamp(self, timestamp: str) -> float:
        """Parse VTT timestamp to seconds.

        Args:
            timestamp: Timestamp string (00:00:00.000 or 00:00:00,000).

        Returns:
            Time in seconds.
        """
        # Handle both . and , as decimal separator
        timestamp = timestamp.replace(",", ".")

        parts = timestamp.split(":")
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
        elif len(parts) == 2:
            minutes, seconds = parts
            return float(minutes) * 60 + float(seconds)
        else:
            return float(timestamp)

    def _clean_transcript_text(self, text: str) -> str:
        """Clean up transcript text.

        Removes duplicate phrases, normalizes whitespace, etc.

        Args:
            text: Raw concatenated transcript text.

        Returns:
            Cleaned text.
        """
        # Remove multiple spaces
        text = re.sub(r"\s+", " ", text)

        # Remove common YouTube auto-caption artifacts
        text = re.sub(r"\[Music\]", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\[Applause\]", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\[Laughter\]", "", text, flags=re.IGNORECASE)

        return text.strip()

    def get_channel_info(self, channel_url: str) -> YouTubeChannel | None:
        """Get metadata for a YouTube channel.

        Args:
            channel_url: Full YouTube channel URL.

        Returns:
            YouTubeChannel with metadata, or None if not found.
        """
        result = self._run_ytdlp([
            "--dump-json",
            "--playlist-items", "0",  # Don't get videos, just channel info
            channel_url,
        ])

        try:
            data = json.loads(result.stdout.split("\n")[0])

            # Extract handle from URL
            handle = extract_channel_id(channel_url)
            if handle and not handle.startswith("@"):
                handle = f"@{handle}"

            # Generate slug ID
            channel_name = data.get("channel", data.get("uploader", "unknown"))
            slug_id = re.sub(r"[^a-z0-9-]", "", channel_name.lower().replace(" ", "-"))

            return YouTubeChannel(
                id=slug_id,
                channel_id=data.get("channel_id", ""),
                handle=handle,
                name=channel_name,
                description=data.get("description"),
                subscriber_count=data.get("channel_follower_count"),
            )

        except (json.JSONDecodeError, IndexError):
            return None
