"""Tests for podstock.rss.manager module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from podstock.core.exceptions import ConfigError, RSSError
from podstock.core.models import Podcast
from podstock.rss.manager import (
    _generate_podcast_id,
    add_podcast,
    get_active_podcasts,
    get_podcast,
    load_podcasts,
    remove_podcast,
    save_podcasts,
    update_podcast,
)


class TestGeneratePodcastId:
    """Tests for _generate_podcast_id helper."""

    def test_simple_name(self) -> None:
        """Should generate slug from simple name."""
        assert _generate_podcast_id("Börspodden") == "borspodden"

    def test_name_with_spaces(self) -> None:
        """Should replace spaces with hyphens."""
        assert _generate_podcast_id("Market Makers") == "market-makers"

    def test_name_with_special_chars(self) -> None:
        """Should remove special characters."""
        assert _generate_podcast_id("Gött Tjöt om Aktier") == "gott-tjot-om-aktier"

    def test_name_with_numbers(self) -> None:
        """Should preserve numbers."""
        assert _generate_podcast_id("Podcast 123") == "podcast-123"


class TestLoadPodcasts:
    """Tests for load_podcasts function."""

    def test_load_missing_file(self, tmp_path: Path) -> None:
        """Should return empty list if file doesn't exist."""
        podcasts = load_podcasts(tmp_path / "missing.json")
        assert podcasts == []

    def test_load_valid_file(self, tmp_path: Path) -> None:
        """Should load podcasts from valid file."""
        podcasts_file = tmp_path / "podcasts.json"
        data = {
            "version": 1,
            "podcasts": [
                {
                    "id": "test",
                    "name": "Test Podcast",
                    "rss_url": "https://example.com/rss",
                    "hosts": ["Host A"],
                    "active": True,
                }
            ],
        }
        podcasts_file.write_text(json.dumps(data))

        podcasts = load_podcasts(podcasts_file)

        assert len(podcasts) == 1
        assert podcasts[0].id == "test"
        assert podcasts[0].name == "Test Podcast"

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        """Should raise ConfigError for invalid JSON."""
        podcasts_file = tmp_path / "podcasts.json"
        podcasts_file.write_text("not valid json")

        with pytest.raises(ConfigError, match="Invalid JSON"):
            load_podcasts(podcasts_file)


class TestSavePodcasts:
    """Tests for save_podcasts function."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """Should create podcasts file."""
        podcasts_file = tmp_path / "podcasts.json"
        podcast = Podcast(
            id="test",
            name="Test",
            rss_url="https://example.com/rss",
        )

        save_podcasts([podcast], podcasts_file)

        assert podcasts_file.exists()

    def test_save_writes_valid_json(self, tmp_path: Path) -> None:
        """Should write valid JSON."""
        podcasts_file = tmp_path / "podcasts.json"
        podcast = Podcast(
            id="test",
            name="Test",
            rss_url="https://example.com/rss",
            hosts=["Host A", "Host B"],
        )

        save_podcasts([podcast], podcasts_file)

        data = json.loads(podcasts_file.read_text())
        assert len(data["podcasts"]) == 1
        assert data["podcasts"][0]["hosts"] == ["Host A", "Host B"]

    def test_roundtrip(self, tmp_path: Path) -> None:
        """Should preserve data through save/load cycle."""
        podcasts_file = tmp_path / "podcasts.json"
        original = Podcast(
            id="borspodden",
            name="Börspodden",
            rss_url="https://borspodden.libsyn.com/rss",
            hosts=["Johan Isaksson", "John Skogman"],
            description="Test description",
            active=True,
        )

        save_podcasts([original], podcasts_file)
        loaded = load_podcasts(podcasts_file)

        assert len(loaded) == 1
        assert loaded[0].id == original.id
        assert loaded[0].name == original.name
        assert loaded[0].hosts == original.hosts
        assert loaded[0].description == original.description


class TestGetPodcast:
    """Tests for get_podcast function."""

    def test_get_existing(self, tmp_path: Path) -> None:
        """Should return podcast if exists."""
        podcasts_file = tmp_path / "podcasts.json"
        podcast = Podcast(id="test", name="Test", rss_url="https://example.com/rss")
        save_podcasts([podcast], podcasts_file)

        result = get_podcast("test", podcasts_file)

        assert result is not None
        assert result.id == "test"

    def test_get_missing(self, tmp_path: Path) -> None:
        """Should return None if not found."""
        podcasts_file = tmp_path / "podcasts.json"
        save_podcasts([], podcasts_file)

        result = get_podcast("nonexistent", podcasts_file)

        assert result is None


class TestAddPodcast:
    """Tests for add_podcast function."""

    @patch("podstock.rss.manager.validate_rss_url")
    def test_add_new_podcast(self, mock_validate: None, tmp_path: Path) -> None:
        """Should add new podcast."""
        mock_validate.return_value = True
        podcasts_file = tmp_path / "podcasts.json"

        podcast = add_podcast(
            name="Börspodden",
            rss_url="https://borspodden.libsyn.com/rss",
            podcasts_file=podcasts_file,
            hosts=["Johan", "John"],
        )

        assert podcast.id == "borspodden"
        assert podcast.name == "Börspodden"

        # Verify saved
        loaded = load_podcasts(podcasts_file)
        assert len(loaded) == 1

    @patch("podstock.rss.manager.validate_rss_url")
    def test_add_duplicate_raises_error(self, mock_validate: None, tmp_path: Path) -> None:
        """Should raise ConfigError for duplicate ID."""
        mock_validate.return_value = True
        podcasts_file = tmp_path / "podcasts.json"

        # Add first
        add_podcast("Test", "https://example.com/rss", podcasts_file)

        # Try to add duplicate
        with pytest.raises(ConfigError, match="already exists"):
            add_podcast("Test", "https://example.com/other", podcasts_file)

    @patch("podstock.rss.manager.validate_rss_url")
    def test_add_invalid_url_raises_error(self, mock_validate: None, tmp_path: Path) -> None:
        """Should raise RSSError for invalid URL."""
        mock_validate.return_value = False
        podcasts_file = tmp_path / "podcasts.json"

        with pytest.raises(RSSError, match="Invalid RSS"):
            add_podcast("Test", "https://example.com/invalid", podcasts_file)

    def test_add_skip_validation(self, tmp_path: Path) -> None:
        """Should skip validation when requested."""
        podcasts_file = tmp_path / "podcasts.json"

        podcast = add_podcast(
            name="Test",
            rss_url="https://example.com/rss",
            podcasts_file=podcasts_file,
            validate_url=False,
        )

        assert podcast.id == "test"


class TestRemovePodcast:
    """Tests for remove_podcast function."""

    def test_remove_existing(self, tmp_path: Path) -> None:
        """Should remove existing podcast."""
        podcasts_file = tmp_path / "podcasts.json"
        podcast = Podcast(id="test", name="Test", rss_url="https://example.com/rss")
        save_podcasts([podcast], podcasts_file)

        result = remove_podcast("test", podcasts_file)

        assert result is True
        assert load_podcasts(podcasts_file) == []

    def test_remove_nonexistent(self, tmp_path: Path) -> None:
        """Should return False for nonexistent podcast."""
        podcasts_file = tmp_path / "podcasts.json"
        save_podcasts([], podcasts_file)

        result = remove_podcast("nonexistent", podcasts_file)

        assert result is False


class TestUpdatePodcast:
    """Tests for update_podcast function."""

    def test_update_name(self, tmp_path: Path) -> None:
        """Should update podcast name."""
        podcasts_file = tmp_path / "podcasts.json"
        podcast = Podcast(id="test", name="Old Name", rss_url="https://example.com/rss")
        save_podcasts([podcast], podcasts_file)

        updated = update_podcast("test", podcasts_file, name="New Name")

        assert updated is not None
        assert updated.name == "New Name"

    def test_update_active_status(self, tmp_path: Path) -> None:
        """Should update active status."""
        podcasts_file = tmp_path / "podcasts.json"
        podcast = Podcast(id="test", name="Test", rss_url="https://example.com/rss", active=True)
        save_podcasts([podcast], podcasts_file)

        updated = update_podcast("test", podcasts_file, active=False)

        assert updated is not None
        assert updated.active is False

    def test_update_nonexistent(self, tmp_path: Path) -> None:
        """Should return None for nonexistent podcast."""
        podcasts_file = tmp_path / "podcasts.json"
        save_podcasts([], podcasts_file)

        result = update_podcast("nonexistent", podcasts_file, name="New")

        assert result is None


class TestGetActivePodcasts:
    """Tests for get_active_podcasts function."""

    def test_returns_only_active(self, tmp_path: Path) -> None:
        """Should return only active podcasts."""
        podcasts_file = tmp_path / "podcasts.json"
        active = Podcast(id="active", name="Active", rss_url="https://example.com/rss", active=True)
        inactive = Podcast(
            id="inactive", name="Inactive", rss_url="https://example.com/rss2", active=False
        )
        save_podcasts([active, inactive], podcasts_file)

        result = get_active_podcasts(podcasts_file)

        assert len(result) == 1
        assert result[0].id == "active"
