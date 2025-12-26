"""Sökfunktioner för extraherad data."""

import json
from datetime import datetime, timedelta
from pathlib import Path


class RecommendationSearch:
    """Sök i extraherad rekommendationsdata."""

    def __init__(self, extracted_dir: Path):
        self.extracted_dir = Path(extracted_dir)
        self._load_data()

    def _load_data(self):
        """Ladda index och rekommendationer."""
        index_file = self.extracted_dir / "index.json"
        recs_file = self.extracted_dir / "recommendations.json"

        if not index_file.exists():
            raise FileNotFoundError(
                f"Index saknas: {index_file}. Kör 'rebuild-index' först."
            )

        self.index = json.loads(index_file.read_text(encoding="utf-8"))
        self.recommendations = json.loads(recs_file.read_text(encoding="utf-8"))

    def get_recommendations_for_stock(
        self, stock: str, action: str | None = None
    ) -> list:
        """
        Hämta alla rekommendationer för en aktie.

        Args:
            stock: Aktienamn (case-insensitive)
            action: Filtrera på 'buy', 'sell', etc. (optional)
        """
        stock_lower = stock.lower()
        results = [
            r for r in self.recommendations if stock_lower in r["stock"].lower()
        ]

        if action:
            results = [r for r in results if r["action"] == action]

        return results

    def get_recent_recommendations(
        self, days: int = 30, action: str | None = None
    ) -> list:
        """Hämta rekommendationer från senaste X dagar."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        results = [
            r for r in self.recommendations if r["date"] and r["date"] >= cutoff
        ]

        if action:
            results = [r for r in results if r["action"] == action]

        return results

    def get_episode_summary(self, episode_id: str) -> dict | None:
        """Hämta sammanfattning för ett avsnitt."""
        for ep in self.index["episodes"]:
            if ep["id"] == episode_id:
                return ep
        return None

    def get_full_episode(self, episode_id: str) -> dict | None:
        """Hämta fullständig episod-analys."""
        episode_file = self.extracted_dir / "episodes" / f"{episode_id}.json"
        if episode_file.exists():
            return json.loads(episode_file.read_text(encoding="utf-8"))
        return None

    def search_by_speaker(self, speaker: str) -> list:
        """Sök rekommendationer från en specifik person."""
        speaker_lower = speaker.lower()
        return [
            r
            for r in self.recommendations
            if r.get("speaker") and speaker_lower in r["speaker"].lower()
        ]

    def search_by_sector(self, sector: str) -> list:
        """Sök rekommendationer inom en sektor."""
        sector_lower = sector.lower()
        return [
            r
            for r in self.recommendations
            if r.get("sector") and sector_lower in r["sector"].lower()
        ]

    def search_by_podcast(self, podcast: str) -> list:
        """Sök rekommendationer från en specifik podcast."""
        podcast_lower = podcast.lower()
        return [
            r
            for r in self.recommendations
            if r.get("podcast") and podcast_lower in r["podcast"].lower()
        ]

    def get_stats(self) -> dict:
        """Övergripande statistik."""
        action_counts = {}
        for r in self.recommendations:
            action = r["action"]
            action_counts[action] = action_counts.get(action, 0) + 1

        podcast_counts = {}
        for r in self.recommendations:
            podcast = r.get("podcast", "Okänd")
            podcast_counts[podcast] = podcast_counts.get(podcast, 0) + 1

        return {
            "total_episodes": self.index["episode_count"],
            "total_recommendations": self.index["recommendation_count"],
            "unique_stocks": self.index["unique_stocks"],
            "recommendations_by_action": action_counts,
            "recommendations_by_podcast": podcast_counts,
            "last_updated": self.index["last_updated"],
        }

    def get_top_stocks(self, n: int = 10) -> list:
        """Aktier med flest omnämnanden."""
        stocks = [{"name": k, **v} for k, v in self.index["stocks"].items()]
        stocks.sort(key=lambda x: x["mention_count"], reverse=True)
        return stocks[:n]

    def get_all_buy_recommendations(self) -> list:
        """Hämta alla köprekommendationer."""
        return [r for r in self.recommendations if r["action"] == "buy"]

    def get_all_sell_recommendations(self) -> list:
        """Hämta alla säljrekommendationer."""
        return [r for r in self.recommendations if r["action"] == "sell"]
