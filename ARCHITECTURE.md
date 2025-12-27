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
│       │   ├── manager.py       # TwitterManager (CRUD)
│       │   ├── api_client.py    # TwitterApiClient (twitterapi.io)
│       │   ├── api_collector.py # Insamling via API
│       │   ├── collector.py     # Legacy scraper
│       │   ├── storage.py       # Tweet-lagring (JSONL)
│       │   ├── state.py         # TwitterState
│       │   ├── search.py        # Sökindex
│       │   ├── analyze.py       # LLM-analys
│       │   ├── report.py        # Rapportgenerering
│       │   ├── models.py        # Pydantic-modeller
│       │   └── exceptions.py    # Undantag
│       │
│       ├── youtube/             # YouTube-integration
│       │   ├── channel_manager.py  # Kanal-CRUD
│       │   ├── extractor.py     # Transkript-extraktion (yt-dlp)
│       │   ├── storage.py       # Video/transkript-lagring
│       │   ├── models.py        # Pydantic-modeller
│       │   └── exceptions.py    # Undantag
│       │
│       ├── crypto/              # Crypto-sentiment
│       │   ├── analyzer.py      # CryptoAnalyzer
│       │   ├── aggregator.py    # Aggregera prediktioner
│       │   ├── price_tracker.py # Prisverifiering (CoinGecko)
│       │   ├── coingecko.py     # CoinGecko API-klient
│       │   ├── prompt_templates.py  # LLM-prompts
│       │   ├── report.py        # Rapportgenerering
│       │   └── models.py        # Pydantic-modeller
│       │
│       ├── filings/             # Årsredovisningsanalys
│       │   ├── models.py        # Filing, Company, FilingAnalysis
│       │   ├── exceptions.py    # FilingsError, PDFParseError
│       │   ├── clients/         # API-klienter (SEC EDGAR)
│       │   ├── pdf/             # PDF-parsing och chunking
│       │   └── analysis/        # LLM-analys av rapporter
│       │
│       ├── prices/              # Prisdata och verifiering
│       │   ├── clients/         # API-klienter (Yahoo)
│       │   ├── tracker.py       # PriceTracker
│       │   └── storage.py       # Lokal cache
│       │
│       └── db/                  # NYA: SQLite databas
│           ├── __init__.py      # Publika exporter
│           ├── engine.py        # Database engine & sessions
│           ├── models.py        # SQLAlchemy ORM-modeller
│           ├── schema.sql       # SQL-schema (13 tabeller)
│           ├── loader.py        # PodcastLoader, TwitterLoader
│           ├── queries.py       # Sökfunktioner
│           ├── ticker_lookup.py # Security resolution
│           ├── performance.py   # Avkastningsberäkning
│           └── cli.py           # CLI-kommandon
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
│   │   └── {podcast}-{date}-{hash}.json
│   │
│   ├── twitter/                 # Twitter/X-data
│   │   ├── sources.json         # Konfigurerade källor
│   │   ├── raw/{source}/        # Råa tweets (JSONL)
│   │   └── analyses/            # LLM-analyserade tweets
│   │
│   ├── youtube/                 # YouTube-data
│   │   ├── channels.json        # Konfigurerade kanaler
│   │   ├── transcripts/{channel}/ # Transkript per kanal
│   │   └── state.json           # Insamlingsstatus
│   │
│   ├── crypto/                  # Crypto-analysdata
│   │   ├── technicalroundup-analysis/ # Per-kanal analyser
│   │   └── glm-batch/           # GLM batch-input/output
│   │
│   ├── prices/                  # Prisdata
│   │   ├── ticker_mapping.json  # Aktie → ticker mappning
│   │   ├── recommendations.json # Spårade rekommendationer
│   │   └── history/             # Historisk prisdata (cache)
│   │
│   ├── podstock.db              # SQLite-databas (gitignored)
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

### 3.18 `db/` – SQLite Database Module (NY)
Ansvar: Persitent lagring, frågor, och prestanda-spårning

#### 3.18.1 `db/engine.py` – Databas-engine
```python
def get_engine(db_path: Path | None = None, echo: bool = False) -> Engine
def get_session(engine: Engine | None = None) -> Generator[Session]
def init_db(engine: Engine | None = None, force: bool = False) -> None
```

#### 3.18.2 `db/models.py` – ORM-modeller
```python
class Source(Base):       # Podcast/Twitter-källa
class Content(Base):      # Episode/Tweet
class Analysis(Base):     # AI-analys med versionshantering
class Security(Base):     # Normaliserad aktie/ticker
class SecurityAlias(Base) # Alternativa namn (EVO, Evolution Gaming)
class Recommendation(Base) # Köp/sälj-rekommendation
class Price(Base):        # Historisk kursdata
class RecommendationPerformance(Base)  # Avkastning 1d/7d/30d/90d/365d
```

#### 3.18.3 `db/loader.py` – Dataimport
```python
class BaseLoader:
    def compute_content_hash(data: dict) -> str  # SHA256 för idempotens
    def should_load(session, file_path, file_hash) -> bool

class PodcastLoader(BaseLoader):
    """Laddar podcast-analyser från data/extracted/glm-batch/*.json"""
    def load(json_path: Path, session: Session) -> LoadResult

class TwitterLoader(BaseLoader):
    """Laddar tweet-analyser från data/twitter/analyses/*-tweet-analyses.json"""
    def load(json_path: Path, session: Session) -> LoadResult

class YouTubeLoader(BaseLoader):
    """Laddar crypto-analyser från data/crypto/{channel}-analysis/*.json"""
    def load(json_path: Path, session: Session) -> LoadResult
```

**Datatyper som laddas vs inte laddas:**
| Typ | Mönster | Laddas? | Beskrivning |
|-----|---------|---------|-------------|
| Podcast | `*.json` | Ja | Episode-analyser med recommendations |
| Twitter tweets | `*-tweet-analyses.json` | Ja | Tweet-för-tweet analyser |
| Twitter profiler | `*-analysis.json` | Nej | Profilsammanfattningar (custom) |
| YouTube/Crypto | `{video_id}.json` | Ja | Crypto-mentions med sentiment |

Se [docs/DATA-FORMATS.md](docs/DATA-FORMATS.md) för fullständig dokumentation.

#### 3.18.4 `db/queries.py` – Sökfunktioner
```python
def search_recommendations(session, stock, ticker, action, since, speaker, source_id, limit) -> list[RecommendationResult]
def get_top_stocks(session, days, action, limit) -> list[tuple]
def get_recent_by_source(session, source_id, limit) -> list[Recommendation]
def get_speaker_stats(session, days, limit) -> list[tuple]
def get_unmatched_securities(session, limit) -> list[PendingSecurity]
```

#### 3.18.5 `db/ticker_lookup.py` – Aktie-resolution
```python
def parse_ticker_suffix(ticker: str) -> tuple[str, str, str]  # base, suffix, exchange
def resolve_security(session, name, ticker) -> Security | None
def get_or_create_security(session, ticker, name, ...) -> tuple[Security, bool]
def add_alias(session, security_id, alias, alias_type) -> bool
def seed_from_ticker_mapping(session, mapping_path) -> dict[str, int]
```

#### 3.18.6 `db/performance.py` – Avkastningsberäkning
```python
def get_price_on_date(session, security_id, target_date, lookback_days) -> float | None
def calculate_return(price_at_rec: float, current_price: float) -> float
def update_recommendation_performance(session, recommendation_id, force) -> RecommendationPerformance | None
def update_all_performance(session, limit, force) -> dict[str, int]
def import_prices_from_tracker(session, data_dir) -> dict[str, int]
```

#### 3.18.7 `db/cli.py` – CLI-kommandon
```bash
podstock db init [--force]           # Skapa/återskapa databas
podstock db status                   # Visa statistik
podstock db seed-securities          # Ladda aktier från ticker_mapping
podstock db load [--type podcast|twitter|youtube]  # Importera analyser
podstock db load --type youtube [--channel NAME]   # Ladda crypto-data
podstock db search "query" [--action buy]  # Sök rekommendationer
podstock db pending list             # Visa omatchade aktier
podstock db performance update       # Beräkna avkastning
```

### 3.19 `twitter/` – Twitter/X-integration
Ansvar: Samla in och analysera tweets från finanskonton

```python
class TwitterManager:
    def add_source(username, category, description) -> TwitterSource
    def list_sources(active_only: bool) -> list[TwitterSource]
    def remove_source(source_id: str) -> bool

class TwitterApiClient:
    def get_user_tweets(username, since_id, max_results) -> list[Tweet]
    def get_user_info(username) -> UserInfo

class TwitterStorage:
    def save_tweets(tweets: list[Tweet]) -> int  # JSONL format
    def get_tweets(source_id, since, until) -> list[Tweet]
    def get_tweet_analyses(source_id) -> list[TweetAnalysis]
```

### 3.20 `youtube/` – YouTube-integration
Ansvar: Extrahera transkript från YouTube-kanaler för crypto-analys

```python
class YouTubeChannelManager:
    def add_channel(channel_url, category, language) -> YouTubeChannel
    def list_channels(active_only: bool) -> list[YouTubeChannel]
    def remove_channel(channel_id: str) -> bool

class YouTubeExtractor:
    def get_channel_videos(channel_url, max_videos) -> list[YouTubeVideo]
    def extract_transcript(video_id, language) -> YouTubeTranscript

class YouTubeStorage:
    def save_videos(videos: list[YouTubeVideo]) -> int
    def save_transcript(transcript: YouTubeTranscript) -> None
    def has_transcript(channel_id, video_id) -> bool
```

### 3.21 `crypto/` – Crypto-sentiment
Ansvar: Analysera crypto-prediktioner från YouTube-kanaler

```python
class CryptoAnalyzer:
    def analyze_transcript(transcript: str, video_info: dict) -> CryptoAnalysis
    def batch_analyze(transcripts: list[str]) -> list[CryptoAnalysis]

class CryptoAggregator:
    def get_predictions(coin: str, channel: str) -> list[CryptoPrediction]
    def get_top_coins(days: int, limit: int) -> list[tuple]
    def get_channel_bias(channel_id: str) -> ChannelBias

class CryptoPriceTracker:
    def verify_prediction(prediction_id: str) -> VerificationResult
    def get_accuracy_stats(channel: str) -> AccuracyStats
```

### 3.22 `prices/` – Prisverifiering
Ansvar: Hämta priser och verifiera rekommendationers utfall

```python
class TickerMapper:
    def add_mapping(name: str, ticker: str) -> None
    def get_ticker(name: str) -> str | None
    def search(query: str) -> list[tuple[str, str, int]]  # name, ticker, score

class PriceTracker:
    def track_recommendation(source_type, source_id, asset_name, action, ...) -> TrackedRecommendation
    def verify_recommendation(tracking_id, interval_months) -> VerificationResult
    def verify_all_due() -> list[tuple[TrackedRecommendation, VerificationResult]]
    def get_accuracy_stats(source_name, speaker, action) -> AccuracyStats
    def import_from_extractions(episode_ids, ...) -> ImportResult
```

### 3.23 `filings/` – Årsredovisningsanalys (Library Only)
Ansvar: Parsa och analysera finansiella rapporter (10-K, 10-Q, årsredovisningar)

**OBS:** Denna modul har ännu ingen CLI-integration.

```python
class FilingsClient:
    def add_company(ticker: str, market: str) -> Company
    def sync_filings(company_id: str, limit: int) -> list[Filing]
    def get_filing(filing_id: str) -> Filing

class FilingAnalyzer:
    def analyze(filing: Filing, model: str) -> FilingAnalysis
    def chunk_document(pdf_path: Path, max_tokens: int) -> list[DocumentChunk]
    def extract_metrics(filing: Filing) -> FinancialMetrics

class FilingType(Enum):
    ANNUAL_REPORT = "10-K"
    QUARTERLY_REPORT = "10-Q"
    SWEDISH_ANNUAL = "årsredovisning"

class FilingSource(Enum):
    SEC_EDGAR = "edgar"  # US companies
    MANUAL_PDF = "pdf"   # Any company
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

### 4.6 Database Load Flow (NY)
```
1. User: podstock db load
2. CLI iterates over data/extracted/*.json
3. For each file:
   a. Compute file hash (SHA256)
   b. Check LoadLog – skip if already loaded with same hash
   c. Parse JSON, validate structure
   d. Get/create Source (podcast/twitter)
   e. Get/create Content (episode/tweet)
   f. Compute content hash for versioning
   g. Create Analysis with version number
   h. For each recommendation:
      i.   Try resolve_security() → match to Security
      ii.  If unmatched: create PendingSecurity entry
      iii. Create Recommendation with security_id (or null)
   i. Log to LoadLog
4. Session commit
5. CLI prints summary (loaded, skipped, failed)
```

### 4.7 Performance Update Flow (NY)
```
1. User: podstock db performance update
2. CLI calls update_all_performance()
3. Query: Recommendations with security_id but incomplete performance
4. For each recommendation:
   a. Get recommendation date from Content.published_at
   b. get_price_on_date() for price_at_rec
   c. For each interval (1d, 7d, 30d, 90d, 365d):
      i.  Check if enough days have passed
      ii. get_price_on_date() for that interval
      iii. calculate_return()
   d. Create/update RecommendationPerformance
   e. Mark is_complete if 365d available
5. CLI prints results (updated, skipped, failed)
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
sqlalchemy>=2.0.0      # Database ORM
yfinance>=0.2.0        # Yahoo Finance prisdata
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

### 8.5 Database Module (Implementerat ✅)
SQLite-baserat frågelager för strukturerad sökning och prestanda-spårning:
- **13 tabeller**: sources, content, analyses, securities, recommendations, prices, etc.
- **Loaders**: PodcastLoader, TwitterLoader, YouTubeLoader med idempotent import
- **Security resolution**: Ticker-normalisering med alias-support
- **Performance tracking**: Automatisk avkastningsberäkning (1d-365d)
- **CLI**: `podstock db` kommandogrupp
