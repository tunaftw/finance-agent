"""Apple Podcast transcript extraction for PodStock.

This module handles extraction of transcripts from Apple Podcasts app cache.
TTML files are cached when users view transcripts in the Apple Podcasts app.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from podstock.core.exceptions import TranscribeError
from podstock.core.models import Podcast

# Apple Podcasts data locations
APPLE_PODCASTS_CONTAINER = Path.home() / "Library/Group Containers/243LU875E5.groups.com.apple.podcasts"
TTML_CACHE_PATH = APPLE_PODCASTS_CONTAINER / "Library/Cache/Assets/TTML"
SQLITE_DB_PATH = APPLE_PODCASTS_CONTAINER / "Documents/MTLibrary.sqlite"

# Apple's Cocoa timestamp epoch (2001-01-01 00:00:00 UTC)
COCOA_EPOCH = datetime(2001, 1, 1)


@dataclass
class AppleTranscript:
    """Represents an available Apple Podcast transcript."""

    episode_title: str
    podcast_name: str
    pub_date: datetime
    transcript_id: str
    ttml_path: Path | None  # None if not cached locally
    is_cached: bool


def find_ttml_cache() -> Path | None:
    """Find the Apple Podcasts TTML cache directory.

    Returns:
        Path to TTML cache if it exists, None otherwise.
    """
    if TTML_CACHE_PATH.exists():
        return TTML_CACHE_PATH
    return None


def find_database() -> Path | None:
    """Find the Apple Podcasts SQLite database.

    Returns:
        Path to database if it exists, None otherwise.
    """
    if SQLITE_DB_PATH.exists():
        return SQLITE_DB_PATH
    return None


def _cocoa_to_datetime(cocoa_timestamp: float) -> datetime:
    """Convert Apple Cocoa timestamp to Python datetime."""
    return COCOA_EPOCH + timedelta(seconds=cocoa_timestamp)


def _normalize_podcast_name(name: str) -> str:
    """Normalize podcast name for matching.

    Converts to lowercase, removes special characters, and normalizes whitespace.
    """
    # Convert Swedish characters
    name = name.lower()
    name = name.replace("ö", "o").replace("ä", "a").replace("å", "a")
    # Remove special characters and normalize whitespace
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", "", name)
    return name


def _generate_episode_id(podcast_id: str, pub_date: datetime, episode_title: str) -> str:
    """Generate a PodStock episode ID from Apple metadata.

    Format: {podcast_id}-{YYYY-MM-DD}-{4char-hash}
    """
    date_str = pub_date.strftime("%Y-%m-%d")
    # Create a short hash from the title for uniqueness
    title_hash = hashlib.md5(episode_title.encode()).hexdigest()[:4]
    return f"{podcast_id}-{date_str}-{title_hash}"


def list_available_transcripts(
    podcasts: list[Podcast] | None = None,
) -> list[AppleTranscript]:
    """List all available Apple Podcast transcripts.

    Args:
        podcasts: Optional list of configured podcasts to filter by.
                  If None, returns all transcripts.

    Returns:
        List of AppleTranscript objects.

    Raises:
        TranscribeError: If database cannot be read.
    """
    db_path = find_database()
    if not db_path:
        raise TranscribeError(
            "Apple Podcasts database not found. "
            "Is Apple Podcasts installed?"
        )

    ttml_cache = find_ttml_cache()
    transcripts = []

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                e.ZTITLE,
                p.ZTITLE,
                e.ZPUBDATE,
                e.ZTRANSCRIPTIDENTIFIER
            FROM ZMTEPISODE e
            JOIN ZMTPODCAST p ON e.ZPODCAST = p.Z_PK
            WHERE e.ZTRANSCRIPTIDENTIFIER IS NOT NULL
            ORDER BY e.ZPUBDATE DESC
        """)

        for row in cursor.fetchall():
            episode_title, podcast_name, pub_date_cocoa, transcript_id = row

            # Convert Cocoa timestamp to datetime
            pub_date = _cocoa_to_datetime(pub_date_cocoa) if pub_date_cocoa else datetime.now()

            # Check if TTML is cached locally
            # Apple caches files with a modified name: transcript_ID.ttml-ID.ttml
            ttml_path = None
            is_cached = False
            if ttml_cache and transcript_id:
                # Try exact path first
                potential_path = ttml_cache / transcript_id
                if potential_path.exists():
                    ttml_path = potential_path
                    is_cached = True
                else:
                    # Try with duplicated suffix (e.g., transcript_123.ttml-123.ttml)
                    # Extract the ID from the transcript_id
                    match = re.search(r'transcript_(\d+)\.ttml$', transcript_id)
                    if match:
                        ttml_id = match.group(1)
                        alt_filename = f"transcript_{ttml_id}.ttml-{ttml_id}.ttml"
                        alt_path = ttml_cache / transcript_id.replace(f"transcript_{ttml_id}.ttml", alt_filename)
                        if alt_path.exists():
                            ttml_path = alt_path
                            is_cached = True

            # Filter by configured podcasts if provided
            if podcasts:
                normalized_apple = _normalize_podcast_name(podcast_name)
                matched = False
                for podcast in podcasts:
                    normalized_config = _normalize_podcast_name(podcast.name)
                    if normalized_apple == normalized_config or normalized_apple in normalized_config or normalized_config in normalized_apple:
                        matched = True
                        break
                if not matched:
                    continue

            transcripts.append(AppleTranscript(
                episode_title=episode_title,
                podcast_name=podcast_name,
                pub_date=pub_date,
                transcript_id=transcript_id,
                ttml_path=ttml_path,
                is_cached=is_cached,
            ))

        conn.close()

    except sqlite3.Error as e:
        raise TranscribeError(f"Failed to read Apple Podcasts database: {e}") from e

    return transcripts


def match_to_podcast(podcast_name: str, podcasts: list[Podcast]) -> Podcast | None:
    """Match an Apple podcast name to a configured PodStock podcast.

    Args:
        podcast_name: Name from Apple Podcasts.
        podcasts: List of configured podcasts.

    Returns:
        Matching Podcast or None if no match found.
    """
    normalized_apple = _normalize_podcast_name(podcast_name)

    for podcast in podcasts:
        normalized_config = _normalize_podcast_name(podcast.name)
        # Check for exact match or substring match
        if normalized_apple == normalized_config:
            return podcast
        if normalized_apple in normalized_config or normalized_config in normalized_apple:
            return podcast

    return None


def _format_timestamp(ttml_time: str) -> str:
    """Format TTML timestamp to [HH:MM:SS] or [MM:SS] format.

    TTML uses formats like:
    - "00:01:23.456" (hours:minutes:seconds.milliseconds)
    - "83.456s" (seconds with 's' suffix)
    """
    if not ttml_time:
        return ""

    try:
        # Handle "seconds.ms" format with 's' suffix
        if ttml_time.endswith("s"):
            total_seconds = float(ttml_time[:-1])
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
        else:
            # Handle "HH:MM:SS.mmm" format
            parts = ttml_time.split(":")
            if len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = int(float(parts[2]))
            elif len(parts) == 2:
                hours = 0
                minutes = int(parts[0])
                seconds = int(float(parts[1]))
            else:
                return ""

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    except (ValueError, IndexError):
        return ""


def parse_ttml(ttml_path: Path, *, with_timestamps: bool = True) -> str:
    """Parse TTML file and extract transcript text.

    Apple Podcasts TTML structure:
    - <p> elements contain paragraphs with speaker info and timestamps
    - <span podcasts:unit="sentence"> contain sentences
    - <span podcasts:unit="word"> contain individual words

    Args:
        ttml_path: Path to TTML file.
        with_timestamps: Include timestamps in output.

    Returns:
        Extracted transcript text.

    Raises:
        TranscribeError: If parsing fails.
    """
    if not ttml_path.exists():
        raise TranscribeError(f"TTML file not found: {ttml_path}")

    try:
        tree = ET.parse(ttml_path)
        root = tree.getroot()

        # Define namespaces
        ns = {
            "tt": "http://www.w3.org/ns/ttml",
            "podcasts": "http://podcasts.apple.com/transcript-ttml-internal",
        }

        # Find all paragraph elements
        paragraphs = root.findall(".//{http://www.w3.org/ns/ttml}p")

        if not paragraphs:
            # Try without namespace
            paragraphs = root.findall(".//p")

        lines = []
        last_timestamp = ""

        for p in paragraphs:
            # Get paragraph timestamp
            begin = p.get("begin", "")

            # Extract words with spaces between them
            words = []
            for span in p.iter():
                # Look for word-level spans
                unit = span.get("{http://podcasts.apple.com/transcript-ttml-internal}unit", "")
                if unit == "word" and span.text:
                    words.append(span.text.strip())

            # If no word units found, try sentence units or direct text
            if not words:
                for span in p.iter():
                    unit = span.get("{http://podcasts.apple.com/transcript-ttml-internal}unit", "")
                    if unit == "sentence" and span.text:
                        words.append(span.text.strip())

            # Final fallback: get all text
            if not words:
                text = "".join(p.itertext()).strip()
                if text:
                    words = [text]

            if not words:
                continue

            # Join words with spaces
            text = " ".join(w for w in words if w)

            if not text:
                continue

            if with_timestamps and begin:
                timestamp = _format_timestamp(begin)
                # Only add timestamp if it changed significantly (avoid repetitive timestamps)
                if timestamp and timestamp != last_timestamp:
                    lines.append(f"[{timestamp}] {text}")
                    last_timestamp = timestamp
                else:
                    lines.append(text)
            else:
                lines.append(text)

        if not lines:
            raise TranscribeError("No text content found in TTML file")

        return "\n".join(lines)

    except ET.ParseError as e:
        raise TranscribeError(f"Failed to parse TTML XML: {e}") from e
    except Exception as e:
        raise TranscribeError(f"Error processing TTML: {e}") from e


def extract_and_save(
    transcript: AppleTranscript,
    transcript_dir: Path,
    podcast: Podcast,
    *,
    with_timestamps: bool = True,
) -> tuple[Path, str]:
    """Extract transcript from Apple cache and save in PodStock format.

    Args:
        transcript: AppleTranscript object with metadata.
        transcript_dir: Base directory for transcripts.
        podcast: Matched PodStock podcast.
        with_timestamps: Include timestamps in output.

    Returns:
        Tuple of (transcript_path, episode_id).

    Raises:
        TranscribeError: If extraction or save fails.
    """
    if not transcript.is_cached or not transcript.ttml_path:
        raise TranscribeError(
            f"Transcript not cached locally: {transcript.episode_title}\n"
            "View this episode's transcript in Apple Podcasts to cache it."
        )

    # Parse TTML content
    text = parse_ttml(transcript.ttml_path, with_timestamps=with_timestamps)

    # Generate episode ID
    episode_id = _generate_episode_id(podcast.id, transcript.pub_date, transcript.episode_title)

    # Create podcast subdirectory
    podcast_dir = transcript_dir / podcast.id
    podcast_dir.mkdir(parents=True, exist_ok=True)

    transcript_path = podcast_dir / f"{episode_id}.txt"

    # Build header (same format as whisper.py)
    header_lines = [
        "=" * 60,
        f"Episode: {episode_id}",
        f"Podcast: {podcast.id}",
        f"source: apple",
        f"original_title: {transcript.episode_title}",
        f"pub_date: {transcript.pub_date.strftime('%Y-%m-%d')}",
        f"has_timestamps: {with_timestamps}",
        "=" * 60,
        "",
    ]
    header = "\n".join(header_lines)

    # Write atomically
    temp_path = transcript_path.with_suffix(".tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(header)
            f.write(text)
            f.write("\n")

        temp_path.replace(transcript_path)
    except OSError as e:
        if temp_path.exists():
            temp_path.unlink()
        raise TranscribeError(f"Failed to save transcript: {e}") from e

    return transcript_path, episode_id


def get_cached_transcripts_for_podcast(
    podcast: Podcast,
) -> list[AppleTranscript]:
    """Get all cached transcripts for a specific podcast.

    Args:
        podcast: PodStock podcast to find transcripts for.

    Returns:
        List of cached AppleTranscript objects.
    """
    all_transcripts = list_available_transcripts(podcasts=[podcast])
    return [t for t in all_transcripts if t.is_cached]


def get_transcript_stats() -> dict:
    """Get statistics about available Apple transcripts.

    Returns:
        Dictionary with stats like total_in_database, total_cached, by_podcast.
    """
    try:
        all_transcripts = list_available_transcripts()
    except TranscribeError:
        return {"error": "Could not read Apple Podcasts database"}

    stats = {
        "total_in_database": len(all_transcripts),
        "total_cached": sum(1 for t in all_transcripts if t.is_cached),
        "by_podcast": {},
    }

    for t in all_transcripts:
        if t.podcast_name not in stats["by_podcast"]:
            stats["by_podcast"][t.podcast_name] = {"total": 0, "cached": 0}
        stats["by_podcast"][t.podcast_name]["total"] += 1
        if t.is_cached:
            stats["by_podcast"][t.podcast_name]["cached"] += 1

    return stats
