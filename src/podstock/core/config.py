"""Configuration management for PodStock.

This module handles loading, saving, and accessing application configuration.
Configuration is stored in data/config.json.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from podstock.core.exceptions import ConfigError


@dataclass
class Config:
    """Application configuration.

    Attributes:
        data_dir: Base directory for all data files.
        whisper_model: Whisper model to use for transcription.
        audio_format: Preferred audio format for downloads.
        default_time_horizon: Default investment time horizon.
        download_timeout: Timeout for downloads in seconds.
        retry_attempts: Number of retry attempts for network operations.

    Example:
        >>> config = Config(data_dir=Path("data"))
        >>> config.audio_dir
        PosixPath('data/audio')
    """

    data_dir: Path
    whisper_model: str = "large-v3"
    audio_format: str = "mp3"
    default_time_horizon: str = "6m"
    download_timeout: int = 300
    retry_attempts: int = 3

    @property
    def audio_dir(self) -> Path:
        """Directory for downloaded audio files."""
        return self.data_dir / "audio"

    @property
    def transcripts_dir(self) -> Path:
        """Directory for transcript files."""
        return self.data_dir / "transcripts"

    @property
    def recommendations_dir(self) -> Path:
        """Directory for recommendation JSON files."""
        return self.data_dir / "recommendations"

    @property
    def reports_dir(self) -> Path:
        """Directory for generated reports."""
        return self.data_dir / "reports"

    @property
    def config_file(self) -> Path:
        """Path to config.json."""
        return self.data_dir / "config.json"

    @property
    def state_file(self) -> Path:
        """Path to state.json."""
        return self.data_dir / "state.json"

    @property
    def podcasts_file(self) -> Path:
        """Path to podcasts.json."""
        return self.data_dir / "podcasts.json"

    def ensure_directories(self) -> None:
        """Create all required directories if they don't exist."""
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)
        self.recommendations_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)


# Default configuration values
DEFAULT_CONFIG: dict[str, Any] = {
    "version": 1,
    "data_dir": "data",
    "whisper_model": "large-v3",
    "audio_format": "mp3",
    "default_time_horizon": "6m",
    "download_timeout": 300,
    "retry_attempts": 3,
}


def load_config(config_path: Path | None = None, data_dir: Path | None = None) -> Config:
    """Load configuration from file or create default.

    Args:
        config_path: Path to config.json. If None, uses data_dir/config.json.
        data_dir: Base data directory. Defaults to 'data' in current directory.

    Returns:
        Loaded configuration.

    Raises:
        ConfigError: If config file exists but is invalid.

    Example:
        >>> config = load_config(data_dir=Path("data"))
        >>> config.whisper_model
        'large-v3'
    """
    if data_dir is None:
        data_dir = Path("data")

    if config_path is None:
        config_path = data_dir / "config.json"

    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in config file: {e}") from e
        except OSError as e:
            raise ConfigError(f"Failed to read config file: {e}") from e

        # Merge with defaults for any missing keys
        merged = {**DEFAULT_CONFIG, **data}
    else:
        merged = DEFAULT_CONFIG.copy()

    # Override data_dir if explicitly provided
    if data_dir is not None:
        merged["data_dir"] = str(data_dir)

    return Config(
        data_dir=Path(merged["data_dir"]),
        whisper_model=merged.get("whisper_model", DEFAULT_CONFIG["whisper_model"]),
        audio_format=merged.get("audio_format", DEFAULT_CONFIG["audio_format"]),
        default_time_horizon=merged.get(
            "default_time_horizon", DEFAULT_CONFIG["default_time_horizon"]
        ),
        download_timeout=merged.get("download_timeout", DEFAULT_CONFIG["download_timeout"]),
        retry_attempts=merged.get("retry_attempts", DEFAULT_CONFIG["retry_attempts"]),
    )


def save_config(config: Config) -> None:
    """Save configuration to file.

    Performs atomic write (write to temp file, then rename).

    Args:
        config: Configuration to save.

    Raises:
        ConfigError: If save fails.

    Example:
        >>> config = Config(data_dir=Path("data"))
        >>> save_config(config)
    """
    config_path = config.config_file
    temp_path = config_path.with_suffix(".tmp")

    data = {
        "version": 1,
        "data_dir": str(config.data_dir),
        "whisper_model": config.whisper_model,
        "audio_format": config.audio_format,
        "default_time_horizon": config.default_time_horizon,
        "download_timeout": config.download_timeout,
        "retry_attempts": config.retry_attempts,
    }

    try:
        # Ensure parent directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file first
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

        # Atomic rename
        temp_path.replace(config_path)

    except OSError as e:
        # Clean up temp file if it exists
        if temp_path.exists():
            temp_path.unlink()
        raise ConfigError(f"Failed to save config: {e}") from e
