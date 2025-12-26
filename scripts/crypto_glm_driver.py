#!/usr/bin/env python3
"""
GLM Driver för TechnicalRoundup crypto-analys.

Anropar OpenCode CLI med GLM-4.7 för att analysera YouTube-transkript
och extrahera crypto sentiment och mentions.

ANVÄNDNING:
    python3 scripts/crypto_glm_driver.py <video_id>

    Exempel:
    python3 scripts/crypto_glm_driver.py -ds7GO4SrLg
"""

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Configuration
OPENCODE_CLI = "/Users/pontus/.opencode/bin/opencode"
GLM_MODEL = "opencode/glm-4.7-free"

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
TRANSCRIPT_DIR = PROJECT_ROOT / "data" / "youtube" / "transcripts" / "technicalroundup"
OUTPUT_DIR = PROJECT_ROOT / "data" / "crypto" / "technicalroundup-analysis"
DATE_TABLE = OUTPUT_DIR / "video-dates.txt"
COMPLETION_LOG = OUTPUT_DIR / "completion-log.json"


def get_video_date(video_id: str) -> str:
    """Hämta datum från video-dates.txt."""
    try:
        for line in DATE_TABLE.read_text().splitlines():
            if "|" in line:
                vid, date = line.split("|")
                if vid.strip() == video_id:
                    # Convert YYYYMMDD -> YYYY-MM-DD
                    d = date.strip()
                    return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
    except FileNotFoundError:
        pass
    return "unknown"


def extract_json_from_response(text: str) -> str:
    """Extrahera JSON från markdown code blocks eller ren text."""

    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        return match.group(1)

    match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        return match.group(1)

    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        return text[start:end]

    return text


def validate_crypto_analysis(data: dict) -> tuple[bool, str]:
    """Validera crypto-analys mot schema."""

    required_fields = [
        "source_id",
        "mentions",
        "overall_market_sentiment",
        "summary"
    ]

    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"

    if not isinstance(data["mentions"], list):
        return False, "mentions must be a list"

    for i, mention in enumerate(data["mentions"]):
        mention_required = ["asset_symbol", "sentiment", "speaker", "quote"]
        for field in mention_required:
            if field not in mention:
                return False, f"mentions[{i}] missing field: {field}"

        valid_sentiments = ["bullish", "bearish", "neutral", "mixed", "strongly_bullish", "strongly_bearish"]
        if mention["sentiment"] not in valid_sentiments:
            return False, f"mentions[{i}] invalid sentiment: {mention['sentiment']}"

    valid_market_sentiments = ["bullish", "bearish", "neutral", "mixed", "uncertain"]
    if data["overall_market_sentiment"] not in valid_market_sentiments:
        return False, f"Invalid overall_market_sentiment: {data['overall_market_sentiment']}"

    return True, ""


def parse_opencode_output(stdout: str) -> Optional[dict]:
    """Parse JSON output från OpenCode CLI."""

    ai_response = None
    tokens_info = None

    for line in stdout.split('\n'):
        if line.strip():
            try:
                event = json.loads(line)
                if event.get("type") == "text":
                    ai_response = event.get("part", {}).get("text")
                elif event.get("type") == "step_finish":
                    tokens_info = event.get("part", {}).get("tokens", {})
            except json.JSONDecodeError:
                pass

    if not ai_response:
        return None

    json_str = extract_json_from_response(ai_response)

    try:
        data = json.loads(json_str)

        if tokens_info:
            data["_token_usage"] = tokens_info

        return data
    except json.JSONDecodeError as e:
        return None


def analyze_transcript(
    transcript_path: Path,
    video_id: str,
    max_retries: int = 3,
    timeout: int = 180
) -> tuple[Optional[dict], bool, str]:
    """
    Analysera ett crypto-transkript med GLM-4.7.

    Returns:
        (analysis_data, success, error_message)
    """

    video_date = get_video_date(video_id)

    for attempt in range(1, max_retries + 1):
        try:
            content = transcript_path.read_text(encoding="utf-8")
            word_count = len(content.split())

            print(f"  📝 Analyserar: {transcript_path.name} ({word_count:,} ord) [försök {attempt}/{max_retries}]")

            prompt = f"""You are an expert at analyzing cryptocurrency podcasts and extracting market sentiment and asset mentions.

PODCAST INFO:
- Source: TechnicalRoundup YouTube channel
- Video ID: {video_id}
- Date: {video_date}
- Hosts: CryptoCred (Cred) and DonAlt (Duck)

YOUR TASK:
Analyze this transcript and extract:
1. ALL cryptocurrency/token mentions with sentiment
2. Overall market sentiment
3. Key trading insights and predictions

SPEAKER IDENTIFICATION:
- "Cred" or "CryptoCred" = Use "Cred"
- "Duck" or "DonAlt" = Use "Duck"
- If unclear who is speaking, use "Unknown"

SENTIMENT LEVELS:
- strongly_bullish: Very positive, expecting significant upside
- bullish: Positive outlook, expecting gains
- neutral: No clear directional bias
- bearish: Negative outlook, expecting decline
- strongly_bearish: Very negative, expecting significant downside
- mixed: Conflicting signals or uncertainty

IMPORTANT GUIDELINES:
- Include ALL crypto assets mentioned (BTC, ETH, altcoins, etc.)
- Capture the CONTEXT around each mention
- Note any price targets or levels mentioned
- Include EXACT quotes that support the sentiment
- Distinguish between Cred and Duck's opinions

EXCLUDE:
- Sponsor mentions (not relevant to analysis)
- Social media plugs
- Non-crypto discussion

OUTPUT:
Return ONLY valid JSON (no markdown, no code blocks):

{{
  "source_id": "{video_id}",
  "source_type": "youtube",
  "channel": "TechnicalRoundup",
  "date": "{video_date}",
  "hosts": ["Cred", "Duck"],
  "mentions": [
    {{
      "asset_symbol": "BTC",
      "asset_name": "Bitcoin",
      "sentiment": "bullish|bearish|neutral|mixed|strongly_bullish|strongly_bearish",
      "speaker": "Cred|Duck|Unknown",
      "context": "Brief description of the discussion context",
      "quote": "Exact quote supporting the sentiment (max 100 words)",
      "price_levels": ["$X", "$Y"] or null,
      "timeframe": "short-term|medium-term|long-term" or null,
      "confidence": "high|medium|low"
    }}
  ],
  "overall_market_sentiment": "bullish|bearish|neutral|mixed|uncertain",
  "market_analysis": {{
    "btc_dominance_view": "increasing|decreasing|stable|not_discussed",
    "altcoin_season_view": "yes|no|uncertain|not_discussed",
    "key_levels": {{"BTC": ["$X"], "ETH": ["$Y"]}} or null
  }},
  "key_insights": [
    "Insight 1",
    "Insight 2"
  ],
  "trading_ideas": [
    {{
      "asset": "BTC",
      "direction": "long|short",
      "entry": "$X or range",
      "target": "$Y or range",
      "stop": "$Z",
      "speaker": "Cred|Duck"
    }}
  ],
  "summary": "3-5 sentence summary of the episode's main points",
  "transcript_word_count": {word_count},
  "model_used": "glm-4.7",
  "analyzed_at": "{datetime.now().isoformat()}"
}}

TRANSCRIPT:
{content}
"""

            cmd = [
                OPENCODE_CLI, "run",
                "--format", "json",
                "-m", GLM_MODEL,
                prompt
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode != 0:
                error = f"CLI error (exit {result.returncode}): {result.stderr[:200]}"
                if attempt < max_retries:
                    print(f"  ⚠️  {error} - försöker igen...")
                    continue
                return None, False, error

            data = parse_opencode_output(result.stdout)

            if not data:
                error = "Kunde inte parsa JSON-respons"
                if attempt < max_retries:
                    print(f"  ⚠️  {error} - försöker igen...")
                    continue
                return None, False, error

            is_valid, validation_error = validate_crypto_analysis(data)

            if not is_valid:
                error = f"Validation error: {validation_error}"
                if attempt < max_retries:
                    print(f"  ⚠️  {error} - försöker igen...")
                    continue
                return None, False, error

            tokens = data.pop("_token_usage", {})
            mentions_count = len(data.get("mentions", []))
            print(f"  ✅ Analys klar! Tokens: {tokens.get('input', 0):,} in / {tokens.get('output', 0):,} out | Mentions: {mentions_count}")

            return data, True, ""

        except subprocess.TimeoutExpired:
            error = f"Timeout efter {timeout} sekunder"
            if attempt < max_retries:
                print(f"  ⚠️  {error} - försöker igen...")
                continue
            return None, False, error

        except Exception as e:
            error = f"Unexpected error: {str(e)}"
            if attempt < max_retries:
                print(f"  ⚠️  {error} - försöker igen...")
                continue
            return None, False, error

    return None, False, "Max retries exceeded"


def save_analysis(analysis: dict, output_dir: Path) -> Path:
    """Spara analys till JSON-fil."""

    output_file = output_dir / f"{analysis['source_id']}.json"

    output_file.write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return output_file


def update_completion_log(
    log_file: Path,
    transcript_name: str,
    success: bool,
    error_message: str = ""
) -> bool:
    """Uppdatera completion-log."""

    try:
        log_data = json.loads(log_file.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        log_data = {
            "completed": [],
            "failed": [],
            "last_updated": "",
            "total_processed": 0
        }

    if success:
        if transcript_name not in log_data["completed"]:
            log_data["completed"].append(transcript_name)
            log_data["total_processed"] = len(log_data["completed"])

        # Remove from failed if present
        log_data["failed"] = [f for f in log_data["failed"]
                              if (f.get("name") if isinstance(f, dict) else f) != transcript_name]
    else:
        if transcript_name not in [f.get("name") if isinstance(f, dict) else f for f in log_data["failed"]]:
            log_data["failed"].append({
                "name": transcript_name,
                "error": error_message,
                "timestamp": datetime.now().isoformat()
            })

    log_data["last_updated"] = datetime.now().isoformat()

    log_file.write_text(
        json.dumps(log_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return True


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 crypto_glm_driver.py <video_id>")
        print("Example: python3 crypto_glm_driver.py -ds7GO4SrLg")
        sys.exit(1)

    video_id = sys.argv[1]
    transcript_path = TRANSCRIPT_DIR / f"{video_id}.txt"

    if not transcript_path.exists():
        print(f"❌ Fel: Transkript-filen existerar inte: {transcript_path}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    analysis, success, error = analyze_transcript(transcript_path, video_id)

    if success and analysis:
        output_file = save_analysis(analysis, OUTPUT_DIR)
        print(f"  💾 Sparade: {output_file}")

        update_completion_log(
            COMPLETION_LOG,
            f"{video_id}.txt",
            success=True
        )
        sys.exit(0)
    else:
        print(f"  ❌ Misslyckades: {error}")

        update_completion_log(
            COMPLETION_LOG,
            f"{video_id}.txt",
            success=False,
            error_message=error
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
