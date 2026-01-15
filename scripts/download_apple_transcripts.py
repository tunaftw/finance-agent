#!/usr/bin/env python3
"""
Download Apple Podcasts transcripts using the FetchTranscript tool.

This script:
1. Queries the Apple Podcasts database for episodes with transcripts
2. Filters out episodes that are already cached locally
3. Downloads missing transcripts using the FetchTranscript tool
4. Converts them to our standard format

Requirements:
- macOS 15.5+ (uses Apple's private frameworks)
- FetchTranscript binary from: https://github.com/dado3212/apple-podcast-transcript-downloader

Usage:
    python scripts/download_apple_transcripts.py --podcast "Fill or Kill" --max 50
    python scripts/download_apple_transcripts.py --all --delay 1.0
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Apple Podcasts paths
APPLE_PODCASTS_CONTAINER = Path.home() / "Library/Group Containers/243LU875E5.groups.com.apple.podcasts"
SQLITE_DB_PATH = APPLE_PODCASTS_CONTAINER / "Documents/MTLibrary.sqlite"
TTML_CACHE_PATH = APPLE_PODCASTS_CONTAINER / "Library/Cache/Assets/TTML"

# Tool paths - relative to project root
# FetchTranscript binary from: https://github.com/dado3212/apple-podcast-transcript-downloader
# Compiled binary should be placed at tools/apple-transcripts/FetchTranscript
PROJECT_ROOT = Path(__file__).parent.parent
FETCH_TRANSCRIPT_PATH = PROJECT_ROOT / "tools/apple-transcripts/FetchTranscript"
DOWNLOAD_DIR = PROJECT_ROOT / "tools/apple-transcripts"

# Cocoa epoch for timestamp conversion
COCOA_EPOCH = datetime(2001, 1, 1)

# Podcast mapping file
PODCAST_MAPPING_PATH = PROJECT_ROOT / "data/podcast_mapping.json"


def load_podcast_mapping() -> dict:
    """Load podcast mapping from JSON file.

    Returns dict with:
      - apple_to_id: {Apple name -> our ID}
      - id_to_apple: {our ID -> Apple name}
    """
    if not PODCAST_MAPPING_PATH.exists():
        return {"apple_to_id": {}, "id_to_apple": {}}

    with open(PODCAST_MAPPING_PATH) as f:
        data = json.load(f)

    apple_to_id = data.get("apple_to_id", {})
    # Create reverse mapping
    id_to_apple = {v: k for k, v in apple_to_id.items()}

    return {"apple_to_id": apple_to_id, "id_to_apple": id_to_apple}


def resolve_podcast_filter(podcast_input: str) -> str:
    """Resolve podcast input to Apple name for DB query.

    Accepts either:
      - Our podcast ID (e.g., 'marketmakers') -> returns 'Market Makers'
      - Apple name (e.g., 'Market Makers') -> returns as-is
    """
    mapping = load_podcast_mapping()
    id_to_apple = mapping["id_to_apple"]

    # Check if input is one of our IDs
    if podcast_input.lower() in id_to_apple:
        return id_to_apple[podcast_input.lower()]

    # Check if input matches an ID (case-insensitive)
    for our_id, apple_name in id_to_apple.items():
        if podcast_input.lower() == our_id.lower():
            return apple_name

    # Assume it's already an Apple name
    return podcast_input


def check_requirements():
    """Check that required tools are available."""
    if not FETCH_TRANSCRIPT_PATH.exists():
        print("❌ FetchTranscript tool not found!")
        print("   Clone and build from: https://github.com/dado3212/apple-podcast-transcript-downloader")
        print("   Or run: cd /tmp && git clone https://github.com/dado3212/apple-podcast-transcript-downloader")
        return False

    if not SQLITE_DB_PATH.exists():
        print("❌ Apple Podcasts database not found!")
        print("   Make sure Apple Podcasts is installed and has been opened at least once.")
        return False

    return True


def get_cached_transcript_ids() -> set:
    """Get set of transcript IDs that are already cached locally."""
    cached = set()
    if not TTML_CACHE_PATH.exists():
        return cached

    for ttml_file in TTML_CACHE_PATH.rglob("*.ttml"):
        # Extract transcript ID from filename like transcript_1000741696914.ttml-1000741696914.ttml
        match = re.search(r'transcript_(\d+)\.ttml', ttml_file.name)
        if match:
            cached.add(match.group(1))

    return cached


def get_episodes_with_transcripts(podcast_filter: str = None) -> list:
    """Get episodes that have transcripts available in Apple Podcasts database."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    query = """
        SELECT
            e.ZTITLE as episode_title,
            p.ZTITLE as podcast_name,
            e.ZPUBDATE as pub_date,
            e.ZTRANSCRIPTIDENTIFIER as transcript_id,
            e.ZUUID as episode_uuid
        FROM ZMTEPISODE e
        JOIN ZMTPODCAST p ON e.ZPODCAST = p.Z_PK
        WHERE e.ZTRANSCRIPTIDENTIFIER IS NOT NULL
    """

    if podcast_filter:
        query += f" AND p.ZTITLE LIKE '%{podcast_filter}%'"

    query += " ORDER BY e.ZPUBDATE DESC"

    cursor.execute(query)
    episodes = []

    for row in cursor.fetchall():
        episode_title, podcast_name, pub_date_cocoa, transcript_id, episode_uuid = row

        # Convert Cocoa timestamp
        pub_date = COCOA_EPOCH + timedelta(seconds=pub_date_cocoa) if pub_date_cocoa else datetime.now()

        # Extract Apple episode ID from transcript identifier
        # Format: PodcastContent211/v4/.../transcript_1000741696914.ttml
        match = re.search(r'transcript_(\d+)\.ttml', transcript_id)
        if not match:
            continue

        apple_episode_id = match.group(1)

        episodes.append({
            'episode_title': episode_title,
            'podcast_name': podcast_name,
            'pub_date': pub_date,
            'transcript_id': transcript_id,
            'apple_episode_id': apple_episode_id,
            'episode_uuid': episode_uuid,
        })

    conn.close()
    return episodes


def download_transcript(apple_episode_id: str, cache_token: bool = True) -> Path | None:
    """Download a transcript using the FetchTranscript tool."""
    args = [str(FETCH_TRANSCRIPT_PATH), apple_episode_id]
    if cache_token:
        args.append("--cache-bearer-token")

    try:
        result = subprocess.run(
            args,
            cwd=DOWNLOAD_DIR,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Check if file was created
        ttml_path = DOWNLOAD_DIR / f"transcript_{apple_episode_id}.ttml"
        if ttml_path.exists():
            return ttml_path

        if result.stderr:
            print(f"   ⚠️  stderr: {result.stderr[:200]}")

        return None

    except subprocess.TimeoutExpired:
        print(f"   ⚠️  Timeout downloading {apple_episode_id}")
        return None
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
        return None


def move_to_cache(ttml_path: Path, transcript_id: str) -> bool:
    """Move downloaded TTML to Apple Podcasts cache for native integration."""
    # Parse the transcript_id to get the cache path
    # Format: PodcastContent211/v4/xx/xx/xx/uuid/transcript_xxx.ttml

    cache_path = TTML_CACHE_PATH / transcript_id

    # Create parent directories
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Apple uses a duplicated filename format
    # transcript_xxx.ttml -> transcript_xxx.ttml-xxx.ttml
    match = re.search(r'transcript_(\d+)\.ttml', ttml_path.name)
    if match:
        ttml_id = match.group(1)
        final_filename = f"transcript_{ttml_id}.ttml-{ttml_id}.ttml"
        final_path = cache_path.parent / final_filename
    else:
        final_path = cache_path

    try:
        shutil.copy2(ttml_path, final_path)
        return True
    except Exception as e:
        print(f"   ⚠️  Failed to copy to cache: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download Apple Podcasts transcripts")
    parser.add_argument("--podcast", "-p", help="Filter by podcast (our ID like 'marketmakers' or Apple name like 'Market Makers')")
    parser.add_argument("--max", "-m", type=int, default=0, help="Maximum number to download (0 = unlimited)")
    parser.add_argument("--delay", "-d", type=float, default=0.5, help="Delay between downloads in seconds")
    parser.add_argument("--all", "-a", action="store_true", help="Download for all podcasts")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded without downloading")
    parser.add_argument("--no-cache-move", action="store_true", help="Don't move downloaded files to Apple cache")

    args = parser.parse_args()

    if not check_requirements():
        sys.exit(1)

    print("🎙️  Apple Podcasts Transcript Downloader")
    print("=" * 50)

    # Get already cached transcripts
    cached_ids = get_cached_transcript_ids()
    print(f"📦 Already cached: {len(cached_ids)} transcripts")

    # Get episodes with transcripts
    # Resolve our podcast ID to Apple name if needed
    podcast_filter = None
    if args.podcast and not args.all:
        podcast_filter = resolve_podcast_filter(args.podcast)
        if podcast_filter != args.podcast:
            print(f"🔄 Resolved '{args.podcast}' → '{podcast_filter}'")
    episodes = get_episodes_with_transcripts(podcast_filter)
    print(f"📚 Total episodes with transcripts: {len(episodes)}")

    # Filter to only missing ones
    missing = [e for e in episodes if e['apple_episode_id'] not in cached_ids]
    print(f"📥 Missing (need to download): {len(missing)}")

    if not missing:
        print("\n✅ All transcripts are already cached!")
        return

    # Apply max limit
    if args.max > 0:
        missing = missing[:args.max]
        print(f"📊 Will download: {len(missing)} (limited by --max)")

    if args.dry_run:
        print("\n🔍 Dry run - would download:")
        for ep in missing[:20]:
            print(f"   • [{ep['pub_date'].strftime('%Y-%m-%d')}] {ep['podcast_name']}: {ep['episode_title'][:50]}...")
        if len(missing) > 20:
            print(f"   ... and {len(missing) - 20} more")
        return

    # Download loop
    print(f"\n🚀 Starting download of {len(missing)} transcripts...")
    print("   (Using --cache-bearer-token for faster batch processing)\n")

    success_count = 0
    fail_count = 0

    for i, ep in enumerate(missing, 1):
        print(f"[{i}/{len(missing)}] {ep['episode_title'][:60]}...")

        ttml_path = download_transcript(ep['apple_episode_id'])

        if ttml_path:
            if not args.no_cache_move:
                if move_to_cache(ttml_path, ep['transcript_id']):
                    print(f"   ✅ Downloaded and cached")
                    success_count += 1
                else:
                    print(f"   ⚠️  Downloaded but cache copy failed")
                    success_count += 1  # Still count as success

                # Clean up download dir copy
                ttml_path.unlink(missing_ok=True)
            else:
                print(f"   ✅ Downloaded to {ttml_path}")
                success_count += 1
        else:
            print(f"   ❌ Failed")
            fail_count += 1

        if i < len(missing) and args.delay > 0:
            time.sleep(args.delay)

    print("\n" + "=" * 50)
    print(f"📊 Results: {success_count} succeeded, {fail_count} failed")

    if success_count > 0:
        print("\n💡 Run 'podstock transcribe --source apple' to extract the new transcripts")


if __name__ == "__main__":
    main()
