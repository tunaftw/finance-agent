"""Storage management for earnings transcripts.

This module handles persisting transcripts, analysis results, and state.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from podstock.earnings.models import (
    EarningsStateFile,
    EarningsTranscript,
    TranscriptAnalysis,
)

if TYPE_CHECKING:
    from podstock.core.config import Config


class EarningsStorage:
    """Storage manager for earnings transcripts.

    Handles:
    - Transcript storage (earnings_state.json + individual JSON files)
    - Analysis results (analysis/*.json)

    Example:
        >>> storage = EarningsStorage(config)
        >>> storage.save_transcript(transcript)
        >>> transcripts = storage.list_transcripts()
    """

    def __init__(self, config: Config):
        """Initialize storage with configuration.

        Args:
            config: Application configuration with earnings paths.
        """
        self.config = config
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create required directories."""
        self.config.earnings_dir.mkdir(parents=True, exist_ok=True)
        self.config.earnings_transcripts_dir.mkdir(parents=True, exist_ok=True)
        self.config.earnings_analysis_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # State Management
    # =========================================================================

    def _load_state_file(self) -> EarningsStateFile:
        """Load state file or create empty."""
        path = self.config.earnings_state_file
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return EarningsStateFile.model_validate(data)
        return EarningsStateFile()

    def _save_state_file(self, state: EarningsStateFile) -> None:
        """Save state file atomically."""
        state.last_updated = datetime.now()
        path = self.config.earnings_state_file
        temp_path = path.with_suffix(".tmp")

        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(state.model_dump_json(indent=2))

        temp_path.replace(path)

    # =========================================================================
    # Transcript Management
    # =========================================================================

    def list_transcripts(self, company_id: str | None = None) -> list[EarningsTranscript]:
        """Get all transcripts, optionally filtered by company.

        Args:
            company_id: Filter by company ID.

        Returns:
            List of transcripts sorted by date (newest first).
        """
        state = self._load_state_file()
        transcripts = list(state.transcripts.values())

        if company_id:
            transcripts = [t for t in transcripts if t.company_id == company_id]

        # Sort by year/quarter descending
        transcripts.sort(
            key=lambda t: (t.fiscal_year, t.fiscal_quarter),
            reverse=True,
        )
        return transcripts

    def get_transcript(self, transcript_id: str) -> EarningsTranscript | None:
        """Get a transcript by ID.

        Args:
            transcript_id: Transcript ID.

        Returns:
            Transcript or None if not found.
        """
        state = self._load_state_file()
        return state.transcripts.get(transcript_id)

    def save_transcript(self, transcript: EarningsTranscript) -> Path:
        """Save a transcript to storage.

        Saves to both the state file and an individual JSON file in the
        company's transcript directory.

        Args:
            transcript: Transcript to save.

        Returns:
            Path to saved transcript file.

        Raises:
            OSError: If directory creation or file write fails.
            ValidationError: If transcript data fails Pydantic validation.
        """
        # Ensure company directory exists
        company_dir = self.config.earnings_transcripts_dir / transcript.company_id
        company_dir.mkdir(parents=True, exist_ok=True)

        # Save individual file
        filename = f"{transcript.company_id}_earnings_{transcript.fiscal_year}_q{transcript.fiscal_quarter}.json"
        file_path = company_dir / filename
        transcript.local_path = str(file_path.relative_to(self.config.earnings_dir))

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(transcript.model_dump_json(indent=2))

        # Update state
        state = self._load_state_file()
        state.transcripts[transcript.id] = transcript
        self._save_state_file(state)

        return file_path

    def transcript_exists(self, transcript_id: str) -> bool:
        """Check if a transcript exists.

        Args:
            transcript_id: Transcript ID.

        Returns:
            True if transcript exists.
        """
        state = self._load_state_file()
        return transcript_id in state.transcripts

    def delete_transcript(self, transcript_id: str) -> bool:
        """Delete a transcript.

        Args:
            transcript_id: Transcript ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        state = self._load_state_file()

        if transcript_id not in state.transcripts:
            return False

        transcript = state.transcripts[transcript_id]

        # Delete local file if exists
        if transcript.local_path:
            file_path = self.config.earnings_dir / transcript.local_path
            if file_path.exists():
                file_path.unlink()

        # Remove from state
        del state.transcripts[transcript_id]
        if transcript_id in state.analyzed_transcripts:
            state.analyzed_transcripts.remove(transcript_id)

        self._save_state_file(state)
        return True

    # =========================================================================
    # Analysis Management
    # =========================================================================

    def save_analysis(self, analysis: TranscriptAnalysis) -> Path:
        """Save analysis results to storage.

        Args:
            analysis: Analysis to save.

        Returns:
            Path to saved JSON file.

        Raises:
            OSError: If file write fails.
            ValidationError: If analysis data fails Pydantic validation.
        """
        path = self.config.earnings_analysis_dir / f"{analysis.transcript_id}.json"

        with open(path, "w", encoding="utf-8") as f:
            f.write(analysis.model_dump_json(indent=2))

        # Mark as analyzed in state
        self.mark_analyzed(analysis.transcript_id)

        return path

    def load_analysis(self, transcript_id: str) -> TranscriptAnalysis | None:
        """Load analysis results for a transcript.

        Args:
            transcript_id: Transcript ID.

        Returns:
            Analysis or None if not found.
        """
        path = self.config.earnings_analysis_dir / f"{transcript_id}.json"

        if not path.exists():
            return None

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        return TranscriptAnalysis.model_validate(data)

    def mark_analyzed(self, transcript_id: str) -> None:
        """Mark a transcript as analyzed.

        Args:
            transcript_id: Transcript ID.
        """
        state = self._load_state_file()

        if transcript_id not in state.analyzed_transcripts:
            state.analyzed_transcripts.append(transcript_id)

        self._save_state_file(state)

    def is_analyzed(self, transcript_id: str) -> bool:
        """Check if a transcript has been analyzed.

        Args:
            transcript_id: Transcript ID.

        Returns:
            True if analyzed.
        """
        state = self._load_state_file()
        return transcript_id in state.analyzed_transcripts

    # =========================================================================
    # Linking
    # =========================================================================

    def link_to_filing(self, transcript_id: str, filing_id: str) -> None:
        """Link a transcript to a filing.

        Args:
            transcript_id: Transcript ID.
            filing_id: Filing ID to link to.
        """
        state = self._load_state_file()

        if transcript_id in state.transcripts:
            state.transcripts[transcript_id].linked_filing_id = filing_id
            self._save_state_file(state)

    def link_to_presentation(self, transcript_id: str, presentation_id: str) -> None:
        """Link a transcript to a presentation.

        Args:
            transcript_id: Transcript ID.
            presentation_id: Presentation ID to link to.
        """
        state = self._load_state_file()

        if transcript_id in state.transcripts:
            state.transcripts[transcript_id].linked_presentation_id = presentation_id
            self._save_state_file(state)

    # =========================================================================
    # Sync State
    # =========================================================================

    def update_last_sync(self) -> None:
        """Update last sync timestamp."""
        state = self._load_state_file()
        state.last_sync = datetime.now()
        self._save_state_file(state)

    def get_last_sync(self) -> datetime | None:
        """Get last sync timestamp."""
        state = self._load_state_file()
        return state.last_sync
