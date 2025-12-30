# Insider Transactions Feature Design

**Date:** 2025-12-30
**Status:** Ready for Implementation

---

## Overview

Add insider transaction tracking as a new data source and skill. Fetch insider buying/selling activity for US and Nordic stocks, both for standalone analysis and to validate podcast recommendations.

### Goals

1. **Single stock lookup** - `/insider AAPL` shows recent insider activity
2. **Portfolio scan** - `/insider` checks all stocks with active recommendations
3. **On-demand fetching** - No background sync, fetch when skill invoked
4. **Start free** - Use public APIs (SEC EDGAR, Finansinspektionen), upgrade later if needed

### Markets Covered

| Market | Source | Status |
|--------|--------|--------|
| US | SEC EDGAR (Form 4) | Phase 2 |
| Sweden | Finansinspektionen | Phase 3 |
| Norway | Oslo Børs | Future |
| Denmark/Finland | Nasdaq Nordic | Future |

---

## Module Structure

```
src/podstock/insider/
├── __init__.py
├── models.py              # InsiderTransaction, InsiderReport, etc.
├── exceptions.py          # InsiderError, SourceUnavailable, etc.
├── base_client.py         # Abstract base class for all market clients
├── clients/
│   ├── __init__.py
│   ├── sec_edgar.py       # US: SEC Form 4 filings
│   ├── finansinspektionen.py  # Sweden: FI's insider registry
│   ├── oslo_bors.py       # Norway: Oslo Børs (future placeholder)
│   └── nasdaq_nordic.py   # Denmark/Finland (future placeholder)
├── router.py              # Routes ticker → correct client based on suffix
├── portfolio.py           # Scans recommendations table for active positions
├── cache.py               # Response caching (1 hour TTL)
└── formatter.py           # Formats output for CLI/skill display
```

### Ticker Routing

The router detects market from ticker suffix:

| Pattern | Market | Client |
|---------|--------|--------|
| `AAPL`, `MSFT` (no suffix) | US | SEC EDGAR |
| `EVO.ST`, `VOLV-B.ST` | Sweden | Finansinspektionen |
| `EQNR.OL` | Norway | Oslo Børs (future) |
| `NOVO-B.CO` | Denmark | Nasdaq Nordic (future) |

---

## Data Models

```python
# models.py

from enum import Enum
from datetime import date, datetime
from pydantic import BaseModel


class InsiderRole(str, Enum):
    CEO = "ceo"
    CFO = "cfo"
    DIRECTOR = "director"
    OFFICER = "officer"
    MAJOR_SHAREHOLDER = "major_shareholder"
    OTHER = "other"


class TransactionType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    GIFT = "gift"
    EXERCISE = "exercise"
    OTHER = "other"


class InsiderTransaction(BaseModel):
    """Single insider transaction."""
    insider_name: str
    role: InsiderRole
    transaction_type: TransactionType
    shares: int
    price: float | None
    total_value: float
    currency: str
    transaction_date: date
    filing_date: date
    shares_after: int | None
    source: str
    source_url: str | None


class InsiderReport(BaseModel):
    """Response for a single stock lookup."""
    ticker: str
    company_name: str
    market: str
    transactions: list[InsiderTransaction]
    period_days: int
    fetched_at: datetime
```

---

## Client Interface

```python
# base_client.py

from abc import ABC, abstractmethod


class InsiderClient(ABC):
    """Base class for market-specific insider data clients."""

    @property
    @abstractmethod
    def market_code(self) -> str:
        """E.g., 'US', 'SE', 'NO'"""

    @property
    @abstractmethod
    def supported_suffixes(self) -> list[str]:
        """Ticker suffixes this client handles. Empty list = no suffix (US)."""

    @abstractmethod
    async def get_transactions(
        self,
        ticker: str,
        days: int = 90
    ) -> InsiderReport:
        """Fetch insider transactions for a ticker."""

    def supports_ticker(self, ticker: str) -> bool:
        """Check if this client handles the given ticker."""
        if not self.supported_suffixes:
            return "." not in ticker
        return any(ticker.upper().endswith(s) for s in self.supported_suffixes)
```

### SEC EDGAR Client (US)

The SEC provides Form 4 filings via their free EDGAR API.

**Flow:**
1. Map ticker → CIK using SEC's `company_tickers.json`
2. Fetch recent Form 4 filings for that CIK
3. Parse XML to extract transaction details
4. Normalize to `InsiderTransaction` model

**Rate limit:** 10 requests/second (implement throttle).

**No API key required.**

### Finansinspektionen Client (Sweden)

Sweden's Financial Supervisory Authority publishes insider transactions at `fi.se/insynsregistret`.

**Approach:**
- RSS feed for recent transactions
- Web scraping for historical lookups

**Challenge:** FI uses company names and ISIN, not tickers. Extend existing `ticker_mapping.json` with ISINs.

---

## Skill Interface

Skill location: `.claude/skills/insider/`

### Mode 1: Single Stock Lookup

```
/insider AAPL
/insider EVO.ST
```

**Output:**
```
## Insider Activity: AAPL (Apple Inc.)
Period: Last 90 days | Source: SEC EDGAR

| Date       | Insider          | Role     | Type | Shares    | Value      |
|------------|------------------|----------|------|-----------|------------|
| 2025-12-15 | Tim Cook         | CEO      | SELL | 50,000    | $12.5M     |
| 2025-12-10 | Luca Maestri     | CFO      | SELL | 20,000    | $5.0M      |
| 2025-11-28 | Jeff Williams    | Officer  | BUY  | 10,000    | $2.4M      |

Summary: 2 sells, 1 buy | Net: -$15.1M (bearish signal)
```

### Mode 2: Portfolio Scan

```
/insider
/insider --days 30
```

**Output:**
```
## Portfolio Insider Scan
Checked 12 stocks with active recommendations | Last 30 days

⚠️  Notable activity:
• EVO.ST: 3 insiders bought $2.1M (confirms your BUY rec from Dec 15)
• AAPL: CEO sold $12.5M (watch your position)

✓ No insider activity: MSFT, GOOG, VOLV-B.ST (8 others)
```

---

## Portfolio Integration

```python
# portfolio.py

class PortfolioScanner:
    """Scans insider activity for stocks with active recommendations."""

    def get_active_positions(self, session: Session) -> list[Security]:
        """
        Get securities with recent recommendations.

        Criteria for 'active':
        - Has BUY recommendation in last 180 days, OR
        - Has any recommendation without a closing SELL
        """
        pass

    async def scan_all(
        self,
        session: Session,
        days: int = 90
    ) -> list[tuple[Security, InsiderReport]]:
        """
        Fetch insider data for all active positions.

        Returns list of (security, report) pairs.
        Skips securities in unsupported markets.
        """
        pass
```

Reuses existing `Security` and `Recommendation` tables - no new database tables needed for MVP.

---

## Data Storage Structure

```
data/
├── insider/
│   ├── sources.json               # Configured sources/markets
│   ├── cache/                     # Temporary API response cache (1h TTL)
│   │   ├── sec_edgar/
│   │   │   └── AAPL-2025-12-30.json
│   │   └── finansinspektionen/
│   │       └── EVO.ST-2025-12-30.json
│   ├── raw/                       # Raw API responses
│   │   ├── sec_edgar/
│   │   │   └── apple-AAPL/
│   │   │       └── {filing_id}.json
│   │   └── finansinspektionen/
│   │       └── evolution-EVO.ST/
│   │           └── {date}-transactions.json
│   └── reports/                   # Generated insider reports
│       ├── portfolio-scan-2025-12-30.json
│       ├── apple-AAPL-2025-12-30.json
│       └── evolution-EVO.ST-2025-12-30.json
```

**Naming convention:** `{company_name_slug}-{ticker}` (lowercase, hyphenated).

### sources.json

```json
{
  "version": 1,
  "updated_at": "2025-12-30T10:00:00Z",
  "markets": {
    "US": {"enabled": true, "client": "sec_edgar"},
    "SE": {"enabled": true, "client": "finansinspektionen"},
    "NO": {"enabled": false, "client": null}
  }
}
```

---

## Error Handling

```python
# exceptions.py

class InsiderError(Exception):
    """Base exception for insider module."""

class SourceUnavailable(InsiderError):
    """Market/source not yet supported."""

class TickerNotFound(InsiderError):
    """Could not map ticker to company in source."""

class RateLimitExceeded(InsiderError):
    """Hit API rate limit, retry later."""

class ParseError(InsiderError):
    """Failed to parse response from source."""
```

### Edge Cases

| Situation | Behavior |
|-----------|----------|
| Unknown ticker suffix (e.g., `.DE`) | Return "Market not supported yet" |
| Ticker exists but no insider activity | Return empty report with "No transactions found" |
| SEC rate limit hit | Wait and retry (max 3 attempts) |
| FI website down or changed | Return error, suggest manual check |
| Company delisted | Note in response, show historical data if available |
| Dual-listed stocks (e.g., Spotify) | Use primary market based on ticker suffix |

### Caching

- Cache responses for 1 hour in `data/insider/cache/`
- Skill checks cache before fetching
- `--refresh` flag to bypass cache

---

## Implementation Roadmap

### Phase 1: Core Infrastructure
- [ ] `models.py` - Data models
- [ ] `exceptions.py` - Error types
- [ ] `base_client.py` - Abstract client interface
- [ ] `router.py` - Ticker → client routing
- [ ] `formatter.py` - Output formatting
- [ ] `cache.py` - Response caching

### Phase 2: US Market
- [ ] `clients/sec_edgar.py` - SEC Form 4 parsing
- [ ] Ticker → CIK mapping
- [ ] Rate limiting (10 req/sec)
- [ ] Test with common US stocks (AAPL, MSFT, TSLA)

### Phase 3: Swedish Market
- [ ] `clients/finansinspektionen.py` - FI registry scraping
- [ ] RSS feed parsing
- [ ] Ticker → ISIN/company name mapping
- [ ] Test with Swedish stocks (EVO.ST, VOLV-B.ST)

### Phase 4: Skill & Portfolio
- [ ] `.claude/skills/insider/` - Skill definition
- [ ] `portfolio.py` - Portfolio scanner
- [ ] Database integration for active positions
- [ ] Single stock mode (`/insider AAPL`)
- [ ] Portfolio scan mode (`/insider`)

### Phase 5: Polish
- [ ] `--days` flag for custom lookback period
- [ ] `--refresh` flag to bypass cache
- [ ] Better error messages
- [ ] Handle edge cases gracefully

### Future Phases
- [ ] Oslo Børs (Norway)
- [ ] Nasdaq Nordic (Denmark/Finland)
- [ ] Dashboard integration
- [ ] Paid data provider integration (if needed)

---

## Dependencies

No new dependencies required for Phase 1-2. Potential additions:

- `beautifulsoup4` - For Finansinspektionen scraping (Phase 3)
- `lxml` - XML parsing for SEC filings (may use stdlib)

---

## Open Questions

1. **Significant transaction thresholds** - Define exact rules for what triggers "notable activity" in portfolio scan (size, cluster, proportional)?
2. **ISIN mapping** - Extend `ticker_mapping.json` or create separate `isin_mapping.json`?
3. **Historical depth** - How far back should raw data be stored vs just cached?
