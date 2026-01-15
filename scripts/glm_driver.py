#!/usr/bin/env python3
"""
GLM Driver för podcast-transkript analys.

Anropar OpenCode CLI med GLM-4.7 för att analysera transkript
och extrahera aktierekommendationer.

VIKTIGT: Använder enhetlig prompt från prompt_templates.py för
konsekvent output mellan Claude och GLM.
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from podstock.extract.prompt_templates import get_unified_prompt


# Configuration
GLM_MODEL = "opencode/glm-4.7-free"


def find_opencode_cli() -> str:
    """Find OpenCode CLI in common locations across different machines."""
    import shutil

    # Locations to search (in order of preference)
    locations = [
        # macOS app bundle (common on laptops/desktops)
        Path("/Applications/OpenCode.app/Contents/MacOS/opencode-cli"),
        # User's local opencode installation
        Path.home() / ".opencode" / "bin" / "opencode",
        # Alternative user paths
        Path.home() / ".local" / "bin" / "opencode",
        Path("/usr/local/bin/opencode"),
    ]

    # Check explicit paths first
    for loc in locations:
        if loc.exists() and loc.is_file():
            return str(loc)

    # Fall back to PATH lookup
    path_result = shutil.which("opencode")
    if path_result:
        return path_result

    path_result = shutil.which("opencode-cli")
    if path_result:
        return path_result

    raise FileNotFoundError(
        "OpenCode CLI not found. Searched:\n" +
        "\n".join(f"  - {loc}" for loc in locations) +
        "\n  - PATH (opencode, opencode-cli)"
    )


OPENCODE_CLI = find_opencode_cli()
PROMPT_TEMPLATE_FILE = Path(__file__).parent.parent / "docs" / "GLM-ANALYSIS-INSTRUCTIONS.md"
JSON_SCHEMA_FILE = Path(__file__).parent.parent / "docs" / "JSON-SCHEMA.md"


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


def validate_analysis(data: dict) -> tuple[bool, str]:
    """Validera analys mot schema."""

    # Lägg till model_used om det saknas (GLM glömmer ibland)
    if "model_used" not in data:
        data["model_used"] = "glm-4.7"

    required_fields = [
        "episode_id",
        "podcast_name",
        "date",
        "recommendations",
        "market_sentiment",
        "summary",
        "model_used"
    ]

    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"

    if not isinstance(data["recommendations"], list):
        return False, "recommendations must be a list"

    for i, rec in enumerate(data["recommendations"]):
        rec_required = ["stock_name", "action", "confidence", "reasoning", "quote"]
        for field in rec_required:
            if field not in rec:
                return False, f"recommendation[{i}] missing field: {field}"

        valid_actions = ["buy", "sell", "hold", "watch", "avoid"]
        if rec["action"] not in valid_actions:
            return False, f"recommendation[{i}] invalid action: {rec['action']}"

        valid_confidence = ["high", "medium", "low", "speculative"]
        if rec["confidence"] not in valid_confidence:
            return False, f"recommendation[{i}] invalid confidence: {rec['confidence']}"

    # Validera stock_segments om de finns (v2.0 schema)
    if "stock_segments" in data and data["stock_segments"]:
        if not isinstance(data["stock_segments"], list):
            return False, "stock_segments must be a list"

        for i, seg in enumerate(data["stock_segments"]):
            seg_required = ["stock_name", "discussion_summary"]
            for field in seg_required:
                if field not in seg:
                    return False, f"stock_segments[{i}] missing field: {field}"

            # Validera quotes om de finns
            if "quotes" in seg and seg["quotes"]:
                if not isinstance(seg["quotes"], list):
                    return False, f"stock_segments[{i}].quotes must be a list"
                for j, quote in enumerate(seg["quotes"]):
                    if "speaker" not in quote or "text" not in quote:
                        return False, f"stock_segments[{i}].quotes[{j}] missing speaker or text"

            # Normalisera position_disclosure (GLM ger ibland fritext)
            if "position_disclosure" in seg and seg["position_disclosure"]:
                valid_positions = ["owns", "bought", "sold", "none", "unknown"]
                pd = str(seg["position_disclosure"]).lower().strip()
                if pd not in valid_positions:
                    # Försök mappa fritext till närmaste värde
                    if any(x in pd for x in ["köp", "buy", "bought", "köpt"]):
                        seg["position_disclosure"] = "bought"
                    elif any(x in pd for x in ["sål", "sell", "sold", "sålt", "short", "blankar", "blankat", "avoid", "undvik"]):
                        seg["position_disclosure"] = "sold"
                    elif any(x in pd for x in ["äger", "own", "har", "innehar", "hold"]):
                        seg["position_disclosure"] = "owns"
                    elif any(x in pd for x in ["ingen", "none", "nej", "inte"]):
                        seg["position_disclosure"] = "none"
                    else:
                        seg["position_disclosure"] = "unknown"

    # Validera insights om de finns (v2.1 schema)
    if "insights" in data and data["insights"]:
        if not isinstance(data["insights"], list):
            return False, "insights must be a list"

        for i, insight in enumerate(data["insights"]):
            insight_required = ["quote", "summary", "category", "speaker"]
            for field in insight_required:
                if field not in insight:
                    return False, f"insights[{i}] missing field: {field}"

            valid_categories = ["philosophy", "lesson", "wisdom"]
            if insight["category"] not in valid_categories:
                return False, f"insights[{i}] invalid category: {insight['category']}"

            if "confidence" in insight and insight["confidence"]:
                valid_insight_confidence = ["high", "medium", "low"]
                if insight["confidence"] not in valid_insight_confidence:
                    return False, f"insights[{i}] invalid confidence: {insight['confidence']}"

    # Validera crypto_mentions om de finns (v2.1 schema)
    if "crypto_mentions" in data and data["crypto_mentions"]:
        if not isinstance(data["crypto_mentions"], list):
            return False, "crypto_mentions must be a list"

        for i, crypto in enumerate(data["crypto_mentions"]):
            crypto_required = ["asset_symbol", "sentiment", "speaker", "quote"]
            for field in crypto_required:
                if field not in crypto:
                    return False, f"crypto_mentions[{i}] missing field: {field}"

            valid_sentiment = ["bullish", "bearish", "neutral", "mixed"]
            if crypto["sentiment"] not in valid_sentiment:
                return False, f"crypto_mentions[{i}] invalid sentiment: {crypto['sentiment']}"

            if "confidence" in crypto and crypto["confidence"]:
                valid_crypto_confidence = ["high", "medium", "low"]
                if crypto["confidence"] not in valid_crypto_confidence:
                    return False, f"crypto_mentions[{i}] invalid confidence: {crypto['confidence']}"

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
    max_retries: int = 3,
    timeout: int = 600  # 10 min - GLM-4.7 med stora prompts
) -> tuple[Optional[dict], bool, str]:
    """
    Analysera ett transkript med GLM-4.7.
    
    Returns:
        (analysis_data, success, error_message)
    """
    
    for attempt in range(1, max_retries + 1):
        try:
            content = transcript_path.read_text(encoding="utf-8")
            word_count = len(content.split())
            
            episode_stem = transcript_path.stem

            print(f"  📝 Analyserar: {transcript_path.name} ({word_count:,} ord) [försök {attempt}/{max_retries}]")

            # Använd enhetlig prompt från prompt_templates.py
            prompt = get_unified_prompt(
                transcript=content,
                episode_id=episode_stem,
                model_name="glm-4.7"
            )

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
                timeout=timeout,
                cwd="/tmp"  # Run from /tmp to avoid parsing .claude/skills files
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
            
            is_valid, validation_error = validate_analysis(data)
            
            if not is_valid:
                error = f"Validation error: {validation_error}"
                if attempt < max_retries:
                    print(f"  ⚠️  {error} - försöker igen...")
                    continue
                return None, False, error
            
            tokens = data.pop("_token_usage", {})
            print(f"  ✅ Analys klar! Tokens: {tokens.get('input', 0):,} in / {tokens.get('output', 0):,} out | Rek: {len(data.get('recommendations', []))}")
            
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
    
    output_file = output_dir / f"{analysis['episode_id']}.json"
    
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
            "total_processed": 0,
            "current_batch": 0
        }
    
    if success:
        if transcript_name not in log_data["completed"]:
            log_data["completed"].append(transcript_name)
            log_data["total_processed"] += 1
        
        if transcript_name in log_data["failed"]:
            log_data["failed"].remove(transcript_name)
    else:
        if transcript_name not in log_data["failed"]:
            log_data["failed"].append({
                "name": transcript_name,
                "error": error_message,
                "timestamp": Path(__file__).stat().st_mtime
            })
        
        if transcript_name in log_data["completed"]:
            log_data["completed"].remove(transcript_name)
            log_data["total_processed"] -= 1
    
    import datetime
    log_data["last_updated"] = datetime.datetime.now().isoformat()
    
    log_file.write_text(
        json.dumps(log_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    return True


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 glm_driver.py <transcript_file> <output_dir>")
        sys.exit(1)
    
    transcript_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    
    if not transcript_path.exists():
        print(f"❌ Fel: Transkript-filen existerar inte: {transcript_path}")
        sys.exit(1)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    project_root = Path(__file__).parent.parent
    completion_log = project_root / "data" / "extracted" / "glm-batch" / "completion-log.json"
    
    analysis, success, error = analyze_transcript(transcript_path)
    
    if success and analysis:
        output_file = save_analysis(analysis, output_dir)
        print(f"  💾 Sparade: {output_file}")
        
        update_completion_log(
            completion_log,
            transcript_path.name,
            success=True
        )
        sys.exit(0)
    else:
        print(f"  ❌ Misslyckades: {error}")
        
        update_completion_log(
            completion_log,
            transcript_path.name,
            success=False,
            error_message=error
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
