#!/usr/bin/env python3
"""
AUTOMATISERAD BATCH-RUNNER FÖR CRYPTO SENTIMENT ANALYS
========================================================

Kör detta script för att automatiskt analysera alla TechnicalRoundup
YouTube-transkript med GLM-4.7.

ANVÄNDNING:
    cd /Users/pontus/Developer/podcast-transcriber
    python3 scripts/crypto_batch_runner.py

FUNKTIONER:
    - Läser remaining.txt och completion-log.json
    - Hoppar över redan analyserade transkript
    - Analyserar BATCH_SIZE transkript per batch
    - Sparar progress automatiskt
    - Kan stoppas med Ctrl+C och återupptas

TIPS:
    - Kör i bakgrunden: nohup python3 scripts/crypto_batch_runner.py > crypto_batch.log 2>&1 &
    - Följ progress: tail -f crypto_batch.log
"""

import json
import sys
import time
from pathlib import Path

# Force unbuffered output for nohup
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Importera crypto_glm_driver
sys.path.insert(0, str(Path(__file__).parent))
from crypto_glm_driver import (
    analyze_transcript,
    save_analysis,
    update_completion_log,
    TRANSCRIPT_DIR,
    OUTPUT_DIR,
    COMPLETION_LOG
)

# === KONFIGURATION ===
PROJECT_ROOT = Path(__file__).parent.parent
REMAINING_FILE = OUTPUT_DIR / "remaining.txt"
BATCH_SIZE = 2  # Antal transkript per batch innan paus
PAUSE_BETWEEN_BATCHES = 2  # Sekunder mellan batchar


def get_completed_files() -> set:
    """Hämta lista med redan analyserade filer."""
    try:
        data = json.loads(COMPLETION_LOG.read_text())
        return set(data.get("completed", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def get_total_count() -> int:
    """Hämta totalt antal transkript."""
    try:
        # Count from remaining.txt + completed
        remaining = sum(1 for line in REMAINING_FILE.read_text().splitlines() if line.strip())
        completed = len(get_completed_files())
        return remaining + completed
    except FileNotFoundError:
        return 0


def get_next_batch() -> list[str]:
    """Hämta nästa batch av video IDs att analysera."""
    completed = get_completed_files()
    batch = []

    if not REMAINING_FILE.exists():
        print("❌ remaining.txt saknas!")
        return []

    for line in REMAINING_FILE.read_text().splitlines():
        video_id = line.strip()
        if not video_id:
            continue

        transcript_name = f"{video_id}.txt"

        if transcript_name not in completed:
            batch.append(video_id)
            if len(batch) >= BATCH_SIZE:
                break

    return batch


def show_progress():
    """Visa aktuell progress."""
    completed = len(get_completed_files())

    # Calculate total from remaining + completed
    try:
        remaining_count = sum(1 for line in REMAINING_FILE.read_text().splitlines() if line.strip())
    except FileNotFoundError:
        remaining_count = 0

    total = remaining_count + completed

    try:
        failed = len(json.loads(COMPLETION_LOG.read_text()).get("failed", []))
    except:
        failed = 0

    pct = (completed / total * 100) if total > 0 else 0
    print(f"\n📊 Progress: {completed}/{total} ({pct:.1f}%) | ❌ Failed: {failed}")


def main():
    print("=" * 50)
    print("  GLM-4.7 Crypto Batch Analysis Runner")
    print("=" * 50)

    batch_num = 0

    try:
        while True:
            batch_num += 1

            # Visa progress
            show_progress()

            # Hämta nästa batch
            batch = get_next_batch()

            if not batch:
                print("\n✅ KLART! Alla transkript är analyserade!")
                show_progress()
                break

            print(f"\n📦 Batch {batch_num}: {len(batch)} filer")
            for video_id in batch:
                print(f"   • {video_id}.txt")
            print()

            # Analysera varje fil
            for i, video_id in enumerate(batch, 1):
                transcript_path = TRANSCRIPT_DIR / f"{video_id}.txt"
                print(f"\n[{i}/{len(batch)}] {video_id}.txt")

                if not transcript_path.exists():
                    print(f"   ⚠️ Fil saknas, hoppar över")
                    continue

                # Analysera
                analysis, success, error = analyze_transcript(transcript_path, video_id)

                if success and analysis:
                    save_analysis(analysis, OUTPUT_DIR)
                    update_completion_log(COMPLETION_LOG, f"{video_id}.txt", True)
                else:
                    update_completion_log(COMPLETION_LOG, f"{video_id}.txt", False, error)

            # Paus mellan batchar
            print(f"\n⏸️  Pausar {PAUSE_BETWEEN_BATCHES}s innan nästa batch...")
            time.sleep(PAUSE_BETWEEN_BATCHES)

    except KeyboardInterrupt:
        print("\n\n⚠️ Avbruten av användare")
        print("Progress sparad. Kör igen för att fortsätta.")
        show_progress()
        sys.exit(0)


if __name__ == "__main__":
    main()
