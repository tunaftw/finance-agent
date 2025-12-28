"""Tests for podstock.core.models module."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from podstock.core.models import (
    ConfidenceLevel,
    Episode,
    EpisodeStatus,
    Podcast,
    PodcastsFile,
    Recommendation,
    StateFile,
)


class TestPodcast:
    """Tests for Podcast model."""

    def test_valid_podcast(self) -> None:
        """Should create podcast with valid data."""
        podcast = Podcast(
            id="borspodden",
            name="Börspodden",
            rss_url="https://borspodden.libsyn.com/rss",
            hosts=["Johan Isaksson", "John Skogman"],
        )

        assert podcast.id == "borspodden"
        assert podcast.name == "Börspodden"
        assert str(podcast.rss_url) == "https://borspodden.libsyn.com/rss"
        assert podcast.hosts == ["Johan Isaksson", "John Skogman"]
        assert podcast.language == "sv"
        assert podcast.active is True

    def test_invalid_id_format(self) -> None:
        """Should reject invalid ID format."""
        with pytest.raises(ValidationError, match="string_pattern_mismatch"):
            Podcast(
                id="Invalid ID!",  # Contains spaces and special chars
                name="Test",
                rss_url="https://example.com/rss",
            )

    def test_empty_name_rejected(self) -> None:
        """Should reject empty name."""
        with pytest.raises(ValidationError, match="string_too_short"):
            Podcast(
                id="test",
                name="",
                rss_url="https://example.com/rss",
            )

    def test_invalid_url_rejected(self) -> None:
        """Should reject invalid URL."""
        with pytest.raises(ValidationError, match="url"):
            Podcast(
                id="test",
                name="Test",
                rss_url="not-a-url",
            )

    def test_optional_fields_default_to_none(self) -> None:
        """Should default optional fields to None."""
        podcast = Podcast(
            id="test",
            name="Test",
            rss_url="https://example.com/rss",
        )

        assert podcast.description is None
        assert podcast.website is None
        assert podcast.twitter is None
        assert podcast.hosts == []


class TestEpisode:
    """Tests for Episode model."""

    def test_valid_episode(self) -> None:
        """Should create episode with valid data."""
        episode = Episode(
            id="bp-2024-12-18",
            podcast_id="borspodden",
            title="Avsnitt 598 - Julspecial",
            published_at=datetime(2024, 12, 18),
            audio_url="https://example.com/episode.mp3",
        )

        assert episode.id == "bp-2024-12-18"
        assert episode.podcast_id == "borspodden"
        assert episode.title == "Avsnitt 598 - Julspecial"
        assert episode.duration_seconds is None

    def test_duration_must_be_positive(self) -> None:
        """Should reject non-positive duration."""
        with pytest.raises(ValidationError, match="duration_seconds must be positive"):
            Episode(
                id="test",
                podcast_id="test",
                title="Test",
                published_at=datetime.now(),
                audio_url="https://example.com/test.mp3",
                duration_seconds=0,
            )

    def test_valid_duration(self) -> None:
        """Should accept positive duration."""
        episode = Episode(
            id="test",
            podcast_id="test",
            title="Test",
            published_at=datetime.now(),
            audio_url="https://example.com/test.mp3",
            duration_seconds=3600,
        )

        assert episode.duration_seconds == 3600


class TestRecommendation:
    """Tests for Recommendation model."""

    def test_valid_recommendation(self) -> None:
        """Should create recommendation with valid data."""
        rec = Recommendation(
            id="bp-2024-12-18-001",
            episode_id="bp-2024-12-18",
            company_name="Evolution Gaming",
            ticker="EVO",
            quote="Vi har ökat i Evolution",
            context="Diskussion om Q3-rapporten",
            confidence=ConfidenceLevel.HIGH,
            reasoning="Explicit köputtryck",
        )

        assert rec.id == "bp-2024-12-18-001"
        assert rec.company_name == "Evolution Gaming"
        assert rec.ticker == "EVO"
        assert rec.confidence == ConfidenceLevel.HIGH

    def test_confidence_levels(self) -> None:
        """Should support all confidence levels."""
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.LOW.value == "low"

    def test_optional_fields(self) -> None:
        """Should allow optional fields to be None."""
        rec = Recommendation(
            id="test",
            episode_id="test",
            company_name="Test Company",
            quote="Test quote",
            context="Test context",
            confidence=ConfidenceLevel.MEDIUM,
            reasoning="Test reasoning",
        )

        assert rec.ticker is None
        assert rec.market is None
        assert rec.host is None
        assert rec.timestamp_hint is None
        assert rec.time_horizon is None


class TestEpisodeStatus:
    """Tests for EpisodeStatus model."""

    def test_default_status(self) -> None:
        """Should initialize with all flags False."""
        status = EpisodeStatus(episode_id="test")

        assert status.downloaded is False
        assert status.transcribed is False
        assert status.analyzed is False
        assert status.recommendations_count == 0

    def test_status_with_values(self) -> None:
        """Should store provided values."""
        from pathlib import Path

        status = EpisodeStatus(
            episode_id="test",
            downloaded=True,
            downloaded_at=datetime(2024, 12, 18),
            audio_path=Path("/path/to/audio.mp3"),
        )

        assert status.downloaded is True
        assert status.audio_path == Path("/path/to/audio.mp3")


class TestPodcastsFile:
    """Tests for PodcastsFile model."""

    def test_empty_podcasts_file(self) -> None:
        """Should create empty podcasts file."""
        pf = PodcastsFile()

        assert pf.version == 1
        assert pf.podcasts == []

    def test_with_podcasts(self) -> None:
        """Should store podcast list."""
        podcast = Podcast(
            id="test",
            name="Test",
            rss_url="https://example.com/rss",
        )
        pf = PodcastsFile(podcasts=[podcast])

        assert len(pf.podcasts) == 1
        assert pf.podcasts[0].id == "test"


class TestStateFile:
    """Tests for StateFile model."""

    def test_empty_state_file(self) -> None:
        """Should create empty state file."""
        sf = StateFile()

        assert sf.version == 1
        assert sf.episodes == {}

    def test_with_episodes(self) -> None:
        """Should store episode statuses."""
        status = EpisodeStatus(episode_id="test")
        sf = StateFile(episodes={"test": status})

        assert "test" in sf.episodes
        assert sf.episodes["test"].downloaded is False
