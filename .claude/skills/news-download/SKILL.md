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
