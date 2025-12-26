# PodStock – Architecture Document

**Version:** 2.0
**Datum:** 2025-12-26

---

## 1. System Overview

### 1.1 Historisk Analys (manuellt flöde)

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

### 1.2 Real-time Monitoring (automatiserat flöde)

```
┌─────────────────────────────────────────────────────────────────┐
│                      Real-time Monitoring                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐                                               │
│  │    Lists     │ ◀── broad / niche / custom                    │
│  │   Manager    │                                               │
│  └──────┬───────┘                                               │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │    Sync      │───▶│    Apple     │ or │   Whisper    │      │
│  │ Orchestrator │    │  Podcasts    │    │ Transcriber  │      │
│  └──────┬───────┘    └──────────────┘    └──────────────┘      │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────┐                                               │
│  │    State     │ ◀── published_at, podcast_id, title          │
│  │   Manager    │                                               │
│  └──────┬───────┘                                               │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Summary    │───▶│    Data      │───▶│   Prompt     │      │
│  │  Generator   │    │   Loader     │    │   Builder    │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  Claude Code (tokens)  OR  Opencode/GLM-4.7 (gratis) │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Directory Structure

```
podstock/
├── README.md                    # Quick start guide
├── ARCHITECTURE.md              # This file
├── pyproject.toml               # Project configuration
│
├── src/
│   └── podstock/
│       ├── __init__.py
│       ├── __main__.py          # Entry point: python -m podstock
│       ├── cli.py               # CLI commands (argparse)
│       │
│       ├── core/                # Kärnfunktionalitet
│       │   ├── config.py        # Konfigurationshantering
│       │   ├── state.py         # Tillståndsspårning
│       │   ├── models.py        # Pydantic-modeller
│       │   └── exceptions.py    # Undantag
│       │
│       ├── rss/                 # RSS-hantering
│       │   ├── parser.py        # RSS-parsing
│       │   ├── downloader.py    # Ljudnedladdning
│       │   └── manager.py       # Podcast CRUD
│       │
│       ├── transcribe/          # Transkribering
│       │   ├── whisper.py       # mlx-whisper integration
│       │   └── apple.py         # Apple Podcasts transcripts
│       │
│       ├── analyze/             # Analys
│       │   ├── prompt_builder.py  # Claude prompts
│       │   └── result_parser.py   # Resultatparsning
│       │
│       ├── report/              # Rapportgenerering
│       │   └── markdown.py      # Markdown-rapporter
│       │
│       ├── lists/               # NYA: List-hantering
│       │   ├── models.py        # PodcastList, ListsFile
│       │   └── manager.py       # CRUD för listor
│       │
│       ├── sync/                # NYA: Synkronisering
│       │   ├── models.py        # SyncSummary, EpisodeSyncResult
│       │   └── orchestrator.py  # SyncOrchestrator
│       │
│       ├── reports/             # NYA: Sammanfattningar
│       │   ├── models.py        # SummaryConfig, ReportData
│       │   ├── prompts.py       # LLM prompt-templates
│       │   ├── data_loader.py   # ReportDataLoader
│       │   └── generator.py     # SummaryReportGenerator
│       │
│       ├── extract/             # AI-extraktion
│       │   ├── process_transcript.py
│       │   ├── batch_runner.py
│       │   ├── search.py
│       │   └── build_index.py
│       │
│       ├── summary/             # Gäst-sammanfattning
│       │   └── generator.py
│       │
│       ├── twitter/             # Twitter/X-integration
│       │   ├── manager.py
│       │   ├── api_collector.py
│       │   ├── storage.py
│       │   └── state.py
│       │
│       ├── youtube/             # YouTube-integration
│       │   └── ...
│       │
│       └── crypto/              # Crypto-sentiment
│           └── ...
│
├── data/                        # Runtime-data (gitignored audio)
│   ├── config.json              # Användarkonfiguration
│   ├── state.json               # Processingsstatus
│   ├── podcasts.json            # Podcast-definitioner
│   ├── lists.json               # NYA: Podcast-listor
│   │
│   ├── audio/                   # Nedladdade ljudfiler
│   │   └── {podcast_id}/
│   │       └── {episode_id}.mp3
│   │
│   ├── transcripts/             # Transkript
│   │   └── {podcast_id}/
│   │       └── {episode_id}.txt
│   │
│   ├── extracted/               # AI-extraherad data
│   │   └── recommendations.json
│   │
│   └── reports/                 # Genererade rapporter
│       ├── prompts/             # NYA: LLM-prompts
│       │   ├── YYYY-MM-DD-broad-prompt.md
│       │   └── YYYY-MM-DD-broad-opencode.json
│       └── summaries/           # NYA: Sammanfattningar
│           └── YYYY-MM-DD-summary.md
│
├── .claude/commands/            # NYA: Claude Code skills
│   ├── sync.md                  # /sync skill
│   └── summary.md               # /summary skill
│
├── docs/                        # Dokumentation
│   ├── REAL-TIME-MONITORING.md
│   ├── CLI-REFERENCE.md
│   └── ...
│
└── tests/
    └── ...
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

### 3.11 `lists/manager.py` – List-hantering (NY)
Ansvar: CRUD-operationer för podcast-listor

```python
class ListManager:
    def create_list(list_id, name, list_type, description) -> PodcastList
    def get_list(list_id) -> PodcastList | None
    def get_all_lists() -> list[PodcastList]
    def add_podcast_to_list(list_id, podcast_id) -> bool
    def remove_podcast_from_list(list_id, podcast_id) -> bool
    def delete_list(list_id) -> bool
```

### 3.12 `lists/models.py` – List-modeller (NY)
Ansvar: Datamodeller för podcast-listor

```python
class PodcastList(BaseModel):
    id: str
    name: str
    description: str | None
    type: Literal["broad", "niche", "custom"]
    podcast_ids: list[str]
    created_at: datetime
    active: bool

class ListsFile(BaseModel):
    version: int
    updated_at: datetime
    lists: list[PodcastList]
```

### 3.13 `sync/orchestrator.py` – Sync-orkestrering (NY)
Ansvar: Koordinera hämtning och transkribering av nya avsnitt

```python
class SyncOrchestrator:
    def sync_podcast(podcast, latest_n, force, dry_run) -> list[EpisodeSyncResult]
    def sync_list(list_id, latest_n, force, dry_run) -> SyncSummary
    def sync_all(latest_n, force, dry_run) -> SyncSummary
```

### 3.14 `sync/models.py` – Sync-modeller (NY)
Ansvar: Resultatmodeller för synkronisering

```python
class EpisodeSyncResult(BaseModel):
    episode_id: str
    podcast_id: str
    title: str
    published_at: datetime
    status: Literal["synced", "skipped", "failed"]
    transcript_source: Literal["apple", "whisper"] | None
    error: str | None

class SyncSummary(BaseModel):
    started_at: datetime
    completed_at: datetime | None
    podcasts_checked: int
    new_episodes: int
    transcribed: int
    failed: int
    errors: list[str]
    episodes: list[EpisodeSyncResult]
```

### 3.15 `reports/generator.py` – Sammanfattningsgenerator (NY)
Ansvar: Generera periodiska sammanfattningar

```python
class SummaryReportGenerator:
    def prepare_for_claude_code(start_date, end_date, list_id, report_type) -> Path
    def prepare_for_opencode(start_date, end_date, list_id, report_type) -> Path
    def get_available_data(start_date, end_date, list_id) -> dict
    def save_report(content, output_path) -> Path
```

### 3.16 `reports/data_loader.py` – Dataladdning (NY)
Ansvar: Ladda och förbereda data för sammanfattningar

```python
class ReportDataLoader:
    def load_for_period(start_date, end_date, list_id) -> ReportData
    def _load_transcripts(episodes) -> dict[str, str]
    def _load_recommendations(podcast_ids) -> list[dict]
```

### 3.17 `reports/prompts.py` – LLM-prompts (NY)
Ansvar: Prompt-templates för sammanfattningsgenerering

```python
BROAD_SUMMARY_SYSTEM: str   # System-prompt för bred analys
BROAD_SUMMARY_USER: str     # User-prompt för bred analys
DETAILED_SUMMARY_SYSTEM: str # System-prompt för detaljerad analys
DETAILED_SUMMARY_USER: str   # User-prompt för detaljerad analys
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

### 4.4 Sync Flow (NY)
```
1. User: podstock sync --list broad --latest 2
2. CLI loads ListManager, gets podcasts in list
3. For each podcast:
   a. RSS Parser fetches latest episodes
   b. State checks which episodes exist
   c. For new episodes:
      i.  If transcript_source == "auto" or "apple":
          - Try Apple Podcasts cache
          - If found: save transcript, update state
      ii. If Apple not available and source != "apple":
          - Download audio
          - Whisper transcribes
          - Save transcript, update state
   d. Track result (synced/skipped/failed)
4. SyncSummary returned
5. CLI prints summary
```

### 4.5 Summary Flow (NY)
```
1. User: podstock summary prepare --from 2025-12-20 --to 2025-12-26
2. CLI creates SummaryReportGenerator
3. ReportDataLoader:
   a. Gets podcasts from list
   b. Gets episodes in date range from State
   c. Loads transcripts from files
   d. Loads recommendations from extracted/
4. Prompt Builder creates LLM prompt
5. Prompt saved to data/reports/prompts/
6. User runs prompt in Claude Code or Opencode
7. User saves result: podstock summary save --output rapport.md
```

---

## 5. State Management

### 5.1 State File Format (`data/state.json`)
```json
{
  "version": 1,
  "last_updated": "2025-12-26T14:30:00Z",
  "episodes": {
    "borspodden-2025-12-20-abc1": {
      "podcast_id": "borspodden",
      "title": "Avsnitt 600: Julspecial",
      "published_at": "2025-12-20T10:00:00Z",
      "downloaded": true,
      "downloaded_at": "2025-12-21T10:00:00Z",
      "audio_path": "data/audio/borspodden/borspodden-2025-12-20-abc1.mp3",
      "transcribed": true,
      "transcribed_at": "2025-12-21T10:15:00Z",
      "transcript_path": "data/transcripts/borspodden/borspodden-2025-12-20-abc1.txt",
      "transcript_source": "apple",
      "analyzed": true,
      "analyzed_at": "2025-12-21T14:30:00Z",
      "recommendations_count": 3
    }
  }
}
```

### 5.2 List File Format (`data/lists.json`) (NY)
```json
{
  "version": 1,
  "updated_at": "2025-12-26T12:00:00Z",
  "lists": [
    {
      "id": "broad",
      "name": "Bred Analys",
      "description": "Alla podcasts för övergripande marknadsöversikt",
      "type": "broad",
      "podcast_ids": ["borspodden", "marketmakers", "aktiepodden"],
      "created_at": "2025-12-26T12:00:00Z",
      "active": true
    },
    {
      "id": "niche",
      "name": "Detaljerad Analys",
      "description": "Utvalda podcasts för djupanalys",
      "type": "niche",
      "podcast_ids": ["borsensfinest", "fillorkill"],
      "created_at": "2025-12-26T12:00:00Z",
      "active": true
    }
  ]
}
```

### 5.3 Idempotens-regler
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
