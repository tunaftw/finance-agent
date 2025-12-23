# PodStock – Architecture Document

**Version:** 1.0  
**Datum:** 2024-12-21

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         PodStock CLI                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐    ┌─────────────┐    ┌──────────────┐            │
│  │   RSS   │───▶│  Downloader │───▶│   Audio      │            │
│  │  Parser │    │             │    │   Storage    │            │
│  └─────────┘    └─────────────┘    └──────────────┘            │
│                                           │                     │
│                                           ▼                     │
│                                    ┌──────────────┐            │
│                                    │   Whisper    │            │
│                                    │ Transcriber  │            │
│                                    └──────────────┘            │
│                                           │                     │
│                                           ▼                     │
│                                    ┌──────────────┐            │
│                                    │  Transcript  │            │
│                                    │   Storage    │            │
│                                    └──────────────┘            │
│                                           │                     │
│                                           ▼                     │
│  ┌──────────────┐               ┌──────────────────┐           │
│  │    Claude    │◀─── prompt ───│  Prompt Builder  │           │
│  │   (manual)   │               └──────────────────┘           │
│  └──────────────┘                        │                     │
│         │                                │                     │
│         │ analysis result                │                     │
│         ▼                                ▼                     │
│  ┌──────────────┐               ┌──────────────────┐           │
│  │    Parser    │───────────────│  Recommendation  │           │
│  │              │               │     Storage      │           │
│  └──────────────┘               └──────────────────┘           │
│                                           │                     │
│                                           ▼                     │
│                                    ┌──────────────┐            │
│                                    │   Reporter   │            │
│                                    │  (Markdown)  │            │
│                                    └──────────────┘            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Directory Structure

```
podstock/
├── README.md                    # Quick start guide
├── PRD.md                       # Product requirements (reference)
├── ARCHITECTURE.md              # This file
├── IMPLEMENTATION.md            # Implementation checklist
├── CONVENTIONS.md               # Coding conventions
├── pyproject.toml               # Project configuration
├── requirements.txt             # Dependencies
│
├── src/
│   └── podstock/
│       ├── __init__.py
│       ├── __main__.py          # Entry point: python -m podstock
│       ├── cli.py               # CLI commands (argparse)
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py        # Configuration management
│       │   ├── state.py         # State/progress tracking
│       │   └── models.py        # Pydantic data models
│       │
│       ├── rss/
│       │   ├── __init__.py
│       │   ├── parser.py        # RSS feed parsing
│       │   └── downloader.py    # Audio file downloading
│       │
│       ├── transcribe/
│       │   ├── __init__.py
│       │   └── whisper.py       # mlx-whisper integration
│       │
│       ├── analyze/
│       │   ├── __init__.py
│       │   ├── prompt_builder.py  # Generate Claude prompts
│       │   └── result_parser.py   # Parse Claude responses
│       │
│       └── report/
│           ├── __init__.py
│           └── markdown.py      # Markdown report generator
│
├── prompts/
│   └── analyze_transcript.md    # Template for Claude analysis
│
├── data/                        # All runtime data (gitignored)
│   ├── config.json              # User configuration
│   ├── state.json               # Processing state
│   ├── podcasts.json            # Podcast definitions
│   │
│   ├── audio/                   # Downloaded audio files
│   │   └── {podcast_id}/
│   │       └── {episode_id}.mp3
│   │
│   ├── transcripts/             # Transcribed text
│   │   └── {podcast_id}/
│   │       └── {episode_id}.txt
│   │
│   ├── recommendations/         # Extracted recommendations
│   │   └── {podcast_id}/
│   │       └── {episode_id}.json
│   │
│   └── reports/                 # Generated reports
│       └── report_2024-12-21.md
│
└── tests/
    ├── __init__.py
    ├── test_rss_parser.py
    ├── test_models.py
    └── fixtures/
        └── sample_rss.xml
```

---

## 3. Module Responsibilities

### 3.1 `cli.py` – Command Line Interface
Ansvar: Användargränssnitt, validering av input, orkestrering

```python
# Kommandon:
podstock podcast add <name> <rss_url>    # Lägg till podcast
podstock podcast list                     # Lista alla podcasts
podstock download [--podcast <id>] [--latest <n>]  # Ladda ner avsnitt
podstock transcribe [--podcast <id>] [--episode <id>]  # Transkribera
podstock analyze <episode_id>             # Generera prompt + parsa resultat
podstock report [--since <date>]          # Generera rapport
podstock status                           # Visa status för alla avsnitt
```

### 3.2 `core/config.py` – Konfiguration
Ansvar: Läsa/skriva konfiguration, defaultvärden

```python
@dataclass
class Config:
    data_dir: Path
    whisper_model: str = "large-v3"
    audio_format: str = "mp3"
    default_time_horizon: str = "6m"
```

### 3.3 `core/state.py` – Tillståndsspårning
Ansvar: Hålla koll på vad som är gjort, idempotens

```python
class State:
    def is_downloaded(episode_id: str) -> bool
    def is_transcribed(episode_id: str) -> bool
    def is_analyzed(episode_id: str) -> bool
    def mark_downloaded(episode_id: str, path: Path)
    def mark_transcribed(episode_id: str, path: Path)
    def mark_analyzed(episode_id: str, recommendations: list)
```

### 3.4 `core/models.py` – Datamodeller
Ansvar: Typad datastruktur med validering

```python
from pydantic import BaseModel

class Podcast(BaseModel):
    id: str
    name: str
    rss_url: str
    hosts: list[str] = []

class Episode(BaseModel):
    id: str
    podcast_id: str
    title: str
    published_at: datetime
    audio_url: str
    # ...

class Recommendation(BaseModel):
    id: str
    episode_id: str
    company_name: str
    ticker: str | None
    quote: str
    context: str
    time_horizon: str | None
    # ...
```

### 3.5 `rss/parser.py` – RSS-parsing
Ansvar: Hämta och parsa RSS-flöden

```python
def fetch_feed(url: str) -> Feed
def parse_episodes(feed: Feed) -> list[Episode]
def get_latest_episodes(url: str, n: int = 10) -> list[Episode]
```

### 3.6 `rss/downloader.py` – Nedladdning
Ansvar: Ladda ner ljudfiler med progress

```python
def download_episode(episode: Episode, dest_dir: Path) -> Path
def download_with_progress(url: str, dest: Path) -> None
```

### 3.7 `transcribe/whisper.py` – Transkribering
Ansvar: Köra mlx-whisper, hantera output

```python
def transcribe(audio_path: Path, model: str = "large-v3") -> str
def estimate_duration(audio_path: Path) -> int  # seconds
```

### 3.8 `analyze/prompt_builder.py` – Prompt-generering
Ansvar: Bygga optimerade prompts för Claude

```python
def build_analysis_prompt(
    transcript: str,
    podcast_name: str,
    episode_title: str,
    hosts: list[str]
) -> str
```

### 3.9 `analyze/result_parser.py` – Resultatparsning
Ansvar: Parsa Claude's svar till strukturerad data

```python
def parse_claude_response(response: str) -> list[Recommendation]
```

### 3.10 `report/markdown.py` – Rapportgenerering
Ansvar: Skapa läsbara Markdown-rapporter

```python
def generate_report(
    recommendations: list[Recommendation],
    output_path: Path
) -> None
```

---

## 4. Data Flow

### 4.1 Download Flow
```
1. User: podstock download --podcast borspodden --latest 3
2. CLI parses args, loads config
3. RSS Parser fetches feed
4. State checks which episodes exist
5. Downloader downloads missing episodes
6. State marks episodes as downloaded
7. CLI prints summary
```

### 4.2 Transcribe Flow
```
1. User: podstock transcribe --podcast borspodden
2. CLI loads state, finds downloaded but not transcribed episodes
3. For each episode:
   a. Whisper transcribes audio
   b. Transcript saved to file
   c. State updated
4. CLI prints summary
```

### 4.3 Analyze Flow
```
1. User: podstock analyze bp-2024-12-18
2. CLI loads transcript
3. Prompt Builder creates prompt
4. CLI prints prompt + instructions
5. User copies to Claude, gets response
6. User pastes response back (or saves to file)
7. Result Parser extracts recommendations
8. Recommendations saved to JSON
9. State updated
```

---

## 5. State Management

### 5.1 State File Format (`data/state.json`)
```json
{
  "version": 1,
  "last_updated": "2024-12-21T14:30:00Z",
  "episodes": {
    "bp-2024-12-18": {
      "downloaded": true,
      "downloaded_at": "2024-12-21T10:00:00Z",
      "audio_path": "data/audio/borspodden/bp-2024-12-18.mp3",
      "transcribed": true,
      "transcribed_at": "2024-12-21T10:15:00Z",
      "transcript_path": "data/transcripts/borspodden/bp-2024-12-18.txt",
      "analyzed": true,
      "analyzed_at": "2024-12-21T14:30:00Z",
      "recommendations_count": 3
    }
  }
}
```

### 5.2 Idempotens-regler
1. Innan nedladdning: kolla om filen finns OCH har rätt storlek
2. Innan transkribering: kolla om transkript finns OCH är non-empty
3. Innan analys: kolla state, fråga användaren om re-run
4. Alla writes: atomiska (skriv till temp, sedan rename)

---

## 6. Error Handling

### 6.1 Strategi
- **Fail fast** för konfigurationsfel
- **Graceful degradation** för nätverksfel (retry 3x, sedan skip)
- **Aldrig förlora data** – skriv inkrementellt
- **Tydliga felmeddelanden** med actionable suggestions

### 6.2 Feltyper
```python
class PodStockError(Exception):
    """Base exception"""

class ConfigError(PodStockError):
    """Invalid configuration"""

class RSSError(PodStockError):
    """RSS fetch/parse failed"""

class DownloadError(PodStockError):
    """Audio download failed"""

class TranscribeError(PodStockError):
    """Whisper transcription failed"""

class AnalysisError(PodStockError):
    """Claude analysis parsing failed"""
```

---

## 7. Dependencies

### 7.1 Runtime
```
feedparser>=6.0.0      # RSS parsing
requests>=2.28.0       # HTTP requests
pydantic>=2.0.0        # Data validation
rich>=13.0.0           # Terminal UI (progress bars, tables)
mlx-whisper>=0.1.0     # Apple Silicon optimized Whisper
```

### 7.2 Development
```
pytest>=7.0.0          # Testing
pytest-cov             # Coverage
ruff                   # Linting
mypy                   # Type checking
```

---

## 8. Future Extensibility

### 8.1 Adding New Podcasts
1. Lägg till i `data/podcasts.json`
2. Kör `podstock download --podcast <id>`
3. Inga kodändringar krävs

### 8.2 Changing Analysis Prompt
1. Redigera `prompts/analyze_transcript.md`
2. Kör `podstock analyze` med `--force` för att re-analysera

### 8.3 Adding New Output Formats
1. Skapa ny modul i `report/`
2. Registrera i CLI
3. Ingen påverkan på befintlig kod

### 8.4 Claude API Integration (Fas 2)
1. Lägg till `analyze/claude_api.py`
2. Konfigurera API-nyckel i config
3. CLI väljer automatiskt baserat på config
