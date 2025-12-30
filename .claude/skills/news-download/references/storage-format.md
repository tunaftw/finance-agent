# Storage Format

JSON schemas and examples for news data storage.

## Directory Structure

```
data/news/
├── sources.json              # Company watchlist
├── state.json                # Sync state
├── raw/
│   └── {ticker}-{company}/   # e.g., evo-evolution
│       ├── press-releases/
│       │   └── 2024-12-15-abc123.json
│       └── articles/
│           └── 2024-12-16-def456.json
└── analyses/                 # Phase 2
    └── evo-evolution-analysis.json
```

## sources.json Schema

```json
{
  "version": 1,
  "updated_at": "2025-12-30T10:00:00Z",
  "companies": [
    {
      "id": "evo-evolution",
      "name": "Evolution AB",
      "ticker": "EVO.ST",
      "ticker_base": "EVO",
      "exchange": "OMX",
      "market": "sweden",
      "nasdaq_id": "SSE197998",
      "isin": "SE0012673267",
      "feeds": {
        "nasdaq": "https://www.nasdaqomxnordic.com/news/companynews?symbol=EVO",
        "globenewswire": "https://www.globenewswire.com/RssFeed/ticker/EVO"
      },
      "since": "2024-01-01",
      "added_at": "2025-12-30T10:00:00Z",
      "active": true
    }
  ],
  "media_feeds": [
    {
      "id": "affarsvarlden",
      "name": "Affärsvärlden",
      "url": "https://www.affarsvarlden.se/rss/senaste",
      "active": true
    }
  ]
}
```

### Company Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | Yes | Unique ID: `{ticker_base}-{name_slug}` |
| name | string | Yes | Official company name |
| ticker | string | Yes | Full ticker with suffix (EVO.ST) |
| ticker_base | string | Yes | Ticker without suffix (EVO) |
| exchange | string | Yes | Exchange code (OMX, OSE, etc.) |
| market | string | Yes | Market region (sweden, norway, etc.) |
| nasdaq_id | string | No | Nasdaq Nordic instrument ID |
| isin | string | No | ISIN code |
| feeds | object | Yes | RSS feed URLs by source |
| since | string | Yes | Collect news from this date (YYYY-MM-DD) |
| added_at | string | Yes | ISO timestamp when added |
| active | boolean | Yes | Whether to sync this company |

## state.json Schema

```json
{
  "version": 1,
  "updated_at": "2025-12-30T12:00:00Z",
  "companies": {
    "evo-evolution": {
      "last_synced_at": "2025-12-30T12:00:00Z",
      "press_releases_count": 45,
      "articles_count": 123,
      "last_item_date": "2025-12-28T07:00:00Z",
      "errors": []
    }
  }
}
```

## News Item Schema

File: `data/news/raw/{company_id}/press-releases/{date}-{id}.json`

```json
{
  "id": "globenewswire-abc123",
  "source": "globenewswire",
  "company_id": "evo-evolution",
  "ticker": "EVO",
  "title": "Evolution AB (publ) publicerar Q4-rapport 2024",
  "published_at": "2024-12-15T07:00:00Z",
  "collected_at": "2025-12-30T10:15:00Z",
  "url": "https://www.globenewswire.com/news-release/...",
  "summary": "Evolution AB (publ) publicerar idag sin rapport för fjärde kvartalet 2024...",
  "content": null,
  "category": null,
  "language": "sv",
  "analyzed": false
}
```

### News Item Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | Yes | Unique ID (source-specific) |
| source | string | Yes | Source feed ID |
| company_id | string | Yes | Company ID from sources.json |
| ticker | string | Yes | Company ticker |
| title | string | Yes | News headline |
| published_at | string | Yes | ISO timestamp of publication |
| collected_at | string | Yes | ISO timestamp when collected |
| url | string | Yes | Link to original |
| summary | string | No | Short summary from RSS |
| content | string | No | Full text (if available) |
| category | string | No | Auto-categorized (Phase 2) |
| language | string | No | Language code (sv, en) |
| analyzed | boolean | No | Whether AI-analyzed |

## Article Schema

Same as news item, stored in `articles/` subdirectory.

## Filename Convention

```
{date}-{id}.json

Examples:
2024-12-15-abc123.json
2024-12-16-def456.json
unknown-xyz789.json  (if date unknown)
```

## ID Generation

```python
import hashlib

def generate_id(source: str, unique_value: str) -> str:
    """Generate item ID from source and unique value."""
    hash_input = f"{source}:{unique_value}"
    return hashlib.md5(hash_input.encode()).hexdigest()[:12]

# Example
item_id = generate_id("globenewswire", "https://globenewswire.com/news/123")
# Result: "abc123def456"
```
