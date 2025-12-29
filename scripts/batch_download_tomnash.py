#!/usr/bin/env python3
"""Batch download YouTube transcripts from TomNashTV channel."""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_SCRIPT = PROJECT_ROOT / ".claude/skills/youtube-download/scripts/download_youtube.py"
VIDEO_IDS_FILE = Path("/tmp/tomnash_videos.txt")
LOG_FILE = PROJECT_ROOT / "data/youtube/raw/tom-nash/_download_log.txt"

def main():
    """Download all transcripts."""
    video_ids = VIDEO_IDS_FILE.read_text().strip().split("\n")
    total = len(video_ids)

    success_count = 0
    error_count = 0
    errors = []

    print(f"Starting download of {total} videos...")

    with open(LOG_FILE, "w") as log:
        log.write(f"Downloading {total} videos from TomNashTV\n")
        log.write("=" * 60 + "\n\n")

        for i, video_id in enumerate(video_ids, 1):
            video_id = video_id.strip()
            if not video_id:
                continue

            print(f"\n[{i}/{total}] Downloading: {video_id}")
            log.write(f"[{i}/{total}] {video_id}: ")
            log.flush()

            try:
                result = subprocess.run(
                    [sys.executable, str(DOWNLOAD_SCRIPT), video_id],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=PROJECT_ROOT
                )

                if result.returncode == 0:
                    success_count += 1
                    log.write("SUCCESS\n")
                    # Extract title from output
                    for line in result.stdout.split("\n"):
                        if line.startswith("Title:"):
                            print(f"    ✓ {line}")
                            break
                else:
                    error_count += 1
                    error_msg = result.stderr.strip() or "Unknown error"
                    errors.append((video_id, error_msg))
                    log.write(f"ERROR: {error_msg}\n")
                    print(f"    ✗ Error: {error_msg[:80]}")

            except subprocess.TimeoutExpired:
                error_count += 1
                errors.append((video_id, "Timeout"))
                log.write("ERROR: Timeout\n")
                print(f"    ✗ Timeout")

            except Exception as e:
                error_count += 1
                errors.append((video_id, str(e)))
                log.write(f"ERROR: {e}\n")
                print(f"    ✗ {e}")

            log.flush()

        # Summary
        log.write("\n" + "=" * 60 + "\n")
        log.write(f"SUMMARY\n")
        log.write(f"Total: {total}\n")
        log.write(f"Success: {success_count}\n")
        log.write(f"Errors: {error_count}\n")

        if errors:
            log.write(f"\nFailed videos:\n")
            for vid, err in errors:
                log.write(f"  {vid}: {err}\n")

    print(f"\n{'=' * 60}")
    print(f"DOWNLOAD COMPLETE")
    print(f"{'=' * 60}")
    print(f"Success: {success_count}/{total}")
    print(f"Errors: {error_count}")
    print(f"Log: {LOG_FILE}")

if __name__ == "__main__":
    main()
