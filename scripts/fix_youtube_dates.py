#!/usr/bin/env python3
"""Fix missing/wrong dates in YouTube analysis files using yt-dlp."""

import json
import subprocess
import time
from pathlib import Path

ANALYSIS_DIR = Path(__file__).parent.parent / "data" / "crypto" / "technicalroundup-analysis"

# Dates that are known to be wrong (analysis date instead of video date)
WRONG_DATES = {None, "2025-12-26"}


def get_video_date(video_id: str) -> str | None:
    """Fetch video publish date using yt-dlp."""
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--print",
                "upload_date",
                f"https://youtube.com/watch?v={video_id}",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            date_str = result.stdout.strip()  # Format: YYYYMMDD
            if len(date_str) == 8:
                return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    except subprocess.TimeoutExpired:
        print(f"  Timeout fetching {video_id}")
    except Exception as e:
        print(f"  Error fetching {video_id}: {e}")
    return None


def fix_dates(dry_run: bool = False):
    """Find and fix all files with missing/wrong dates."""
    # First, find all files that need fixing
    files_to_fix = []
    for json_file in sorted(ANALYSIS_DIR.glob("*.json")):
        # Skip non-video files
        if json_file.name in ("completion-log.json",):
            continue
        try:
            with open(json_file) as f:
                data = json.load(f)
            date = data.get("date")
            if date in WRONG_DATES:
                video_id = data.get("source_id", json_file.stem)
                files_to_fix.append((json_file, video_id, date))
        except Exception as e:
            print(f"Error reading {json_file}: {e}")

    print(f"Found {len(files_to_fix)} files to fix\n")

    if dry_run:
        for json_file, video_id, old_date in files_to_fix:
            print(f"  Would fix: {json_file.name} (current: {old_date})")
        return

    fixed = 0
    failed = 0
    for i, (json_file, video_id, old_date) in enumerate(files_to_fix, 1):
        print(f"[{i}/{len(files_to_fix)}] Fetching date for {video_id}...")
        new_date = get_video_date(video_id)

        if new_date:
            # Re-read file to get fresh data
            with open(json_file) as f:
                data = json.load(f)

            data["date"] = new_date
            with open(json_file, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  Fixed: {old_date} -> {new_date}")
            fixed += 1
        else:
            print(f"  Failed to get date for {video_id}")
            failed += 1

        # Small delay to avoid rate limiting
        if i < len(files_to_fix):
            time.sleep(1)

    print(f"\nDone! Fixed {fixed} files, failed {failed}")


if __name__ == "__main__":
    import sys

    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("DRY RUN - no changes will be made\n")
    fix_dates(dry_run=dry_run)
