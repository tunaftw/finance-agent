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
