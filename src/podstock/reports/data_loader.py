"""Data loader for report generation.

This module handles loading and preparing data from state
and extracted recommendations for report generation.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from podstock.reports.models import EpisodeData, RecommendationData, ReportData

if TYPE_CHECKING:
    from podstock.core.config import Config
    from podstock.core.state import State


class ReportDataLoader:
    """Loads and prepares data for report generation.

    Collects episode and recommendation data from state.json
    and extracted recommendations, filtering by date range
    and podcast list.

    Attributes:
        config: Application configuration.
        state: Episode state manager.

    Example:
        >>> loader = ReportDataLoader(config, state)
        >>> data = loader.load_for_period(
        ...     start_date=datetime(2025, 12, 20),
        ...     end_date=datetime(2025, 12, 26),
        ...     list_id="broad"
        ... )
    """

    def __init__(self, config: Config, state: State) -> None:
        """Initialize the data loader.

        Args:
            config: Application configuration.
            state: Episode state manager.
        """
        self.config = config
        self.state = state

    def load_for_period(
        self,
        start_date: datetime,
        end_date: datetime,
        list_id: str,
    ) -> ReportData:
        """Load all data for a reporting period.

        Args:
            start_date: Start of period (inclusive).
            end_date: End of period (inclusive).
            list_id: ID of podcast list to use.

        Returns:
            ReportData with episodes and recommendations.
        """
        from podstock.lists.manager import ListManager
        from podstock.rss.manager import get_podcast

        # Load list
        manager = ListManager(self.config.lists_file)
        lst = manager.get_list(list_id)

        if lst is None:
            return ReportData(
                period=f"{start_date.strftime('%Y-%m-%d')} till {end_date.strftime('%Y-%m-%d')}",
                start_date=start_date,
                end_date=end_date,
                list_id=list_id,
                list_name="Unknown",
            )

        # Get podcast names
        podcasts = []
        podcast_names: dict[str, str] = {}
        for pid in lst.podcast_ids:
            podcast = get_podcast(pid, self.config.podcasts_file)
            if podcast:
                podcasts.append(podcast.name)
                podcast_names[pid] = podcast.name

        # Get episodes in period
        episode_statuses = self.state.get_episodes_in_period(
            start_date, end_date, lst.podcast_ids
        )

        # Convert to EpisodeData
        episodes = []
        for status in episode_statuses:
            podcast_id = status.podcast_id or self.state._extract_podcast_from_id(status.episode_id)
            podcast_name = podcast_names.get(podcast_id, podcast_id) if podcast_id else "Unknown"

            episodes.append(
                EpisodeData(
                    episode_id=status.episode_id,
                    podcast_id=podcast_id or "",
                    podcast_name=podcast_name,
                    title=status.title or status.episode_id,
                    published_at=status.published_at or self.state._extract_date_from_id(status.episode_id) or datetime.now(),
                    transcript_available=status.transcribed,
                )
            )

        # Load recommendations
        recommendations = self._load_recommendations(
            [ep.episode_id for ep in episodes],
            podcast_names,
        )

        return ReportData(
            period=f"{start_date.strftime('%Y-%m-%d')} till {end_date.strftime('%Y-%m-%d')}",
            start_date=start_date,
            end_date=end_date,
            list_id=list_id,
            list_name=lst.name,
            podcasts=podcasts,
            episodes=episodes,
            recommendations=recommendations,
        )

    def _load_recommendations(
        self,
        episode_ids: list[str],
        podcast_names: dict[str, str],
    ) -> list[RecommendationData]:
        """Load recommendations for given episodes.

        Args:
            episode_ids: Episode IDs to load recommendations for.
            podcast_names: Mapping of podcast_id to name.

        Returns:
            List of RecommendationData.
        """
        recommendations = []

        # Try to load from extracted/recommendations.json
        recs_file = self.config.data_dir / "extracted" / "recommendations.json"
        if recs_file.exists():
            try:
                all_recs = json.loads(recs_file.read_text())
                for rec in all_recs:
                    ep_id = rec.get("episode_id")
                    if ep_id and ep_id in episode_ids:
                        podcast_id = self.state._extract_podcast_from_id(ep_id) or ""
                        recommendations.append(
                            RecommendationData(
                                episode_id=ep_id,
                                podcast_name=rec.get("podcast", podcast_names.get(podcast_id, podcast_id)),
                                stock=rec.get("stock", "?"),
                                action=rec.get("action", "?"),
                                speaker=rec.get("speaker"),
                                reasoning=rec.get("reasoning"),
                                quote=rec.get("quote"),
                                date=rec.get("date"),
                            )
                        )
            except (json.JSONDecodeError, OSError):
                pass

        # Also try individual recommendation files
        recs_dir = self.config.recommendations_dir
        if recs_dir.exists():
            for ep_id in episode_ids:
                # Try different filename patterns
                for pattern in [
                    f"{ep_id}-recommendations.json",
                    f"{ep_id}.json",
                ]:
                    rec_file = recs_dir / pattern
                    if rec_file.exists():
                        try:
                            rec_data = json.loads(rec_file.read_text())
                            # Handle different formats
                            recs_list = rec_data.get("recommendations", [rec_data])
                            for rec in recs_list:
                                podcast_id = self.state._extract_podcast_from_id(ep_id) or ""
                                recommendations.append(
                                    RecommendationData(
                                        episode_id=ep_id,
                                        podcast_name=rec.get("podcast_name", rec.get("podcast", podcast_names.get(podcast_id, podcast_id))),
                                        stock=rec.get("stock_name", rec.get("stock", "?")),
                                        action=rec.get("action", "?"),
                                        speaker=rec.get("speaker"),
                                        reasoning=rec.get("reasoning"),
                                        quote=rec.get("quote"),
                                        date=rec.get("date"),
                                    )
                                )
                        except (json.JSONDecodeError, OSError):
                            pass

        return recommendations
