# Fetching News

How to fetch press releases and news articles from RSS feeds.

## Prerequisites

```python
# Install if needed
# pip install feedparser requests python-dateutil
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
