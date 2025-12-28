"""Prompt building for Claude analysis.

This module generates prompts for analyzing podcast transcripts
to extract stock recommendations.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from podstock.core.exceptions import AnalysisError

# Default prompt template path
DEFAULT_TEMPLATE_PATH = Path(__file__).parent.parent.parent.parent / "prompts" / "analyze_transcript.md"


def load_template(template_path: Path | None = None) -> str:
    """Load prompt template from file.

    Args:
        template_path: Path to template file. Uses default if None.

    Returns:
        Template string.

    Raises:
        AnalysisError: If template file not found.
    """
    if template_path is None:
        template_path = DEFAULT_TEMPLATE_PATH

    if not template_path.exists():
        raise AnalysisError(f"Prompt template not found: {template_path}")

    try:
        return template_path.read_text(encoding="utf-8")
    except OSError as e:
        raise AnalysisError(f"Failed to read template: {e}") from e


def build_analysis_prompt(
    transcript: str,
    podcast_name: str,
    episode_title: str,
    episode_date: datetime | str,
    hosts: list[str] | None = None,
    *,
    template_path: Path | None = None,
    max_transcript_length: int = 100000,
) -> str:
    """Build a prompt for Claude to analyze a transcript.

    Args:
        transcript: The episode transcript text.
        podcast_name: Name of the podcast.
        episode_title: Title of the episode.
        episode_date: Publication date.
        hosts: List of host names.
        template_path: Custom template path (optional).
        max_transcript_length: Maximum transcript length before truncation.

    Returns:
        Complete prompt string ready for Claude.

    Raises:
        AnalysisError: If template loading fails.

    Example:
        >>> prompt = build_analysis_prompt(
        ...     transcript="Hej och välkommen...",
        ...     podcast_name="Börspodden",
        ...     episode_title="Avsnitt 598",
        ...     episode_date="2024-12-18",
        ...     hosts=["Johan", "John"]
        ... )
        >>> "Börspodden" in prompt
        True
    """
    template = load_template(template_path)

    # Format date
    if isinstance(episode_date, datetime):
        date_str = episode_date.strftime("%Y-%m-%d")
    else:
        date_str = str(episode_date)

    # Format hosts
    hosts_str = ", ".join(hosts) if hosts else "Okänd"

    # Truncate transcript if too long
    if len(transcript) > max_transcript_length:
        transcript = transcript[:max_transcript_length] + "\n\n[TRANSCRIPT TRUNCATED]"

    # Replace placeholders
    prompt = template.replace("{{PODCAST_NAME}}", podcast_name)
    prompt = prompt.replace("{{EPISODE_TITLE}}", episode_title)
    prompt = prompt.replace("{{EPISODE_DATE}}", date_str)
    prompt = prompt.replace("{{HOSTS}}", hosts_str)
    prompt = prompt.replace("{{TRANSCRIPT}}", transcript)
    prompt = prompt.replace("{{ISO_TIMESTAMP}}", datetime.now().isoformat())

    return prompt


def chunk_transcript(
    transcript: str,
    chunk_size: int = 50000,
    overlap: int = 1000,
) -> list[str]:
    """Split a long transcript into overlapping chunks.

    Useful for very long episodes that exceed token limits.

    Args:
        transcript: Full transcript text.
        chunk_size: Maximum characters per chunk.
        overlap: Number of characters to overlap between chunks.

    Returns:
        List of transcript chunks.

    Example:
        >>> chunks = chunk_transcript("A" * 100000, chunk_size=50000)
        >>> len(chunks) == 2
        True
    """
    if len(transcript) <= chunk_size:
        return [transcript]

    chunks = []
    start = 0

    while start < len(transcript):
        end = start + chunk_size

        # Try to find a good break point (sentence end)
        if end < len(transcript):
            # Look for sentence end within last 500 chars
            search_start = max(end - 500, start)
            for marker in [". ", "! ", "? ", "\n\n"]:
                pos = transcript.rfind(marker, search_start, end)
                if pos > search_start:
                    end = pos + len(marker)
                    break

        chunk = transcript[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start, accounting for overlap
        start = end - overlap

    return chunks


def build_summary_prompt(
    partial_results: list[str],
    podcast_name: str,
    episode_title: str,
) -> str:
    """Build a prompt to summarize partial analysis results.

    Used when a transcript was analyzed in chunks.

    Args:
        partial_results: List of partial analysis JSON strings.
        podcast_name: Name of the podcast.
        episode_title: Title of the episode.

    Returns:
        Prompt for summarizing/deduplicating results.
    """
    results_text = "\n\n---\n\n".join(partial_results)

    return f"""Du har analyserat ett långt podcast-avsnitt i flera delar.
Nedan finns resultaten från varje del. Sammanfatta och deduplicera till ett slutgiltigt resultat.

**Podcast:** {podcast_name}
**Episode:** {episode_title}

## Partiella resultat

{results_text}

## Instruktioner

1. Ta bort duplicerade rekommendationer (samma bolag nämnt flera gånger)
2. Behåll den mest kompletta versionen av varje rekommendation
3. Returnera ett slutgiltigt JSON-objekt i samma format som input
4. Om samma bolag rekommenderas flera gånger, slå ihop informationen

Returnera endast JSON, inget annat.
"""
