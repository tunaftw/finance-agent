#!/usr/bin/env python3
"""
Trigger Apple Podcasts to download transcripts via UI automation.

Opens each episode in Apple Podcasts and triggers transcript view to cache the TTML.
"""

import subprocess
import time
import sqlite3
import json
import re
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

COCOA_EPOCH = datetime(2001, 1, 1)
APPLE_PODCASTS_CONTAINER = Path.home() / "Library/Group Containers/243LU875E5.groups.com.apple.podcasts"
SQLITE_DB_PATH = APPLE_PODCASTS_CONTAINER / "Documents/MTLibrary.sqlite"
PROJECT_ROOT = Path(__file__).parent.parent
TRANSCRIPTS_DIR = PROJECT_ROOT / "data/transcripts"

def run_applescript(script: str) -> str:
    """Run AppleScript and return output."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def open_podcast_episode(episode_url: str):
    """Open an episode URL in Apple Podcasts."""
    # Use open command which handles podcasts: URLs
    subprocess.run(["open", episode_url], check=True)


def activate_podcasts():
    """Bring Podcasts app to foreground."""
    run_applescript('tell application "Podcasts" to activate')
    time.sleep(0.5)


def click_transcript_button():
    """Try to click the transcript button in the Now Playing view."""
    # The transcript button is typically in the player controls
    # We'll use keyboard shortcut if available, otherwise click coordinates
    script = '''
    tell application "System Events"
        tell process "Podcasts"
            -- Try to find and click the transcript button
            -- This may need adjustment based on macOS/app version
            set frontmost to true
            delay 0.3

            -- Try clicking the transcript icon in the mini player
            -- Coordinates may need calibration
            try
                click at {1700, 1000}
            end try
        end tell
    end tell
    '''
    try:
        run_applescript(script)
        return True
    except:
        return False


def get_missing_episodes():
    """Get episodes that need transcript download."""
    # Load podcast mapping
    mapping_path = PROJECT_ROOT / "data/podcast_mapping.json"
    with open(mapping_path) as f:
        mapping = json.load(f)
    apple_to_id = mapping.get("apple_to_id", {})

    # Load cached episode IDs
    cache_ids_file = Path("/tmp/cached_episode_ids.txt")
    if cache_ids_file.exists():
        with open(cache_ids_file) as f:
            cached_ids = set(line.strip() for line in f if line.strip())
    else:
        cached_ids = set()

    # Query database
    conn = sqlite3.connect(str(SQLITE_DB_PATH))
    cursor = conn.cursor()

    cutoff = (datetime(2026, 1, 1) - COCOA_EPOCH).total_seconds()
    cursor.execute("""
        SELECT
            e.ZTITLE,
            p.ZTITLE as podcast_name,
            e.ZPUBDATE,
            e.ZTRANSCRIPTIDENTIFIER,
            e.ZWEBPAGEURL,
            e.ZUUID
        FROM ZMTEPISODE e
        JOIN ZMTPODCAST p ON e.ZPODCAST = p.Z_PK
        WHERE e.ZTRANSCRIPTIDENTIFIER IS NOT NULL
        AND e.ZPUBDATE > ?
        ORDER BY e.ZPUBDATE DESC
    """, (cutoff,))

    missing = []
    for row in cursor.fetchall():
        title, podcast, pub_cocoa, transcript_id, web_url, uuid = row
        our_id = apple_to_id.get(podcast)
        if not our_id:
            continue

        pub_date = (COCOA_EPOCH + timedelta(seconds=pub_cocoa)).strftime("%Y-%m-%d")
        episode_id_str = f"{our_id}-{pub_date}-{hashlib.md5(title.encode()).hexdigest()[:4]}"

        # Check if we already have this transcript
        transcript_path = TRANSCRIPTS_DIR / our_id / f"{episode_id_str}.txt"
        if transcript_path.exists():
            continue

        # Extract apple episode ID from transcript identifier
        match = re.search(r'transcript_(\d+)\.ttml', transcript_id)
        if not match:
            continue
        apple_episode_id = match.group(1)

        # Check if already in cache
        if apple_episode_id in cached_ids:
            continue

        missing.append({
            "title": title,
            "podcast": our_id,
            "podcast_name": podcast,
            "date": pub_date,
            "apple_id": apple_episode_id,
            "web_url": web_url,
            "uuid": uuid,
        })

    conn.close()
    return missing


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Trigger Apple Podcasts to download transcripts")
    parser.add_argument("--dry-run", action="store_true", help="Just show what would be triggered")
    parser.add_argument("--delay", type=float, default=3.0, help="Delay between episodes (seconds)")
    args = parser.parse_args()

    print("=" * 60)
    print("Apple Podcasts Transcript Trigger")
    print("=" * 60)

    missing = get_missing_episodes()

    if not missing:
        print("\n✓ No missing transcripts to trigger!")
        return 0

    print(f"\nFound {len(missing)} episodes needing transcript download:\n")
    for ep in missing:
        print(f"  [{ep['podcast']}] {ep['title'][:45]}...")
        print(f"    URL: {ep['web_url']}")

    if args.dry_run:
        print("\n[DRY RUN - no actions taken]")
        return 0

    print("\n" + "=" * 60)
    print("Starting transcript trigger process...")
    print("This will open each episode in Apple Podcasts.")
    print("=" * 60)

    input("\nPress Enter to start (Ctrl+C to cancel)...")

    activate_podcasts()
    time.sleep(1)

    for i, ep in enumerate(missing):
        print(f"\n[{i+1}/{len(missing)}] {ep['podcast']}: {ep['title'][:40]}...")

        # Open the episode URL
        if ep['web_url']:
            # Convert web URL to podcasts:// URL if needed
            url = ep['web_url']
            if 'podcasters.spotify.com' in url or 'anchor.fm' in url:
                # These won't work, skip
                print(f"  ⚠ Spotify-hosted URL, skipping")
                continue

            print(f"  Opening: {url[:50]}...")
            open_podcast_episode(url)
            time.sleep(2)

            # Try to trigger transcript view
            # Note: This is imprecise - manual triggering is more reliable
            activate_podcasts()
            time.sleep(args.delay)
        else:
            print(f"  ⚠ No URL available")

    print("\n" + "=" * 60)
    print("Done! Please verify in Apple Podcasts that transcripts are loading.")
    print("Then run: python3 scripts/sync_from_apple_cache.py")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
