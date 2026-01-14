#!/usr/bin/env python3
"""
Check podcast sync status by comparing Apple Podcasts database with local transcripts.

This script:
1. Reads the Apple Podcasts SQLite database to find all episodes
2. Compares against local transcripts in data/podcasts/raw/*/transcripts/
3. Reports which episodes are missing transcripts

Usage:
    python3 scripts/podcast/check_sync_status.py [--year 2025] [--podcast borspodden]
"""

import sqlite3
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict


# Apple Podcasts epoch: 2001-01-01
APPLE_EPOCH = datetime(2001, 1, 1)

# Apple Podcasts database location
APPLE_DB_PATH = Path.home() / 'Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Documents/MTLibrary.sqlite'

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
MAPPING_FILE = PROJECT_ROOT / 'data/podcast_mapping.json'
TRANSCRIPTS_DIR = PROJECT_ROOT / 'data/podcasts/raw'
ALT_TRANSCRIPTS_DIR = PROJECT_ROOT / 'data/transcripts'


def apple_timestamp_to_datetime(ts: float) -> datetime:
    """Convert Apple's timestamp (seconds since 2001-01-01) to datetime."""
    if ts is None:
        return None
    return APPLE_EPOCH + timedelta(seconds=ts)


def load_podcast_mapping() -> dict:
    """Load the podcast name to ID mapping."""
    if not MAPPING_FILE.exists():
        print(f"Warning: Mapping file not found at {MAPPING_FILE}")
        return {}

    with open(MAPPING_FILE) as f:
        data = json.load(f)
    return data.get('apple_to_id', {})


def get_apple_episodes(year_cutoff: int = 2025) -> dict:
    """
    Read episodes from Apple Podcasts database.

    Returns:
        dict: {apple_podcast_name: [{title, date, ...}, ...]}
    """
    if not APPLE_DB_PATH.exists():
        raise FileNotFoundError(f"Apple Podcasts database not found at {APPLE_DB_PATH}")

    conn = sqlite3.connect(str(APPLE_DB_PATH))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.ZTITLE as podcast_name,
            e.ZTITLE as episode_title,
            e.ZPUBDATE as pub_date
        FROM ZMTEPISODE e
        JOIN ZMTPODCAST p ON e.ZPODCAST = p.Z_PK
        WHERE e.ZPUBDATE IS NOT NULL
        ORDER BY e.ZPUBDATE DESC
    """)

    episodes_by_podcast = defaultdict(list)

    for podcast_name, episode_title, pub_date in cursor.fetchall():
        if not podcast_name or not pub_date:
            continue

        dt = apple_timestamp_to_datetime(pub_date)
        if dt and dt.year >= year_cutoff:
            episodes_by_podcast[podcast_name].append({
                'title': episode_title,
                'date': dt.strftime('%Y-%m-%d'),
                'datetime': dt
            })

    conn.close()
    return dict(episodes_by_podcast)


def get_local_transcripts() -> dict:
    """
    Find all local transcripts and extract their dates.

    Returns:
        dict: {podcast_id: set of dates as 'YYYY-MM-DD'}
    """
    transcripts_by_podcast = defaultdict(set)

    # Check both transcript locations
    for base_dir in [TRANSCRIPTS_DIR, ALT_TRANSCRIPTS_DIR]:
        if not base_dir.exists():
            continue

        for txt_file in base_dir.rglob('*.txt'):
            # Parse filename like: borspodden-2025-01-15-abc1.txt
            name = txt_file.stem
            parts = name.split('-')

            if len(parts) >= 4:
                podcast_id = parts[0]
                try:
                    # Extract date: parts[1]=year, parts[2]=month, parts[3]=day (first 2 chars)
                    date_str = f"{parts[1]}-{parts[2]}-{parts[3][:2]}"
                    # Validate it's a real date
                    datetime.strptime(date_str, '%Y-%m-%d')
                    transcripts_by_podcast[podcast_id].add(date_str)
                except (ValueError, IndexError):
                    pass

    return dict(transcripts_by_podcast)


def compare_and_report(apple_episodes: dict, local_transcripts: dict,
                       mapping: dict, filter_podcast: str = None) -> list:
    """
    Compare Apple episodes with local transcripts and report gaps.

    Returns:
        list: Missing episodes with details
    """
    missing = []

    for apple_name, episodes in sorted(apple_episodes.items()):
        podcast_id = mapping.get(apple_name)

        if not podcast_id:
            continue  # Not a tracked podcast

        if filter_podcast and podcast_id != filter_podcast:
            continue

        local_dates = local_transcripts.get(podcast_id, set())

        for ep in episodes:
            if ep['date'] not in local_dates:
                missing.append({
                    'podcast_name': apple_name,
                    'podcast_id': podcast_id,
                    'title': ep['title'],
                    'date': ep['date']
                })

    return missing


def print_report(apple_episodes: dict, local_transcripts: dict,
                 mapping: dict, missing: list, year_cutoff: int):
    """Print a formatted sync status report."""

    print("=" * 80)
    print(f"PODCAST SYNC STATUS ({year_cutoff}+)")
    print("=" * 80)
    print(f"{'Podcast':<35} {'I Apple':<10} {'Lokalt':<10} {'Saknas':<10}")
    print("-" * 80)

    # Group missing by podcast
    missing_by_podcast = defaultdict(list)
    for m in missing:
        missing_by_podcast[m['podcast_id']].append(m)

    total_in_apple = 0
    total_local = 0
    total_missing = 0

    for apple_name in sorted(apple_episodes.keys()):
        podcast_id = mapping.get(apple_name)
        if not podcast_id:
            continue

        apple_count = len(apple_episodes[apple_name])
        local_count = len([d for d in local_transcripts.get(podcast_id, set())
                          if d >= f'{year_cutoff}-01-01'])
        missing_count = len(missing_by_podcast.get(podcast_id, []))

        total_in_apple += apple_count
        total_local += local_count
        total_missing += missing_count

        status = "OK" if missing_count == 0 else f"{missing_count} saknas"
        print(f"{apple_name[:34]:<35} {apple_count:<10} {local_count:<10} {status:<10}")

    print("-" * 80)
    print(f"{'TOTALT':<35} {total_in_apple:<10} {total_local:<10} {total_missing:<10}")

    # Show missing episodes
    if missing:
        print("\n" + "=" * 80)
        print("AVSNITT SOM SAKNAS TRANSKRIPT")
        print("=" * 80)

        for podcast_id in sorted(missing_by_podcast.keys()):
            eps = missing_by_podcast[podcast_id]
            print(f"\n{podcast_id.upper()} ({len(eps)} saknas):")
            for ep in sorted(eps, key=lambda x: x['date'], reverse=True):
                title = ep['title'][:55] if ep['title'] else '(ingen titel)'
                print(f"  - {ep['date']}: {title}...")

    # Validation warnings
    print("\n" + "=" * 80)
    print("VALIDERING")
    print("=" * 80)

    # Check for podcasts not in Apple
    tracked_podcasts = set(mapping.values())
    podcasts_with_transcripts = set(local_transcripts.keys())
    not_in_apple = podcasts_with_transcripts - set(mapping.get(name) for name in apple_episodes.keys() if mapping.get(name))

    if not_in_apple:
        print(f"\nVarning: Dessa podcasts har transkript men finns inte i Apple Podcasts:")
        for pid in sorted(not_in_apple):
            print(f"  - {pid}")

    # Check for stale podcasts (no recent episodes in Apple)
    today = datetime.now()
    stale_threshold = (today - timedelta(days=30)).strftime('%Y-%m-%d')

    stale = []
    for apple_name, episodes in apple_episodes.items():
        podcast_id = mapping.get(apple_name)
        if podcast_id and episodes:
            latest = max(ep['date'] for ep in episodes)
            if latest < stale_threshold:
                stale.append((apple_name, podcast_id, latest))

    if stale:
        print(f"\nInfo: Dessa podcasts har inga nya avsnitt senaste 30 dagarna:")
        for apple_name, podcast_id, latest in sorted(stale, key=lambda x: x[2]):
            print(f"  - {podcast_id}: senast {latest}")

    if total_missing == 0:
        print("\nAllt synkat!")

    return total_missing


def main():
    current_year = datetime.now().year
    parser = argparse.ArgumentParser(description='Check podcast sync status')
    parser.add_argument('--year', type=int, default=current_year, help=f'Year cutoff (default: {current_year})')
    parser.add_argument('--podcast', type=str, help='Filter to specific podcast ID')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    # Load data
    mapping = load_podcast_mapping()
    if not mapping:
        print("Error: Could not load podcast mapping")
        return 1

    try:
        apple_episodes = get_apple_episodes(args.year)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nMake sure Apple Podcasts app is installed and has synced podcasts.")
        return 1

    local_transcripts = get_local_transcripts()

    # Compare
    missing = compare_and_report(apple_episodes, local_transcripts, mapping, args.podcast)

    if args.json:
        print(json.dumps(missing, indent=2, ensure_ascii=False))
    else:
        print_report(apple_episodes, local_transcripts, mapping, missing, args.year)

    return 0 if not missing else len(missing)


if __name__ == '__main__':
    exit(main())
