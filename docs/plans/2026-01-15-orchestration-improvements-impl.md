# Orchestration Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Göra orchestration-skillen felfri för daglig körning med enhetlig prompt, schema-validering, körningsrapport och självläkande mekanism.

**Architecture:** Konsolidera GLM och Claude prompts till en master-prompt i `prompt_templates.py`. Lägg till schema-normalisering i `process_transcript.py` och `exporters.py`. Skapa `OrchestrationReport` klass för körningsrapporter. Uppdatera orchestration-skillen med modellval och förbättringsförslag.

**Tech Stack:** Python 3.11+, Pydantic, Rich (terminal output), Markdown (rapporter)

---

## Task 1: Schema-normalisering för Insights

**Files:**
- Modify: `src/podstock/extract/process_transcript.py:39-66`
- Test: `tests/test_normalize_insight.py` (create)

**Step 1: Write the failing test**

Create `tests/test_normalize_insight.py`:

```python
"""Test insight schema normalization."""
import pytest


def test_normalize_insight_wrong_schema():
    """Wrong schema (topic/insight) should be transformed to correct (quote/summary)."""
    from podstock.extract.process_transcript import normalize_insight

    wrong_format = {
        "topic": "AI-marknaden",
        "insight": "AI-modeller har blivit en commodity",
        "speaker": "Niklas"
    }

    result = normalize_insight(wrong_format)

    assert "quote" in result
    assert "summary" in result
    assert "category" in result
    assert "tags" in result
    assert result["quote"] == "AI-modeller har blivit en commodity"
    assert result["summary"] == "AI-modeller har blivit en commodity"
    assert result["speaker"] == "Niklas"


def test_normalize_insight_correct_schema():
    """Correct schema should pass through unchanged."""
    from podstock.extract.process_transcript import normalize_insight

    correct_format = {
        "quote": "Jag köper aldrig bolag jag inte förstår",
        "summary": "Investera bara i det du förstår",
        "category": "philosophy",
        "speaker": "Johan",
        "speaker_role": "host",
        "timestamp": "00:15:23",
        "confidence": "high",
        "tags": ["discipline", "understanding"]
    }

    result = normalize_insight(correct_format)

    assert result == correct_format


def test_normalize_analysis_data_with_insights():
    """Full analysis normalization should handle insights array."""
    from podstock.extract.process_transcript import _normalize_analysis_data

    data = {
        "recommendations": [],
        "insights": [
            {"topic": "Test", "insight": "Test insight", "speaker": "A"},
            {"quote": "Correct", "summary": "Correct", "category": "wisdom",
             "speaker": "B", "tags": []}
        ]
    }

    result = _normalize_analysis_data(data)

    # First insight should be normalized
    assert result["insights"][0]["quote"] == "Test insight"
    assert result["insights"][0]["summary"] == "Test insight"
    # Second insight unchanged
    assert result["insights"][1]["quote"] == "Correct"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_normalize_insight.py -v`
Expected: FAIL with "cannot import name 'normalize_insight'"

**Step 3: Write the implementation**

Add to `src/podstock/extract/process_transcript.py` after line 36 (after `_normalize_confidence`):

```python
def normalize_insight(ins: dict) -> dict:
    """Transform wrong insight schema to correct v2.1 format.

    Wrong format: {"topic": "...", "insight": "...", "speaker": "..."}
    Correct format: {"quote": "...", "summary": "...", "category": "...",
                    "speaker": "...", "speaker_role": "...", "tags": [...]}
    """
    # Already correct format
    if "summary" in ins and "quote" in ins:
        return ins

    # Wrong format - transform
    if "insight" in ins or "topic" in ins:
        insight_text = ins.get("insight", ins.get("topic", ""))
        return {
            "quote": insight_text,
            "summary": insight_text,
            "category": ins.get("category", "wisdom"),
            "speaker": ins.get("speaker", ""),
            "speaker_role": ins.get("speaker_role", "unknown"),
            "timestamp": ins.get("timestamp"),
            "confidence": ins.get("confidence", "medium"),
            "tags": ins.get("tags", [])
        }

    return ins
```

**Step 4: Update `_normalize_analysis_data` to use it**

Modify `src/podstock/extract/process_transcript.py` lines 56-59:

```python
    # Normalize insights schema AND confidence
    for i, ins in enumerate(data.get("insights", [])):
        data["insights"][i] = normalize_insight(ins)
        if "confidence" in data["insights"][i]:
            data["insights"][i]["confidence"] = _normalize_confidence(
                data["insights"][i]["confidence"]
            )
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_normalize_insight.py -v`
Expected: PASS (3 tests)

**Step 6: Commit**

```bash
git add tests/test_normalize_insight.py src/podstock/extract/process_transcript.py
git commit -m "feat(extract): add insight schema normalization

Transforms wrong format (topic/insight) to correct v2.1 (quote/summary/category/tags).
Fixes issue where dashboard showed empty insights.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Schema-normalisering i Dashboard Exporter

**Files:**
- Modify: `src/podstock/dashboard/exporters.py:489-502`

**Step 1: Write the failing test**

Add to `tests/test_normalize_insight.py`:

```python
def test_exporter_normalize_insight():
    """Exporter should normalize insights before export."""
    from podstock.dashboard.exporters import _normalize_insight_for_export

    wrong_format = {
        "topic": "Test topic",
        "insight": "Test insight text",
        "speaker": "TestSpeaker"
    }

    result = _normalize_insight_for_export(wrong_format)

    assert result["summary"] == "Test insight text"
    assert result["quote"] == "Test insight text"
    assert result["category"] == "wisdom"
    assert result["speaker"] == "TestSpeaker"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_normalize_insight.py::test_exporter_normalize_insight -v`
Expected: FAIL with "cannot import name '_normalize_insight_for_export'"

**Step 3: Write the implementation**

Add helper function in `src/podstock/dashboard/exporters.py` near other helper functions (around line 50):

```python
def _normalize_insight_for_export(ins: dict) -> dict:
    """Normalize insight schema for dashboard export.

    Handles both v2.1 correct format and legacy wrong format.
    """
    # If wrong format (topic/insight instead of quote/summary)
    if "summary" not in ins and ("insight" in ins or "topic" in ins):
        insight_text = ins.get("insight", ins.get("topic", ""))
        return {
            "summary": insight_text,
            "quote": insight_text,
            "category": ins.get("category", "wisdom"),
            "speaker": ins.get("speaker", ""),
            "speaker_role": ins.get("speaker_role", ""),
            "timestamp": ins.get("timestamp"),
            "confidence": _numeric_to_text_confidence(ins.get("confidence", "")),
            "tags": ins.get("tags") or [],
        }

    # Correct format - just normalize confidence
    return {
        "summary": ins.get("summary", ""),
        "category": ins.get("category", ""),
        "speaker": ins.get("speaker", ""),
        "speaker_role": ins.get("speaker_role", ""),
        "timestamp": ins.get("timestamp"),
        "confidence": _numeric_to_text_confidence(ins.get("confidence", "")),
        "tags": ins.get("tags") or [],
        "quote": ins.get("quote", ""),
    }
```

**Step 4: Update the insights export loop**

Change `src/podstock/dashboard/exporters.py` lines 489-502 from:

```python
            "insights": [
                {
                    "summary": ins.get("summary", ""),
                    ...
                }
                for ins in data.get("insights", [])
            ],
```

To:

```python
            "insights": [
                _normalize_insight_for_export(ins)
                for ins in data.get("insights", [])
            ],
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_normalize_insight.py -v`
Expected: PASS (4 tests)

**Step 6: Commit**

```bash
git add src/podstock/dashboard/exporters.py tests/test_normalize_insight.py
git commit -m "feat(dashboard): normalize insights during export

Ensures dashboard displays insights correctly even with legacy schema.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Enhetlig Master-Prompt

**Files:**
- Modify: `src/podstock/extract/prompt_templates.py` (major rewrite)
- Modify: `scripts/glm_driver.py:216-442` (remove hardcoded prompt)

**Step 1: Backup and read current GLM prompt**

```bash
cp scripts/glm_driver.py scripts/glm_driver.py.bak
```

**Step 2: Update `prompt_templates.py` with merged master prompt**

Replace `EXTRACTION_SYSTEM_PROMPT` in `src/podstock/extract/prompt_templates.py` with:

```python
EXTRACTION_SYSTEM_PROMPT = """Du är en expert på att analysera svenska finanspoddar och extrahera investeringsrekommendationer.

Din uppgift är att noggrant läsa podcast-transkript och identifiera:
1. KONKRETA aktie-rekommendationer (köp, sälj, bevaka, undvik)
2. Vem som ger rekommendationen (host eller gäst)
3. Argumenten bakom rekommendationen
4. Eventuella kursmål eller tidshorisonter
5. DJUPANALYS: För ALLA aktier som diskuteras, skapa detaljerade stock_segments

VIKTIGA RIKTLINJER:
- Var KONSERVATIV: Inkludera bara tydliga rekommendationer, inte vag diskussion
- "Intressant bolag" eller "värt att titta på" = watch, INTE buy
- "Vi äger aktien" utan vidare kontext = hold
- "Stark köpkandidat", "köpläge", "vi köper" = buy
- "Dags att ta hem vinst", "sälj", "vi säljer" = sell
- Fånga EXAKTA citat som stödjer rekommendationen

⏱️ TIMESTAMPS (KRITISKT):
Transkriptet innehåller tidsstämplar i formatet [HH:MM:SS] eller [MM:SS].
DU MÅSTE extrahera timestamp för varje rekommendation!
Sök efter närmaste [XX:XX:XX] före eller vid varje aktie-diskussion.
Om transkriptet har timestamps men du inte hittar en specifik, använd den närmaste.
Lämna ALDRIG null om transkriptet har timestamps.

📈 TICKERS:
- Svenska bolag: Använd Stockholmsbörsen-ticker (t.ex. EVO, HM-B, VOLV-B, HEXA-B)
- Japanska bolag: Använd Tokyo-ticker med .T suffix (t.ex. 3673.T för Broadleaf)
- Amerikanska: Använd NYSE/NASDAQ ticker (t.ex. AAPL, MSFT)
- Om okänd: Lämna null men sätt ALLTID korrekt "market" (sweden/japan/us/hongkong/etc)

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

TAGS (använd relevanta för varje insight):
psychology, timing, diversification, risk_management, position_sizing,
valuation, quality, growth, contrarian, momentum, long_term, patience,
mistakes, success_factors, market_cycles

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
- "30% nedsida härifrån" → "30% downside"
- "Värsta fall 50 SEK" → "Downside 50 SEK"
- "3:1 risk/reward" → "Risk/reward 3:1"

CATALYST TIMING (catalyst_timing):
- "Rapport 15 feb" → "Rapport 2025-02-15"
- "Produktlansering Q2" → "Produktlansering Q2 2025"
- "Efter nästa Fed-möte" → "Efter Fed-möte jan"

📊 STOCK SEGMENTS (DJUPANALYS):
För VARJE aktie som diskuteras (INGEN minimumtröskel), skapa ett detaljerat segment med:
1. ALLA relevanta citat (inte bara ett!) - med kontext (thesis/bull_case/bear_case/metric/conclusion)
2. Finansiella nyckeltal som nämns (P/E, EV/EBITDA, FCF yield, tillväxt, etc.)
3. Bull case: Varför köpa? Vad är positivt?
4. Bear case: Vad kan gå fel? Vilka risker?
5. Katalysatorer: Vad kan driva aktien?
6. Position disclosure: Äger/köpte/sålde talaren aktien?
7. Sammanfattning av hela diskussionen (3-5 meningar)

SPEAKER-IDENTIFIERING:
Om kända hosts anges i prompten:
1. Matcha namn mot kända hosts (fullständigt namn ELLER smeknamn)
2. Gäster introduceras ofta i introt: "Välkommen till X, vd för Y"
3. speaker_role: "host" för kända hosts, "guest" för identifierade gäster
4. Fånga gästens titel/roll om det nämns
5. Om osäker: använd förnamn + speaker_role: "unknown"

OUTPUT:
Returnera ENDAST valid JSON enligt schemat. Ingen annan text."""
```

**Step 3: Add `get_unified_prompt()` function**

Add to end of `src/podstock/extract/prompt_templates.py`:

```python
def get_unified_prompt(
    transcript: str,
    podcast_name: str,
    date: str,
    filename: str,
    hosts: list[str] | None = None,
    episode_id: str | None = None,
) -> str:
    """Get unified analysis prompt for both Claude and GLM.

    Returns a single combined prompt string suitable for any LLM.
    """
    hosts_str = ", ".join(hosts) if hosts else "Okända (extrahera från introt)"

    # Build JSON schema inline
    schema = '''
{
  "schema_version": "2.1",
  "episode_id": "''' + (episode_id or filename.replace('.txt', '')) + '''",
  "podcast_name": "Podcastens namn",
  "episode_title": "Avsnittets titel om känd",
  "episode_number": null,
  "date": "YYYY-MM-DD",
  "hosts": ["host1", "host2"],
  "guests": ["gäst1"],
  "main_topics": ["ämne1", "ämne2"],
  "stocks_discussed": ["Aktie1", "Aktie2"],
  "recommendations": [
    {
      "stock_name": "Aktiens namn",
      "ticker": null,
      "action": "buy|sell|hold|watch|avoid",
      "confidence": "high|medium|low|speculative",
      "speaker": "Vem som pratar",
      "speaker_role": "host|guest|unknown",
      "timestamp": null,
      "reasoning": "DETALJERAD motivering (50-100 ord)",
      "price_target": null,
      "time_horizon": null,
      "quote": "Exakt citat, max 200 ord",
      "sector": null,
      "market": "sweden|us|europe|other|unknown",
      "position_context": null,
      "downside_note": null,
      "catalyst_timing": null
    }
  ],
  "stock_segments": [
    {
      "stock_name": "Aktiens namn",
      "ticker": null,
      "timestamp_start": "HH:MM:SS",
      "timestamp_end": "HH:MM:SS",
      "speakers": ["Talare1"],
      "primary_speaker": "Huvudtalare",
      "discussion_summary": "3-5 meningar",
      "quotes": [
        {
          "speaker": "Namn",
          "text": "Exakt citat...",
          "timestamp": "HH:MM:SS",
          "context": "thesis|bull_case|bear_case|metric|conclusion|other"
        }
      ],
      "financial_metrics": {
        "pe_ratio": null,
        "ev_ebitda": null,
        "fcf_yield": null,
        "margin": null,
        "revenue_growth": null,
        "custom": []
      },
      "thesis": {
        "bull_case": [],
        "bear_case": [],
        "catalysts": [],
        "risks": []
      },
      "position_disclosure": "owns|bought|sold|none|unknown"
    }
  ],
  "insights": [
    {
      "quote": "Exakt citat med investeringsvisdom",
      "summary": "1-2 meningar sammanfattning",
      "category": "philosophy|lesson|wisdom",
      "speaker": "Vem som sa det",
      "speaker_role": "host|guest|unknown",
      "timestamp": null,
      "confidence": "high|medium|low",
      "tags": ["relevanta", "taggar"]
    }
  ],
  "crypto_mentions": [
    {
      "asset_symbol": "BTC|ETH|SOL|etc",
      "asset_name": "Bitcoin|Ethereum|etc",
      "sentiment": "bullish|bearish|neutral|mixed",
      "speaker": "Vem",
      "quote": "Stödjande citat",
      "confidence": "high|medium|low"
    }
  ],
  "market_sentiment": "bullish|bearish|neutral|mixed",
  "summary": "3-5 meningar",
  "key_takeaways": ["punkt1", "punkt2", "punkt3"]
}'''

    prompt = f"""{EXTRACTION_SYSTEM_PROMPT}

{FEW_SHOT_EXAMPLE}

---

PODCAST: {podcast_name}
DATUM: {date}
FIL: {filename}
KÄNDA HOSTS: {hosts_str}

OUTPUT SCHEMA:
{schema}

---
TRANSKRIPT:
{transcript}
---

Returnera ENDAST valid JSON enligt schemat ovan (ingen markdown, inga code blocks)."""

    return prompt
```

**Step 4: Update `glm_driver.py` to use unified prompt**

Replace lines 216-442 in `scripts/glm_driver.py` with:

```python
            # Import unified prompt
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
            from podstock.extract.prompt_templates import get_unified_prompt, get_podcast_hosts

            # Get podcast info from filename
            parts = episode_stem.split("-")
            podcast_id = parts[0] if parts else None
            date = f"{parts[1]}-{parts[2]}-{parts[3]}" if len(parts) >= 4 else "unknown"
            hosts = get_podcast_hosts(podcast_id) if podcast_id else []

            # Get podcast name
            podcast_name = podcast_id or "Okänd podcast"
            podcasts_file = Path(__file__).parent.parent / "data" / "podcasts.json"
            if podcasts_file.exists() and podcast_id:
                import json
                pdata = json.loads(podcasts_file.read_text(encoding="utf-8"))
                for p in pdata.get("podcasts", []):
                    if p.get("id") == podcast_id:
                        podcast_name = p.get("name", podcast_id)
                        break

            prompt = get_unified_prompt(
                transcript=content,
                podcast_name=podcast_name,
                date=date,
                filename=transcript_path.name,
                hosts=hosts,
                episode_id=episode_stem,
            )
```

**Step 5: Test manually**

```bash
# Test that GLM driver still works
python3 scripts/glm_driver.py data/transcripts/borspodden/borspodden-2026-01-14-test.txt data/podcasts/analyses-v2/ --dry-run
```

**Step 6: Commit**

```bash
git add src/podstock/extract/prompt_templates.py scripts/glm_driver.py
git commit -m "feat(extract): unified prompt for Claude and GLM

Single source of truth for analysis prompts.
- Merged best parts from GLM and Claude prompts
- No minimum threshold for stock_segments
- Added get_unified_prompt() function
- GLM driver now imports from prompt_templates.py

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Körningsrapport Datastruktur

**Files:**
- Create: `src/podstock/orchestration/report.py`
- Create: `logs/orchestration/.gitkeep`

**Step 1: Create directory structure**

```bash
mkdir -p src/podstock/orchestration
mkdir -p logs/orchestration
touch src/podstock/orchestration/__init__.py
touch logs/orchestration/.gitkeep
```

**Step 2: Write the report module**

Create `src/podstock/orchestration/report.py`:

```python
"""Orchestration run reports."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class TranscriptDownload:
    """Record of a downloaded transcript."""
    filename: str
    destination: str
    source: str  # "apple" or "whisper"


@dataclass
class AnalysisResult:
    """Record of an analysis."""
    filename: str
    destination: str
    recommendations: int
    stock_segments: int
    insights: int


@dataclass
class ImprovementObservation:
    """Observed issue that could be improved."""
    category: str  # critical/quality/optimization/skill
    description: str
    suggested_fix: str
    file_path: str | None
    auto_fixable: bool
    evidence: str


@dataclass
class OrchestrationReport:
    """Complete report of an orchestration run."""

    timestamp: datetime = field(default_factory=datetime.now)
    model_used: str = ""

    # Downloads
    transcripts: list[TranscriptDownload] = field(default_factory=list)

    # Analyses
    analyses: list[AnalysisResult] = field(default_factory=list)

    # Totals
    total_recommendations: int = 0
    total_segments: int = 0
    total_insights: int = 0
    new_tickers: list[str] = field(default_factory=list)

    # Timing
    timing: dict[str, float] = field(default_factory=dict)

    # Improvements
    improvements: list[ImprovementObservation] = field(default_factory=list)

    def add_transcript(self, filename: str, destination: str, source: str):
        """Add a downloaded transcript."""
        self.transcripts.append(TranscriptDownload(filename, destination, source))

    def add_analysis(self, filename: str, destination: str, recs: int, segs: int, ins: int):
        """Add an analysis result."""
        self.analyses.append(AnalysisResult(filename, destination, recs, segs, ins))
        self.total_recommendations += recs
        self.total_segments += segs
        self.total_insights += ins

    def add_improvement(
        self,
        category: str,
        description: str,
        suggested_fix: str,
        file_path: str | None = None,
        auto_fixable: bool = False,
        evidence: str = ""
    ):
        """Add an improvement observation."""
        self.improvements.append(ImprovementObservation(
            category=category,
            description=description,
            suggested_fix=suggested_fix,
            file_path=file_path,
            auto_fixable=auto_fixable,
            evidence=evidence
        ))

    def to_terminal(self) -> str:
        """Format report for terminal output."""
        lines = [
            "═" * 65,
            f"📊 KÖRNINGSRAPPORT - {self.timestamp.strftime('%Y-%m-%d %H:%M')}",
            "═" * 65,
            "",
        ]

        # Downloads
        if self.transcripts:
            lines.append(f"📥 NEDLADDADE TRANSKRIPT ({len(self.transcripts)} st)")
            for t in self.transcripts:
                source_icon = "🍎" if t.source == "apple" else "🎙️"
                lines.append(f"   {source_icon} {t.filename}")
                lines.append(f"      → {t.destination}")
            lines.append("")

        # Analyses
        if self.analyses:
            lines.append(f"📝 ANALYSER ({len(self.analyses)} st, modell: {self.model_used})")
            for a in self.analyses:
                lines.append(f"   • {a.filename}")
                lines.append(f"     └─ {a.recommendations} recs, {a.stock_segments} segments, {a.insights} insights")
            lines.append("")

        # Summary
        lines.append("📈 SAMMANFATTNING")
        lines.append(f"   • Totalt rekommendationer: {self.total_recommendations}")
        lines.append(f"   • Totalt stock_segments:   {self.total_segments}")
        lines.append(f"   • Totalt insights:         {self.total_insights}")
        if self.new_tickers:
            lines.append(f"   • Nya tickers:             {', '.join(self.new_tickers)}")
        lines.append("")

        # Timing
        if self.timing:
            lines.append("⏱️  TIMING")
            total = sum(self.timing.values())
            for step, duration in self.timing.items():
                if duration >= 60:
                    time_str = f"{int(duration // 60)}m {int(duration % 60)}s"
                else:
                    time_str = f"{int(duration)}s"
                lines.append(f"   • {step}: {time_str}")
            if total >= 60:
                lines.append(f"   • Total: {int(total // 60)}m {int(total % 60)}s")
            lines.append("")

        # Improvements
        if self.improvements:
            lines.append("💡 FÖRBÄTTRINGSFÖRSLAG")
            for i, imp in enumerate(self.improvements, 1):
                icon = {"critical": "🔴", "quality": "🟡", "optimization": "🟢", "skill": "🔵"}.get(imp.category, "⚪")
                lines.append(f"   {icon} {i}. {imp.description}")
                lines.append(f"      Förslag: {imp.suggested_fix}")
            lines.append("")

        lines.append("═" * 65)

        return "\n".join(lines)

    def to_markdown(self) -> str:
        """Format report as markdown for file storage."""
        lines = [
            f"# Körningsrapport {self.timestamp.strftime('%Y-%m-%d %H:%M')}",
            "",
            f"**Modell:** {self.model_used}",
            "",
        ]

        # Downloads
        if self.transcripts:
            lines.append(f"## Nedladdade transkript ({len(self.transcripts)} st)")
            lines.append("")
            lines.append("| Fil | Destination | Källa |")
            lines.append("|-----|-------------|-------|")
            for t in self.transcripts:
                lines.append(f"| {t.filename} | {t.destination} | {t.source} |")
            lines.append("")

        # Analyses
        if self.analyses:
            lines.append(f"## Analyser ({len(self.analyses)} st)")
            lines.append("")
            lines.append("| Fil | Recs | Segments | Insights |")
            lines.append("|-----|------|----------|----------|")
            for a in self.analyses:
                lines.append(f"| {a.filename} | {a.recommendations} | {a.stock_segments} | {a.insights} |")
            lines.append("")

        # Summary
        lines.append("## Sammanfattning")
        lines.append("")
        lines.append(f"- **Totalt rekommendationer:** {self.total_recommendations}")
        lines.append(f"- **Totalt stock_segments:** {self.total_segments}")
        lines.append(f"- **Totalt insights:** {self.total_insights}")
        if self.new_tickers:
            lines.append(f"- **Nya tickers:** {', '.join(self.new_tickers)}")
        lines.append("")

        # Timing
        if self.timing:
            lines.append("## Timing")
            lines.append("")
            lines.append("| Steg | Tid |")
            lines.append("|------|-----|")
            for step, duration in self.timing.items():
                if duration >= 60:
                    time_str = f"{int(duration // 60)}m {int(duration % 60)}s"
                else:
                    time_str = f"{int(duration)}s"
                lines.append(f"| {step} | {time_str} |")
            lines.append("")

        # Improvements
        if self.improvements:
            lines.append("## Förbättringsförslag")
            lines.append("")
            for imp in self.improvements:
                lines.append(f"### [{imp.category.upper()}] {imp.description}")
                lines.append("")
                lines.append(f"**Förslag:** {imp.suggested_fix}")
                if imp.file_path:
                    lines.append(f"**Fil:** `{imp.file_path}`")
                lines.append(f"**Auto-fix:** {'Ja' if imp.auto_fixable else 'Nej'}")
                if imp.evidence:
                    lines.append(f"**Bevis:** {imp.evidence}")
                lines.append("")
        else:
            lines.append("## Förbättringsförslag")
            lines.append("")
            lines.append("_Inga observerade problem denna körning._")
            lines.append("")

        return "\n".join(lines)

    def save(self, logs_dir: Path | None = None) -> Path:
        """Save report to logs/orchestration/ directory."""
        if logs_dir is None:
            logs_dir = Path("logs/orchestration")
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Save timestamped file
        filename = f"{self.timestamp.strftime('%Y-%m-%dT%H-%M-%S')}.md"
        filepath = logs_dir / filename
        filepath.write_text(self.to_markdown(), encoding="utf-8")

        # Update latest symlink/copy
        latest = logs_dir / "latest.md"
        latest.write_text(self.to_markdown(), encoding="utf-8")

        return filepath
```

**Step 3: Commit**

```bash
git add src/podstock/orchestration/ logs/orchestration/.gitkeep
git commit -m "feat(orchestration): add run report module

OrchestrationReport class for tracking and displaying run results.
- Terminal output with colors/icons
- Markdown output for persistent logs
- Saves to logs/orchestration/ with timestamps

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Retroaktiv Fix Script

**Files:**
- Create: `scripts/fix_insight_schema.py`

**Step 1: Write the fix script**

Create `scripts/fix_insight_schema.py`:

```python
#!/usr/bin/env python3
"""Fix insight schema in existing analysis files.

Transforms wrong format (topic/insight) to correct v2.1 (quote/summary/category/tags).
Creates .bak backups before modifying files.
"""

import json
import shutil
from pathlib import Path


def normalize_insight(ins: dict) -> dict:
    """Transform wrong insight schema to correct v2.1 format."""
    if "summary" in ins and "quote" in ins:
        return ins  # Already correct

    if "insight" in ins or "topic" in ins:
        insight_text = ins.get("insight", ins.get("topic", ""))
        return {
            "quote": insight_text,
            "summary": insight_text,
            "category": ins.get("category", "wisdom"),
            "speaker": ins.get("speaker", ""),
            "speaker_role": ins.get("speaker_role", "unknown"),
            "timestamp": ins.get("timestamp"),
            "confidence": ins.get("confidence", "medium"),
            "tags": ins.get("tags", [])
        }

    return ins


def fix_file(filepath: Path, dry_run: bool = False) -> tuple[bool, int]:
    """Fix insights in a single file.

    Returns: (was_modified, num_insights_fixed)
    """
    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  ⚠️  Could not read {filepath.name}: {e}")
        return False, 0

    insights = data.get("insights", [])
    if not insights:
        return False, 0

    fixed_count = 0
    new_insights = []

    for ins in insights:
        # Check if needs fixing
        needs_fix = "summary" not in ins and ("insight" in ins or "topic" in ins)
        if needs_fix:
            new_insights.append(normalize_insight(ins))
            fixed_count += 1
        else:
            new_insights.append(ins)

    if fixed_count == 0:
        return False, 0

    if dry_run:
        print(f"  📝 Would fix {fixed_count} insights in {filepath.name}")
        return True, fixed_count

    # Create backup
    backup_path = filepath.with_suffix(".json.bak")
    shutil.copy2(filepath, backup_path)

    # Write fixed data
    data["insights"] = new_insights
    filepath.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"  ✅ Fixed {fixed_count} insights in {filepath.name}")
    return True, fixed_count


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fix insight schema in analysis files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be fixed without modifying")
    parser.add_argument("--path", default="data/podcasts/analyses-v2", help="Path to analyses directory")
    args = parser.parse_args()

    analyses_dir = Path(args.path)
    if not analyses_dir.exists():
        print(f"❌ Directory not found: {analyses_dir}")
        return 1

    print(f"{'DRY RUN - ' if args.dry_run else ''}Scanning {analyses_dir}...")
    print()

    files_fixed = 0
    insights_fixed = 0

    for filepath in sorted(analyses_dir.glob("*-20??-??-??-????.json")):
        was_modified, count = fix_file(filepath, dry_run=args.dry_run)
        if was_modified:
            files_fixed += 1
            insights_fixed += count

    print()
    print("=" * 50)
    if args.dry_run:
        print(f"Would fix {insights_fixed} insights in {files_fixed} files")
    else:
        print(f"✅ Fixed {insights_fixed} insights in {files_fixed} files")
        if files_fixed > 0:
            print(f"   Backups created with .bak extension")

    return 0


if __name__ == "__main__":
    exit(main())
```

**Step 2: Test with dry-run**

```bash
python3 scripts/fix_insight_schema.py --dry-run
```

**Step 3: Commit**

```bash
git add scripts/fix_insight_schema.py
git commit -m "feat(scripts): add insight schema fix script

Retroactively fixes wrong insight format (topic/insight) to correct v2.1.
- Creates .bak backups before modifying
- Supports --dry-run for preview
- Reports total files and insights fixed

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Uppdatera Orchestration Skill

**Files:**
- Modify: `.claude/skills/orchestrate-podcast-publish/SKILL.md`

**Step 1: Add model selection step after pre-flight**

Insert after "## Steg 1: Pre-flight Check" section (around line 65):

```markdown
---

## Steg 1b: Välj Analysmodell

**ALLTID FRÅGA ANVÄNDAREN:**

```
"X transkript att analysera. Vilken modell vill du använda?"

Options:
1. Claude (rekommenderas för kvalitet)
2. GLM-4.7 (snabbare, gratis)
```

Använd AskUserQuestion med dessa alternativ. Spara valet för användning i Steg 3.
```

**Step 2: Add run report section at end**

Replace "## Steg 6: Slutrapport" with:

```markdown
---

## Steg 6: Körningsrapport

**VIKTIGT:** Visa ALLTID körningsrapport efter avslutad körning.

```python
from podstock.orchestration.report import OrchestrationReport

# Skapa rapport (populera under körningen)
report = OrchestrationReport()
report.model_used = selected_model  # "Claude" eller "GLM-4.7"

# Lägg till nedladdningar
for t in downloaded_transcripts:
    report.add_transcript(t["filename"], t["destination"], t["source"])

# Lägg till analyser
for a in completed_analyses:
    report.add_analysis(
        a["filename"],
        a["destination"],
        a["recommendations"],
        a["stock_segments"],
        a["insights"]
    )

# Lägg till timing
report.timing = {
    "Nedladdning": download_time,
    "Analys": analysis_time,
    "Databas-synk": sync_time,
    "Dashboard": dashboard_time,
}

# Visa i terminal
print(report.to_terminal())

# Spara till fil
saved_path = report.save()
print(f"\n📁 Rapport sparad: {saved_path}")
```

---

## Steg 7: Förbättringsförslag (Självläkning)

**Efter körningsrapporten, om förbättringar observerats:**

```
if report.improvements:
    print("\n💡 FÖRBÄTTRINGSFÖRSLAG")
    for i, imp in enumerate(report.improvements, 1):
        print(f"  {i}. [{imp.category}] {imp.description}")
        print(f"     Förslag: {imp.suggested_fix}")

    # Fråga användaren
    answer = AskUserQuestion(
        "Vill du att jag åtgärdar dessa förbättringar?",
        options=["Ja, åtgärda alla", "Visa detaljer först", "Nej, hoppa över"]
    )

    if answer == "Ja, åtgärda alla":
        for imp in report.improvements:
            if imp.auto_fixable:
                # Applicera fix
                apply_improvement(imp)
else:
    print("\n✨ Inga förbättringar att föreslå - allt ser bra ut!")
```

**Typer av förbättringar att observera under körning:**

| Observation | Kategori | Auto-fix |
|-------------|----------|----------|
| Insight med fel schema | quality | Ja |
| Saknad ticker-mappning | quality | Ja (lägg till i pending) |
| Timeout på analys | optimization | Ja (öka timeout) |
| Schema-version <2.1 | critical | Ja (uppgradera) |
| Prompt-inkonsekvens | skill | Fråga först |

**VIKTIGT:** Föreslå ENDAST om det finns något tydligt att förbättra. Krysta inte fram feedback.
```

**Step 3: Commit**

```bash
git add .claude/skills/orchestrate-podcast-publish/SKILL.md
git commit -m "feat(skill): add model selection and run reports

Updates orchestration skill with:
- Model selection prompt (Claude vs GLM)
- Run report generation and display
- Self-healing improvement suggestions
- Saves reports to logs/orchestration/

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Kör Retroaktiv Fix

**Step 1: Run dry-run first**

```bash
python3 scripts/fix_insight_schema.py --dry-run
```

**Step 2: Run actual fix**

```bash
python3 scripts/fix_insight_schema.py
```

**Step 3: Verify fixes**

```bash
# Check a fixed file
cat data/podcasts/analyses-v2/marketmakers-2026-01-15-78d2.json | jq '.insights[0]'
```

Expected: Should show `quote`, `summary`, `category`, `tags` fields.

**Step 4: Regenerate dashboard**

```bash
.venv/bin/python -m podstock dashboard generate --no-embed
```

**Step 5: Commit fixed files**

```bash
git add data/podcasts/analyses-v2/*.json
git commit -m "fix(data): normalize insight schema in existing analyses

Applied fix_insight_schema.py to convert legacy format to v2.1.
Backups saved with .bak extension.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Verifiering

Efter alla tasks, verifiera:

1. **Schema-normalisering:**
   ```bash
   pytest tests/test_normalize_insight.py -v
   ```

2. **Enhetlig prompt:**
   ```bash
   python3 -c "from podstock.extract.prompt_templates import get_unified_prompt; print(len(get_unified_prompt('test', 'Test', '2026-01-15', 'test.txt')))"
   ```
   Expected: ~8000+ characters

3. **Körningsrapport:**
   ```bash
   python3 -c "from podstock.orchestration.report import OrchestrationReport; r = OrchestrationReport(); r.add_analysis('test.json', 'data/', 5, 3, 2); print(r.to_terminal())"
   ```

4. **Dashboard visar insights korrekt:**
   - Kör `open data/dashboard/index.html`
   - Kontrollera att "Insikter:" sektionen visar text, inte bara namn

5. **Full orchestration test:**
   - Kör `/orchestrate-podcast-publish`
   - Verifiera modellval-prompt
   - Verifiera körningsrapport visas och sparas
