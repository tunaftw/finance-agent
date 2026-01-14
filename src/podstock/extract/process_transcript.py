"""Huvudlogik för att processa enskilda transkript."""

import json
import re
from pathlib import Path
from typing import Any

from podstock.analysis import extract_json_from_response
from .llm_client import LLMClient, create_llm_client
from .models import EpisodeAnalysis
from .prompt_templates import (
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_USER_PROMPT,
    FEW_SHOT_EXAMPLE,
)


def _normalize_confidence(value: Any) -> str:
    """Convert numeric confidence (0-1) to text category.

    Claude sometimes outputs numeric confidence (0.65) instead of
    text categories ("high", "medium", "low", "speculative").
    This normalizes the output to match the expected schema.
    """
    if isinstance(value, str) and value in ("high", "medium", "low", "speculative"):
        return value  # Already correct format
    if not isinstance(value, (int, float)):
        return "medium"  # Default fallback
    if value >= 0.7:
        return "high"
    elif value >= 0.5:
        return "medium"
    elif value >= 0.3:
        return "low"
    else:
        return "speculative"


def _normalize_analysis_data(data: dict) -> dict:
    """Normalize LLM output to match expected schema.

    Handles common schema mismatches where Claude outputs:
    - 'sentiment' instead of 'action'
    - numeric confidence instead of text categories
    """
    # Normalize recommendations
    for rec in data.get("recommendations", []):
        # Handle 'sentiment' -> 'action' field name mismatch
        if "action" not in rec and "sentiment" in rec:
            rec["action"] = rec.pop("sentiment")

        # Normalize confidence to text
        if "confidence" in rec:
            rec["confidence"] = _normalize_confidence(rec["confidence"])

    # Normalize insights confidence
    for ins in data.get("insights", []):
        if "confidence" in ins:
            ins["confidence"] = _normalize_confidence(ins["confidence"])

    # Normalize crypto_mentions confidence
    for crypto in data.get("crypto_mentions", []):
        if "confidence" in crypto:
            crypto["confidence"] = _normalize_confidence(crypto["confidence"])

    return data


class TranscriptProcessor:
    """Processar podcast-transkript och extraherar rekommendationer."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        llm_client: LLMClient | None = None,
    ):
        """Initiera processor.

        Args:
            api_key: Anthropic API-nyckel (krävs för Claude)
            model: Modellspecifikation (t.ex. "claude-sonnet-4-20250514" eller "ollama:llama3.3")
            llm_client: Förbyggd LLM-klient (om None, skapas från model+api_key)
        """
        if llm_client:
            self.client = llm_client
        else:
            self.client = create_llm_client(model, api_key)
        self.model = self.client.model_name

    def parse_filename(self, filepath: Path) -> dict:
        """
        Extrahera metadata från filnamn.

        Hanterar format som:
        - borspodden-2024-12-20-abc1.txt
        - veckanstrade-2025-06-11-2aae.txt
        - borspodden_2024-12-20.txt
        """
        stem = filepath.stem

        # Försök hitta datum i olika format
        date_patterns = [
            r"(\d{4}-\d{2}-\d{2})",  # 2024-12-20
            r"(\d{8})",  # 20241220
            r"(\d{4}_\d{2}_\d{2})",  # 2024_12_20
        ]

        date = None
        for pattern in date_patterns:
            match = re.search(pattern, stem)
            if match:
                date_str = match.group(1).replace("_", "-")
                if len(date_str) == 8:  # 20241220 format
                    date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                else:
                    date = date_str
                break

        # Identifiera podcast-namn baserat på fil eller katalog
        podcast_patterns = {
            "borspodden": "Börspodden",
            "fill_or_kill": "Fill or Kill",
            "fillorkill": "Fill or Kill",
            "borsmagasinet": "Börsmagasinet",
            "market_makers": "Market Makers",
            "marketmakers": "Market Makers",
            "gott_tjot": "Gött Tjöt om Aktier",
            "gotttjot": "Gött Tjöt om Aktier",
            "borsens_finest": "Börsens Finest",
            "veckanstrade": "Veckans Trade",
            "veckans_trade": "Veckans Trade",
        }

        podcast_name = "Okänd podcast"
        stem_lower = stem.lower()
        parent_lower = filepath.parent.name.lower()

        # Kolla först katalognamnet, sen filnamnet
        for key, name in podcast_patterns.items():
            if key in parent_lower or key in stem_lower:
                podcast_name = name
                break

        return {
            "date": date or "unknown",
            "podcast_name": podcast_name,
            "episode_id": stem,
        }

    def process_transcript(self, filepath: Path) -> EpisodeAnalysis:
        """Processa ett enskilt transkript."""

        # Läs fil
        content = filepath.read_text(encoding="utf-8")
        word_count = len(content.split())
        has_timestamps = bool(re.search(r"\[\d{2}:\d{2}:\d{2}\]", content))

        # Parse metadata från filnamn
        file_meta = self.parse_filename(filepath)

        # Bygg prompt
        user_prompt = EXTRACTION_USER_PROMPT.format(
            podcast_name=file_meta["podcast_name"],
            date=file_meta["date"],
            filename=filepath.name,
            transcript=content,
        )

        # Anropa LLM
        system_prompt = EXTRACTION_SYSTEM_PROMPT + "\n\n" + FEW_SHOT_EXAMPLE
        response_text = self.client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=8000,
        )

        # Extrahera JSON från response (hanterar markdown code blocks)
        json_str = extract_json_from_response(response_text)

        # Parse och validera
        data = json.loads(json_str)

        # Normalize schema mismatches (sentiment->action, numeric->text confidence)
        data = _normalize_analysis_data(data)

        # Lägg till metadata
        data["episode_id"] = file_meta["episode_id"]
        data["transcript_file"] = str(filepath)
        data["transcript_word_count"] = word_count
        data["has_timestamps"] = has_timestamps
        data["model_used"] = self.model

        # Säkerställ att date finns
        if "date" not in data or not data["date"]:
            data["date"] = file_meta["date"]

        # Säkerställ att podcast_name finns
        if "podcast_name" not in data or not data["podcast_name"]:
            data["podcast_name"] = file_meta["podcast_name"]

        return EpisodeAnalysis(**data)

    def save_analysis(self, analysis: EpisodeAnalysis, output_dir: Path) -> Path:
        """Spara analys till JSON-fil."""
        episodes_dir = output_dir / "episodes"
        episodes_dir.mkdir(parents=True, exist_ok=True)

        output_file = episodes_dir / f"{analysis.episode_id}.json"
        output_file.write_text(
            analysis.model_dump_json(indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return output_file
