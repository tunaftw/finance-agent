"""
Podcast Re-analysis Runner

Huvudklass för att köra re-analys av podcast-transkript.
"""

import json
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Fixa imports för att fungera både som modul och direkt körning
try:
    from .progress import ProgressTracker
    from .glm_analyzer import analyze_transcript, save_analysis, count_words
except ImportError:
    from progress import ProgressTracker
    from glm_analyzer import analyze_transcript, save_analysis, count_words


# Podcast-namn mapping
PODCAST_NAMES = {
    "aktiepodden": "Aktiepodden",
    "analyspodden": "Analyspodden",
    "avanzapodden": "Avanzapodden",
    "borsensfinest": "Börsens Finest",
    "borsmagasinet": "Börsmagasinet",
    "borsmaklarna": "Börsmäklarna",
    "borspodden": "Börspodden",
    "bullochbjorn": "Bull & Björn",
    "ettrikareliv": "Ett rikare liv",
    "fillorkill": "Fill or Kill",
    "globalgains": "Global Gains",
    "gotttjot": "Gött Tjöt om Aktier",
    "igborssnack": "IG Börssnack",
    "kortochlang": "Kort & Lång",
    "kvalitetforpengarna": "Kvalitet för Pengarna",
    "kvalitetsaktiepodden": "Kvalitetsaktiepodden",
    "marknaden": "Marknaden",
    "marketmakers": "Market Makers",
    "montrosepodden": "Montrosepodden",
    "smaspararpodden": "Småspararpodden",
    "sparpodden": "Sparpodden",
    "veckanstrade": "Veckans Trade"
}


class PodcastRunner:
    """Kör re-analys för en podcast (eller chunk)."""

    def __init__(
        self,
        podcast_id: str,
        chunk: Optional[tuple[int, int]] = None,
        output_dir: Optional[Path] = None,
        transcripts_dir: Optional[Path] = None
    ):
        self.podcast_id = podcast_id
        self.chunk = chunk  # (start_index, end_index)

        # Projektroten
        self.project_root = Path(__file__).parent.parent.parent

        # Output-dir för analyser
        self.output_dir = output_dir or self.project_root / "data" / "podcasts" / "analyses-v2"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Transkript-dir
        self.transcripts_dir = transcripts_dir or self.project_root / "data" / "podcasts" / "raw" / podcast_id / "transcripts"

        # Progress tracker
        self.progress = ProgressTracker(podcast_id, self.output_dir, chunk)

        # Graceful shutdown
        self._shutdown_requested = False
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Hantera Ctrl+C gracefully."""
        print("\n\n⚠️  Avbryter... Sparar progress...")
        self._shutdown_requested = True

    def get_all_transcripts(self) -> list[Path]:
        """
        Hämta alla transkript, sorterade efter datum (2025 först, bakåt).
        """
        if not self.transcripts_dir.exists():
            return []

        transcripts = list(self.transcripts_dir.glob("*.txt"))

        # Sortera efter datum i filnamnet (podcast-YYYY-MM-DD-hash.txt)
        # Extrahera datum-delen och sortera omvänt (nyast först)
        def extract_date(p: Path) -> str:
            parts = p.stem.split("-")
            if len(parts) >= 4:
                # YYYY-MM-DD
                return f"{parts[1]}-{parts[2]}-{parts[3]}"
            return "0000-00-00"

        transcripts.sort(key=extract_date, reverse=True)  # 2025 först

        return transcripts

    def get_pending_transcripts(self) -> list[Path]:
        """
        Hämta transkript som ännu inte analyserats.
        """
        all_transcripts = self.get_all_transcripts()

        # Applicera chunk om det finns
        if self.chunk:
            start, end = self.chunk
            all_transcripts = all_transcripts[start:end]

        # Filtrera bort redan analyserade
        pending = []
        for t in all_transcripts:
            episode_id = t.stem
            if not self.progress.is_completed(episode_id):
                pending.append(t)

        return pending

    def print_header(self, total: int, pending: int) -> None:
        """Skriv ut header med status."""
        podcast_name = PODCAST_NAMES.get(self.podcast_id, self.podcast_id.upper())

        chunk_info = ""
        if self.chunk:
            chunk_info = f" (chunk {self.chunk[0]}-{self.chunk[1]})"

        completed = total - pending
        pct = (completed / total * 100) if total > 0 else 0

        print()
        print("━" * 50)
        print(f"📦 {podcast_name.upper()} RE-ANALYS{chunk_info}")
        print("━" * 50)
        print(f"✅ Completed: {completed}/{total} ({pct:.1f}%)")
        print(f"⏳ Remaining: {pending}")
        print(f"❌ Failed: {len(self.progress.failed)}")
        print("━" * 50)
        print()

    def run(self) -> None:
        """Kör re-analys på alla pending transkript."""

        all_transcripts = self.get_all_transcripts()

        # Applicera chunk
        if self.chunk:
            start, end = self.chunk
            all_transcripts = all_transcripts[start:end]

        total = len(all_transcripts)
        pending = self.get_pending_transcripts()

        if not pending:
            self.print_header(total, 0)
            print("✅ Alla transkript är redan analyserade!")
            return

        self.print_header(total, len(pending))

        for i, transcript in enumerate(pending):
            if self._shutdown_requested:
                print("\n👋 Avslutad. Progress sparad.")
                break

            episode_id = transcript.stem
            word_count = count_words(transcript)

            print(f"[{len(self.progress.completed) + 1}/{total}] {transcript.name}")
            print(f"  📝 {word_count:,} ord | försök 1/3")
            print(f"  ⏳ Anropar GLM-4.7...")

            analysis, success, error = analyze_transcript(transcript)

            if success and analysis:
                # Spara analys
                output_file = save_analysis(analysis, self.output_dir)

                # Markera som klar (sparar progress omedelbart)
                self.progress.mark_completed(episode_id, analysis)

                rec_count = len(analysis.get("recommendations", []))
                insight_count = len(analysis.get("insights", []))
                crypto_count = len(analysis.get("crypto_mentions", []))

                print(f"  ✅ Klar! {rec_count} rek, {insight_count} insights, {crypto_count} crypto")
                print(f"  💾 Sparad: {output_file.name}")

            else:
                # Markera som misslyckad (sparar progress omedelbart)
                self.progress.mark_failed(episode_id, error)
                print(f"  ❌ Misslyckades: {error}")

            print()

        # Sammanfattning
        print("━" * 50)
        print("📊 SAMMANFATTNING")
        print("━" * 50)
        print(f"✅ Analyserade: {len(self.progress.completed)}")
        print(f"❌ Misslyckade: {len(self.progress.failed)}")
        print(f"📈 Totalt: {self.progress.get_stats_summary()}")
        print("━" * 50)


def run_podcast(podcast_id: str, chunk: Optional[tuple[int, int]] = None) -> None:
    """
    Convenience-funktion för att köra en podcast.

    Används av genererade runner-scripts.
    """
    runner = PodcastRunner(podcast_id, chunk)
    runner.run()
