"""Whisper transcription for PodStock.

This module handles audio transcription using mlx-whisper,
optimized for Apple Silicon (M1/M2/M3/M4).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from podstock.core.exceptions import TranscribeError

# Available Whisper models (smallest to largest)
WHISPER_MODELS = [
    "tiny",
    "base",
    "small",
    "medium",
    "large",
    "large-v2",
    "large-v3",
]

DEFAULT_MODEL = "large-v3"


def get_available_models() -> list[str]:
    """Get list of available Whisper models.

    Returns:
        List of model names from smallest to largest.

    Example:
        >>> models = get_available_models()
        >>> "large-v3" in models
        True
    """
    return WHISPER_MODELS.copy()


def transcribe(
    audio_path: Path,
    model: str = DEFAULT_MODEL,
    *,
    language: str = "sv",
    progress_callback: Callable[[str], None] | None = None,
) -> str:
    """Transcribe audio file using mlx-whisper.

    Args:
        audio_path: Path to audio file (mp3, m4a, wav, etc.).
        model: Whisper model to use.
        language: Language code (default: Swedish).
        progress_callback: Optional callback for status updates.

    Returns:
        Transcribed text.

    Raises:
        TranscribeError: If transcription fails.

    Example:
        >>> text = transcribe(Path("episode.mp3"))
        >>> len(text) > 0
        True
    """
    if not audio_path.exists():
        raise TranscribeError(f"Audio file not found: {audio_path}")

    if model not in WHISPER_MODELS:
        raise TranscribeError(f"Unknown model: {model}. Available: {WHISPER_MODELS}")

    try:
        import mlx_whisper
    except ImportError as e:
        raise TranscribeError(
            "mlx-whisper not installed. Install with: pip install mlx-whisper"
        ) from e

    if progress_callback:
        progress_callback(f"Loading model {model}...")

    try:
        # mlx-whisper uses HuggingFace model IDs
        model_id = f"mlx-community/whisper-{model}-mlx"

        if progress_callback:
            progress_callback(f"Transcribing {audio_path.name}...")

        result = mlx_whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=model_id,
            language=language,
            verbose=False,
        )

        text = result.get("text", "")

        if not text:
            raise TranscribeError("Transcription returned empty result")

        return text.strip()

    except Exception as e:
        if "mlx" in str(type(e).__module__).lower():
            raise TranscribeError(f"MLX transcription error: {e}") from e
        raise TranscribeError(f"Transcription failed: {e}") from e


def save_transcript(
    episode_id: str,
    text: str,
    transcript_dir: Path,
    podcast_id: str,
    *,
    metadata: dict[str, str] | None = None,
) -> Path:
    """Save transcript to file with metadata header.

    Args:
        episode_id: Episode identifier.
        text: Transcribed text.
        transcript_dir: Base directory for transcripts.
        podcast_id: Podcast identifier.
        metadata: Optional metadata to include in header.

    Returns:
        Path to saved transcript file.

    Example:
        >>> path = save_transcript("bp-2024-12-18", "Hello...", Path("transcripts"), "borspodden")
        >>> path.exists()
        True
    """
    # Create podcast subdirectory
    podcast_dir = transcript_dir / podcast_id
    podcast_dir.mkdir(parents=True, exist_ok=True)

    transcript_path = podcast_dir / f"{episode_id}.txt"

    # Build header
    header_lines = [
        "=" * 60,
        f"Episode: {episode_id}",
        f"Podcast: {podcast_id}",
    ]

    if metadata:
        for key, value in metadata.items():
            header_lines.append(f"{key}: {value}")

    header_lines.append("=" * 60)
    header_lines.append("")

    header = "\n".join(header_lines)

    # Write atomically
    temp_path = transcript_path.with_suffix(".tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(header)
            f.write(text)
            f.write("\n")

        temp_path.replace(transcript_path)
    except OSError as e:
        if temp_path.exists():
            temp_path.unlink()
        raise TranscribeError(f"Failed to save transcript: {e}") from e

    return transcript_path


def load_transcript(episode_id: str, transcript_dir: Path, podcast_id: str) -> str:
    """Load transcript from file.

    Args:
        episode_id: Episode identifier.
        transcript_dir: Base directory for transcripts.
        podcast_id: Podcast identifier.

    Returns:
        Transcript text (without header).

    Raises:
        TranscribeError: If file not found or read fails.

    Example:
        >>> text = load_transcript("bp-2024-12-18", Path("transcripts"), "borspodden")
        >>> len(text) > 0
        True
    """
    transcript_path = transcript_dir / podcast_id / f"{episode_id}.txt"

    if not transcript_path.exists():
        raise TranscribeError(f"Transcript not found: {transcript_path}")

    try:
        content = transcript_path.read_text(encoding="utf-8")
    except OSError as e:
        raise TranscribeError(f"Failed to read transcript: {e}") from e

    # Skip header (everything before double newline after header markers)
    lines = content.split("\n")
    text_start = 0

    # Find end of header (line after second "====")
    header_count = 0
    for i, line in enumerate(lines):
        if line.startswith("===="):
            header_count += 1
            if header_count == 2:
                text_start = i + 1
                break

    # Skip empty lines after header
    while text_start < len(lines) and not lines[text_start].strip():
        text_start += 1

    return "\n".join(lines[text_start:]).strip()


def estimate_duration(audio_path: Path) -> int | None:
    """Estimate audio duration in seconds.

    Uses file size heuristics if metadata unavailable.

    Args:
        audio_path: Path to audio file.

    Returns:
        Estimated duration in seconds, or None if unable to estimate.

    Example:
        >>> duration = estimate_duration(Path("episode.mp3"))
        >>> duration > 0
        True
    """
    if not audio_path.exists():
        return None

    # Try to get actual duration via mutagen if available
    try:
        from mutagen import File as MutagenFile

        audio = MutagenFile(audio_path)
        if audio and audio.info:
            return int(audio.info.length)
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback: estimate from file size
    # Typical podcast MP3: ~128kbps = 16KB/s
    file_size = audio_path.stat().st_size
    estimated_seconds = file_size / (16 * 1024)

    return int(estimated_seconds)
