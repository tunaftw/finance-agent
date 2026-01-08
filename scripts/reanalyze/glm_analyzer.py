"""
GLM Analyzer wrapper för podcast re-analys.

Importerar och återanvänder logik från glm_driver.py.
"""

import json
import sys
from pathlib import Path
from typing import Optional

# Lägg till scripts-mappen i path för import
sys.path.insert(0, str(Path(__file__).parent.parent))

from glm_driver import (
    analyze_transcript as _analyze_transcript,
    save_analysis as _save_analysis,
    validate_analysis,
    parse_opencode_output,
    extract_json_from_response
)


def analyze_transcript(
    transcript_path: Path,
    max_retries: int = 3,
    timeout: int = 600  # 10 min - GLM-4.7 med stora transkript
) -> tuple[Optional[dict], bool, str]:
    """
    Analysera ett transkript med GLM-4.7.

    Wrapper runt glm_driver.analyze_transcript.

    Returns:
        (analysis_data, success, error_message)
    """
    return _analyze_transcript(transcript_path, max_retries, timeout)


def save_analysis(analysis: dict, output_dir: Path) -> Path:
    """
    Spara analys till JSON-fil.

    Wrapper runt glm_driver.save_analysis.
    """
    return _save_analysis(analysis, output_dir)


def count_words(transcript_path: Path) -> int:
    """Räkna ord i transkript."""
    content = transcript_path.read_text(encoding="utf-8")
    return len(content.split())
