"""Tests for podstock.rss.downloader module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from podstock.core.exceptions import DownloadError
from podstock.core.models import Episode
from podstock.rss.downloader import (
    _get_filename_from_episode,
    download_episode,
    verify_download,
)


@pytest.fixture
def sample_episode() -> Episode:
    """Create a sample episode for testing."""
    return Episode(
        id="bp-2024-12-18-a1b2",
        podcast_id="borspodden",
        title="Avsnitt 598 - Julspecial",
        published_at=datetime(2024, 12, 18),
        audio_url="https://example.com/bp-598.mp3",
        duration_seconds=4530,
    )


class TestGetFilenameFromEpisode:
    """Tests for _get_filename_from_episode helper."""

    def test_generates_filename_with_extension(self, sample_episode: Episode) -> None:
        """Should generate filename with correct extension."""
        filename = _get_filename_from_episode(sample_episode)
        assert filename == "bp-2024-12-18-a1b2.mp3"

    def test_handles_url_with_query_params(self) -> None:
        """Should ignore query params in URL."""
        episode = Episode(
            id="test",
            podcast_id="test",
            title="Test",
            published_at=datetime.now(),
            audio_url="https://example.com/audio.mp3?token=abc123",
        )
        filename = _get_filename_from_episode(episode)
        assert filename == "test.mp3"

    def test_default_extension(self) -> None:
        """Should use .mp3 as default extension."""
        episode = Episode(
            id="test",
            podcast_id="test",
            title="Test",
            published_at=datetime.now(),
            audio_url="https://example.com/audio",
        )
        filename = _get_filename_from_episode(episode)
        assert filename == "test.mp3"


class TestVerifyDownload:
    """Tests for verify_download function."""

    def test_verify_existing_file(self, tmp_path: Path) -> None:
        """Should return True for existing file."""
        test_file = tmp_path / "test.mp3"
        test_file.write_bytes(b"test content")

        assert verify_download(test_file) is True

    def test_verify_missing_file(self, tmp_path: Path) -> None:
        """Should return False for missing file."""
        assert verify_download(tmp_path / "missing.mp3") is False

    def test_verify_with_expected_size(self, tmp_path: Path) -> None:
        """Should check file size if provided."""
        test_file = tmp_path / "test.mp3"
        content = b"test content"
        test_file.write_bytes(content)

        assert verify_download(test_file, expected_size=len(content)) is True
        assert verify_download(test_file, expected_size=len(content) + 100) is False

    def test_verify_empty_file(self, tmp_path: Path) -> None:
        """Should return False for empty file."""
        test_file = tmp_path / "empty.mp3"
        test_file.touch()

        assert verify_download(test_file) is False


class TestDownloadEpisode:
    """Tests for download_episode function."""

    @patch("podstock.rss.downloader.requests.get")
    def test_download_success(
        self, mock_get: MagicMock, tmp_path: Path, sample_episode: Episode
    ) -> None:
        """Should download file successfully."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Length": "100"}
        mock_response.iter_content = MagicMock(return_value=[b"x" * 100])
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        dest_dir = tmp_path / "audio"
        path = download_episode(
            sample_episode, dest_dir, show_progress=False, retry_attempts=1
        )

        assert path.exists()
        assert path.name == "bp-2024-12-18-a1b2.mp3"
        assert path.stat().st_size == 100

    @patch("podstock.rss.downloader.requests.get")
    def test_download_creates_directory(
        self, mock_get: MagicMock, tmp_path: Path, sample_episode: Episode
    ) -> None:
        """Should create destination directory if missing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Length": "50"}
        mock_response.iter_content = MagicMock(return_value=[b"x" * 50])
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        dest_dir = tmp_path / "new" / "nested" / "dir"
        path = download_episode(
            sample_episode, dest_dir, show_progress=False, retry_attempts=1
        )

        assert dest_dir.exists()
        assert path.exists()

    @patch("podstock.rss.downloader.requests.get")
    def test_download_retries_on_failure(
        self, mock_get: MagicMock, tmp_path: Path, sample_episode: Episode
    ) -> None:
        """Should retry on failure."""
        import requests

        # First call fails, second succeeds
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.headers = {"Content-Length": "50"}
        mock_success.iter_content = MagicMock(return_value=[b"x" * 50])
        mock_success.raise_for_status = MagicMock()

        mock_get.side_effect = [requests.RequestException("Network error"), mock_success]

        dest_dir = tmp_path / "audio"
        path = download_episode(
            sample_episode, dest_dir, show_progress=False, retry_attempts=2
        )

        assert path.exists()
        assert mock_get.call_count == 2

    @patch("podstock.rss.downloader.requests.get")
    @patch("podstock.rss.downloader.DEFAULT_RETRY_DELAY", 0)  # Skip delay in tests
    def test_download_fails_after_retries(
        self, mock_get: MagicMock, tmp_path: Path, sample_episode: Episode
    ) -> None:
        """Should raise DownloadError after all retries fail."""
        import requests

        mock_get.side_effect = requests.RequestException("Network error")

        dest_dir = tmp_path / "audio"
        with pytest.raises(DownloadError, match="Failed to download"):
            download_episode(sample_episode, dest_dir, show_progress=False, retry_attempts=2)

    @patch("podstock.rss.downloader.requests.get")
    def test_download_with_progress_callback(
        self, mock_get: MagicMock, tmp_path: Path, sample_episode: Episode
    ) -> None:
        """Should call progress callback during download."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Length": "100"}
        mock_response.iter_content = MagicMock(return_value=[b"x" * 50, b"x" * 50])
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        progress_calls = []

        def callback(downloaded: int, total: int) -> None:
            progress_calls.append((downloaded, total))

        dest_dir = tmp_path / "audio"
        download_episode(
            sample_episode,
            dest_dir,
            show_progress=False,
            progress_callback=callback,
            retry_attempts=1,
        )

        assert len(progress_calls) == 2
        assert progress_calls[-1][0] == 100  # Final downloaded amount
