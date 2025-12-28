"""Tests for podstock.rss.parser module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import feedparser
import pytest

from podstock.core.exceptions import RSSError
from podstock.rss.parser import (
    _extract_audio_url,
    _generate_episode_id,
    _parse_duration,
    fetch_feed,
    get_all_episodes,
    get_latest_episodes,
    parse_episode,
    validate_rss_url,
)


@pytest.fixture
def sample_libsyn_rss(fixtures_dir: Path) -> str:
    """Load sample Libsyn RSS fixture."""
    return (fixtures_dir / "sample_rss_libsyn.xml").read_text()


@pytest.fixture
def sample_acast_rss(fixtures_dir: Path) -> str:
    """Load sample Acast RSS fixture."""
    return (fixtures_dir / "sample_rss_acast.xml").read_text()


@pytest.fixture
def parsed_libsyn_feed(sample_libsyn_rss: str) -> feedparser.FeedParserDict:
    """Parse sample Libsyn RSS."""
    return feedparser.parse(sample_libsyn_rss)


@pytest.fixture
def parsed_acast_feed(sample_acast_rss: str) -> feedparser.FeedParserDict:
    """Parse sample Acast RSS."""
    return feedparser.parse(sample_acast_rss)


class TestParseDuration:
    """Tests for _parse_duration helper."""

    def test_parse_hms_format(self) -> None:
        """Should parse HH:MM:SS format."""
        assert _parse_duration("01:15:30") == 4530

    def test_parse_ms_format(self) -> None:
        """Should parse MM:SS format."""
        assert _parse_duration("58:20") == 3500

    def test_parse_seconds_format(self) -> None:
        """Should parse plain seconds."""
        assert _parse_duration("5400") == 5400

    def test_parse_none(self) -> None:
        """Should return None for None input."""
        assert _parse_duration(None) is None

    def test_parse_invalid(self) -> None:
        """Should return None for invalid format."""
        assert _parse_duration("invalid") is None


class TestGenerateEpisodeId:
    """Tests for _generate_episode_id helper."""

    def test_generates_id_with_date(self) -> None:
        """Should include date in ID."""
        episode_id = _generate_episode_id(
            "borspodden",
            datetime(2024, 12, 18),
            "Test Episode",
        )
        assert episode_id.startswith("borspodden-2024-12-18-")

    def test_different_titles_different_ids(self) -> None:
        """Should generate different IDs for different titles."""
        id1 = _generate_episode_id("test", datetime(2024, 1, 1), "Title A")
        id2 = _generate_episode_id("test", datetime(2024, 1, 1), "Title B")
        assert id1 != id2


class TestExtractAudioUrl:
    """Tests for _extract_audio_url helper."""

    def test_extract_from_enclosure(self, parsed_libsyn_feed: feedparser.FeedParserDict) -> None:
        """Should extract URL from enclosure."""
        entry = parsed_libsyn_feed.entries[0]
        url = _extract_audio_url(entry)
        assert url == "https://traffic.libsyn.com/borspodden/bp-598.mp3"

    def test_extract_from_media_content(self, parsed_acast_feed: feedparser.FeedParserDict) -> None:
        """Should extract URL from media:content."""
        entry = parsed_acast_feed.entries[0]
        url = _extract_audio_url(entry)
        assert url == "https://media.acast.com/marketmakers/mm-450.mp3"


class TestParseEpisode:
    """Tests for parse_episode function."""

    def test_parse_libsyn_episode(self, parsed_libsyn_feed: feedparser.FeedParserDict) -> None:
        """Should parse Libsyn episode correctly."""
        entry = parsed_libsyn_feed.entries[0]
        episode = parse_episode(entry, "borspodden")

        assert episode is not None
        assert episode.podcast_id == "borspodden"
        assert "Julspecial" in episode.title
        assert episode.duration_seconds == 4530  # 01:15:30
        assert "libsyn" in str(episode.audio_url)

    def test_parse_acast_episode(self, parsed_acast_feed: feedparser.FeedParserDict) -> None:
        """Should parse Acast episode correctly."""
        entry = parsed_acast_feed.entries[0]
        episode = parse_episode(entry, "marketmakers")

        assert episode is not None
        assert episode.podcast_id == "marketmakers"
        assert "Techbolagen" in episode.title
        assert episode.duration_seconds == 5400  # seconds format
        assert "acast" in str(episode.audio_url)

    def test_returns_none_for_missing_title(self) -> None:
        """Should return None if title missing."""
        entry = MagicMock()
        entry.title = None
        episode = parse_episode(entry, "test")
        assert episode is None

    def test_returns_none_for_missing_audio(self) -> None:
        """Should return None if no audio URL found."""
        entry = MagicMock()
        entry.title = "Test Episode"
        entry.enclosures = []
        entry.media_content = None
        entry.links = []
        episode = parse_episode(entry, "test")
        assert episode is None


class TestFetchFeed:
    """Tests for fetch_feed function."""

    @patch("podstock.rss.parser.requests.get")
    def test_fetch_success(self, mock_get: MagicMock, sample_libsyn_rss: str) -> None:
        """Should fetch and parse feed successfully."""
        mock_response = MagicMock()
        mock_response.content = sample_libsyn_rss.encode()
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        feed = fetch_feed("https://example.com/rss")

        assert len(feed.entries) == 3
        assert feed.feed.title == "Börspodden"

    @patch("podstock.rss.parser.requests.get")
    def test_fetch_timeout_raises_error(self, mock_get: MagicMock) -> None:
        """Should raise RSSError on timeout."""
        import requests

        mock_get.side_effect = requests.Timeout()

        with pytest.raises(RSSError, match="Timeout"):
            fetch_feed("https://example.com/rss")

    @patch("podstock.rss.parser.requests.get")
    def test_fetch_empty_feed_raises_error(self, mock_get: MagicMock) -> None:
        """Should raise RSSError for empty feed."""
        mock_response = MagicMock()
        mock_response.content = b"<rss><channel></channel></rss>"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with pytest.raises(RSSError, match="no entries"):
            fetch_feed("https://example.com/rss")


class TestGetAllEpisodes:
    """Tests for get_all_episodes function."""

    @patch("podstock.rss.parser.fetch_feed")
    def test_returns_sorted_episodes(
        self, mock_fetch: MagicMock, parsed_libsyn_feed: feedparser.FeedParserDict
    ) -> None:
        """Should return episodes sorted by date (newest first)."""
        mock_fetch.return_value = parsed_libsyn_feed

        episodes = get_all_episodes("https://example.com/rss", "borspodden")

        assert len(episodes) == 3
        # Verify sorted newest first
        assert episodes[0].published_at >= episodes[1].published_at
        assert episodes[1].published_at >= episodes[2].published_at


class TestGetLatestEpisodes:
    """Tests for get_latest_episodes function."""

    @patch("podstock.rss.parser.fetch_feed")
    def test_returns_limited_episodes(
        self, mock_fetch: MagicMock, parsed_libsyn_feed: feedparser.FeedParserDict
    ) -> None:
        """Should return only N episodes."""
        mock_fetch.return_value = parsed_libsyn_feed

        episodes = get_latest_episodes("https://example.com/rss", "borspodden", n=2)

        assert len(episodes) == 2


class TestValidateRssUrl:
    """Tests for validate_rss_url function."""

    @patch("podstock.rss.parser.fetch_feed")
    def test_valid_url(self, mock_fetch: MagicMock, parsed_libsyn_feed: feedparser.FeedParserDict) -> None:
        """Should return True for valid RSS URL."""
        mock_fetch.return_value = parsed_libsyn_feed

        assert validate_rss_url("https://example.com/rss") is True

    def test_invalid_url_format(self) -> None:
        """Should return False for invalid URL format."""
        assert validate_rss_url("not-a-url") is False

    @patch("podstock.rss.parser.fetch_feed")
    def test_fetch_failure(self, mock_fetch: MagicMock) -> None:
        """Should return False on fetch failure."""
        mock_fetch.side_effect = RSSError("Failed")

        assert validate_rss_url("https://example.com/rss") is False
