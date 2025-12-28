#!/usr/bin/env python3
"""
PARALLELL BATCH-RUNNER FÖR GLM ANALYS
======================================

Kör separata instanser per podcast i parallella terminaler.

ANVÄNDNING:
    Terminal 1: python3 scripts/parallel_batch_runner.py --podcast sparpodden
    Terminal 2: python3 scripts/parallel_batch_runner.py --podcast marknaden
    Terminal 3: python3 scripts/parallel_batch_runner.py --podcast smaspararpodden

    Visa status: python3 scripts/parallel_batch_runner.py --status
    Visa alla:   python3 scripts/parallel_batch_runner.py --status --all

FUNKTIONER:
    - Filtrerar transkript per podcast
    - Hoppar över redan analyserade (kollar om JSON finns)
    - Sparar körlogg per podcast
    - Kan stoppas med Ctrl+C och återupptas
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Importera glm_driver
sys.path.insert(0, str(Path(__file__).parent))
from glm_driver import analyze_transcript, save_analysis

# === KONFIGURATION ===
PROJECT_ROOT = Path(__file__).parent.parent
TRANSCRIPTS_BASE = PROJECT_ROOT / "data" / "podcasts" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "data" / "podcasts" / "analyses"
INDEX_DIR = PROJECT_ROOT / "data" / "podcasts" / "index"
LOGS_DIR = INDEX_DIR / "logs"

BATCH_SIZE = 2  # Antal transkript per batch innan paus
PAUSE_BETWEEN_BATCHES = 2  # Sekunder mellan batchar


def get_all_podcasts() -> list[str]:
    """Hämta alla podcast-mappar."""
    if not TRANSCRIPTS_BASE.exists():
        return []
    # Varje podcast har en mapp under raw/, och transkript finns i transcripts/
    podcasts = []
    for d in TRANSCRIPTS_BASE.iterdir():
        if d.is_dir() and (d / "transcripts").exists():
            podcasts.append(d.name)
    return sorted(podcasts)


def get_pending_transcripts(podcast: str) -> list[Path]:
    """Hitta transkript utan motsvarande analys."""
    transcripts_dir = TRANSCRIPTS_BASE / podcast / "transcripts"

    if not transcripts_dir.exists():
        print(f"Transkript-mapp saknas: {transcripts_dir}")
        return []

    pending = []
    for transcript in transcripts_dir.glob("*.txt"):
        analysis_file = OUTPUT_DIR / f"{transcript.stem}.json"
        if not analysis_file.exists():
            pending.append(transcript)

    return sorted(pending)


def get_run_log(podcast: str) -> dict:
    """Hämta körlogg för podcast."""
    log_file = LOGS_DIR / f"{podcast}-run.json"
    try:
        return json.loads(log_file.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "podcast": podcast,
            "started": None,
            "last_updated": None,
            "processed": 0,
            "failed": [],
            "current_session": []
        }


def update_run_log(podcast: str, transcript_name: str, success: bool, error: str = ""):
    """Uppdatera körlogg."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"{podcast}-run.json"

    log = get_run_log(podcast)

    if log["started"] is None:
        log["started"] = datetime.now().isoformat()

    log["last_updated"] = datetime.now().isoformat()

    if success:
        log["processed"] += 1
        log["current_session"].append(transcript_name)
    else:
        log["failed"].append({
            "name": transcript_name,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })

    log_file.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")


def show_status(all_podcasts: bool = False):
    """Visa status för alla podcasts."""
    print("\n" + "=" * 60)
    print("  PODCAST ANALYS STATUS")
    print("=" * 60)

    podcasts = get_all_podcasts()

    total_transcripts = 0
    total_analyzed = 0
    total_pending = 0

    rows = []

    for podcast in podcasts:
        transcripts_dir = TRANSCRIPTS_BASE / podcast / "transcripts"
        if not transcripts_dir.exists():
            continue

        transcripts = list(transcripts_dir.glob("*.txt"))
        analyzed = sum(1 for t in transcripts if (OUTPUT_DIR / f"{t.stem}.json").exists())
        pending = len(transcripts) - analyzed

        total_transcripts += len(transcripts)
        total_analyzed += analyzed
        total_pending += pending

        if pending > 0 or all_podcasts:
            pct = (analyzed / len(transcripts) * 100) if transcripts else 0
            rows.append((podcast, len(transcripts), analyzed, pending, pct))

    # Sortera efter pending (mest först)
    rows.sort(key=lambda x: -x[3])

    print(f"\n{'Podcast':<25} {'Total':>8} {'Klar':>8} {'Kvar':>8} {'%':>8}")
    print("-" * 60)

    for podcast, total, done, pending, pct in rows:
        status = "" if pending > 0 else "✓"
        print(f"{podcast:<25} {total:>8} {done:>8} {pending:>8} {pct:>7.1f}% {status}")

    print("-" * 60)
    pct_total = (total_analyzed / total_transcripts * 100) if total_transcripts else 0
    print(f"{'TOTALT':<25} {total_transcripts:>8} {total_analyzed:>8} {total_pending:>8} {pct_total:>7.1f}%")
    print()


def run_podcast(podcast: str, batch_size: int = BATCH_SIZE, part: str = None):
    """Kör analys för en specifik podcast."""
    part_info = ""
    if part:
        part_info = f" (del {part})"

    print("=" * 60)
    print(f"  GLM Analys: {podcast}{part_info}")
    print("=" * 60)

    # Säkerställ att output-katalogen finns
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Parsa part-parameter (t.ex. "1/2" -> part_num=1, total_parts=2)
    part_num = None
    total_parts = None
    if part:
        try:
            part_num, total_parts = map(int, part.split("/"))
            if part_num < 1 or part_num > total_parts:
                print(f"❌ Ogiltig del: {part} (måste vara 1-{total_parts})")
                return
        except ValueError:
            print(f"❌ Ogiltigt format för --part: {part} (använd t.ex. '1/2')")
            return

    batch_num = 0

    try:
        while True:
            batch_num += 1

            # Hämta väntande transkript
            pending = get_pending_transcripts(podcast)

            # Filtrera på del om angiven
            if part_num and total_parts and pending:
                chunk_size = len(pending) // total_parts
                remainder = len(pending) % total_parts

                # Beräkna start/slut för denna del
                start = (part_num - 1) * chunk_size + min(part_num - 1, remainder)
                end = start + chunk_size + (1 if part_num <= remainder else 0)
                pending = pending[start:end]

            if not pending:
                print(f"\n✅ KLART! Alla {podcast}-transkript är analyserade!")
                break

            # Ta nästa batch
            batch = pending[:batch_size]

            print(f"\n📊 Status: {len(pending)} kvar att analysera")
            print(f"\n📦 Batch {batch_num}: {len(batch)} filer")
            for f in batch:
                print(f"   • {f.name}")
            print()

            # Analysera varje fil
            for i, filepath in enumerate(batch, 1):
                print(f"\n[{i}/{len(batch)}] {filepath.name}")

                if not filepath.exists():
                    print(f"   ⚠️ Fil saknas, hoppar över")
                    continue

                # Analysera
                analysis, success, error = analyze_transcript(filepath)

                if success and analysis:
                    save_analysis(analysis, OUTPUT_DIR)
                    update_run_log(podcast, filepath.name, True)
                    print(f"   💾 Sparade: {filepath.stem}.json")
                else:
                    update_run_log(podcast, filepath.name, False, error)
                    print(f"   ❌ Misslyckades: {error}")

            # Paus mellan batchar
            print(f"\n⏸️  Pausar {PAUSE_BETWEEN_BATCHES}s innan nästa batch...")
            time.sleep(PAUSE_BETWEEN_BATCHES)

    except KeyboardInterrupt:
        print("\n\n⚠️ Avbruten av användare")
        pending = get_pending_transcripts(podcast)
        print(f"   Kvarvarande: {len(pending)} transkript")
        print("   Kör igen för att fortsätta.")
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="Parallell GLM batch-runner per podcast",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exempel:
  %(prog)s --status              Visa status för podcasts med kvarvarande arbete
  %(prog)s --status --all        Visa status för ALLA podcasts
  %(prog)s --podcast sparpodden  Kör analys för sparpodden
        """
    )

    parser.add_argument(
        "--podcast", "-p",
        help="Podcast att analysera (t.ex. sparpodden, marknaden)"
    )
    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="Visa status för alla podcasts"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Tillsammans med --status: visa även färdiga podcasts"
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=BATCH_SIZE,
        help=f"Antal filer per batch (default: {BATCH_SIZE})"
    )
    parser.add_argument(
        "--part",
        help="Kör en del av podcast (t.ex. '1/2' för första halvan, '2/2' för andra)"
    )

    args = parser.parse_args()

    if args.status:
        show_status(all_podcasts=args.all)
        return

    if args.podcast:
        # Validera podcast
        podcasts = get_all_podcasts()
        if args.podcast not in podcasts:
            print(f"❌ Okänd podcast: {args.podcast}")
            print(f"   Tillgängliga: {', '.join(podcasts)}")
            sys.exit(1)

        run_podcast(args.podcast, batch_size=args.batch_size, part=args.part)
        return

    # Ingen flagga - visa hjälp
    parser.print_help()
    print("\n💡 Tips: Kör --status för att se vilka podcasts som behöver analyseras")


if __name__ == "__main__":
    main()
