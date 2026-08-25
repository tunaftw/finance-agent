#!/usr/bin/env python3
"""
Extract Apple Podcasts TTML transcripts to our standard text format.

Preserves speaker labels (ttm:agent="SPEAKER_N") and optionally timestamps.
Works on TTML files from the Apple cache or downloaded via FetchTranscript.

Usage:
    # Extract a single TTML file (episode metadata given explicitly)
    python3 scripts/extract_ttml.py tools/apple-transcripts/transcript_123.ttml \
        --podcast fillorkill --title "Avsnitt 595 - Casemaraton" --date 2026-08-25

    # Look up title/date automatically from the Apple Podcasts DB via store ID
    python3 scripts/extract_ttml.py tools/apple-transcripts/transcript_1000785814768.ttml \
        --podcast fillorkill

Output: data/transcripts/{podcast}/{podcast}-{date}-{hash}.txt
The 4-char hash is md5(original_title)[:4], matching existing convention.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
TRANSCRIPTS_DIR = PROJECT_ROOT / "data/transcripts"
APPLE_DB = (
    Path.home()
    / "Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Documents/MTLibrary.sqlite"
)
COCOA_EPOCH = datetime(2001, 1, 1)

TTML_NS = "{http://www.w3.org/ns/ttml}"
TTM_NS = "{http://www.w3.org/ns/ttml#metadata}"
PODCASTS_NS = "{http://podcasts.apple.com/transcript-ttml-internal}"


def parse_ttml_with_speakers(ttml_path: Path, with_timestamps: bool = False) -> str:
    """Parse TTML, grouping consecutive paragraphs by speaker.

    Returns text blocks like:
        [SPEAKER_1]
        Sentence. Sentence. ...

        [SPEAKER_2]
        ...
    """
    tree = ET.parse(ttml_path)
    root = tree.getroot()

    blocks: list[str] = []
    current_speaker: str | None = None
    current_lines: list[str] = []

    def flush():
        if current_lines:
            header = f"[{current_speaker}]" if current_speaker else ""
            blocks.append((header + "\n" if header else "") + " ".join(current_lines))

    for p in root.iter(f"{TTML_NS}p"):
        speaker = p.get(f"{TTM_NS}agent")
        sentences = []
        for sent in p.findall(f"{TTML_NS}span[@{PODCASTS_NS}unit='sentence']"):
            words = [
                w.text.strip()
                for w in sent.findall(f"{TTML_NS}span[@{PODCASTS_NS}unit='word']")
                if w.text and w.text.strip()
            ]
            if not words:
                continue
            text = " ".join(words)
            if with_timestamps:
                begin = sent.get("begin", "0")
                secs = _parse_clock(begin)
                text = f"[{secs // 60:02d}:{secs % 60:02d}] {text}"
            sentences.append(text)
        if not sentences:
            continue
        if speaker != current_speaker:
            flush()
            current_speaker = speaker
            current_lines = []
        current_lines.extend(sentences)
    flush()

    return "\n\n".join(blocks)


def _parse_clock(value: str) -> int:
    """TTML begin attribute: '75.5' or '55:23.240' or '1:02:03.4' -> whole seconds."""
    parts = value.split(":")
    secs = 0.0
    for part in parts:
        secs = secs * 60 + float(part)
    return int(secs)


def lookup_episode(store_track_id: str) -> tuple[str, str] | None:
    """Return (title, pub_date_iso) for an Apple store track ID, or None."""
    if not APPLE_DB.exists():
        return None
    conn = sqlite3.connect(f"file:{APPLE_DB}?mode=ro", uri=True)
    try:
        row = conn.execute(
            "SELECT ZTITLE, ZPUBDATE FROM ZMTEPISODE WHERE ZSTORETRACKID = ?",
            (int(store_track_id),),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    title, pub_date_cocoa = row
    pub_date = COCOA_EPOCH + timedelta(seconds=pub_date_cocoa)
    return title, pub_date.strftime("%Y-%m-%d")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ttml", type=Path, help="Path to TTML file")
    ap.add_argument("--podcast", required=True, help="Our podcast ID, e.g. fillorkill")
    ap.add_argument("--title", help="Original episode title (default: look up in Apple DB)")
    ap.add_argument("--date", help="Publication date YYYY-MM-DD (default: look up in Apple DB)")
    ap.add_argument("--timestamps", action="store_true", help="Include [MM:SS] timestamps")
    ap.add_argument("--force", action="store_true", help="Overwrite existing transcript")
    args = ap.parse_args()

    title, pub_date = args.title, args.date
    if not (title and pub_date):
        m = re.search(r"transcript_(\d+)", args.ttml.name)
        looked_up = lookup_episode(m.group(1)) if m else None
        if not looked_up:
            ap.error("--title/--date not given and episode not found in Apple DB")
        title = title or looked_up[0]
        pub_date = pub_date or looked_up[1]

    episode_id = f"{args.podcast}-{pub_date}-{hashlib.md5(title.encode()).hexdigest()[:4]}"
    out_path = TRANSCRIPTS_DIR / args.podcast / f"{episode_id}.txt"
    if out_path.exists() and not args.force:
        print(f"Already exists (use --force to overwrite): {out_path}")
        return 1

    text = parse_ttml_with_speakers(args.ttml, with_timestamps=args.timestamps)
    if len(text.split()) < 100:
        print(f"Suspiciously short transcript ({len(text.split())} words), aborting")
        return 1

    header = (
        f"{'=' * 60}\n"
        f"Episode: {episode_id}\n"
        f"Podcast: {args.podcast}\n"
        f"source: apple_podcasts\n"
        f"method: ttml_extract\n"
        f"original_title: {title}\n"
        f"pub_date: {pub_date}\n"
        f"{'=' * 60}\n\n"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(header + text + "\n")
    n_speakers = len(set(re.findall(r"\[SPEAKER_\d+\]", text)))
    print(f"Wrote {out_path} ({len(text.split())} words, {n_speakers} speakers)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
