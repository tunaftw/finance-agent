#!/usr/bin/env python3
"""
Sync transcripts from Apple Podcasts local cache.

Uses locally cached TTML files instead of API - no bearer token needed!
"""

from typing import Optional, Dict, List, Set
import json
import re
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
APPLE_PODCASTS_CONTAINER = Path.home() / "Library/Group Containers/243LU875E5.groups.com.apple.podcasts"
SQLITE_DB_PATH = APPLE_PODCASTS_CONTAINER / "Documents/MTLibrary.sqlite"
TTML_CACHE_PATH = APPLE_PODCASTS_CONTAINER / "Library/Cache/Assets/TTML"
TRANSCRIPTS_DIR = PROJECT_ROOT / "data/transcripts"
PODCAST_MAPPING_PATH = PROJECT_ROOT / "data/podcast_mapping.json"

COCOA_EPOCH = datetime(2001, 1, 1)


def load_podcast_mapping() -> Dict:
    """Load podcast mapping."""
    if not PODCAST_MAPPING_PATH.exists():
        return {"apple_to_id": {}}
    with open(PODCAST_MAPPING_PATH) as f:
        return json.load(f)


def parse_ttml(ttml_path: Path) -> str:
    """Parse TTML and extract text."""
    raw = ttml_path.read_text(encoding="utf-8")
    words = re.findall(r'podcasts:unit="word"[^>]*>([^<]+)</span>', raw)
    return re.sub(r"\s+", " ", " ".join(w.strip() for w in words if w.strip()))


def get_cached_episode_ids() -> Set[str]:
    """Get all episode IDs available in local cache."""
    cached = set()
    if not TTML_CACHE_PATH.exists():
        return cached

    for ttml_file in TTML_CACHE_PATH.rglob("*.ttml"):
        # Extract episode ID from filename like transcript_1000747417747.ttml-1000747417747.ttml
        match = re.search(r'transcript_(\d+)\.ttml', ttml_file.name)
        if match:
            cached.add(match.group(1))

    return cached


def get_episode_info_from_db(year: int = 2025) -> List[Dict]:
    """Get episode info from Apple Podcasts SQLite database."""
    mapping = load_podcast_mapping()
    apple_to_id = mapping.get("apple_to_id", {})

    if not SQLITE_DB_PATH.exists():
        print(f"✗ SQLite database not found: {SQLITE_DB_PATH}")
        return []

    conn = sqlite3.connect(str(SQLITE_DB_PATH))
    cursor = conn.cursor()

    # Get cutoff date (start of year)
    cutoff = (datetime(year, 1, 1) - COCOA_EPOCH).total_seconds()

    cursor.execute("""
        SELECT
            e.ZTITLE as episode_title,
            p.ZTITLE as podcast_name,
            e.ZPUBDATE as pub_date,
            e.ZUUID as episode_uuid,
            e.ZWEBPAGEURL as web_url
        FROM ZMTEPISODE e
        JOIN ZMTPODCAST p ON e.ZPODCAST = p.Z_PK
        WHERE e.ZPUBDATE > ?
        ORDER BY e.ZPUBDATE DESC
    """, (cutoff,))

    episodes = []
    for row in cursor.fetchall():
        episode_title, podcast_name, pub_date_cocoa, episode_uuid, web_url = row

        # Get our podcast ID
        podcast_id = apple_to_id.get(podcast_name)
        if not podcast_id:
            continue

        pub_date = COCOA_EPOCH + timedelta(seconds=pub_date_cocoa)
        pub_date_str = pub_date.strftime("%Y-%m-%d")

        # Generate episode ID
        episode_id = f"{podcast_id}-{pub_date_str}-{hashlib.md5(episode_title.encode()).hexdigest()[:4]}"

        # Try to extract apple episode ID from web URL
        apple_episode_id = None
        if web_url:
            match = re.search(r'id(\d+)', web_url)
            if match:
                apple_episode_id = match.group(1)

        episodes.append({
            "podcast_id": podcast_id,
            "podcast_name": podcast_name,
            "episode_title": episode_title,
            "episode_id": episode_id,
            "pub_date": pub_date_str,
            "apple_episode_id": apple_episode_id,
            "episode_uuid": episode_uuid,
        })

    conn.close()
    return episodes


def find_ttml_file(apple_episode_id: str) -> Optional[Path]:
    """Find TTML file for an episode in the cache."""
    if not TTML_CACHE_PATH.exists():
        return None

    # Search for the file
    pattern = f"transcript_{apple_episode_id}.ttml*"
    for ttml_file in TTML_CACHE_PATH.rglob(pattern):
        if ttml_file.is_file():
            return ttml_file

    return None


def process_episode(episode: Dict) -> bool:
    """Process a single episode from cache."""
    apple_id = episode.get("apple_episode_id")
    if not apple_id:
        return False

    # Check if already have transcript
    transcript_path = TRANSCRIPTS_DIR / episode["podcast_id"] / f"{episode['episode_id']}.txt"
    if transcript_path.exists():
        return False  # Already exists

    # Find TTML in cache
    ttml_path = find_ttml_file(apple_id)
    if not ttml_path:
        return False

    # Parse TTML
    try:
        text = parse_ttml(ttml_path)
    except Exception as e:
        print(f"  ✗ Parse error for {episode['episode_id']}: {e}")
        return False

    if len(text.split()) < 100:
        print(f"  ✗ Too short ({len(text.split())} words): {episode['episode_id']}")
        return False

    # Save transcript
    transcript_path.parent.mkdir(parents=True, exist_ok=True)

    header = (
        f"{'='*60}\n"
        f"Episode: {episode['episode_id']}\n"
        f"Podcast: {episode['podcast_id']}\n"
        f"source: apple-cache\n"
        f"original_title: {episode['episode_title']}\n"
        f"pub_date: {episode['pub_date']}\n"
        f"{'='*60}\n\n"
    )
    transcript_path.write_text(header + text + "\n")

    print(f"  ✓ {episode['episode_id']}")
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sync transcripts from Apple Podcasts local cache")
    parser.add_argument("--year", type=int, default=2025, help="Year filter")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be synced")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    print("=" * 60)
    print("Apple Podcasts Local Cache Sync")
    print("=" * 60)

    # Get cached episode IDs
    print("\nScanning local cache...")
    cached_ids = get_cached_episode_ids()
    print(f"✓ Found {len(cached_ids)} TTML files in cache")

    # Get episodes from database
    print(f"\nQuerying Apple Podcasts database (year >= {args.year})...")
    episodes = get_episode_info_from_db(args.year)
    print(f"✓ Found {len(episodes)} episodes in tracked podcasts")

    # Find episodes that are in cache but not in our transcripts
    missing = []
    for ep in episodes:
        transcript_path = TRANSCRIPTS_DIR / ep["podcast_id"] / f"{ep['episode_id']}.txt"
        if transcript_path.exists():
            continue

        apple_id = ep.get("apple_episode_id")
        if apple_id and apple_id in cached_ids:
            missing.append(ep)

    print(f"\n✓ {len(missing)} episodes available in cache but missing locally")

    if not missing:
        print("\nAll cached transcripts already synced!")
        return 0

    # Show what we found
    print("\nMissing transcripts available in cache:")
    by_podcast = {}
    for ep in missing:
        pid = ep["podcast_id"]
        if pid not in by_podcast:
            by_podcast[pid] = []
        by_podcast[pid].append(ep)

    for pid, eps in sorted(by_podcast.items()):
        print(f"\n  {pid}: {len(eps)} episodes")
        if args.verbose:
            for ep in eps[:5]:
                print(f"    - {ep['episode_title'][:50]}... ({ep['pub_date']})")
            if len(eps) > 5:
                print(f"    ... and {len(eps) - 5} more")

    if args.dry_run:
        print("\n[DRY RUN - no changes made]")
        return 0

    # Process all missing episodes
    print("\n" + "=" * 60)
    print("Processing...")
    print("=" * 60)

    success = 0
    failed = 0

    for ep in missing:
        if process_episode(ep):
            success += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print(f"✓ Synced: {success}")
    if failed:
        print(f"✗ Failed/skipped: {failed}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
