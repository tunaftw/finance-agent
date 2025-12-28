"""Sync orchestrator for podcast episodes.

This module coordinates the process of fetching new episodes,
downloading transcripts or audio, and transcribing.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from podstock.core.config import Config
from podstock.core.exceptions import PodStockError
from podstock.core.state import State
from podstock.sync.models import EpisodeSyncResult, SyncSummary

if TYPE_CHECKING:
    from podstock.core.models import Episode, Podcast

console = Console()


class SyncError(PodStockError):
    """Error during sync operation."""

    pass


class SyncOrchestrator:
    """Coordinates syncing of podcast episodes.

    Handles the full sync workflow:
    1. Fetch RSS feeds for new episodes
    2. Try Apple Podcasts transcripts first (if configured)
    3. Fall back to audio download + Whisper transcription
    4. Update state with results

    Attributes:
        config: Application configuration.
        state: Episode state manager.

    Example:
        >>> orchestrator = SyncOrchestrator(config, state)
        >>> summary = orchestrator.sync_podcast(podcast, latest_n=3)
        >>> print(f"Synced {summary.transcribed} episodes")
    """

    def __init__(self, config: Config, state: State) -> None:
        """Initialize the sync orchestrator.

        Args:
            config: Application configuration.
            state: Episode state manager.
        """
        self.config = config
        self.state = state

    def sync_podcast(
        self,
        podcast: Podcast,
        latest_n: int = 1,
        force: bool = False,
        dry_run: bool = False,
    ) -> list[EpisodeSyncResult]:
        """Sync a single podcast.

        Fetches the latest episodes from RSS, checks for new ones,
        and transcribes them using the configured source.

        Args:
            podcast: Podcast to sync.
            latest_n: Number of latest episodes to check.
            force: Force re-sync even if already processed.
            dry_run: Show what would be synced without processing.

        Returns:
            List of sync results for each episode.
        """
        from podstock.rss.parser import get_latest_episodes

        results: list[EpisodeSyncResult] = []

        # Fetch RSS feed
        try:
            episodes = get_latest_episodes(str(podcast.rss_url), podcast.id, n=latest_n)
        except Exception as e:
            console.print(f"  [red]Failed to fetch RSS:[/red] {e}")
            return results

        for episode in episodes:
            # Check if already processed
            if self.state.is_transcribed(episode.id) and not force:
                results.append(
                    EpisodeSyncResult(
                        episode_id=episode.id,
                        podcast_id=podcast.id,
                        title=episode.title,
                        published_at=episode.published_at,
                        status="skipped",
                    )
                )
                continue

            if dry_run:
                console.print(f"  [dim]Would sync:[/dim] {episode.title}")
                results.append(
                    EpisodeSyncResult(
                        episode_id=episode.id,
                        podcast_id=podcast.id,
                        title=episode.title,
                        published_at=episode.published_at,
                        status="synced",  # Would be synced
                    )
                )
                continue

            # Try to sync the episode
            result = self._sync_episode(episode, podcast)
            results.append(result)

        return results

    def _sync_episode(self, episode: Episode, podcast: Podcast) -> EpisodeSyncResult:
        """Sync a single episode.

        Tries transcript sources in order based on podcast.transcript_source:
        - "apple": Only try Apple Podcasts
        - "whisper": Only use Whisper transcription
        - "auto": Try Apple first, fall back to Whisper

        Args:
            episode: Episode to sync.
            podcast: Parent podcast.

        Returns:
            Sync result for the episode.
        """
        source = podcast.transcript_source or "auto"
        transcript_path: Path | None = None
        used_source: str | None = None
        error: str | None = None

        # Store episode metadata
        self.state.set_episode_metadata(
            episode.id,
            podcast_id=podcast.id,
            title=episode.title,
            published_at=episode.published_at,
        )

        # Try Apple Podcasts first (if enabled)
        if source in ("apple", "auto"):
            transcript_path = self._try_apple_transcript(episode, podcast)
            if transcript_path:
                used_source = "apple"

        # Fall back to Whisper (if enabled and Apple failed)
        if transcript_path is None and source in ("whisper", "auto"):
            try:
                transcript_path = self._transcribe_with_whisper(episode, podcast)
                if transcript_path:
                    used_source = "whisper"
            except Exception as e:
                error = str(e)

        # If Apple-only and failed
        if transcript_path is None and source == "apple":
            error = "Apple transcript not available"

        # Return result
        if transcript_path:
            return EpisodeSyncResult(
                episode_id=episode.id,
                podcast_id=podcast.id,
                title=episode.title,
                published_at=episode.published_at,
                status="synced",
                transcript_source=used_source,
            )
        else:
            return EpisodeSyncResult(
                episode_id=episode.id,
                podcast_id=podcast.id,
                title=episode.title,
                published_at=episode.published_at,
                status="failed",
                error=error or "Unknown error",
            )

    def _try_apple_transcript(self, episode: Episode, podcast: Podcast) -> Path | None:
        """Try to get transcript from Apple Podcasts cache.

        Note: This requires the user to have viewed the transcript in Apple Podcasts
        app first, which caches the TTML file locally.

        Args:
            episode: Episode to get transcript for.
            podcast: Parent podcast.

        Returns:
            Path to transcript file if successful, None otherwise.
        """
        try:
            from podstock.transcribe.apple import (
                list_available_transcripts,
                parse_ttml,
            )
            from datetime import timedelta

            # Get all available transcripts
            available = list_available_transcripts()

            # Try to find a matching transcript
            # Match by podcast name (fuzzy) and publication date (within 1 day)
            for item in available:
                # Check podcast name similarity
                if not self._fuzzy_match_podcast(item.get("podcast_name", ""), podcast.name):
                    continue

                # Check date proximity (within 1 day)
                item_date = item.get("published_at")
                if item_date and episode.published_at:
                    date_diff = abs((item_date - episode.published_at).days)
                    if date_diff > 1:
                        continue

                # Check title similarity (basic)
                item_title = item.get("episode_title", "")
                if not self._fuzzy_match_title(item_title, episode.title):
                    continue

                # Found a match - parse and save
                ttml_path = item.get("ttml_path")
                if not ttml_path:
                    continue

                # Parse TTML
                transcript_text = parse_ttml(ttml_path, include_timestamps=True)

                # Save transcript
                output_dir = self.config.transcripts_dir / podcast.id
                output_dir.mkdir(parents=True, exist_ok=True)
                transcript_path = output_dir / f"{episode.id}.txt"

                # Write with header
                header = f"""============================================================
Episode: {episode.id}
Podcast: {podcast.id}
source: apple
============================================================

"""
                transcript_path.write_text(header + transcript_text)

                # Update state
                self.state.mark_transcribed(
                    episode.id,
                    transcript_path,
                    source="apple",
                    has_timestamps=True,
                )

                console.print(f"  [green]✓[/green] {episode.title} (Apple)")
                return transcript_path

            # No match found
            return None

        except ImportError:
            # Apple module not available
            return None
        except Exception as e:
            console.print(f"  [dim]Apple failed: {e}[/dim]")
            return None

    def _fuzzy_match_podcast(self, apple_name: str, podcast_name: str) -> bool:
        """Check if podcast names match (case-insensitive, handles Swedish chars)."""
        # Normalize both names
        a = apple_name.lower().replace("ö", "o").replace("ä", "a").replace("å", "a")
        b = podcast_name.lower().replace("ö", "o").replace("ä", "a").replace("å", "a")

        # Check if one contains the other
        return a in b or b in a

    def _fuzzy_match_title(self, apple_title: str, episode_title: str) -> bool:
        """Check if episode titles match (fuzzy)."""
        # Simple check: at least 50% of words match
        a_words = set(apple_title.lower().split())
        b_words = set(episode_title.lower().split())

        if not a_words or not b_words:
            return False

        common = len(a_words & b_words)
        return common >= min(len(a_words), len(b_words)) * 0.5

    def _transcribe_with_whisper(self, episode: Episode, podcast: Podcast) -> Path | None:
        """Download audio and transcribe with Whisper.

        Args:
            episode: Episode to transcribe.
            podcast: Parent podcast.

        Returns:
            Path to transcript file if successful, None otherwise.
        """
        from podstock.rss.downloader import download_episode
        from podstock.transcribe.whisper import transcribe, save_transcript

        # Download audio if not already downloaded
        if not self.state.is_downloaded(episode.id):
            dest_dir = self.config.audio_dir / podcast.id
            dest_dir.mkdir(parents=True, exist_ok=True)

            console.print(f"  [dim]Downloading audio...[/dim]")
            audio_path = download_episode(episode, dest_dir, show_progress=False)
            self.state.mark_downloaded(episode.id, audio_path)
        else:
            audio_path = self.state.get_audio_path(episode.id)
            if audio_path is None:
                raise SyncError(f"Audio path not found for {episode.id}")

        # Transcribe
        console.print(f"  [dim]Transcribing with Whisper...[/dim]")
        transcript = transcribe(
            audio_path,
            model=self.config.whisper_model,
            language="sv",
        )

        # Save transcript
        output_dir = self.config.transcripts_dir / podcast.id
        output_dir.mkdir(parents=True, exist_ok=True)
        transcript_path = output_dir / f"{episode.id}.txt"

        save_transcript(
            transcript,
            transcript_path,
            episode_id=episode.id,
            podcast_id=podcast.id,
        )

        # Update state
        self.state.mark_transcribed(
            episode.id,
            transcript_path,
            source="whisper",
            has_timestamps=False,
        )

        console.print(f"  [green]✓[/green] {episode.title} (Whisper)")
        return transcript_path

    def sync_list(
        self,
        list_id: str,
        latest_n: int = 1,
        force: bool = False,
        dry_run: bool = False,
    ) -> SyncSummary:
        """Sync all podcasts in a list.

        Args:
            list_id: List identifier.
            latest_n: Number of latest episodes per podcast.
            force: Force re-sync.
            dry_run: Show what would be synced.

        Returns:
            Summary of sync operation.
        """
        from podstock.lists.manager import ListManager
        from podstock.rss.manager import get_podcast

        summary = SyncSummary()

        # Load list
        manager = ListManager(self.config.lists_file)
        lst = manager.get_list(list_id)

        if lst is None:
            summary.errors.append(f"List not found: {list_id}")
            summary.finish()
            return summary

        # Sync each podcast in the list
        for podcast_id in lst.podcast_ids:
            podcast = get_podcast(podcast_id, self.config.podcasts_file)
            if podcast is None:
                summary.errors.append(f"Podcast not found: {podcast_id}")
                continue

            if not podcast.active:
                continue

            console.print(f"\n[bold]{podcast.name}[/bold]")
            summary.podcasts_checked += 1

            results = self.sync_podcast(podcast, latest_n, force, dry_run)
            for result in results:
                summary.add_result(result)

        summary.finish()
        return summary

    def sync_all(
        self,
        latest_n: int = 1,
        force: bool = False,
        dry_run: bool = False,
    ) -> SyncSummary:
        """Sync all active podcasts.

        Args:
            latest_n: Number of latest episodes per podcast.
            force: Force re-sync.
            dry_run: Show what would be synced.

        Returns:
            Summary of sync operation.
        """
        from podstock.rss.manager import load_podcasts

        summary = SyncSummary()

        podcasts = load_podcasts(self.config.podcasts_file)
        active_podcasts = [p for p in podcasts if p.active]

        for podcast in active_podcasts:
            if not podcast.rss_url:
                continue

            console.print(f"\n[bold]{podcast.name}[/bold]")
            summary.podcasts_checked += 1

            results = self.sync_podcast(podcast, latest_n, force, dry_run)
            for result in results:
                summary.add_result(result)

        summary.finish()
        return summary
