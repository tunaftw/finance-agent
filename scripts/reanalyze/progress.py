"""
Progress tracking för podcast re-analys.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class ProgressTracker:
    """Spårar progress för en podcast (eller chunk)."""

    def __init__(self, podcast_id: str, output_dir: Path, chunk: Optional[tuple[int, int]] = None):
        self.podcast_id = podcast_id
        self.output_dir = output_dir
        self.chunk = chunk

        # Progress-fil namn
        if chunk:
            self.progress_file = output_dir / f"{podcast_id}-chunk{chunk[0]}-{chunk[1]}-progress.json"
        else:
            self.progress_file = output_dir / f"{podcast_id}-progress.json"

        self._data = self._load()

    def _load(self) -> dict:
        """Ladda progress från fil."""
        if self.progress_file.exists():
            try:
                return json.loads(self.progress_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass

        return {
            "podcast": self.podcast_id,
            "chunk": list(self.chunk) if self.chunk else None,
            "completed": [],
            "failed": [],
            "last_updated": None,
            "stats": {
                "total_recommendations": 0,
                "total_insights": 0,
                "total_crypto": 0
            }
        }

    def save(self) -> None:
        """Spara progress till fil."""
        self._data["last_updated"] = datetime.now().isoformat()
        self.progress_file.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    @property
    def completed(self) -> list[str]:
        """Lista av färdiga episode_ids."""
        return self._data["completed"]

    @property
    def failed(self) -> list[str]:
        """Lista av misslyckade episode_ids."""
        return self._data["failed"]

    def is_completed(self, episode_id: str) -> bool:
        """Kolla om en episode redan är analyserad."""
        return episode_id in self._data["completed"]

    def mark_completed(self, episode_id: str, analysis: dict) -> None:
        """Markera en episode som klar och uppdatera stats."""
        if episode_id not in self._data["completed"]:
            self._data["completed"].append(episode_id)

        # Ta bort från failed om den finns där
        if episode_id in self._data["failed"]:
            self._data["failed"].remove(episode_id)

        # Uppdatera stats
        self._data["stats"]["total_recommendations"] += len(analysis.get("recommendations", []))
        self._data["stats"]["total_insights"] += len(analysis.get("insights", []))
        self._data["stats"]["total_crypto"] += len(analysis.get("crypto_mentions", []))

        # Spara OMEDELBART
        self.save()

    def mark_failed(self, episode_id: str, error: str) -> None:
        """Markera en episode som misslyckad."""
        if episode_id not in self._data["failed"]:
            self._data["failed"].append(episode_id)

        # Spara OMEDELBART
        self.save()

    def get_stats_summary(self) -> str:
        """Returnera en sammanfattning av stats."""
        stats = self._data["stats"]
        return f"{stats['total_recommendations']} rek, {stats['total_insights']} insights, {stats['total_crypto']} crypto"
