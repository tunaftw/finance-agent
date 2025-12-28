"""YouTube transcript collection module.

This module provides functionality for:
- Managing YouTube channels to collect from
- Extracting auto-generated transcripts via yt-dlp
- Storing transcripts in a structured format
- Tracking collection state

Usage:
    from podstock.youtube import YouTubeChannel, YouTubeExtractor

    extractor = YouTubeExtractor(data_dir=Path("data"))
    transcript = extractor.extract_transcript("dQw4w9WgXcQ")
"""

from podstock.youtube.models import (
    TranscriptSegment,
    VideoTranscript,
    YouTubeChannel,
    YouTubeChannelsFile,
    YouTubeCollectionState,
    YouTubeStateFile,
    YouTubeVideo,
)

__all__ = [
    "YouTubeChannel",
    "YouTubeVideo",
    "VideoTranscript",
    "TranscriptSegment",
    "YouTubeCollectionState",
    "YouTubeChannelsFile",
    "YouTubeStateFile",
]
