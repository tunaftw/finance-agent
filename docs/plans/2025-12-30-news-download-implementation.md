# News Download Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a skill to download press releases and news articles for Nordic companies from RSS feeds.

**Architecture:** Skill-based approach using Claude Code skills in `.claude/skills/news-download/`. Data stored in `data/news/` following existing patterns (raw/ for downloads, analyses/ for AI processing). RSS fetching via Python scripts using feedparser.

**Tech Stack:** feedparser (RSS parsing), requests (HTTP), existing ticker_mapping.json for company lookup

---

## Task 1: Create Directory Structure

**Files:**
- Create: `data/news/` directory
- Create: `data/news/raw/` directory
- Create: `data/news/analyses/` directory
- Create: `data/news/sources.json`
- Create: `data/news/state.json`

**Step 1: Create directories**

```bash
mkdir -p data/news/raw data/news/analyses
```

**Step 2: Create sources.json template**

Create `data/news/sources.json`:

```json
{
  "version": 1,
  "updated_at": null,
  "companies": [],
  "media_feeds": [
    {
      "id": "affarsvarlden",
      "name": "Affärsvärlden",
      "url": "https://www.affarsvarlden.se/rss/senaste",
      "active": true
    },
    {
      "id": "realtid",
      "name": "Realtid",
      "url": "https://www.realtid.se/feed",
      "active": true
    },
    {
      "id": "placera",
      "name": "Placera",
      "url": "https://www.placera.se/rss/nyheter.xml",
      "active": true
    }
  ]
}
```

**Step 3: Create state.json template**

Create `data/news/state.json`:

```json
{
  "version": 1,
  "updated_at": null,
  "companies": {}
}
```

**Step 4: Verify structure**

```bash
ls -la data/news/
cat data/news/sources.json | python -m json.tool
```

Expected: directories exist, JSON is valid

**Step 5: Commit**

```bash
git add data/news/
git commit -m "feat(news): create data/news directory structure"
```

---

## Task 2: Create Skill Directory Structure

**Files:**
- Create: `.claude/skills/news-download/SKILL.md`
- Create: `.claude/skills/news-download/references/` directory

**Step 1: Create skill directory**

```bash
mkdir -p .claude/skills/news-download/references
```

**Step 2: Create SKILL.md**

Create `.claude/skills/news-download/SKILL.md`:

```markdown
---
name: news-download
description: Download press releases and news articles for Nordic companies. Use when user wants to add a company to news watchlist, download news for a company, or sync all tracked companies. Supports Nasdaq Nordic, GlobeNewswire, and Swedish media RSS feeds.
---

# News Download Skill

Download press releases and news articles for Nordic companies with automatic storage and deduplication.

## Quick Start

1. Ask user: **Add new company** or **Download for existing**?
2. If new: Get ticker/name, verify company, set historical depth
3. Execute: Fetch RSS feeds, deduplicate, save to data/news/raw/
4. Report: X press releases, Y articles saved

## Workflow

### Step 1: Gather Requirements

Ask the user (use AskUserQuestion tool):

```
1. Action?
   - Add new company to watchlist
   - Download news for existing company
   - Download news for all companies

2. If new company:
   - Ticker or company name? (e.g., "EVO" or "Evolution")
   - Historical depth? (e.g., "since 2024-01-01" or "1 year back")

3. If existing:
   - Which company? (show list from sources.json)
   - Date range? (new since last sync / specific range / all)
```

### Step 2: Company Lookup (New Companies)

See [references/company-lookup.md](references/company-lookup.md)

### Step 3: Fetch Press Releases

See [references/fetch-news.md](references/fetch-news.md)

### Step 4: Fetch Media Articles

Filter media RSS feeds by company name/ticker keywords.
See [references/fetch-news.md](references/fetch-news.md)

### Step 5: Report Summary

After collection, report:
- Number of press releases downloaded
- Number of media articles found
- Storage location: `data/news/raw/{ticker}-{company}/`
- Next steps: "Run /news-analyze to extract insights"

## Storage Format

### Directory Structure

```
data/news/
├── sources.json              # Configured companies
├── state.json                # Collection state
├── raw/
│   └── {ticker}-{company}/   # e.g., evo-evolution
│       ├── press-releases/
│       │   └── {id}.json
│       └── articles/
│           └── {id}.json
└── analyses/
    └── {ticker}-{company}-analysis.json
```

### News Item Format

```json
{
  "id": "nasdaq-12345",
  "source": "nasdaq",
  "ticker": "EVO",
  "company_id": "evo-evolution",
  "title": "Evolution AB publicerar Q4-rapport 2024",
  "published_at": "2024-12-15T07:00:00Z",
  "collected_at": "2025-12-30T10:15:00Z",
  "url": "https://...",
  "content": "Full text or summary...",
  "category": null,
  "language": "sv"
}
```

## Error Handling

| Error | Solution |
|-------|----------|
| Company not found | Verify ticker spelling, try full name |
| RSS feed timeout | Retry after 30 seconds |
| No news in period | Try different date range or check feed URL |
| Duplicate items | Already deduplicated by ID |
```

**Step 3: Verify file exists**

```bash
cat .claude/skills/news-download/SKILL.md | head -20
```

**Step 4: Commit**

```bash
git add .claude/skills/news-download/
git commit -m "feat(news): create news-download skill structure"
```

---

## Task 3: Create Company Lookup Reference

**Files:**
- Create: `.claude/skills/news-download/references/company-lookup.md`

**Step 1: Create company-lookup.md**

Create `.claude/skills/news-download/references/company-lookup.md`:

```markdown
# Company Lookup

How to verify and enrich company information when adding to watchlist.

## Lookup Priority

1. Check internal `ticker_mapping.json`
2. Check `avanza_mapping.json` for First North stocks
3. Check delisted list (warn if found)
4. Query Nasdaq Nordic if not found locally

## Step 1: Check Internal Mappings

```python
import json
from pathlib import Path

def lookup_company(query: str) -> dict | None:
    """Look up company in internal mappings."""
    query_lower = query.lower()
    query_upper = query.upper()

    # Check ticker_mapping.json
    ticker_map = json.loads(Path('data/prices/ticker_mapping.json').read_text())
    mappings = ticker_map.get('mappings', {})

    # Direct ticker match (e.g., "EVO" -> "EVO.ST")
    for name, ticker in mappings.items():
        if query_upper in ticker or query_lower in name.lower():
            return {
                'name': name,
                'ticker': ticker,
                'source': 'ticker_mapping'
            }

    # Check avanza_mapping.json for First North
    avanza_map = json.loads(Path('data/prices/avanza_mapping.json').read_text())
    for name, avanza_id in avanza_map.get('mappings', {}).items():
        if query_lower in name.lower():
            return {
                'name': name,
                'avanza_id': avanza_id,
                'source': 'avanza_mapping',
                'note': 'First North - may not have Nasdaq RSS'
            }

    # Check if delisted
    for name, reason in avanza_map.get('delisted', {}).items():
        if query_lower in name.lower():
            return {
                'name': name,
                'delisted': True,
                'reason': reason,
                'source': 'avanza_mapping'
            }

    return None

# Example usage
result = lookup_company("EVO")
print(json.dumps(result, indent=2))
```

## Step 2: Parse Ticker for Exchange Info

```python
from podstock.db.ticker_lookup import parse_ticker_suffix

ticker = "EVO.ST"
exchange, market, currency = parse_ticker_suffix(ticker)
print(f"Exchange: {exchange}, Market: {market}, Currency: {currency}")
# Output: Exchange: OMX, Market: sweden, Currency: SEK
```

## Step 3: Query Nasdaq Nordic (if not found)

```python
import requests

def search_nasdaq_nordic(query: str) -> list[dict]:
    """Search Nasdaq Nordic for company."""
    url = "https://www.nasdaqomxnordic.com/webproxy/DataFeedProxy.aspx"
    params = {
        "SubSystem": "Prices",
        "Action": "Search",
        "json": f'{{"query":"{query}"}}'
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get('items', []):
            results.append({
                'name': item.get('name'),
                'ticker': item.get('symbol'),
                'nasdaq_id': item.get('id'),
                'isin': item.get('isin'),
                'market': item.get('market')
            })
        return results
    except Exception as e:
        print(f"Nasdaq search failed: {e}")
        return []

# Example
results = search_nasdaq_nordic("Evolution")
for r in results[:3]:
    print(f"{r['ticker']}: {r['name']}")
```

## Step 4: Build Company Entry

Once verified, create entry for sources.json:

```python
import json
from pathlib import Path
from datetime import datetime

def add_company_to_sources(
    ticker: str,
    name: str,
    since: str = "2024-01-01",
    nasdaq_id: str = None,
    isin: str = None
) -> dict:
    """Add company to news sources."""

    # Generate ID
    ticker_base = ticker.split('.')[0].lower()
    name_slug = name.lower().replace(' ', '-').replace('ab', '').strip('-')
    company_id = f"{ticker_base}-{name_slug}"

    # Load existing sources
    sources_path = Path('data/news/sources.json')
    sources = json.loads(sources_path.read_text())

    # Check if already exists
    existing_ids = [c['id'] for c in sources['companies']]
    if company_id in existing_ids:
        print(f"Company {company_id} already exists")
        return None

    # Create entry
    entry = {
        "id": company_id,
        "name": name,
        "ticker": ticker,
        "ticker_base": ticker_base.upper(),
        "exchange": "OMX",
        "market": "sweden",
        "nasdaq_id": nasdaq_id,
        "isin": isin,
        "feeds": {
            "nasdaq": f"https://www.nasdaqomxnordic.com/news/companynews?symbol={ticker_base.upper()}"
        },
        "since": since,
        "added_at": datetime.now().isoformat(),
        "active": True
    }

    # Add and save
    sources['companies'].append(entry)
    sources['updated_at'] = datetime.now().isoformat()
    sources_path.write_text(json.dumps(sources, indent=2, ensure_ascii=False))

    # Create directories
    company_dir = Path(f'data/news/raw/{company_id}')
    (company_dir / 'press-releases').mkdir(parents=True, exist_ok=True)
    (company_dir / 'articles').mkdir(parents=True, exist_ok=True)

    print(f"Added {name} ({ticker}) to news sources")
    print(f"Storage: data/news/raw/{company_id}/")

    return entry
```

## Full Lookup Flow

```python
# Complete example: add Evolution to watchlist
query = "EVO"

# 1. Check internal mappings
result = lookup_company(query)

if result and result.get('delisted'):
    print(f"WARNING: {result['name']} is delisted: {result['reason']}")
elif result:
    print(f"Found: {result['name']} -> {result.get('ticker')}")

    # 2. Get Nasdaq info if needed
    if not result.get('nasdaq_id'):
        nasdaq_results = search_nasdaq_nordic(result['name'])
        if nasdaq_results:
            result['nasdaq_id'] = nasdaq_results[0].get('nasdaq_id')
            result['isin'] = nasdaq_results[0].get('isin')

    # 3. Add to sources
    entry = add_company_to_sources(
        ticker=result['ticker'],
        name=result['name'],
        since="2024-01-01",
        nasdaq_id=result.get('nasdaq_id'),
        isin=result.get('isin')
    )
else:
    print(f"Not found locally, searching Nasdaq...")
    nasdaq_results = search_nasdaq_nordic(query)
    if nasdaq_results:
        r = nasdaq_results[0]
        entry = add_company_to_sources(
            ticker=r['ticker'],
            name=r['name'],
            since="2024-01-01",
            nasdaq_id=r.get('nasdaq_id'),
            isin=r.get('isin')
        )
    else:
        print("Company not found")
```
```

**Step 2: Verify file**

```bash
wc -l .claude/skills/news-download/references/company-lookup.md
```

Expected: ~180 lines

**Step 3: Commit**

```bash
git add .claude/skills/news-download/references/company-lookup.md
git commit -m "feat(news): add company lookup reference"
```

---

## Task 4: Create Fetch News Reference

**Files:**
- Create: `.claude/skills/news-download/references/fetch-news.md`

**Step 1: Create fetch-news.md**

Create `.claude/skills/news-download/references/fetch-news.md`:

```markdown
# Fetching News

How to fetch press releases and news articles from RSS feeds.

## Prerequisites

```python
# Install if needed
# pip install feedparser requests
```

## RSS Feed Sources

### Nasdaq Nordic (Primary)

```
Company news URL:
https://www.nasdaqomxnordic.com/news/companynews?symbol={TICKER}

Example for Evolution:
https://www.nasdaqomxnordic.com/news/companynews?symbol=EVO

Note: This returns HTML. For RSS, may need to scrape or use API.
```

### GlobeNewswire

```
RSS by company:
https://www.globenewswire.com/RssFeed/orgid/{ORG_ID}

RSS by ticker:
https://www.globenewswire.com/RssFeed/ticker/{TICKER}
```

### MFN.se (Swedish Regulatory)

```
All announcements RSS:
https://mfn.se/s/rss?type=all
```

### Media Feeds

| Source | RSS URL |
|--------|---------|
| Affärsvärlden | `https://www.affarsvarlden.se/rss/senaste` |
| Realtid | `https://www.realtid.se/feed` |
| Placera | `https://www.placera.se/rss/nyheter.xml` |

## Fetch Press Releases

```python
import feedparser
import json
import hashlib
from pathlib import Path
from datetime import datetime
from dateutil import parser as date_parser

def fetch_nasdaq_news(ticker: str, since: str = None) -> list[dict]:
    """Fetch news from Nasdaq Nordic for a company."""

    # Note: Nasdaq doesn't have clean RSS, we scrape the news page
    # For MVP, use their JSON endpoint
    import requests

    url = f"https://www.nasdaqomxnordic.com/news/companynews"
    params = {"symbol": ticker}

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()

        # Parse HTML for news items (simplified - real impl needs BeautifulSoup)
        # For now, return empty and rely on other sources
        print(f"Nasdaq page fetched for {ticker}, manual parsing needed")
        return []

    except Exception as e:
        print(f"Failed to fetch Nasdaq news: {e}")
        return []


def fetch_rss_feed(url: str, since: str = None) -> list[dict]:
    """Fetch and parse an RSS feed."""

    feed = feedparser.parse(url)

    if feed.bozo:
        print(f"Warning: Feed parsing issue: {feed.bozo_exception}")

    items = []
    since_dt = date_parser.parse(since) if since else None

    for entry in feed.entries:
        # Parse date
        published = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            published = datetime(*entry.published_parsed[:6])
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            published = datetime(*entry.updated_parsed[:6])

        # Filter by date
        if since_dt and published and published < since_dt:
            continue

        # Generate ID from URL or title
        id_source = entry.get('id') or entry.get('link') or entry.get('title', '')
        item_id = hashlib.md5(id_source.encode()).hexdigest()[:12]

        items.append({
            'id': item_id,
            'title': entry.get('title', ''),
            'url': entry.get('link', ''),
            'published_at': published.isoformat() if published else None,
            'summary': entry.get('summary', ''),
            'source_feed': url
        })

    return items


def fetch_globenewswire(ticker: str, since: str = None) -> list[dict]:
    """Fetch press releases from GlobeNewswire."""

    url = f"https://www.globenewswire.com/RssFeed/ticker/{ticker}"
    items = fetch_rss_feed(url, since)

    for item in items:
        item['source'] = 'globenewswire'

    return items


def fetch_mfn(company_name: str, since: str = None) -> list[dict]:
    """Fetch Swedish regulatory announcements from MFN.se."""

    url = "https://mfn.se/s/rss?type=all"
    all_items = fetch_rss_feed(url, since)

    # Filter by company name
    name_lower = company_name.lower()
    filtered = []
    for item in all_items:
        if name_lower in item['title'].lower() or name_lower in item.get('summary', '').lower():
            item['source'] = 'mfn'
            filtered.append(item)

    return filtered
```

## Fetch Media Articles

```python
def fetch_media_for_company(
    company_name: str,
    ticker: str,
    since: str = None
) -> list[dict]:
    """Fetch media articles mentioning a company."""

    # Load media feeds from sources.json
    sources = json.loads(Path('data/news/sources.json').read_text())
    media_feeds = [f for f in sources.get('media_feeds', []) if f.get('active')]

    keywords = [company_name.lower(), ticker.lower()]
    articles = []

    for feed in media_feeds:
        print(f"Fetching {feed['name']}...")
        items = fetch_rss_feed(feed['url'], since)

        for item in items:
            text = (item['title'] + ' ' + item.get('summary', '')).lower()
            if any(kw in text for kw in keywords):
                item['source'] = feed['id']
                articles.append(item)

    return articles
```

## Save News Items

```python
def save_news_item(
    company_id: str,
    item: dict,
    item_type: str = 'press-releases'  # or 'articles'
) -> bool:
    """Save a news item to disk."""

    # Build path
    base_dir = Path(f'data/news/raw/{company_id}/{item_type}')
    base_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename from date and ID
    pub_date = item.get('published_at', '')[:10] or 'unknown'
    filename = f"{pub_date}-{item['id']}.json"
    filepath = base_dir / filename

    # Skip if exists (deduplication)
    if filepath.exists():
        return False

    # Enrich item
    item['collected_at'] = datetime.now().isoformat()
    item['company_id'] = company_id

    # Save
    filepath.write_text(json.dumps(item, indent=2, ensure_ascii=False))
    return True


def update_state(company_id: str, press_count: int, article_count: int):
    """Update state.json after collection."""

    state_path = Path('data/news/state.json')
    state = json.loads(state_path.read_text())

    now = datetime.now().isoformat()

    if company_id not in state['companies']:
        state['companies'][company_id] = {
            'press_releases_count': 0,
            'articles_count': 0
        }

    state['companies'][company_id]['last_synced_at'] = now
    state['companies'][company_id]['press_releases_count'] += press_count
    state['companies'][company_id]['articles_count'] += article_count
    state['updated_at'] = now

    state_path.write_text(json.dumps(state, indent=2))
```

## Full Collection Flow

```python
def collect_news_for_company(company_id: str, since: str = None) -> dict:
    """Collect all news for a company."""

    # Load company info
    sources = json.loads(Path('data/news/sources.json').read_text())
    company = next((c for c in sources['companies'] if c['id'] == company_id), None)

    if not company:
        return {'error': f'Company {company_id} not found'}

    since = since or company.get('since')
    ticker = company['ticker_base']
    name = company['name']

    print(f"Collecting news for {name} ({ticker}) since {since}")

    # Fetch press releases
    press_items = []
    press_items += fetch_globenewswire(ticker, since)
    press_items += fetch_mfn(name, since)

    # Fetch media articles
    articles = fetch_media_for_company(name, ticker, since)

    # Save items
    press_saved = 0
    for item in press_items:
        if save_news_item(company_id, item, 'press-releases'):
            press_saved += 1

    articles_saved = 0
    for item in articles:
        if save_news_item(company_id, item, 'articles'):
            articles_saved += 1

    # Update state
    update_state(company_id, press_saved, articles_saved)

    return {
        'company': name,
        'ticker': ticker,
        'press_releases_fetched': len(press_items),
        'press_releases_saved': press_saved,
        'articles_fetched': len(articles),
        'articles_saved': articles_saved,
        'storage': f'data/news/raw/{company_id}/'
    }


# Example usage
result = collect_news_for_company('evo-evolution', since='2024-01-01')
print(json.dumps(result, indent=2))
```

## Testing a Feed

```python
# Quick test of any RSS feed
import feedparser

url = "https://www.affarsvarlden.se/rss/senaste"
feed = feedparser.parse(url)

print(f"Feed: {feed.feed.get('title', 'Unknown')}")
print(f"Items: {len(feed.entries)}")
for entry in feed.entries[:3]:
    print(f"  - {entry.title[:60]}...")
```
```

**Step 2: Verify file**

```bash
wc -l .claude/skills/news-download/references/fetch-news.md
```

Expected: ~250 lines

**Step 3: Commit**

```bash
git add .claude/skills/news-download/references/fetch-news.md
git commit -m "feat(news): add fetch news reference"
```

---

## Task 5: Create Storage Format Reference

**Files:**
- Create: `.claude/skills/news-download/references/storage-format.md`

**Step 1: Create storage-format.md**

Create `.claude/skills/news-download/references/storage-format.md`:

```markdown
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
```

**Step 2: Verify file**

```bash
wc -l .claude/skills/news-download/references/storage-format.md
```

Expected: ~150 lines

**Step 3: Commit**

```bash
git add .claude/skills/news-download/references/storage-format.md
git commit -m "feat(news): add storage format reference"
```

---

## Task 6: Test the Skill

**Step 1: Verify skill appears in Claude Code**

Restart Claude Code or run `/skills` to see if `news-download` appears.

**Step 2: Test RSS feed parsing**

```python
import feedparser

# Test Affärsvärlden RSS
url = "https://www.affarsvarlden.se/rss/senaste"
feed = feedparser.parse(url)
print(f"Feed title: {feed.feed.get('title', 'N/A')}")
print(f"Entry count: {len(feed.entries)}")
if feed.entries:
    print(f"Sample: {feed.entries[0].title[:60]}...")
```

**Step 3: Test GlobeNewswire**

```python
import feedparser

# Test GlobeNewswire for a known Swedish company
url = "https://www.globenewswire.com/RssFeed/ticker/EVO"
feed = feedparser.parse(url)
print(f"Entry count: {len(feed.entries)}")
for e in feed.entries[:3]:
    print(f"  - {e.title[:50]}...")
```

**Step 4: Report findings**

Document which feeds work and which need adjustments.

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat(news): complete news-download skill implementation"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Create directory structure | data/news/, sources.json, state.json |
| 2 | Create skill structure | SKILL.md, references/ |
| 3 | Company lookup reference | references/company-lookup.md |
| 4 | Fetch news reference | references/fetch-news.md |
| 5 | Storage format reference | references/storage-format.md |
| 6 | Test the skill | Verify RSS feeds work |

**Total estimated time:** 30-45 minutes

**After completion:** Run `/news-download` to add first company and test full flow.
