---
name: news-analyze
description: Analyze collected news and press releases using AI. Use when user wants to categorize news, extract key facts, or summarize press releases for a company. Works on data collected by news-download skill.
---

# News Analyze Skill

Analyze collected press releases and news articles to extract insights, categorize by type, and identify key information.

## Quick Start

1. Ask user: Which company to analyze?
2. Load unanalyzed news from `data/news/raw/{company}/`
3. Analyze each item (categorize, extract facts, sentiment)
4. Save analysis to `data/news/analyses/{company}-analysis.json`

## Workflow

### Step 1: Select Company

```python
import json
from pathlib import Path

# List companies with news
sources = json.loads(Path('data/news/sources.json').read_text())
for company in sources['companies']:
    news_dir = Path(f"data/news/raw/{company['id']}/press-releases")
    count = len(list(news_dir.glob('*.json'))) if news_dir.exists() else 0
    print(f"{company['name']} ({company['ticker']}): {count} press releases")
```

### Step 2: Load News Items

```python
def load_news_for_company(company_id: str) -> list[dict]:
    """Load all news items for a company."""
    items = []

    for subdir in ['press-releases', 'articles']:
        news_dir = Path(f'data/news/raw/{company_id}/{subdir}')
        if news_dir.exists():
            for f in news_dir.glob('*.json'):
                item = json.loads(f.read_text())
                item['_file'] = str(f)
                item['_type'] = subdir
                items.append(item)

    return sorted(items, key=lambda x: x.get('published_at') or '', reverse=True)
```

### Step 3: Analyze Each Item

For each news item, determine:

**Category** (one of):
- `quarterly_report` - Q1/Q2/Q3/Q4 earnings reports
- `annual_report` - Full year reports
- `partnership` - New partnerships, collaborations
- `product_launch` - New products, features, launches
- `expansion` - Geographic expansion, new markets
- `management` - Executive changes, board updates
- `regulatory` - Compliance, licenses, regulatory news
- `financial` - Funding, acquisitions, financial transactions
- `other` - General news

**Sentiment**: `positive`, `neutral`, `negative`

**Key facts**: Extract 2-3 bullet points

### Step 4: Save Analysis

Save to `data/news/analyses/{company_id}-analysis.json`:

```json
{
  "company_id": "hack-hacksaw-gaming",
  "company_name": "Hacksaw Gaming",
  "analyzed_at": "2025-12-30T12:00:00Z",
  "total_items": 48,
  "items": [
    {
      "id": "mfn-abc123",
      "title": "Hacksaw Gaming Q3 Report",
      "published_at": "2024-10-15T07:00:00Z",
      "category": "quarterly_report",
      "sentiment": "positive",
      "key_facts": [
        "Revenue up 35% YoY",
        "Expanded to 3 new markets",
        "New studio partnership announced"
      ],
      "summary": "Strong Q3 with continued growth..."
    }
  ],
  "category_summary": {
    "quarterly_report": 4,
    "partnership": 15,
    "expansion": 8
  }
}
```

## Analysis Prompt Template

For each news item, use this prompt structure:

```
Analyze this press release:

Title: {title}
URL: {url}
Content: {summary or content}

Respond in JSON:
{
  "category": "one of: quarterly_report, annual_report, partnership, product_launch, expansion, management, regulatory, financial, other",
  "sentiment": "positive/neutral/negative",
  "key_facts": ["fact 1", "fact 2", "fact 3"],
  "summary": "One sentence summary"
}
```

## Batch Analysis

For efficiency, analyze multiple items in one prompt:

```python
def batch_analyze(items: list[dict], batch_size: int = 10) -> list[dict]:
    """Analyze items in batches."""
    results = []

    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        # Build prompt with all items in batch
        # Send to LLM
        # Parse results
        results.extend(batch_results)

    return results
```
