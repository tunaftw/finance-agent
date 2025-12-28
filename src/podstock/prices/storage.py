"""JSONL storage for tracked recommendations.

This module provides persistence for TrackedRecommendation objects
using the JSON Lines format for efficient append operations.

The JSONL format stores one JSON object per line, which:
- Allows efficient append operations (no full file rewrite)
- Makes it easy to inspect data manually
- Supports streaming reads for large files

Example usage::

    from pathlib import Path
    from podstock.prices import RecommendationStorage

    storage = RecommendationStorage(Path("data/prices/recommendations.jsonl"))

    # Save a new recommendation
    storage.save(recommendation)

    # Get all recommendations
    all_recs = storage.get_all()

    # Get by tracking ID
    rec = storage.get("evolution-abc123")

    # Update existing
    storage.update(updated_rec)

    # Delete
    storage.delete("evolution-abc123")
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from podstock.prices.models import TrackedRecommendation


class RecommendationStorage:
    """JSONL storage for tracked recommendations.

    Uses JSON Lines format where each line is a complete JSON object.
    This allows for efficient append operations without rewriting the entire file.

    Attributes:
        file_path: Path to the JSONL storage file.

    Methods
    -------
    save(rec)
        Append a new recommendation to the file.
    update(rec)
        Update an existing recommendation (rewrites file).
    get(tracking_id)
        Get a recommendation by tracking ID.
    get_all()
        Get all recommendations.
    delete(tracking_id)
        Delete a recommendation by tracking ID.

    Example:
        >>> storage = RecommendationStorage(Path("data/prices/recommendations.jsonl"))
        >>> storage.save(recommendation)
        >>> all_recs = storage.get_all()
    """

    def __init__(self, file_path: Path):
        """Initialize the storage.

        Args:
            file_path: Path to the JSONL file.
        """
        self.file_path = file_path
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Ensure the parent directory exists."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, rec: TrackedRecommendation) -> None:
        """Append a new recommendation to the file.

        Args:
            rec: The recommendation to save.
        """
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(rec.model_dump_json() + "\n")

    def update(self, rec: TrackedRecommendation) -> bool:
        """Update an existing recommendation (rewrites file).

        Args:
            rec: The updated recommendation.

        Returns:
            True if recommendation was found and updated.
        """
        all_recs = self.get_all()
        found = False

        updated_recs = []
        for existing in all_recs:
            if existing.tracking_id == rec.tracking_id:
                updated_recs.append(rec)
                found = True
            else:
                updated_recs.append(existing)

        if found:
            self._write_all(updated_recs)

        return found

    def upsert(self, rec: TrackedRecommendation) -> None:
        """Insert or update a recommendation.

        Args:
            rec: The recommendation to save or update.
        """
        if not self.update(rec):
            self.save(rec)

    def get(self, tracking_id: str) -> TrackedRecommendation | None:
        """Get a recommendation by ID.

        Args:
            tracking_id: The tracking ID to look up.

        Returns:
            The recommendation or None if not found.
        """
        for rec in self.get_all():
            if rec.tracking_id == tracking_id:
                return rec
        return None

    def get_all(self) -> list[TrackedRecommendation]:
        """Load all recommendations from storage.

        Returns:
            List of all tracked recommendations.
        """
        if not self.file_path.exists():
            return []

        recs: list[TrackedRecommendation] = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    recs.append(TrackedRecommendation.model_validate(data))
                except (json.JSONDecodeError, ValueError) as e:
                    # Log error but continue with other lines
                    print(f"Warning: Error parsing line {line_num}: {e}")

        return recs

    def get_by_source(
        self,
        source_type: str | None = None,
        source_name: str | None = None,
    ) -> list[TrackedRecommendation]:
        """Get recommendations filtered by source.

        Args:
            source_type: Filter by type (podcast, twitter, youtube).
            source_name: Filter by source name.

        Returns:
            Filtered list of recommendations.
        """
        recs = self.get_all()

        if source_type:
            recs = [r for r in recs if r.source_type == source_type]
        if source_name:
            recs = [r for r in recs if r.source_name == source_name]

        return recs

    def get_by_speaker(self, speaker: str) -> list[TrackedRecommendation]:
        """Get recommendations by speaker.

        Args:
            speaker: Speaker name to filter by.

        Returns:
            Recommendations made by this speaker.
        """
        speaker_lower = speaker.lower()
        return [
            r for r in self.get_all()
            if r.speaker and r.speaker.lower() == speaker_lower
        ]

    def get_pending_verifications(self) -> list[TrackedRecommendation]:
        """Get recommendations with pending verifications.

        Returns:
            Recommendations that have intervals not yet verified.
        """
        return [r for r in self.get_all() if r.pending_intervals()]

    def delete(self, tracking_id: str) -> bool:
        """Delete a recommendation.

        Args:
            tracking_id: The tracking ID to delete.

        Returns:
            True if recommendation was found and deleted.
        """
        all_recs = self.get_all()
        filtered = [r for r in all_recs if r.tracking_id != tracking_id]

        if len(filtered) < len(all_recs):
            self._write_all(filtered)
            return True

        return False

    def _write_all(self, recs: list[TrackedRecommendation]) -> None:
        """Atomic rewrite of all recommendations.

        Args:
            recs: Complete list of recommendations to write.
        """
        self._ensure_dir()
        tmp_file = self.file_path.with_suffix(".tmp")

        with open(tmp_file, "w", encoding="utf-8") as f:
            for rec in recs:
                f.write(rec.model_dump_json() + "\n")

        tmp_file.replace(self.file_path)

    def count(self) -> int:
        """Get total number of tracked recommendations.

        Returns:
            Number of recommendations.
        """
        return len(self.get_all())

    def clear(self) -> None:
        """Remove all recommendations."""
        if self.file_path.exists():
            self.file_path.unlink()

    def exists(self, tracking_id: str) -> bool:
        """Check if a tracking ID exists.

        Args:
            tracking_id: The ID to check.

        Returns:
            True if it exists.
        """
        return self.get(tracking_id) is not None
