# Analysarkitektur i PodStock

**Version:** 1.0
**Datum:** 2025-12-27

---

## 1. Översikt

PodStock har fyra analysmoduler som följer ett gemensamt mönster:

| Modul | Källa | Output-modell | Lagringsplats |
|-------|-------|---------------|---------------|
| `extract/` | Podcast-transkript | `EpisodeAnalysis` | `data/extracted/glm-batch/` |
| `crypto/` | YouTube-transkript | `CryptoSentimentAnalysis` | `data/crypto/` |
| `twitter/` | Tweets | `TweetAnalysis` | `data/twitter/analysis/` |
| `filings/` | Årsredovisningar (PDF) | `FilingAnalysis` | `data/filings/analysis/` |

---

## 2. Dataflöde

Alla analyser följer samma grundflöde:

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│    INPUT     │───▶│   PROMPT     │───▶│     LLM      │───▶│   OUTPUT     │
│  (text/PDF)  │    │   BUILDER    │    │  (Claude)    │    │   (JSON)     │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
   Transkript        System prompt       JSON-respons       Pydantic-modell
   Tweet-text        User prompt         (markdown-wrapped) → JSON-fil
   PDF-text          Few-shot exempel
```

---

## 3. Gemensamma Komponenter

### 3.1 LLM-klient

Alla moduler använder `LLMClient` från `extract/llm_client.py`:

```python
from podstock.extract.llm_client import create_llm_client

# Skapa klient
client = create_llm_client(
    model_spec="claude-sonnet-4-20250514",  # eller "ollama:llama3.3"
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

# Generera analys
response = client.generate(
    system_prompt="Du är en finansanalytiker...",
    user_prompt="Analysera följande transkript: ...",
    max_tokens=8000
)
```

### 3.2 JSON-parsing

LLM-responser kan vara wrappade i markdown code blocks. Använd gemensam parser:

```python
from podstock.analysis import extract_json_from_response, parse_llm_json

# Extrahera JSON-sträng
json_str = extract_json_from_response(response)

# Eller parsa direkt till dict
data = parse_llm_json(response)
```

### 3.3 Pydantic-modeller

Alla analyser valideras med Pydantic:

```python
from pydantic import BaseModel
from typing import Literal

class StockRecommendation(BaseModel):
    stock_name: str
    ticker: str | None = None
    action: Literal["buy", "sell", "hold", "watch", "avoid"]
    confidence: Literal["high", "medium", "low", "speculative"]
    reasoning: str
    quote: str
```

---

## 4. Modulstruktur

Varje analysmodul har följande struktur:

```
src/podstock/{modul}/
├── __init__.py
├── models.py          # Pydantic-modeller (Input + Output)
├── analyzer.py        # Huvudlogik (Analyzer-klass)
├── prompt_templates.py # System/user prompts + few-shot exempel
└── README.md          # Moduldokumentation
```

---

## 5. Hur man skapar en ny analystyp

### Steg 1: Definiera datamodeller

Skapa `models.py` med input- och output-modeller:

```python
# src/podstock/nymodul/models.py

from pydantic import BaseModel
from typing import Literal
from datetime import datetime

class NyAnalysis(BaseModel):
    """Output från analysen."""
    source_id: str
    date: str

    # Domänspecifika fält
    findings: list[str]
    sentiment: Literal["positive", "negative", "neutral"]
    confidence: Literal["high", "medium", "low"]

    # Metadata
    model_used: str
    processed_at: datetime
```

### Steg 2: Skapa prompt-templates

Definiera system- och user-prompts i `prompt_templates.py`:

```python
# src/podstock/nymodul/prompt_templates.py

SYSTEM_PROMPT = """Du är en expert på [domän].

Din uppgift är att analysera [innehållstyp] och extrahera:
1. [Fält 1]
2. [Fält 2]
3. [Fält 3]

Returnera ENDAST valid JSON enligt detta schema:
{
  "source_id": "string",
  "findings": ["string"],
  "sentiment": "positive | negative | neutral",
  "confidence": "high | medium | low"
}
"""

USER_PROMPT = """Analysera följande {content_type}:

Källa: {source_id}
Datum: {date}

Innehåll:
{content}

Extrahera information enligt instruktionerna."""

FEW_SHOT_EXAMPLE = """
Exempel på korrekt output:
```json
{
  "source_id": "exempel-123",
  "findings": ["Stark tillväxt", "Ökade marginaler"],
  "sentiment": "positive",
  "confidence": "high"
}
```
"""
```

### Steg 3: Implementera Analyzer

Skapa `analyzer.py` med huvudlogiken:

```python
# src/podstock/nymodul/analyzer.py

from pathlib import Path
from datetime import datetime

from podstock.extract.llm_client import create_llm_client, LLMClient
from podstock.analysis import parse_llm_json

from .models import NyAnalysis
from .prompt_templates import SYSTEM_PROMPT, USER_PROMPT, FEW_SHOT_EXAMPLE


class NyAnalyzer:
    """Analyserar [innehållstyp] med LLM."""

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        model: str = "claude-sonnet-4-20250514",
    ):
        self.client = llm_client or create_llm_client(model)
        self.model = model

    def analyze(self, content: str, source_id: str, date: str) -> NyAnalysis:
        """Analysera innehåll och returnera strukturerad analys.

        Args:
            content: Textinnehåll att analysera.
            source_id: Unik identifierare för källan.
            date: Datum i ISO-format (YYYY-MM-DD).

        Returns:
            NyAnalysis med extraherad information.
        """
        # Bygg prompt
        system = SYSTEM_PROMPT + "\n\n" + FEW_SHOT_EXAMPLE
        user = USER_PROMPT.format(
            content_type="[typ]",
            source_id=source_id,
            date=date,
            content=content[:100000],  # Begränsa storlek
        )

        # Anropa LLM
        response = self.client.generate(
            system_prompt=system,
            user_prompt=user,
            max_tokens=4000,
        )

        # Parsa respons
        data = parse_llm_json(response)

        # Lägg till metadata
        data["model_used"] = self.model
        data["processed_at"] = datetime.now().isoformat()

        return NyAnalysis(**data)

    def save(self, analysis: NyAnalysis, output_dir: Path) -> Path:
        """Spara analys till JSON-fil.

        Args:
            analysis: Analys att spara.
            output_dir: Katalog för output.

        Returns:
            Sökväg till sparad fil.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{analysis.source_id}-analysis.json"
        output_path = output_dir / filename

        output_path.write_text(
            analysis.model_dump_json(indent=2),
            encoding="utf-8"
        )

        return output_path
```

### Steg 4: Lägg till CLI-kommando (valfritt)

Exponera via CLI i `cli.py`:

```python
# I src/podstock/cli.py

def cmd_analyze_ny(args):
    """Analysera [innehållstyp]."""
    from podstock.nymodul.analyzer import NyAnalyzer

    analyzer = NyAnalyzer(model=args.model)
    analysis = analyzer.analyze(
        content=Path(args.input).read_text(),
        source_id=args.source_id,
        date=args.date,
    )

    output_path = analyzer.save(analysis, Path(args.output_dir))
    print(f"Analys sparad: {output_path}")
```

---

## 6. Schema-konventioner

### 6.1 Gemensamma fält

Alla analysmodeller bör ha:

| Fält | Typ | Beskrivning |
|------|-----|-------------|
| `source_id` | `str` | Unik identifierare för källan |
| `date` | `str` | Datum i ISO-format (YYYY-MM-DD) |
| `model_used` | `str` | LLM-modell som användes |
| `processed_at` | `datetime` | Tidpunkt för analys |

### 6.2 Sentiment/Action-enums

Standardiserade värden för sentiment och åtgärder:

**Sentiment:**
- `very_bullish`, `bullish`, `neutral`, `bearish`, `very_bearish`
- Eller förenklat: `positive`, `negative`, `neutral`

**Action (för rekommendationer):**
- `buy`, `sell`, `hold`, `watch`, `avoid`

**Confidence:**
- `high`, `medium`, `low`, `speculative`

### 6.3 Namnkonventioner

- Modeller: `PascalCase` (t.ex. `EpisodeAnalysis`, `CryptoMention`)
- Fält: `snake_case` (t.ex. `stock_name`, `price_target`)
- Filer: `kebab-case` (t.ex. `borspodden-2025-01-15-analysis.json`)

---

## 7. Prompt-design Guidelines

### 7.1 System Prompt

Bör innehålla:
1. **Roll**: Vem är AI:n? (t.ex. "finansanalytiker")
2. **Uppgift**: Vad ska göras?
3. **Output-format**: Exakt JSON-schema
4. **Begränsningar**: Vad ska INTE göras

### 7.2 Few-shot Exempel

Inkludera alltid minst ett exempel på korrekt output. Detta förbättrar:
- JSON-formattering avsevärt
- Konsistens i fältnamn
- Rätt användning av enums

### 7.3 User Prompt

Strukturera med tydliga sektioner:
```
Analysera följande {typ}:

Källa: {metadata}
Datum: {datum}

Innehåll:
{faktiskt innehåll}

Extrahera: {specifika instruktioner}
```

---

## 8. Unified Signal Layer

För att normalisera output från olika analystyper, använd `unified/models.py`:

```python
from podstock.unified.models import Signal, SignalNormalizer

# Konvertera podcast-rekommendation till Signal
signal = Signal(
    source_type="podcast",
    source_id="borspodden",
    content_id="borspodden-2025-01-15-abc1",
    asset_symbol="EVO",
    signal=SignalNormalizer.normalize_podcast_action("buy"),
    signal_strength=SignalNormalizer.normalize_confidence("high"),
    # ...
)
```

Se `unified/importers/` för exempel på hur olika analystyper importeras.

---

## 9. Testning

Varje analysmodul bör ha tester för:

1. **Modeller**: Validering av Pydantic-modeller
2. **JSON-parsing**: Hantering av olika LLM-responsformat
3. **Integration**: End-to-end med mock LLM-klient

Exempel:
```python
def test_ny_analysis_model():
    analysis = NyAnalysis(
        source_id="test-123",
        date="2025-01-15",
        findings=["Test finding"],
        sentiment="positive",
        confidence="high",
        model_used="test",
        processed_at=datetime.now(),
    )
    assert analysis.sentiment == "positive"
```

---

## 10. Befintliga Analysmoduler

### 10.1 Podcast (`extract/`)

- **Input**: Transkript från Apple Podcasts eller Whisper
- **Output**: `EpisodeAnalysis` med `StockRecommendation` och `StockSegment`
- **Schema**: Se `docs/JSON-SCHEMA.md`

### 10.2 Crypto (`crypto/`)

- **Input**: YouTube-transkript från kryptokanaler
- **Output**: `CryptoSentimentAnalysis` med `CryptoMention`
- **Fokus**: Bitcoin/altcoin sentiment, price predictions

### 10.3 Twitter (`twitter/`)

- **Input**: Tweets från finansprofiler
- **Output**: `TweetAnalysis` med `StockMention`
- **Fokus**: Aktierekommendationer från Twitter

### 10.4 Filings (`filings/`)

- **Input**: Årsredovisningar (PDF)
- **Output**: `FilingAnalysis` med `DocumentChunk`
- **Metod**: Multi-pass (chunking → analys → syntes)

---

## 11. Nästa steg

1. Läs modulspecifik README i respektive katalog
2. Studera `extract/process_transcript.py` som referensimplementation
3. Använd `podstock.analysis` för gemensamma utilities
