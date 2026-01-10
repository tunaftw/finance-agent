#!/usr/bin/env python3
"""Sync missing podcast episodes using Whisper transcription."""
from __future__ import annotations

import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from podstock.rss.parser import get_all_episodes
from podstock.rss.downloader import download_episode
from podstock.transcribe.whisper import transcribe, save_transcript

# Apple Podcasts database for RSS URLs
DB_PATH = Path.home() / "Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Documents/MTLibrary.sqlite"
COCOA_EPOCH = datetime(2001, 1, 1)

# Episodes to sync (podcast_id, date, partial_title)
EPISODES_TO_SYNC = [
    ('globalgains', '2025-01-17', 'Gyllenram'),
    ('globalgains', '2025-01-15', 'Bottenfisken'),
    ('globalgains', '2025-01-07', 'Aktierna vi tror'),
    ('gotttjot', '2026-01-06', 'Portföljen för 2026'),
    ('kvalitetforpengarna', '2025-10-30', 'Midsommarportföljen'),
    ('montrosepodden', '2025-12-30', 'Revolution'),
    ('smaspararpodden', '2025-06-20', 'God sed'),
    ('veckanstrade', '2025-06-04', 'Kendall Roy'),
    ('veckanstrade', '2025-05-28', 'Välkommen'),
    ('borsensfinest', '2025-06-04', 'Biotech'),
]

# Podcast ID to Apple name mapping
ID_TO_APPLE = {
    'globalgains': 'Global Gains',
    'gotttjot': 'Gött Tjöt',
    'kvalitetforpengarna': 'Kvalitet För Pengarna',
    'montrosepodden': 'Montrosepodden',
    'smaspararpodden': 'Småspararpodden',
    'veckanstrade': 'Veckans Trade',
    'borsensfinest': 'Börsens Finest',
}


def get_rss_url(podcast_id: str) -> str | None:
    """Get RSS URL from Apple Podcasts database."""
    apple_name = ID_TO_APPLE.get(podcast_id)
    if not apple_name:
        return None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT ZFEEDURL FROM ZMTPODCAST WHERE ZTITLE LIKE ?",
        (f"%{apple_name.split()[0]}%",)
    )
    row = cursor.fetchone()
    conn.close()

    return row[0] if row else None


def find_episode_in_rss(rss_url: str, podcast_id: str, target_date: str, title_hint: str):
    """Find a specific episode in RSS feed."""
    target = datetime.strptime(target_date, '%Y-%m-%d')

    episodes = get_all_episodes(rss_url, podcast_id)

    # Find episode matching date and title
    for ep in episodes:
        date_match = abs((ep.published_at.date() - target.date()).days) <= 2
        title_match = title_hint.lower() in ep.title.lower()

        if date_match and title_match:
            return ep
        elif date_match:
            # Close match on date, check title more loosely
            if any(word.lower() in ep.title.lower() for word in title_hint.split()):
                return ep

    # Fallback: just match date
    for ep in episodes:
        if abs((ep.published_at.date() - target.date()).days) <= 1:
            return ep

    return None


def main():
    print("=" * 70)
    print("WHISPER SYNC - 10 MISSING EPISODES")
    print("=" * 70)

    audio_dir = Path('data/audio')
    transcript_dir = Path('data/transcripts')

    results = {'success': [], 'failed': []}

    for i, (podcast_id, date_str, title_hint) in enumerate(EPISODES_TO_SYNC, 1):
        print(f"\n[{i}/10] {podcast_id} | {date_str} | {title_hint}")
        print("-" * 60)

        # Get RSS URL
        rss_url = get_rss_url(podcast_id)
        if not rss_url:
            print(f"  ERROR: No RSS URL found")
            results['failed'].append((podcast_id, date_str, "No RSS URL"))
            continue

        print(f"  RSS: {rss_url[:50]}...")

        # Find episode in RSS
        try:
            episode = find_episode_in_rss(rss_url, podcast_id, date_str, title_hint)
        except Exception as e:
            print(f"  ERROR fetching RSS: {e}")
            results['failed'].append((podcast_id, date_str, str(e)))
            continue

        if not episode:
            print(f"  ERROR: Episode not found in RSS")
            results['failed'].append((podcast_id, date_str, "Not in RSS"))
            continue

        print(f"  Found: {episode.title[:50]}...")
        print(f"  Audio: {str(episode.audio_url)[:60]}...")

        # Check if transcript already exists
        existing = list(transcript_dir.glob(f"{podcast_id}/{podcast_id}-{date_str}*.txt"))
        if existing:
            print(f"  SKIP: Transcript already exists")
            continue

        # Download audio
        print(f"  Downloading audio...")
        try:
            podcast_audio_dir = audio_dir / podcast_id
            podcast_audio_dir.mkdir(parents=True, exist_ok=True)
            audio_path = download_episode(episode, podcast_audio_dir, show_progress=True)
            print(f"  Downloaded: {audio_path.name}")
        except Exception as e:
            print(f"  ERROR downloading: {e}")
            results['failed'].append((podcast_id, date_str, f"Download: {e}"))
            continue

        # Transcribe with Whisper
        print(f"  Transcribing with Whisper large-v3...")
        try:
            text = transcribe(
                audio_path,
                model="large-v3",
                language="sv",
                progress_callback=lambda msg: print(f"    {msg}")
            )
            word_count = len(text.split())
            print(f"  Transcribed: {word_count:,} words")
        except Exception as e:
            print(f"  ERROR transcribing: {e}")
            results['failed'].append((podcast_id, date_str, f"Transcribe: {e}"))
            continue

        # Save transcript
        try:
            transcript_path = save_transcript(
                episode.id,
                text,
                transcript_dir,
                podcast_id,
                metadata={
                    "source": "whisper",
                    "model": "large-v3",
                    "original_title": episode.title,
                    "pub_date": episode.published_at.strftime("%Y-%m-%d"),
                }
            )
            print(f"  Saved: {transcript_path}")
            results['success'].append((podcast_id, date_str, episode.title[:40]))
        except Exception as e:
            print(f"  ERROR saving: {e}")
            results['failed'].append((podcast_id, date_str, f"Save: {e}"))
            continue

        # Clean up audio to save space
        try:
            audio_path.unlink()
            print(f"  Cleaned up audio file")
        except:
            pass

    # Summary
    print("\n" + "=" * 70)
    print("SYNC COMPLETE")
    print("=" * 70)
    print(f"\nSuccess: {len(results['success'])}/10")
    for pid, date, title in results['success']:
        print(f"  ✓ {pid} {date}: {title}...")

    if results['failed']:
        print(f"\nFailed: {len(results['failed'])}/10")
        for pid, date, error in results['failed']:
            print(f"  ✗ {pid} {date}: {error}")


if __name__ == "__main__":
    main()
