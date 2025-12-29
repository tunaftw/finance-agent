---
name: price-sync
description: Synka prisdata till databasen. Anvand nar anvandaren fragar "synka priser", "hamta prisdata", "uppdatera priser", eller vill se avkastning pa rekommendationer. Anvander LOKALT prisbibliotek (prices-tabellen) - Yahoo API anropas ENDAST efter anvandargodkannande. (project)
---

# Price Sync Skill

Synka prisdata for rekommendationer. Anvander lokalt prisbibliotek i forsta hand.

## VIKTIGT: API-Policy

**Yahoo Finance API anropas ENDAST efter explicit anvandargodkannande.**

- Historiska priser: Anvand `prices`-tabellen (lokalt bibliotek)
- Aktuellt pris: Anvand senaste lokala pris ELLER fraga anvandaren om live-pris onskas
- Nya tickers: Fraga anvandaren innan prishistorik laddas ner

## Quick Start

1. **Visa status** - Hur manga recs saknar priser
2. **Ticker-upplosning** - Samla okanda, lat anvandaren mappa
3. **Fraga om API-anrop** - Vill anvandaren hamta nya priser fran Yahoo?
4. **Synka priser** - Fran lokalt bibliotek (+ Yahoo om godkant)
5. **Visa sammanfattning**

## Step 1: Check Status

```python
from pathlib import Path
import sqlite3

def get_price_sync_status():
    db_path = Path("data/podstock.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Recs utan prisdata
    without_price = conn.execute("""
        SELECT COUNT(*) FROM recommendations r
        LEFT JOIN recommendation_performance rp ON r.id = rp.recommendation_id
        WHERE rp.id IS NULL
    """).fetchone()[0]

    # Recs med prisdata
    with_price = conn.execute("""
        SELECT COUNT(*) FROM recommendation_performance WHERE price_at_rec IS NOT NULL
    """).fetchone()[0]

    # Tickers i prices-tabellen
    tickers_with_history = conn.execute("""
        SELECT COUNT(DISTINCT ticker) FROM securities
        WHERE id IN (SELECT DISTINCT security_id FROM prices)
    """).fetchone()[0]

    conn.close()
    return {
        'with_price': with_price,
        'without_price': without_price,
        'tickers_in_db': tickers_with_history
    }
```

## Step 2: Ticker Resolution

Samma som tidigare - samla okanda, lat anvandaren mappa.

## Step 3: FRAGA ANVANDAREN OM API-ANROP

**KRITISKT: Innan nagra Yahoo-anrop gors, fraga anvandaren:**

```
Jag hittade X rekommendationer att synka.

For att hamta priser behovs:
- Y tickers saknar prishistorik (kraver Yahoo API-anrop)
- Z rekommendationer kan synkas fran lokalt bibliotek

Vad vill du gora?
1. Synka endast fran lokalt bibliotek (inga API-anrop)
2. Ladda ner prishistorik for nya tickers (Y API-anrop) + synka
3. Uppdatera aven aktuella priser (kraver Z extra API-anrop)
4. Avbryt
```

## Step 4: Execute Sync

### Alternativ 1: Endast lokalt (INGA API-anrop)

```python
def sync_local_only():
    """Synka endast fran lokalt prisbibliotek, inga Yahoo-anrop."""
    # ... kod som ENDAST laser fran prices-tabellen
    # For price_current: anvand senaste pris i prices-tabellen
    # INGA anrop till yahoo.get_current_price()
```

**For `price_current` utan API:**
```python
def get_latest_local_price(security_id):
    """Hamta senaste lokala pris istallet for live-pris."""
    row = conn.execute("""
        SELECT date, close FROM prices
        WHERE security_id = ?
        ORDER BY date DESC LIMIT 1
    """, (security_id,)).fetchone()
    return row['close'], row['date'] if row else (None, None)
```

### Alternativ 2: Ladda ner prishistorik (med godkannande)

```python
def download_price_history(ticker, start_date):
    """Ladda ner prishistorik - ENDAST efter anvandargodkannande."""
    snapshots = yahoo.get_price_range(ticker, start_date, datetime.now())
    # Spara alla priser till prices-tabellen
    for snap in snapshots:
        conn.execute("""
            INSERT OR IGNORE INTO prices (security_id, date, open, high, low, close, volume, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'yahoo')
        """, ...)
```

### Alternativ 3: Uppdatera aktuella priser (med godkannande)

```python
def update_current_prices(tickers):
    """Hamta aktuella priser - ENDAST efter anvandargodkannande."""
    for ticker in tickers:
        snapshot = yahoo.get_current_price(ticker)
        # Uppdatera price_current i recommendation_performance
```

## Prisbibliotek (prices-tabellen)

Skill:en anvander `prices`-tabellen som lokalt cache:

| Kolumn | Beskrivning |
|--------|-------------|
| security_id | FK till securities |
| date | YYYY-MM-DD |
| open, high, low, close | OHLC-priser |
| volume | Handelsvolym |
| source | 'yahoo' eller 'coingecko' |

**Fordelar:**
- Snabba lokala lookups (inga API-anrop)
- Historik sparas permanent
- Inga rate limits

## Database Tables

| Tabell | Anvandning |
|--------|------------|
| `prices` | Lokalt prisbibliotek (OHLC per dag) |
| `securities` | Ticker -> security_id mapping |
| `recommendation_performance` | Prisdata per rekommendation |

## Nya falt i recommendation_performance

| Falt | Beskrivning |
|------|-------------|
| `price_at_rec` | Pris vid rekommendationsdatum |
| `price_current` | Senaste pris (lokalt eller live) |
| `price_current_date` | Datum for price_current |
| `ticker_used` | Vilken Yahoo-ticker som anvandes |
| `return_current` | Avkastning fran rec till nu |

## Error Handling

| Fel | Losning |
|-----|---------|
| Ticker saknar prishistorik | Fraga anvandaren om nedladdning |
| Yahoo rate limit | Vanta 0.5s (inbyggt) |
| Delisted aktie | Logga, hoppa over |

## Trigger Phrases

- "synka priser"
- "hamta prisdata"
- "uppdatera priser"
- "kolla avkastning"
- "hur har rekommendationerna gatt"
