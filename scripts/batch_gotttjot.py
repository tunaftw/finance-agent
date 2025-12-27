#!/usr/bin/env python3
"""
BATCH RUNNER: GOTT TJÖT OM AKTIER
=================================
Analyserar Gott Tjöt-transkript med GLM-4.7.

ANVÄNDNING:
    cd /Users/pontus/Developer/podcast-transcriber
    python3 scripts/batch_gotttjot.py
"""

import json
import sys
import time
from pathlib import Path

# Importera glm_driver
sys.path.insert(0, str(Path(__file__).parent))
from glm_driver import analyze_transcript, save_analysis, update_completion_log

# === KONFIGURATION ===
PROJECT_ROOT = Path(__file__).parent.parent
TRANSCRIPT_QUEUE = PROJECT_ROOT / "data" / "extracted" / "glm-batch" / "queue-gotttjot.txt"
COMPLETION_LOG = PROJECT_ROOT / "data" / "extracted" / "glm-batch" / "log-gotttjot.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "extracted" / "glm-batch"
BATCH_SIZE = 2
PAUSE_BETWEEN_BATCHES = 2

PODCAST_NAME = "Gott Tjöt om aktier"


def get_completed_files() -> set:
    """Hämta lista med redan analyserade filer."""
    try:
        data = json.loads(COMPLETION_LOG.read_text())
        return set(data.get("completed", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def get_next_batch() -> list[Path]:
    """Hämta nästa batch av transkript att analysera."""
    completed = get_completed_files()
    batch = []

    if not TRANSCRIPT_QUEUE.exists():
        print(f"❌ {TRANSCRIPT_QUEUE.name} saknas!")
        return []

    for line in TRANSCRIPT_QUEUE.read_text().splitlines():
        if not line.strip():
            continue

        filepath = Path(line.strip())
        basename = filepath.name

        if basename not in completed:
            batch.append(filepath)
            if len(batch) >= BATCH_SIZE:
                break

    return batch


def show_progress():
    """Visa aktuell progress."""
    completed = len(get_completed_files())
    total = sum(1 for _ in TRANSCRIPT_QUEUE.read_text().splitlines() if _.strip())

    try:
        failed = len(json.loads(COMPLETION_LOG.read_text()).get("failed", []))
    except:
        failed = 0

    pct = (completed / total * 100) if total > 0 else 0
    print(f"\n📊 Progress: {completed}/{total} ({pct:.1f}%) | ❌ Failed: {failed}")


def main():
    print("=" * 50)
    print(f"  GLM-4.7 Batch Analysis: {PODCAST_NAME}")
    print("=" * 50)

    batch_num = 0

    try:
        while True:
            batch_num += 1

            show_progress()

            batch = get_next_batch()

            if not batch:
                print(f"\n✅ KLART! Alla {PODCAST_NAME}-transkript är analyserade!")
                show_progress()
                break

            print(f"\n📦 Batch {batch_num}: {len(batch)} filer")
            for f in batch:
                print(f"   • {f.name}")
            print()

            for i, filepath in enumerate(batch, 1):
                print(f"\n[{i}/{len(batch)}] {filepath.name}")

                if not filepath.exists():
                    print(f"   ⚠️ Fil saknas, hoppar över")
                    continue

                analysis, success, error = analyze_transcript(filepath)

                if success and analysis:
                    save_analysis(analysis, OUTPUT_DIR)
                    update_completion_log(COMPLETION_LOG, filepath.name, True)
                else:
                    update_completion_log(COMPLETION_LOG, filepath.name, False, error)

            print(f"\n⏸️  Pausar {PAUSE_BETWEEN_BATCHES}s innan nästa batch...")
            time.sleep(PAUSE_BETWEEN_BATCHES)

    except KeyboardInterrupt:
        print("\n\n⚠️ Avbruten av användare")
        print("Progress sparad. Kör igen för att fortsätta.")
        show_progress()
        sys.exit(0)


if __name__ == "__main__":
    main()
