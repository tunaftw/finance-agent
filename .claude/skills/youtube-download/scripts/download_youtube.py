#!/usr/bin/env python3
"""Download YouTube video transcript with descriptive filename.

Usage:
    python download_youtube.py "https://www.youtube.com/watch?v=VIDEO_ID"
    python download_youtube.py VIDEO_ID

Saves transcript to: data/youtube/raw/{channel-slug}/{Channel} - {Title} - {Date}.txt
"""

import re
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from podstock.youtube.extractor import YouTubeExtractor
from podstock.youtube.models import extract_video_id


def sanitize_filename(name: str, max_length: int = 100) -> str:
    """Sanitize a string for use in filename.

    Args:
        name: String to sanitize.
        max_length: Maximum length of the result.

    Returns:
        Sanitized string safe for filenames.
    """
    # Remove invalid filename characters
    invalid_chars = r'<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, "")

    # Replace multiple spaces/whitespace with single space
    name = re.sub(r"\s+", " ", name)

    # Trim whitespace
    name = name.strip()

    # Truncate if too long
    if len(name) > max_length:
        name = name[:max_length].rsplit(" ", 1)[0]  # Don't cut mid-word

    return name


def create_channel_slug(channel_name: str) -> str:
    """Create a slug from channel name.

    Args:
        channel_name: Channel display name.

    Returns:
        Lowercase slug with hyphens.
    """
    # Lowercase and replace spaces with hyphens
    slug = channel_name.lower().replace(" ", "-")

    # Remove non-alphanumeric (except hyphens)
    slug = re.sub(r"[^a-z0-9-]", "", slug)

    # Collapse multiple hyphens
    slug = re.sub(r"-+", "-", slug)

    return slug.strip("-")


def download_youtube_transcript(url_or_id: str, data_dir: Path) -> dict:
    """Download transcript from YouTube video.

    Args:
        url_or_id: YouTube URL or video ID.
        data_dir: Base data directory.

    Returns:
        Dictionary with download results.

    Raises:
        ValueError: If video ID cannot be extracted.
        Exception: If download fails.
    """
    # Extract video ID
    video_id = extract_video_id(url_or_id)
    if not video_id:
        raise ValueError(f"Could not extract video ID from: {url_or_id}")

    # Initialize extractor
    extractor = YouTubeExtractor(data_dir=data_dir)

    # Get video info
    print(f"Fetching video info for {video_id}...")
    video = extractor.get_video_info(video_id)
    if not video:
        raise ValueError(f"Could not fetch video info for: {video_id}")

    # Get channel name from yt-dlp output
    # The extractor returns youtube_channel_id but we need channel name
    # Re-fetch with more details
    import json
    import subprocess

    result = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-download", f"https://www.youtube.com/watch?v={video_id}"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    video_data = json.loads(result.stdout)
    channel_name = video_data.get("channel", video_data.get("uploader", "Unknown Channel"))
    title = video_data.get("title", "Unknown Title")
    upload_date = video_data.get("upload_date", "")

    # Parse upload date
    if upload_date and len(upload_date) == 8:
        date_str = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"Channel: {channel_name}")
    print(f"Title: {title}")
    print(f"Date: {date_str}")

    # Extract transcript
    print("Extracting transcript...")
    channel_slug = create_channel_slug(channel_name)
    transcript = extractor.extract_transcript(video_id, channel_id=channel_slug)

    # Create filename: {Channel} - {Title} - {Date}.txt
    safe_channel = sanitize_filename(channel_name, max_length=50)
    safe_title = sanitize_filename(title, max_length=100)
    filename = f"{safe_channel} - {safe_title} - {date_str}.txt"

    # Create output directory
    output_dir = data_dir / "youtube" / "raw" / channel_slug
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build header
    header_lines = [
        "=" * 60,
        f"Video: {video_id}",
        f"Channel: {channel_name}",
        f"Title: {title}",
        f"Date: {date_str}",
        f"source: youtube-{transcript.transcript_type}",
        f"language: {transcript.language}",
        f"word_count: {transcript.word_count}",
        f"extracted_at: {transcript.extracted_at.isoformat()}",
        "=" * 60,
    ]
    header = "\n".join(header_lines)

    # Save transcript
    output_path = output_dir / filename
    output_path.write_text(f"{header}\n\n{transcript.text}", encoding="utf-8")

    # Also save JSON with timestamps if available
    if transcript.segments:
        json_path = output_dir / f"{video_id}.json"
        json_path.write_text(transcript.model_dump_json(indent=2), encoding="utf-8")

    return {
        "video_id": video_id,
        "channel": channel_name,
        "channel_slug": channel_slug,
        "title": title,
        "date": date_str,
        "word_count": transcript.word_count,
        "language": transcript.language,
        "transcript_type": transcript.transcript_type,
        "output_path": str(output_path),
        "relative_path": str(output_path.relative_to(PROJECT_ROOT)),
    }


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python download_youtube.py <youtube_url_or_id>")
        print("Example: python download_youtube.py https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        sys.exit(1)

    url_or_id = sys.argv[1]
    data_dir = PROJECT_ROOT / "data"

    try:
        result = download_youtube_transcript(url_or_id, data_dir)

        print()
        print("=" * 60)
        print("Download complete!")
        print("=" * 60)
        print(f"Channel: {result['channel']}")
        print(f"Title: {result['title']}")
        print(f"Date: {result['date']}")
        print(f"Words: {result['word_count']:,}")
        print(f"Language: {result['language']}")
        print(f"Type: {result['transcript_type']}")
        print(f"Saved to: {result['relative_path']}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
