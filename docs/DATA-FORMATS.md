# Data Formats and File Conventions

## Overview

PodStock processes data from multiple sources. This document describes the file formats,
naming conventions, and which files are loaded into the database.

## Data Categories

### 1. Database-Bound Data (Structured)

These files have consistent schemas and are loaded into SQLite via `podstock db load`:

| Type | Command | Directory | Pattern |
|------|---------|-----------|---------|
| Podcast | `--type podcast` | `data/extracted/glm-batch/` | `*.json` |
| Twitter | `--type twitter` | `data/twitter/analyses/` | `*-tweet-analyses.json` |
| YouTube | `--type youtube` | `data/crypto/{channel}-analysis/` | `*.json` |

### 2. JSON-Only Data (Reports/Custom)

These files are NOT loaded to the database. They serve as reports or have varying schemas:

| Type | Location | Pattern | Description |
|------|----------|---------|-------------|
| Profile summaries | `data/twitter/analyses/` | `*-analysis.json` | Aggregated user analysis |
| Timelines | `data/twitter/analyses/` | `*-timeline.json` | Trading position history |
| Custom analyses | various | varies | Ad-hoc analyses with custom schemas |

## File Format Specifications

### Podcast Analysis JSON

**Location:** `data/extracted/glm-batch/{podcast}-{date}-{hash}.json`

```json
{
  "episode_id": "aktiepodden-2019-12-09-e2d0",
  "podcast_name": "Aktiepodden",
  "episode_title": "Avsnitt 95",
  "date": "2019-12-09",
  "hosts": ["Carl-Henrik", "Christoffer"],
  "recommendations": [
    {
      "stock_name": "Inwido",
      "ticker": null,
      "action": "buy",
      "confidence": "medium",
      "speaker": "Kristoffer",
      "reasoning": "...",
      "quote": "..."
    }
  ],
  "summary": "...",
  "key_takeaways": ["..."],
  "model_used": "glm-4.7"
}
```

**Actions:** `buy`, `sell`, `hold`, `watch`, `avoid`

**Confidence:** `high`, `medium`, `low`

### Twitter Tweet-Level Analysis JSON

**Location:** `data/twitter/analyses/{username}-tweet-analyses.json`

```json
{
  "source_id": "vildkatten",
  "analyzed_at": "2025-12-25T21:28:12",
  "analyses": [
    {
      "tweet_id": "1862550576351023328",
      "stock_mentions": [
        {
          "stock_name": "Millicom International",
          "ticker": "TIGO",
          "action": "buy",
          "confidence": "high",
          "reasoning": "...",
          "quote": "..."
        }
      ],
      "market_sentiment": "bullish",
      "is_actionable": true
    }
  ]
}
```

### Twitter Profile Summary JSON (NOT loaded to DB)

**Location:** `data/twitter/analyses/{username}-analysis.json`

```json
{
  "source_id": "vildkatten",
  "analyzed_at": "2025-12-25",
  "summary": {
    "total_tweets_analyzed": 636,
    "tweets_with_stock_mentions": 54
  },
  "investment_style": {
    "focus_areas": ["Svenska småbolag", "Telekom"],
    "key_metrics": ["FCF yield", "Utdelning"]
  },
  "core_holdings": [
    {
      "ticker": "TIGO",
      "name": "Millicom/Tigo",
      "signal": "STRONG BUY"
    }
  ]
}
```

### YouTube Crypto Analysis JSON

**Location:** `data/crypto/{channel}-analysis/{video_id}.json`

```json
{
  "source_id": "0C5avyDWnow",
  "source_type": "youtube",
  "channel": "TechnicalRoundup",
  "date": "2021-07-23",
  "hosts": ["Cred", "Duck"],
  "mentions": [
    {
      "asset_symbol": "BTC",
      "asset_name": "Bitcoin",
      "sentiment": "bullish",
      "speaker": "Paolo Arduino",
      "context": "...",
      "quote": "...",
      "confidence": "high"
    }
  ],
  "overall_market_sentiment": "neutral",
  "key_insights": ["..."],
  "summary": "..."
}
```

**Sentiment:** `bullish`, `neutral`, `bearish`

## Database Schema Mapping

| JSON Field | Source Type | DB Table | DB Column |
|------------|-------------|----------|-----------|
| podcast_name | podcast | sources | name |
| source_id (twitter) | twitter | sources | id |
| channel | youtube | sources | name |
| recommendations | podcast | recommendations | * |
| stock_mentions | twitter | recommendations | * |
| mentions | youtube | mentions | * |

## CLI Usage

```bash
# Load all podcasts
podstock db load --type podcast

# Load Twitter tweet analyses
podstock db load --type twitter

# Load YouTube crypto analyses (default channel: technicalroundup)
podstock db load --type youtube

# Load specific YouTube channel
podstock db load --type youtube --channel technicalroundup

# Load from custom directory
podstock db load --type youtube --data-dir /path/to/custom/

# Load single file
podstock db load --file /path/to/file.json

# Verbose output
podstock db -v load --type youtube
```

## File Naming Conventions

### Podcast Files

Pattern: `{podcast_id}-{YYYY-MM-DD}-{4hex_hash}.json`

Examples:
- `aktiepodden-2019-12-09-e2d0.json`
- `kortochlang-2020-03-15-7b3f.json`

### Twitter Files

Pattern: `{username}-{type}.json`

Types:
- `-tweet-analyses.json` - Individual tweet analyses (loaded to DB)
- `-analysis.json` - Profile summary (NOT loaded to DB)
- `-timeline.json` - Position timeline (NOT loaded to DB)

### YouTube/Crypto Files

Pattern: `{video_id}.json`

Examples:
- `0C5avyDWnow.json`
- `HCQhWn1cyLw.json`

Note: Files ending in `-analysis.json` are skipped (duplicates).
