"""Batch-processing av flera transkript."""

import json
import logging
import time
from datetime import datetime
from pathlib import Path

from .process_transcript import TranscriptProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BatchRunner:
    """Kör batch-processing på flera transkript."""

    def __init__(
        self,
        api_key: str,
        transcripts_dir: Path,
        output_dir: Path,
        processing_dir: Path,
        model: str = "claude-sonnet-4-20250514",
    ):
        self.processor = TranscriptProcessor(api_key, model=model)
        self.transcripts_dir = Path(transcripts_dir)
        self.output_dir = Path(output_dir)
        self.processing_dir = Path(processing_dir)

        # Säkerställ mappar finns
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.processing_dir.mkdir(parents=True, exist_ok=True)

        # Status-filer
        self.completed_file = self.processing_dir / "completed.json"
        self.errors_file = self.processing_dir / "errors.json"

    def get_completed(self) -> set:
        """Hämta lista över redan processade filer."""
        if self.completed_file.exists():
            data = json.loads(self.completed_file.read_text())
            return set(data.get("completed", []))
        return set()

    def mark_completed(self, filepath: Path):
        """Markera fil som klar."""
        completed = self.get_completed()
        completed.add(str(filepath.name))
        self.completed_file.write_text(
            json.dumps(
                {"completed": list(completed), "updated": datetime.now().isoformat()},
                indent=2,
            )
        )

    def log_error(self, filepath: Path, error: str):
        """Logga fel."""
        errors = []
        if self.errors_file.exists():
            errors = json.loads(self.errors_file.read_text()).get("errors", [])

        errors.append(
            {
                "file": str(filepath.name),
                "error": error,
                "timestamp": datetime.now().isoformat(),
            }
        )

        self.errors_file.write_text(json.dumps({"errors": errors}, indent=2))

    def find_transcripts(self) -> list[Path]:
        """
        Hitta alla transkript-filer.

        Söker rekursivt i transcripts_dir efter .txt-filer.
        """
        transcript_files = []

        # Kolla om det finns undermappar (borspodden/, veckanstrade/, etc.)
        for item in self.transcripts_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                # Sök i undermappen
                transcript_files.extend(item.glob("*.txt"))
            elif item.is_file() and item.suffix == ".txt":
                # Fil direkt i transcripts_dir
                transcript_files.append(item)

        # Kolla även raw/ om den finns
        raw_dir = self.transcripts_dir / "raw"
        if raw_dir.exists():
            transcript_files.extend(raw_dir.glob("*.txt"))

        return sorted(transcript_files)

    def run(
        self,
        skip_completed: bool = True,
        max_files: int | None = None,
        delay_between: float = 2.0,
        podcast_filter: str | None = None,
    ) -> dict:
        """
        Kör batch-processing på alla transkript.

        Args:
            skip_completed: Hoppa över redan processade filer
            max_files: Max antal filer att processa (None = alla)
            delay_between: Sekunder mellan varje API-anrop (rate limiting)
            podcast_filter: Filtrera på podcast-namn (t.ex. "borspodden")
        """
        # Hitta alla transkript
        transcript_files = self.find_transcripts()
        logger.info(f"Hittade {len(transcript_files)} transkript-filer")

        # Filtrera på podcast om angett
        if podcast_filter:
            podcast_filter_lower = podcast_filter.lower()
            transcript_files = [
                f
                for f in transcript_files
                if podcast_filter_lower in f.parent.name.lower()
                or podcast_filter_lower in f.stem.lower()
            ]
            logger.info(f"  → {len(transcript_files)} efter podcast-filter")

        # Filtrera bort redan processade
        completed = self.get_completed() if skip_completed else set()
        pending = [f for f in transcript_files if f.name not in completed]
        logger.info(f"{len(pending)} filer att processa ({len(completed)} redan klara)")

        if max_files:
            pending = pending[:max_files]

        # Processa
        successful = 0
        failed = 0

        for i, filepath in enumerate(pending):
            logger.info(f"[{i + 1}/{len(pending)}] Processar: {filepath.name}")

            try:
                # Processa
                analysis = self.processor.process_transcript(filepath)

                # Spara
                output_file = self.processor.save_analysis(analysis, self.output_dir)
                logger.info(f"  ✓ Sparade: {output_file.name}")
                logger.info(
                    f"  → {len(analysis.recommendations)} rekommendationer extraherade"
                )

                # Markera klar
                self.mark_completed(filepath)
                successful += 1

            except Exception as e:
                logger.error(f"  ✗ Fel: {e!s}")
                self.log_error(filepath, str(e))
                failed += 1

            # Rate limiting
            if i < len(pending) - 1:
                time.sleep(delay_between)

        # Sammanfattning
        logger.info(f"\n{'=' * 50}")
        logger.info(f"KLAR! Lyckade: {successful}, Misslyckade: {failed}")

        return {"successful": successful, "failed": failed}
