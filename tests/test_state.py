"""Tests for podstock.core.state module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from podstock.core.exceptions import StateError
from podstock.core.state import State, load_state


class TestState:
    """Tests for State class."""

    def test_empty_state(self, tmp_path: Path) -> None:
        """Should start with empty state when file doesn't exist."""
        state_file = tmp_path / "state.json"
        state = State(state_file)

        assert state.get_all_episodes() == {}

    def test_is_downloaded_false_by_default(self, tmp_path: Path) -> None:
        """Should return False for unknown episodes."""
        state_file = tmp_path / "state.json"
        state = State(state_file)

        assert state.is_downloaded("unknown-episode") is False

    def test_is_transcribed_false_by_default(self, tmp_path: Path) -> None:
        """Should return False for unknown episodes."""
        state_file = tmp_path / "state.json"
        state = State(state_file)

        assert state.is_transcribed("unknown-episode") is False

    def test_is_analyzed_false_by_default(self, tmp_path: Path) -> None:
        """Should return False for unknown episodes."""
        state_file = tmp_path / "state.json"
        state = State(state_file)

        assert state.is_analyzed("unknown-episode") is False


class TestStateMarkDownloaded:
    """Tests for mark_downloaded method."""

    def test_mark_downloaded(self, tmp_path: Path) -> None:
        """Should mark episode as downloaded."""
        state_file = tmp_path / "state.json"
        state = State(state_file)
        audio_path = tmp_path / "audio" / "test.mp3"

        state.mark_downloaded("test-episode", audio_path)

        assert state.is_downloaded("test-episode") is True
        assert state.get_audio_path("test-episode") == audio_path

    def test_mark_downloaded_persists(self, tmp_path: Path) -> None:
        """Should persist downloaded status to file."""
        state_file = tmp_path / "state.json"
        state = State(state_file)
        audio_path = tmp_path / "audio" / "test.mp3"

        state.mark_downloaded("test-episode", audio_path)

        # Load fresh state
        new_state = State(state_file)
        assert new_state.is_downloaded("test-episode") is True


class TestStateMarkTranscribed:
    """Tests for mark_transcribed method."""

    def test_mark_transcribed(self, tmp_path: Path) -> None:
        """Should mark episode as transcribed."""
        state_file = tmp_path / "state.json"
        state = State(state_file)
        transcript_path = tmp_path / "transcripts" / "test.txt"

        state.mark_transcribed("test-episode", transcript_path)

        assert state.is_transcribed("test-episode") is True
        assert state.get_transcript_path("test-episode") == transcript_path


class TestStateMarkAnalyzed:
    """Tests for mark_analyzed method."""

    def test_mark_analyzed(self, tmp_path: Path) -> None:
        """Should mark episode as analyzed."""
        state_file = tmp_path / "state.json"
        state = State(state_file)

        state.mark_analyzed("test-episode", recommendations_count=3)

        assert state.is_analyzed("test-episode") is True
        status = state.get_status("test-episode")
        assert status is not None
        assert status.recommendations_count == 3


class TestStatePendingQueries:
    """Tests for pending episode queries."""

    def test_get_pending_transcription(self, tmp_path: Path) -> None:
        """Should return downloaded but not transcribed episodes."""
        state_file = tmp_path / "state.json"
        state = State(state_file)

        # Episode 1: downloaded only
        state.mark_downloaded("ep1", tmp_path / "ep1.mp3")
        # Episode 2: downloaded and transcribed
        state.mark_downloaded("ep2", tmp_path / "ep2.mp3")
        state.mark_transcribed("ep2", tmp_path / "ep2.txt")

        pending = state.get_pending_transcription()

        assert "ep1" in pending
        assert "ep2" not in pending

    def test_get_pending_analysis(self, tmp_path: Path) -> None:
        """Should return transcribed but not analyzed episodes."""
        state_file = tmp_path / "state.json"
        state = State(state_file)

        # Episode 1: transcribed only
        state.mark_downloaded("ep1", tmp_path / "ep1.mp3")
        state.mark_transcribed("ep1", tmp_path / "ep1.txt")
        # Episode 2: fully processed
        state.mark_downloaded("ep2", tmp_path / "ep2.mp3")
        state.mark_transcribed("ep2", tmp_path / "ep2.txt")
        state.mark_analyzed("ep2", 2)

        pending = state.get_pending_analysis()

        assert "ep1" in pending
        assert "ep2" not in pending


class TestStateLoadExisting:
    """Tests for loading existing state files."""

    def test_load_existing_state(self, tmp_path: Path) -> None:
        """Should load existing state from file."""
        state_file = tmp_path / "state.json"
        state_data = {
            "version": 1,
            "last_updated": "2024-12-18T10:00:00",
            "episodes": {
                "test-ep": {
                    "downloaded": True,
                    "downloaded_at": "2024-12-18T10:00:00",
                    "audio_path": "/path/to/audio.mp3",
                    "transcribed": False,
                    "analyzed": False,
                    "recommendations_count": 0,
                }
            },
        }
        state_file.write_text(json.dumps(state_data))

        state = State(state_file)

        assert state.is_downloaded("test-ep") is True
        assert state.is_transcribed("test-ep") is False

    def test_load_invalid_json_raises_error(self, tmp_path: Path) -> None:
        """Should raise StateError for invalid JSON."""
        state_file = tmp_path / "state.json"
        state_file.write_text("not valid json")

        with pytest.raises(StateError, match="Invalid JSON"):
            State(state_file)


class TestLoadState:
    """Tests for load_state convenience function."""

    def test_load_state_creates_state(self, tmp_path: Path) -> None:
        """Should create State instance."""
        state_file = tmp_path / "state.json"
        state = load_state(state_file)

        assert isinstance(state, State)
        assert state.state_file == state_file
