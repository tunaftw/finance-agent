#!/usr/bin/env python3
"""
GLM Driver för podcast-transkript analys.

Anropar OpenCode CLI med GLM-4.7 för att analysera transkript
och extrahera aktierekommendationer.
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

# Configuration
OPENCODE_CLI = "/Users/pontus/.opencode/bin/opencode"
GLM_MODEL = "opencode/glm-4.7-free"
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

            # Validera position_disclosure om det finns
            if "position_disclosure" in seg and seg["position_disclosure"]:
                valid_positions = ["owns", "bought", "sold", "none", "unknown"]
                if seg["position_disclosure"] not in valid_positions:
                    return False, f"stock_segments[{i}] invalid position_disclosure: {seg['position_disclosure']}"

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
    timeout: int = 180
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
            transcript_str = str(transcript_path)
            has_timestamps = bool(re.search(r"\[\d{2}:\d{2}:\d{2}\]", content))
            
            print(f"  📝 Analyserar: {transcript_path.name} ({word_count:,} ord) [försök {attempt}/{max_retries}]")
            
            prompt = f"""Du är en expert på att analysera svenska finanspoddar och extrahera investeringsrekommendationer.

Din uppgift är att noggrant läsa podcast-transkript och identifiera:
1. KONKRETA aktie-rekommendationer (köp, sälj, bevaka, undvik)
2. Vem som ger rekommendationen (host eller gäst)
3. Argumenten bakom rekommendationen
4. Eventuella kursmål eller tidshorisonter
5. DJUPANALYS: För aktier som diskuteras >1 minut, skapa detaljerade segment

VIKTIGA RIKTLINJER:
- Var KONSERVATIV: Inkludera bara tydliga rekommendationer, inte vag diskussion
- "Intressant bolag" eller "värt att titta på" = watch, INTE buy
- "Vi äger aktien" utan vidare kontext = hold
- "Stark köpkandidat", "köpläge", "vi köper" = buy
- "Dags att ta hem vinst", "sälj", "vi säljer" = sell
- Fånga EXAKTA citat som stödjer rekommendationen
- Om tidsstämplar finns [HH:MM:SS], inkludera dem
- Svenska bolag listas ofta utan ticker - det är OK att lämna ticker tom

⚠️ EXKLUDERA FÖLJANDE - DETTA ÄR INTE REKOMMENDATIONER:
- Sponsormeddelanden (Interactive Brokers, Avanza, Nordnet, Syn Society, etc.)
- Reklam och produktplaceringar
- Podcast-prenumerations-uppmaningar
- Sociala media-omnämnanden
- Mäklare/plattformar som omnämns i reklamsyfte
- Fondbolag som sponsrar (Protean, Carnegie, etc. OM de bara nämns som sponsor)

FINANSTERMINOLOGI ATT KÄNNA IGEN:
- Köpsignaler: "köpläge", "köpvärd", "attraktiv", "undervärderad", "vi köper", "stark köp"
- Säljsignaler: "säljläge", "övervärderad", "ta hem vinst", "vi säljer", "sälj"
- Watch: "bevaka", "intressant", "håll koll på", "kan bli köpvärd"
- Undvik: "håll dig borta", "undvik", "för riskfyllt"

🎯 MAXIMAL MATNYTTIGHET - FÅNGA ALLT VÄRDEFULLT:
- Fånga ALLA konkreta siffror och nyckeltal (P/E, EV/EBITDA, tillväxt%, marginaler, omsättning)
- Inkludera HELA resonemanget när någon motiverar en aktie (inte bara sammanfattning)
- Om någon nämner ett kursmål eller riktkurs, fånga det EXAKT
- Om någon delar en portföljstrategi eller allokering, inkludera detaljerna
- Citat får vara längre (max 200 ord) om de innehåller viktig information
- Fånga kontext: varför just nu? Vad har hänt? Vad förväntas?

💡 INSIGHTS - FÅNGA INVESTERINGSVISDOM:
Extrahera tidlösa insikter och lärdomar som inte är specifika aktie-tips:

Kategorier:
- "philosophy": Investeringsfilosofi och grundprinciper
  Exempel: "Jag köper aldrig bolag jag inte förstår", "Tid i marknaden slår timing"
- "lesson": Lärdomar från misstag eller erfarenheter
  Exempel: "Det största misstaget jag gjort var...", "Jag lärde mig att aldrig..."
- "wisdom": Marknadsvisdom, psykologi, timing
  Exempel: "Rädsla skapar möjligheter", "Girigheten tar över när..."

INKLUDERA:
- Tidlösa principer som håller över tid
- Konkreta lärdomar från erfarenhet
- Psykologiska insikter om investerande
- Riskhanterings-filosofi

EXKLUDERA från insights (fångas i recommendations istället):
- Specifika aktie-tips ("köp Evolution")
- Tidsbunden marknadskommentar ("marknaden är övervärderad just nu")

🪙 CRYPTO-OMNÄMNANDEN:
Extrahera alla omnämnanden av kryptovalutor med sentiment:

Tokens att leta efter:
- Major: BTC/Bitcoin, ETH/Ethereum, SOL/Solana, XRP, ADA/Cardano
- DeFi: LINK, UNI, AAVE
- Meme: DOGE, SHIB, PEPE
- Svenska termer: "krypto", "bitcoin", "ethereum"

Sentiment-signaler:
- Bullish: "intressant", "potential", "vi köper", "undervärderat"
- Bearish: "försiktig", "undvik", "risk", "övervärderat"
- Neutral: "håller koll", "osäker"

📊 EXTRA ALFA (fyll bara i om det nämns EXPLICIT - annars null):

POSITION CONTEXT (position_context):
- "50% av portföljen" → "50% av portföljen"
- "Största positionen" → "Största positionen"
- "Liten position" → "Liten position"
- "Vi byggde på" → "Ökade positionen"

DOWNSIDE/RISK (downside_note):
- "30% neddida härifrån" → "30% downside"
- "Värsta fall 50 SEK" → "Downside 50 SEK"
- "3:1 risk/reward" → "Risk/reward 3:1"

CATALYST TIMING (catalyst_timing):
- "Rapport 15 feb" → "Rapport 2025-02-15"
- "Produktlansering Q2" → "Produktlansering Q2 2025"
- "Efter nästa Fed-möte" → "Efter Fed-möte jan"

📊 STOCK SEGMENTS (DJUPANALYS):
För varje aktie som diskuteras i MER ÄN 1 MINUT, skapa ett detaljerat segment med:
1. ALLA relevanta citat (inte bara ett!) - med kontext (thesis/bull_case/bear_case/metric/conclusion)
2. Finansiella nyckeltal som nämns (P/E, EV/EBITDA, FCF yield, tillväxt, etc.)
3. Bull case: Varför köpa? Vad är positivt?
4. Bear case: Vad kan gå fel? Vilka risker?
5. Katalysatorer: Vad kan driva aktien?
6. Position disclosure: Äger/köpte/sålde talaren aktien?
7. Sammanfattning av hela diskussionen (3-5 meningar)

OUTPUT:
Returnera ENDAST valid JSON enligt följande schema (ingen markdown, inga code blocks):

{{
  "schema_version": "2.1",
  "episode_id": "{episode_stem}",
  "podcast_name": "Podcastens namn",
  "episode_title": "Avsnittets titel om känd",
  "episode_number": null,
  "date": "YYYY-MM-DD",
  "hosts": ["host1", "host2"],
  "guests": ["gäst1"],
  "main_topics": ["ämne1", "ämne2"],
  "stocks_discussed": ["Aktie1", "Aktie2"],
  "recommendations": [
    {{
      "stock_name": "Aktiens namn",
      "ticker": null,
      "action": "buy|sell|hold|watch|avoid",
      "confidence": "high|medium|low|speculative",
      "speaker": "Vem som pratar",
      "speaker_role": "host|guest|unknown",
      "timestamp": null,
      "reasoning": "3-5 meningar med FULLSTÄNDIG motivering: inkludera alla argument, nyckeltal och kontext",
      "price_target": null,
      "time_horizon": null,
      "quote": "Exakt citat som stödjer rekommendationen, max 200 ord - inkludera hela resonemanget",
      "sector": null,
      "market": "sweden|us|europe|other|unknown",
      "position_context": null,
      "downside_note": null,
      "catalyst_timing": null
    }}
  ],
  "stock_segments": [
    {{
      "stock_name": "Aktiens namn",
      "ticker": null,
      "timestamp_start": "HH:MM:SS",
      "timestamp_end": "HH:MM:SS",
      "word_count": 500,
      "speakers": ["Talare1", "Talare2"],
      "primary_speaker": "Huvudtalare",
      "discussion_summary": "3-5 meningar som sammanfattar diskussionen om denna aktie",
      "quotes": [
        {{
          "speaker": "Namn",
          "text": "Exakt citat...",
          "timestamp": "HH:MM:SS",
          "context": "thesis|bull_case|bear_case|metric|conclusion|other"
        }}
      ],
      "financial_metrics": {{
        "pe_ratio": null,
        "ev_ebitda": null,
        "ev_sales": null,
        "fcf_yield": "tex: 8.5%",
        "dividend_yield": null,
        "revenue_growth": null,
        "margin": null,
        "debt_level": null,
        "custom": ["branschspecifika KPIer"]
      }},
      "thesis": {{
        "bull_case": ["argument1", "argument2"],
        "bear_case": ["risk1", "risk2"],
        "catalysts": ["katalysator1"],
        "risks": ["risk1"]
      }},
      "position_disclosure": "owns|bought|sold|none|unknown"
    }}
  ],
  "insights": [
    {{
      "quote": "Exakt citat med investeringsvisdom, max 300 ord",
      "summary": "1-2 meningar som sammanfattar insikten",
      "category": "philosophy|lesson|wisdom",
      "speaker": "Vem som sa det",
      "speaker_role": "host|guest|unknown",
      "timestamp": null,
      "confidence": "high|medium|low",
      "tags": ["relevanta", "taggar"]
    }}
  ],
  "crypto_mentions": [
    {{
      "asset_symbol": "BTC|ETH|SOL|etc",
      "asset_name": "Bitcoin|Ethereum|etc",
      "sentiment": "bullish|bearish|neutral|mixed",
      "speaker": "Vem som nämnde det",
      "speaker_role": "host|guest|unknown",
      "quote": "Stödjande citat, max 100 ord",
      "context": "Diskussionskontext",
      "confidence": "high|medium|low",
      "price_levels": ["nivå1", "nivå2"],
      "timeframe": "kort sikt|medellång sikt|lång sikt"
    }}
  ],
  "market_sentiment": "bullish|bearish|neutral|mixed",
  "summary": "3-5 meningar som sammanfattar avsnittet",
  "key_takeaways": ["punkt1", "punkt2", "punkt3"],
  "transcript_file": "{transcript_str}",
  "transcript_word_count": {word_count},
  "has_timestamps": {"true" if has_timestamps else "false"},
  "model_used": "glm-4.7"
}}

VIKTIGT: stock_segments ska innehålla aktier med >1 min diskussion. För korta omnämnanden räcker recommendations.

Transkript:
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
