"""Transcription module for PodStock.

This module provides audio transcription using mlx-whisper,
optimized for Apple Silicon.
"""

from __future__ import annotations

from podstock.transcribe.whisper import (
    DEFAULT_MODEL,
    WHISPER_MODELS,
    estimate_duration,
    get_available_models,
    load_transcript,
    save_transcript,
    transcribe,
)

__all__ = [
    "DEFAULT_MODEL",
    "WHISPER_MODELS",
    "estimate_duration",
    "get_available_models",
    "load_transcript",
    "save_transcript",
    "transcribe",
]
