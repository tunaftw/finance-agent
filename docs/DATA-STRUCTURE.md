# Data Structure Guide

This document describes the data directory structure for PodStock.

## Design Principles

### 1. Source of Truth
- **JSON files** = Source of truth (immutable raw data + analyses)
- **SQLite database** = Cache/index for fast queries (can be regenerated)

### 2. Consistent Pattern
Every data source follows the same structure:
```
{source}/
├── sources.json     # Source definitions
├── state.json       # Processing state
├── raw/             # Unprocessed data
├── analyses/        # LLM-generated analyses
└── index/           # Search index (cache)
```

### 3. Real Names
Use **actual names** for folders, not slugs or abbreviations:

| Category | Good | Bad |
|----------|------|-----|
| Podcast folder | `Börspodden/` | `borspodden/`, `bp/` |
| Twitter folder | `Matematikern/` | `matematikern3/` |
| YouTube folder | `Technical Roundup/` | `tr/` |
| Company folder | `Evolution Gaming/` | `EVO/` |

---

## Directory Structure

```
data/
│
├── ═══════════════════════════════════════════════════
│   CONFIGURATION (root level)
├── ═══════════════════════════════════════════════════
├── config.json              # App settings
├── state.json               # Global processing state
├── lists.json               # Podcast lists
├── podstock.db              # SQLite cache/index
│
├── ═══════════════════════════════════════════════════
│   UNOFFICIAL SOURCES (social media, podcasts)
├── ═══════════════════════════════════════════════════
│
├── podcasts/                # Podcasts
│   ├── sources.json         # Podcast definitions (RSS, hosts, etc.)
│   ├── state.json           # Processing state
│   ├── raw/                 # Raw data
│   │   └── {Podcast Name}/
│   │       ├── audio/       # MP3 files
│   │       └── transcripts/ # Transcript files
│   ├── analyses/            # LLM analyses
│   └── index/               # Search index
│
├── twitter/                 # Twitter
│   ├── sources.json         # Twitter sources (@handles)
│   ├── state.json           # Collection state
│   ├── raw/                 # Raw tweets
│   │   └── {Source Name}/
│   │       └── tweets.jsonl
│   ├── analyses/            # LLM analyses
│   └── index/               # Search index
│
├── youtube/                 # YouTube
│   ├── sources.json         # YouTube channels
│   ├── state.json           # Collection state
│   ├── raw/                 # Raw data
│   │   └── {Channel Name}/
│   │       ├── metadata/
│   │       └── transcripts/
│   ├── analyses/            # LLM analyses (crypto, etc.)
│   └── index/
│
├── ═══════════════════════════════════════════════════
│   OFFICIAL SOURCES (company information)
├── ═══════════════════════════════════════════════════
│
├── filings/                 # Annual/Quarterly Reports
│   ├── companies.json       # Company definitions
│   ├── state.json
│   ├── raw/
│   │   └── {Company Name}/
│   │       ├── annual/
│   │       ├── quarterly/
│   │       └── presentations/
│   ├── analyses/
│   └── index/
│
├── earnings/                # Earnings Calls
│   ├── sources.json
│   ├── state.json
│   ├── raw/
│   │   └── {Company Name}/
│   │       └── {Q#-YYYY}.txt
│   ├── analyses/
│   └── index/
│
├── news/                    # News
│   ├── sources.json
│   ├── state.json
│   ├── raw/
│   │   └── {Source Name}/
│   ├── analyses/
│   └── index/
│
├── ═══════════════════════════════════════════════════
│   AGGREGATED DATA (from all sources)
├── ═══════════════════════════════════════════════════
│
├── recommendations/         # Aggregated recommendations
│   ├── all.jsonl            # All recommendations (append-only)
│   ├── by-ticker/           # Grouped by ticker
│   └── by-source/           # Grouped by source
│
├── prices/                  # Price data & tracking
│   ├── ticker_mapping.json  # Ticker → Yahoo/CoinGecko mapping
│   ├── snapshots/           # Daily price snapshots
│   └── tracking.jsonl       # Performance tracking
│
├── ═══════════════════════════════════════════════════
│   OUTPUT (generated products)
├── ═══════════════════════════════════════════════════
│
└── reports/                 # Reports
    ├── prompts/             # LLM prompts (for reproducibility)
    ├── summaries/           # Summary reports
    └── exports/             # Exported data (JSON, CSV)
```

---

## File Naming Conventions

### Episode IDs
Format: `{Podcast}-{YYYY-MM-DD}-{4char}`

Examples:
- `Börspodden-2025-01-15-a1b2`
- `Market Makers-2025-01-20-c3d4`

### Analysis Files
- Podcast: `{episode_id}.json`
- Twitter: `{Source Name}-analysis.json`
- YouTube: `{Channel Name}-{video_id}-analysis.json`
- Filings: `{Company Name}-{period}.json`

### Raw Data Files
- Tweets: `tweets.jsonl` (in source folder)
- Transcripts: `{episode_id}.txt`
- Audio: `{episode_id}.mp3`

---

## Config Properties

Access paths through the `Config` class:

```python
from podstock.core.config import load_config

config = load_config()

# Podcasts
config.podcasts_dir           # data/podcasts
config.podcasts_sources_file  # data/podcasts/sources.json
config.podcasts_raw_dir       # data/podcasts/raw
config.podcasts_analyses_dir  # data/podcasts/analyses
config.podcasts_index_dir     # data/podcasts/index

# Twitter
config.twitter_dir            # data/twitter
config.twitter_sources_file   # data/twitter/sources.json
config.twitter_raw_dir        # data/twitter/raw
config.twitter_analyses_dir   # data/twitter/analyses

# YouTube
config.youtube_dir            # data/youtube
config.youtube_sources_file   # data/youtube/sources.json
config.youtube_raw_dir        # data/youtube/raw
config.youtube_analyses_dir   # data/youtube/analyses

# Aggregated
config.recommendations_dir    # data/recommendations
config.prices_dir             # data/prices
config.db_path                # data/podstock.db

# Legacy (for backwards compatibility)
config.audio_dir              # data/audio
config.transcripts_dir        # data/transcripts
config.extracted_dir          # data/extracted
```

---

## Migration Status

### Completed
- [x] Twitter: `raw/`, `analyses/`, `index/` structure
- [x] YouTube: `raw/`, `analyses/`, `index/` structure
- [x] Podcasts: `raw/`, `analyses/`, `index/` structure
- [x] Config properties added for all sources
- [x] Code updated to use new paths
- [x] Documentation created

### Migrated Folders
| Old Location | New Location |
|-------------|--------------|
| `audio/{podcast}/` | `podcasts/raw/{podcast}/audio/` |
| `transcripts/{podcast}/` | `podcasts/raw/{podcast}/transcripts/` |
| `extracted/glm-batch/` | `podcasts/analyses/` |
| `crypto/analyses/` | `youtube/analyses/` |
| `twitter_sources.json` | `twitter/sources.json` |
| `twitter_state.json` | `twitter/state.json` |

### Archived Folders
Old test/deprecated data moved to `_archived/`

---

## Adding New Data Sources

1. Create directory structure:
   ```
   {source}/
   ├── sources.json
   ├── state.json
   ├── raw/
   ├── analyses/
   └── index/
   ```

2. Add config properties in `src/podstock/core/config.py`:
   ```python
   @property
   def {source}_dir(self) -> Path:
       return self.data_dir / "{source}"

   @property
   def {source}_sources_file(self) -> Path:
       return self.{source}_dir / "sources.json"

   # ... etc
   ```

3. Update `ensure_directories()` to create new folders.

4. Use real names for subfolders, not slugs.
