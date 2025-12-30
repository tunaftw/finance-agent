# News Download Feature Design

**Date:** 2025-12-30
**Status:** Approved

---

## 1. Overview

A new feature to collect press releases and news articles about Nordic companies to generate alpha for stock investing. Follows the existing PodStock philosophy: download raw data, then parse/analyze with AI.

### Goals
- Collect company press releases from Nasdaq Nordic, GlobeNewswire, MFN
- Collect financial news articles from Swedish media (Affärsvärlden, Realtid, Placera)
- Store in structured format matching existing `data/` patterns
- Enable correlation with podcast mentions, tweets, and filings analysis

### Constraints
- Free or very low cost ($5-10/month max)
- Semi-automated (scripts that user triggers, not fully manual)
- Manual watchlist (user specifies which companies to track)
- Historical depth flexible per company

---

## 2. Data Sources

### Primary Sources (Press Releases)

| Source | Coverage | Historical Depth | Format |
|--------|----------|------------------|--------|
| **Nasdaq Nordic News** | All OMX-listed companies | ~2-3 years | RSS per company |
| **MFN.se** | Swedish regulatory (MAR) | ~1 year | RSS |
| **GlobeNewswire** | International wire releases | ~2 years | RSS by company |

### Secondary Sources (Financial News)

| Source | RSS URL | Active by default |
|--------|---------|-------------------|
| Affärsvärlden | `https://www.affarsvarlden.se/rss/senaste` | Yes |
| Realtid | `https://www.realtid.se/feed` | Yes |
| Placera | `https://www.placera.se/rss/nyheter.xml` | Yes |
| Börsvärlden | `https://borsvarlden.com/feed/` | No (noisy) |

### Nasdaq Nordic Feed URLs

```
Company news feed:
https://www.nasdaqomxnordic.com/news/companynews?symbol={TICKER}

To get nasdaq_id for RSS:
/webproxy/DataFeedProxy.aspx?SubSystem=Prices&Action=Search&json={"query":"EVO"}
```

---

## 3. Directory Structure

```
data/news/
├── sources.json              # Configured companies
├── state.json                # Collection state per company
├── raw/                      # Raw downloaded content
│   └── {ticker}-{company}/   # e.g., evo-evolution, kindsdb-kindred
│       ├── press-releases/   # Official company announcements
│       │   └── {id}.json     # One file per release
│       └── articles/         # Media coverage
│           └── {id}.json     # One file per article
└── analyses/                 # AI-analyzed news (Phase 2)
    └── {ticker}-{company}-analysis.json
```

---

## 4. Data Models

### Sources File (`data/news/sources.json`)

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
      "ir_page": "https://www.evolution.com/investors",
      "feeds": {
        "nasdaq": "https://www.nasdaqomxnordic.com/news/companynews?symbol=EVO",
        "globenewswire": null
      },
      "since": "2023-01-01",
      "added_at": "2025-12-30T10:00:00Z",
      "active": true
    }
  ],
  "media_feeds": [
    {"id": "affarsvarlden", "url": "https://www.affarsvarlden.se/rss/senaste", "active": true},
    {"id": "realtid", "url": "https://www.realtid.se/feed", "active": true},
    {"id": "placera", "url": "https://www.placera.se/rss/nyheter.xml", "active": true}
  ]
}
```

### State File (`data/news/state.json`)

```json
{
  "version": 1,
  "updated_at": "2025-12-30T12:00:00Z",
  "companies": {
    "evo-evolution": {
      "last_synced_at": "2025-12-30T12:00:00Z",
      "press_releases_count": 45,
      "articles_count": 123,
      "last_item_date": "2025-12-28T07:00:00Z"
    }
  }
}
```

### News Item (`data/news/raw/{ticker}-{company}/press-releases/{id}.json`)

```json
{
  "id": "nasdaq-12345",
  "source": "nasdaq",
  "ticker": "EVO",
  "company_id": "evo-evolution",
  "title": "Evolution AB (publ) publicerar Q4-rapport 2024",
  "published_at": "2024-12-15T07:00:00Z",
  "collected_at": "2025-12-30T10:15:00Z",
  "url": "https://www.nasdaqomxnordic.com/news/...",
  "content": "Full text or summary...",
  "category": null,
  "language": "sv",
  "analyzed": false
}
```

---

## 5. Skills

### Skill 1: `news-download`

**Purpose:** Add companies to watchlist, download press releases and articles.

**Trigger phrases:**
- "download news for Evolution"
- "add EVO to news watchlist"
- "sync news for all companies"
- "get press releases for Volvo since 2024"

**Workflow:**

```
Step 1: Gather Requirements
├── Action? (Add new / Download existing / Sync all)
├── If new: Ticker/name? Historical depth (since date)?
└── If existing: Which company? Date range?

Step 2: Company Lookup (for new companies)
├── Check ticker_mapping.json
├── Check avanza_mapping.json
├── Check delisted list (warn if found)
├── If not found: Query Nasdaq Nordic API
└── Enrich: nasdaq_id, ISIN, IR page

Step 3: Fetch News
├── For each configured feed (Nasdaq, GlobeNewswire, MFN)
├── Filter by date range
├── Deduplicate against existing raw/ files
└── Save new items to raw/{ticker}-{company}/press-releases/

Step 4: Fetch Media Articles
├── For each media feed (Affärsvärlden, Realtid, etc.)
├── Filter by company name/ticker keywords
└── Save matches to raw/{ticker}-{company}/articles/

Step 5: Update State & Report
├── Update state.json
└── Report: X press releases, Y articles saved
```

### Skill 2: `news-analyze` (Phase 2)

**Purpose:** AI-analyze collected news, extract signals, categorize.

**Workflow:**
1. Load unanalyzed news items from raw/
2. Generate analysis prompt (categorize, extract key facts, sentiment)
3. Save to analyses/
4. Mark items as analyzed

---

## 6. Internal Resources to Leverage

| Resource | Usage |
|----------|-------|
| `data/prices/ticker_mapping.json` | Company name → Yahoo ticker lookup |
| `data/prices/avanza_mapping.json` | First North stocks, delisted companies |
| `src/podstock/db/ticker_lookup.py` | `get_or_create_security()`, `parse_ticker_suffix()` |
| Database `securities` table | Store company with aliases |

### Lookup Priority

```
1. ticker_mapping.json → If found: use Yahoo ticker
2. avanza_mapping.json → If found: note First North
3. delisted list → If found: warn user
4. Nasdaq Nordic API → Verify listing, get nasdaq_id
5. Auto-add to ticker_mapping.json for future
```

---

## 7. Integration with Existing System

### Connection to Other Data

```
Security (central entity)
    │
    ├── Filings (10-K, annual reports)
    ├── News (press releases, articles) ← NEW
    ├── Podcasts (mentions, recommendations)
    └── Twitter (analyst tweets)
```

### Future Database Tables

```sql
CREATE TABLE news_sources (
    id TEXT PRIMARY KEY,
    name TEXT,
    feed_url_pattern TEXT,
    active BOOLEAN DEFAULT TRUE
);

CREATE TABLE news_items (
    id TEXT PRIMARY KEY,
    security_id INTEGER REFERENCES securities(id),
    source_id TEXT REFERENCES news_sources(id),
    title TEXT,
    content TEXT,
    url TEXT,
    published_at TIMESTAMP,
    collected_at TIMESTAMP,
    category TEXT,
    language TEXT,
    analyzed BOOLEAN DEFAULT FALSE
);
```

### Cross-Reference Queries (Future)

```bash
# Timeline view
podstock news timeline EVO --days 30

# Correlate with other sources
podstock news correlate EVO --with podcasts,twitter
```

---

## 8. Skill Files Structure

```
.claude/skills/news-download/
├── SKILL.md                    # Main skill instructions
└── references/
    ├── nasdaq-lookup.md        # How to find Nasdaq company IDs
    ├── rss-sources.md          # All RSS feed URLs and patterns
    └── storage-format.md       # JSON schema for news items

.claude/skills/news-analyze/    # (Phase 2)
├── SKILL.md
└── references/
    └── analysis-prompt.md
```

---

## 9. Implementation Phases

### Phase 1: Core Download (MVP)
- [ ] Create `data/news/` directory structure
- [ ] Create `sources.json` and `state.json` schemas
- [ ] Build `news-download` skill
- [ ] Implement Nasdaq Nordic RSS fetching
- [ ] Implement media RSS fetching with keyword filtering
- [ ] Test with 2-3 companies

### Phase 2: Analysis
- [ ] Build `news-analyze` skill
- [ ] Create categorization prompt (quarterly report, insider, contract, etc.)
- [ ] Extract key facts and sentiment

### Phase 3: Database Integration
- [ ] Add `news_sources` and `news_items` tables
- [ ] Create NewsLoader for database import
- [ ] Enable cross-referencing with recommendations

### Phase 4: Real-time Monitoring
- [ ] Add cron/scheduled sync capability
- [ ] Alert on new significant news

---

## 10. Open Questions (Resolved)

| Question | Decision |
|----------|----------|
| Single skill or multiple? | Two skills: download + analyze |
| Folder naming | `{ticker}-{company}` (e.g., evo-evolution) |
| Historical depth | Flexible per company (user specifies "since" date) |
| Budget | Free primary, $5-10/month acceptable if needed |
| Company selection | Manual watchlist |
