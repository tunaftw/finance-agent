"""Tests for podstock.core.config module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from podstock.core.config import Config, load_config, save_config
from podstock.core.exceptions import ConfigError


class TestConfig:
    """Tests for Config dataclass."""

    def test_default_values(self, tmp_path: Path) -> None:
        """Should have sensible defaults."""
        config = Config(data_dir=tmp_path)

        assert config.whisper_model == "large-v3"
        assert config.audio_format == "mp3"
        assert config.default_time_horizon == "6m"
        assert config.download_timeout == 300
        assert config.retry_attempts == 3

    def test_directory_properties(self, tmp_path: Path) -> None:
        """Should compute directory paths correctly."""
        config = Config(data_dir=tmp_path)

        assert config.audio_dir == tmp_path / "audio"
        assert config.transcripts_dir == tmp_path / "transcripts"
        assert config.recommendations_dir == tmp_path / "recommendations"
        assert config.reports_dir == tmp_path / "reports"
        assert config.config_file == tmp_path / "config.json"
        assert config.state_file == tmp_path / "state.json"
        assert config.podcasts_file == tmp_path / "podcasts.json"

    def test_ensure_directories(self, tmp_path: Path) -> None:
        """Should create all required directories."""
        config = Config(data_dir=tmp_path)
        config.ensure_directories()

        assert config.audio_dir.exists()
        assert config.transcripts_dir.exists()
        assert config.recommendations_dir.exists()
        assert config.reports_dir.exists()


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_missing_config_returns_defaults(self, tmp_path: Path) -> None:
        """Should return defaults when config file doesn't exist."""
        config = load_config(data_dir=tmp_path)

        assert config.whisper_model == "large-v3"
        assert config.data_dir == tmp_path

    def test_load_existing_config(self, tmp_path: Path) -> None:
        """Should load values from existing config file."""
        config_data = {
            "version": 1,
            "whisper_model": "small",
            "download_timeout": 600,
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config_data))

        config = load_config(config_path=config_path, data_dir=tmp_path)

        assert config.whisper_model == "small"
        assert config.download_timeout == 600
        # Defaults for missing keys
        assert config.audio_format == "mp3"

    def test_load_invalid_json_raises_config_error(self, tmp_path: Path) -> None:
        """Should raise ConfigError for invalid JSON."""
        config_path = tmp_path / "config.json"
        config_path.write_text("not valid json {{{")

        with pytest.raises(ConfigError, match="Invalid JSON"):
            load_config(config_path=config_path, data_dir=tmp_path)

    def test_data_dir_override(self, tmp_path: Path) -> None:
        """Should use provided data_dir even if config specifies different."""
        config_data = {
            "data_dir": "/some/other/path",
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config_data))

        config = load_config(config_path=config_path, data_dir=tmp_path)

        assert config.data_dir == tmp_path


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """Should create config file."""
        config = Config(data_dir=tmp_path)
        save_config(config)

        assert config.config_file.exists()

    def test_save_writes_valid_json(self, tmp_path: Path) -> None:
        """Should write valid JSON."""
        config = Config(
            data_dir=tmp_path,
            whisper_model="medium",
            download_timeout=120,
        )
        save_config(config)

        data = json.loads(config.config_file.read_text())
        assert data["whisper_model"] == "medium"
        assert data["download_timeout"] == 120

    def test_save_is_atomic(self, tmp_path: Path) -> None:
        """Should not leave partial files on error."""
        config = Config(data_dir=tmp_path)
        save_config(config)

        # Verify no temp file left behind
        temp_path = config.config_file.with_suffix(".tmp")
        assert not temp_path.exists()

    def test_roundtrip(self, tmp_path: Path) -> None:
        """Should preserve values through save/load cycle."""
        original = Config(
            data_dir=tmp_path,
            whisper_model="tiny",
            audio_format="m4a",
            default_time_horizon="12m",
            download_timeout=180,
            retry_attempts=5,
        )
        save_config(original)

        loaded = load_config(data_dir=tmp_path)

        assert loaded.whisper_model == original.whisper_model
        assert loaded.audio_format == original.audio_format
        assert loaded.default_time_horizon == original.default_time_horizon
        assert loaded.download_timeout == original.download_timeout
        assert loaded.retry_attempts == original.retry_attempts
