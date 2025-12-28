"""Tests for transcription module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from podstock.core.exceptions import TranscribeError
from podstock.transcribe.whisper import (
    estimate_duration,
    get_available_models,
    load_transcript,
    save_transcript,
    transcribe,
)


class TestGetAvailableModels:
    """Tests for get_available_models function."""

    def test_returns_model_list(self) -> None:
        """Returns list of model names."""
        models = get_available_models()

        assert isinstance(models, list)
        assert "large-v3" in models
        assert "tiny" in models

    def test_returns_copy(self) -> None:
        """Returns a copy, not the original list."""
        models = get_available_models()
        models.append("test")

        assert "test" not in get_available_models()


class TestEstimateDuration:
    """Tests for estimate_duration function."""

    def test_estimate_missing_file(self, tmp_path: Path) -> None:
        """Returns None for missing file."""
        audio_file = tmp_path / "missing.mp3"

        duration = estimate_duration(audio_file)

        assert duration is None

    def test_estimate_from_file_size(self, tmp_path: Path) -> None:
        """Estimates duration from file size."""
        # Create a 1MB file (approximately 1 minute at 128kbps)
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"x" * (1024 * 1024))

        duration = estimate_duration(audio_file)

        # 1MB at 16KB/s = ~64 seconds
        assert duration is not None
        assert 60 <= duration <= 70


class TestSaveTranscript:
    """Tests for save_transcript function."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """Creates transcript file."""
        result = save_transcript(
            episode_id="bp-2024-12-18",
            text="This is a test transcript.",
            transcript_dir=tmp_path,
            podcast_id="bp",
        )

        assert result.exists()
        assert result.name == "bp-2024-12-18.txt"
        content = result.read_text(encoding="utf-8")
        assert "This is a test transcript." in content

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        """Creates podcast subdirectory."""
        result = save_transcript(
            episode_id="bp-2024-12-18",
            text="Test",
            transcript_dir=tmp_path,
            podcast_id="new-podcast",
        )

        assert (tmp_path / "new-podcast").is_dir()
        assert result == tmp_path / "new-podcast" / "bp-2024-12-18.txt"

    def test_save_includes_header(self, tmp_path: Path) -> None:
        """Includes header with episode info."""
        result = save_transcript(
            episode_id="bp-2024-12-18",
            text="Test transcript.",
            transcript_dir=tmp_path,
            podcast_id="bp",
        )

        content = result.read_text(encoding="utf-8")
        assert "Episode: bp-2024-12-18" in content
        assert "Podcast: bp" in content

    def test_save_with_metadata(self, tmp_path: Path) -> None:
        """Includes metadata in header."""
        result = save_transcript(
            episode_id="bp-2024-12-18",
            text="Test transcript.",
            transcript_dir=tmp_path,
            podcast_id="bp",
            metadata={"model": "large-v3", "duration": "60s"},
        )

        content = result.read_text(encoding="utf-8")
        assert "model: large-v3" in content
        assert "duration: 60s" in content


class TestLoadTranscript:
    """Tests for load_transcript function."""

    def test_load_existing(self, tmp_path: Path) -> None:
        """Loads existing transcript, stripping header."""
        # First save a transcript
        save_transcript(
            episode_id="bp-2024-12-18",
            text="Hello world.",
            transcript_dir=tmp_path,
            podcast_id="bp",
        )

        result = load_transcript("bp-2024-12-18", tmp_path, "bp")

        assert result == "Hello world."

    def test_load_missing_raises_error(self, tmp_path: Path) -> None:
        """Raises error for missing file."""
        with pytest.raises(TranscribeError, match="not found"):
            load_transcript("missing-ep", tmp_path, "bp")


class TestTranscribe:
    """Tests for transcribe function."""

    def test_transcribe_calls_mlx_whisper(self, tmp_path: Path) -> None:
        """Calls mlx_whisper.transcribe with correct arguments."""
        import sys

        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"fake audio data")

        mock_mlx = MagicMock()
        mock_mlx.transcribe.return_value = {"text": "Hello world."}
        sys.modules["mlx_whisper"] = mock_mlx

        try:
            result = transcribe(audio_file)

            mock_mlx.transcribe.assert_called_once()
            assert result == "Hello world."
        finally:
            del sys.modules["mlx_whisper"]

    def test_transcribe_with_model(self, tmp_path: Path) -> None:
        """Passes model parameter."""
        import sys

        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"fake audio data")

        mock_mlx = MagicMock()
        mock_mlx.transcribe.return_value = {"text": "Test."}
        sys.modules["mlx_whisper"] = mock_mlx

        try:
            transcribe(audio_file, model="large-v3")

            call_args = mock_mlx.transcribe.call_args
            assert "mlx-community/whisper-large-v3-mlx" in call_args.kwargs.get(
                "path_or_hf_repo", ""
            )
        finally:
            del sys.modules["mlx_whisper"]

    def test_transcribe_missing_file_raises_error(self, tmp_path: Path) -> None:
        """Raises error for missing audio file."""
        audio_file = tmp_path / "missing.mp3"

        with pytest.raises(TranscribeError, match="not found"):
            transcribe(audio_file)

    def test_transcribe_unknown_model_raises_error(self, tmp_path: Path) -> None:
        """Raises error for unknown model."""
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"fake audio data")

        with pytest.raises(TranscribeError, match="Unknown model"):
            transcribe(audio_file, model="not-a-model")

    def test_transcribe_with_progress_callback(self, tmp_path: Path) -> None:
        """Calls progress callback during transcription."""
        import sys

        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"fake audio data")

        mock_mlx = MagicMock()
        mock_mlx.transcribe.return_value = {"text": "Test."}
        sys.modules["mlx_whisper"] = mock_mlx

        messages: list[str] = []

        def callback(msg: str) -> None:
            messages.append(msg)

        try:
            transcribe(audio_file, progress_callback=callback)

            assert len(messages) >= 1
            assert any("Loading" in msg or "Transcribing" in msg for msg in messages)
        finally:
            del sys.modules["mlx_whisper"]

    def test_transcribe_empty_result_raises_error(self, tmp_path: Path) -> None:
        """Raises error when transcription returns empty."""
        import sys

        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"fake audio data")

        mock_mlx = MagicMock()
        mock_mlx.transcribe.return_value = {"text": ""}
        sys.modules["mlx_whisper"] = mock_mlx

        try:
            with pytest.raises(TranscribeError, match="empty"):
                transcribe(audio_file)
        finally:
            del sys.modules["mlx_whisper"]
