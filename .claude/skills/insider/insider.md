---
name: insider
description: Fetch insider transaction data for stocks. Use `/insider AAPL` for single stock or `/insider` to scan portfolio.
---

# Insider Transaction Lookup

Fetch insider buying/selling activity from SEC EDGAR (US) and Finansinspektionen (Sweden).

## Usage

### Single Stock Lookup
```
/insider AAPL
/insider EVO.ST
/insider MSFT --days 30
```

### Portfolio Scan
```
/insider
/insider --days 30
```

## Implementation

When this skill is invoked:

1. **Parse arguments:**
   - If ticker provided: single stock lookup mode
   - If no ticker: portfolio scan mode
   - Optional `--days N` flag (default: 90)
   - Optional `--refresh` flag to bypass cache

2. **For single stock lookup:**
   ```python
   from podstock.insider import InsiderRouter, InsiderStorage, format_report
   from podstock.insider.clients import SECEdgarClient

   # Initialize
   router = InsiderRouter()
   router.register_client(SECEdgarClient())
   storage = InsiderStorage()

   # Check cache first (unless --refresh)
   if not refresh and storage.is_cache_valid(ticker, source, ttl_hours=1):
       report = storage.load_cache(ticker, source)
   else:
       client = router.get_client(ticker)
       report = await client.get_transactions(ticker, days=days)
       storage.save_cache(report, client.market_code.lower())

   # Format and display
   print(format_report(report))
   ```

3. **For portfolio scan:**
   ```python
   from podstock.insider import InsiderRouter, format_portfolio_scan
   from podstock.insider.portfolio import PortfolioScanner
   from podstock.db import get_session

   router = InsiderRouter()
   router.register_client(SECEdgarClient())
   scanner = PortfolioScanner(router)

   with get_session() as session:
       results = await scanner.scan_all(session, days=days)

   print(format_portfolio_scan(results))
   ```

## Supported Markets

| Suffix | Market | Status |
|--------|--------|--------|
| (none) | US | Active |
| .ST | Sweden | Active |
| .NGM | Sweden | Active |
| .OL | Norway | Coming soon |
| .CO | Denmark | Coming soon |
| .HE | Finland | Coming soon |

## Error Handling

- **Unknown ticker suffix:** "Market not supported yet. Supported: US, SE"
- **Ticker not found:** "Could not find TICKER in SEC/FI database"
- **Rate limit:** "Rate limit hit. Try again in 60 seconds."
- **Network error:** "Could not connect to data source. Check your connection."
