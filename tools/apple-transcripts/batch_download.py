#!/usr/bin/env python3
"""
Batch download Apple Podcast transcripts using FetchTranscript.

This script:
1. Reads episode IDs from Apple Podcasts database
2. Downloads TTML transcripts using the compiled FetchTranscript tool
3. Moves them to the TTML cache for processing by PodStock

Usage:
    python batch_download.py [--podcast "Börspodden"] [--limit 50] [--skip-existing]
"""

import argparse
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
FETCH_TRANSCRIPT = SCRIPT_DIR / "FetchTranscript"
APPLE_PODCASTS_CONTAINER = Path.home() / "Library/Group Containers/243LU875E5.groups.com.apple.podcasts"
SQLITE_DB = APPLE_PODCASTS_CONTAINER / "Documents/MTLibrary.sqlite"
TTML_CACHE = APPLE_PODCASTS_CONTAINER / "Library/Cache/Assets/TTML"


def get_episodes(podcast_name: str, limit: int = None) -> list[dict]:
    """Get episode info from Apple Podcasts database."""
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()

    query = """
        SELECT
            e.ZSTORETRACKID as episode_id,
            e.ZTITLE as title,
            e.ZTRANSCRIPTIDENTIFIER as transcript_path,
            e.ZPUBDATE as pub_date
        FROM ZMTEPISODE e
        JOIN ZMTPODCAST p ON e.ZPODCAST = p.Z_PK
        WHERE p.ZTITLE = ?
        AND e.ZSTORETRACKID IS NOT NULL
        AND e.ZTRANSCRIPTIDENTIFIER IS NOT NULL
        ORDER BY e.ZPUBDATE DESC
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query, (podcast_name,))

    episodes = []
    for row in cursor.fetchall():
        episodes.append({
            "episode_id": row[0],
            "title": row[1],
            "transcript_path": row[2],
            "pub_date": row[3],
        })

    conn.close()
    return episodes


def is_cached(transcript_path: str) -> bool:
    """Check if transcript is already in cache."""
    if not transcript_path:
        return False

    # Check both possible file naming conventions
    full_path = TTML_CACHE / transcript_path
    if full_path.exists():
        return True

    # Check with duplicated suffix (transcript_ID.ttml-ID.ttml)
    import re
    match = re.search(r'transcript_(\d+)\.ttml$', transcript_path)
    if match:
        ttml_id = match.group(1)
        alt_filename = f"transcript_{ttml_id}.ttml-{ttml_id}.ttml"
        alt_path = TTML_CACHE / transcript_path.replace(f"transcript_{ttml_id}.ttml", alt_filename)
        if alt_path.exists():
            return True

    return False


def download_transcript(episode_id: int, output_dir: Path) -> Path | None:
    """Download transcript using FetchTranscript tool."""
    result = subprocess.run(
        [str(FETCH_TRANSCRIPT), str(episode_id), "--cache-bearer-token"],
        cwd=output_dir,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"    Error: {result.stderr}")
        return None

    # Find the downloaded file
    expected_file = output_dir / f"transcript_{episode_id}.ttml"
    if expected_file.exists():
        return expected_file

    return None


def move_to_cache(ttml_file: Path, transcript_path: str) -> bool:
    """Move downloaded TTML to Apple Podcasts cache location."""
    if not transcript_path:
        return False

    # Create cache directory structure
    cache_path = TTML_CACHE / transcript_path
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Also create the alternative filename version
    import re
    match = re.search(r'transcript_(\d+)\.ttml$', transcript_path)
    if match:
        ttml_id = match.group(1)
        alt_filename = f"transcript_{ttml_id}.ttml-{ttml_id}.ttml"
        alt_cache_path = TTML_CACHE / transcript_path.replace(f"transcript_{ttml_id}.ttml", alt_filename)

        try:
            shutil.copy2(ttml_file, alt_cache_path)
            return True
        except Exception as e:
            print(f"    Failed to copy to cache: {e}")
            return False

    return False


def main():
    parser = argparse.ArgumentParser(description="Batch download Apple Podcast transcripts")
    parser.add_argument("--podcast", default="Börspodden", help="Podcast name")
    parser.add_argument("--limit", type=int, help="Max episodes to download")
    parser.add_argument("--skip-existing", action="store_true", help="Skip already cached transcripts")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between downloads (seconds)")
    parser.add_argument("--output-dir", type=Path, default=SCRIPT_DIR, help="Temp output directory")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    # Check FetchTranscript exists
    if not FETCH_TRANSCRIPT.exists():
        print(f"Error: FetchTranscript not found at {FETCH_TRANSCRIPT}")
        print("Compile it first with:")
        print("  clang -Wno-objc-method-access -framework Foundation -F/System/Library/PrivateFrameworks -framework AppleMediaServices FetchTranscript.m -o FetchTranscript")
        sys.exit(1)

    # Get episodes
    print(f"Getting episodes for '{args.podcast}'...")
    episodes = get_episodes(args.podcast, args.limit)
    print(f"Found {len(episodes)} episodes with transcripts")

    if not episodes:
        print("No episodes found!")
        sys.exit(1)

    # Filter already cached if requested
    if args.skip_existing:
        to_download = [e for e in episodes if not is_cached(e["transcript_path"])]
        print(f"Skipping {len(episodes) - len(to_download)} already cached")
    else:
        to_download = episodes

    print(f"\nWill download {len(to_download)} transcripts")
    print(f"Delay between downloads: {args.delay}s")
    print()

    if not to_download:
        print("Nothing to download!")
        return

    if not args.yes:
        input("Press Enter to start (Ctrl+C to cancel)...")

    downloaded = 0
    failed = 0

    for i, episode in enumerate(to_download, 1):
        print(f"\n[{i}/{len(to_download)}] {episode['title']}")
        print(f"    ID: {episode['episode_id']}")

        # Download
        ttml_file = download_transcript(episode["episode_id"], args.output_dir)

        if ttml_file:
            # Move to cache
            if move_to_cache(ttml_file, episode["transcript_path"]):
                print(f"    ✓ Downloaded and cached")
                downloaded += 1
                # Clean up temp file
                ttml_file.unlink()
            else:
                print(f"    ✗ Downloaded but failed to cache")
                failed += 1
        else:
            print(f"    ✗ Download failed")
            failed += 1

        if i < len(to_download):
            time.sleep(args.delay)

    print(f"\n{'='*50}")
    print(f"Downloaded: {downloaded}")
    print(f"Failed: {failed}")
    print(f"\nRun 'podstock transcribe --source apple' to extract transcripts")


if __name__ == "__main__":
    main()
