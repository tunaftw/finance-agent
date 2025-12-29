# Price Methods - Detaljerad Implementation

## Overview

Denna fil innehaller detaljerad Python-kod for pris-synk.

Anvander:
- `YahooFinanceClient` - for att hamta priser
- `TickerMapper` - for att losa upp aktienamn till tickers
- `prices` tabell - lokalt prisbibliotek (OHLC per dag)
- `securities` tabell - ticker -> security_id mapping
- `recommendation_performance` - tabell for att lagra prisdata per rec

## Strategi: Lokalt Prisbibliotek

Istallet for att gora ett Yahoo-anrop per datum, anvander vi:

1. **Kolla `prices`-tabellen forst** - har vi redan priset lokalt?
2. **Om nej, ladda ner HELA historiken** for aktien fran Yahoo
3. **Spara i `prices`** - alla framtida lookups ar gratis
4. **Bara `current_price` hamtas live** - det ar alltid "nu"

Detta gor synken MYCKET snabbare efter forsta korningen.

## Full Price Sync Implementation

```python
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
from collections import defaultdict

from podstock.prices.clients.yahoo import YahooFinanceClient
from podstock.prices.ticker_mapping import TickerMapper

# Intervaller att hamta (dagar efter rekommendation)
INTERVALS = [1, 7, 30, 90, 365]


def sync_prices(
    source_types: list[str] = None,
    force_resync: bool = False,
    update_current_only: bool = False,
    verbose: bool = True
):
    """
    Synka prisdata for alla rekommendationer.

    Args:
        source_types: ['podcast', 'twitter', 'youtube'] eller None for alla
        force_resync: Om True, synka aven de som redan har price_at_rec
        update_current_only: Om True, uppdatera bara price_current
        verbose: Visa progress

    Returns:
        dict med resultat
    """
    db_path = Path("data/podstock.db")
    mapper = TickerMapper(Path("data/prices/ticker_mapping.json"))
    yahoo = YahooFinanceClient(rate_limit_delay=0.5)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Bygga WHERE-klausul baserat pa filter
    where_clauses = []
    if not force_resync and not update_current_only:
        where_clauses.append("rp.price_at_rec IS NULL OR rp.id IS NULL")
    if source_types:
        types_str = ", ".join(f"'{t}'" for t in source_types)
        where_clauses.append(f"s.type IN ({types_str})")

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Hamta alla rekommendationer att synka
    query = f"""
        SELECT
            r.id as rec_id,
            r.raw_stock_name,
            r.raw_ticker,
            c.published_at,
            s.type as source_type,
            rp.id as perf_id,
            rp.price_at_rec as existing_price
        FROM recommendations r
        JOIN analyses a ON r.analysis_id = a.id
        JOIN content c ON a.content_id = c.id
        JOIN sources s ON c.source_id = s.id
        LEFT JOIN recommendation_performance rp ON r.id = rp.recommendation_id
        WHERE {where_sql}
        ORDER BY c.published_at DESC
    """

    recs = conn.execute(query).fetchall()

    if verbose:
        print(f"Hittade {len(recs)} rekommendationer att synka")

    # Gruppera per ticker for effektivitet
    # Key: ticker, Value: list of (rec_id, published_at, perf_id)
    ticker_groups = defaultdict(list)
    skipped_no_ticker = []

    for rec in recs:
        stock_name = rec['raw_stock_name']
        raw_ticker = rec['raw_ticker']

        # Forsok losa upp ticker
        ticker = mapper.lookup(stock_name)
        if ticker is None and raw_ticker:
            # Anvand raw_ticker om den ser ut som en giltig ticker
            if '.' in raw_ticker or '-' in raw_ticker:
                ticker = raw_ticker

        if ticker:
            ticker_groups[ticker].append({
                'rec_id': rec['rec_id'],
                'published_at': rec['published_at'],
                'perf_id': rec['perf_id'],
                'existing_price': rec['existing_price']
            })
        else:
            skipped_no_ticker.append(stock_name)

    if verbose:
        print(f"Unika tickers: {len(ticker_groups)}")
        print(f"Hoppar over (ingen ticker): {len(skipped_no_ticker)}")

    # Resultat-tracker
    results = {
        'synced': 0,
        'skipped_no_ticker': len(set(skipped_no_ticker)),
        'failed': 0,
        'errors': [],
        'returns': []
    }

    # Cache for priser (ticker+date -> price)
    price_cache = {}

    # Processa per ticker
    ticker_count = 0
    for ticker, rec_list in ticker_groups.items():
        ticker_count += 1

        if verbose and ticker_count % 10 == 0:
            print(f"  [{ticker_count}/{len(ticker_groups)}] Processar {ticker}...")

        try:
            # Hamta current price en gang per ticker
            current_snapshot = yahoo.get_current_price(ticker)
            current_price = current_snapshot.price if current_snapshot else None
            current_date = datetime.now().strftime("%Y-%m-%d")

            for rec_info in rec_list:
                rec_id = rec_info['rec_id']
                published_at = rec_info['published_at']
                perf_id = rec_info['perf_id']

                # Parsa datum
                try:
                    rec_date = datetime.fromisoformat(published_at[:10])
                except:
                    rec_date = datetime.now() - timedelta(days=365)

                today = datetime.now()

                # Hamta price_at_rec (cacha)
                cache_key_rec = f"{ticker}_{rec_date.strftime('%Y-%m-%d')}"
                if cache_key_rec in price_cache:
                    price_at_rec = price_cache[cache_key_rec]
                else:
                    snapshot = yahoo.get_historical_price(ticker, rec_date)
                    price_at_rec = snapshot.price if snapshot else None
                    price_cache[cache_key_rec] = price_at_rec

                if price_at_rec is None:
                    results['failed'] += 1
                    results['errors'].append(f"{ticker}: No price at {rec_date.date()}")
                    continue

                # Hamta intervallpriser
                interval_prices = {}
                for days in INTERVALS:
                    target_date = rec_date + timedelta(days=days)
                    if target_date <= today:
                        cache_key = f"{ticker}_{target_date.strftime('%Y-%m-%d')}"
                        if cache_key in price_cache:
                            interval_prices[days] = price_cache[cache_key]
                        else:
                            snapshot = yahoo.get_historical_price(ticker, target_date)
                            interval_prices[days] = snapshot.price if snapshot else None
                            price_cache[cache_key] = interval_prices[days]

                # Berakna avkastningar
                returns = {}
                for days in INTERVALS:
                    if days in interval_prices and interval_prices[days]:
                        returns[days] = ((interval_prices[days] - price_at_rec) / price_at_rec) * 100

                return_current = None
                if current_price and price_at_rec:
                    return_current = ((current_price - price_at_rec) / price_at_rec) * 100
                    results['returns'].append(return_current)

                # Uppdatera eller skapa recommendation_performance
                if perf_id:
                    # Update existing
                    update_sql = """
                        UPDATE recommendation_performance SET
                            price_at_rec = COALESCE(price_at_rec, ?),
                            price_1d = COALESCE(price_1d, ?),
                            price_7d = COALESCE(price_7d, ?),
                            price_30d = COALESCE(price_30d, ?),
                            price_90d = COALESCE(price_90d, ?),
                            price_365d = COALESCE(price_365d, ?),
                            return_1d = COALESCE(return_1d, ?),
                            return_7d = COALESCE(return_7d, ?),
                            return_30d = COALESCE(return_30d, ?),
                            return_90d = COALESCE(return_90d, ?),
                            return_365d = COALESCE(return_365d, ?),
                            price_current = ?,
                            price_current_date = ?,
                            ticker_used = ?,
                            return_current = ?,
                            calculated_at = ?
                        WHERE id = ?
                    """
                    conn.execute(update_sql, (
                        price_at_rec,
                        interval_prices.get(1),
                        interval_prices.get(7),
                        interval_prices.get(30),
                        interval_prices.get(90),
                        interval_prices.get(365),
                        returns.get(1),
                        returns.get(7),
                        returns.get(30),
                        returns.get(90),
                        returns.get(365),
                        current_price,
                        current_date,
                        ticker,
                        return_current,
                        datetime.now().isoformat(),
                        perf_id
                    ))
                else:
                    # Insert new
                    insert_sql = """
                        INSERT INTO recommendation_performance (
                            recommendation_id,
                            price_at_rec,
                            price_1d, price_7d, price_30d, price_90d, price_365d,
                            return_1d, return_7d, return_30d, return_90d, return_365d,
                            price_current, price_current_date, ticker_used, return_current,
                            calculated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    conn.execute(insert_sql, (
                        rec_id,
                        price_at_rec,
                        interval_prices.get(1),
                        interval_prices.get(7),
                        interval_prices.get(30),
                        interval_prices.get(90),
                        interval_prices.get(365),
                        returns.get(1),
                        returns.get(7),
                        returns.get(30),
                        returns.get(90),
                        returns.get(365),
                        current_price,
                        current_date,
                        ticker,
                        return_current,
                        datetime.now().isoformat()
                    ))

                results['synced'] += 1

        except Exception as e:
            results['failed'] += 1
            results['errors'].append(f"{ticker}: {str(e)}")

        # Commit var 100:e ticker for sakerhets skull
        if ticker_count % 100 == 0:
            conn.commit()

    conn.commit()
    conn.close()

    return results


def print_price_summary(results: dict):
    """Skriv ut sammanfattning av pris-sync."""
    print("\n" + "=" * 60)
    print("PRICE SYNC KLAR")
    print("=" * 60)

    total = results['synced'] + results['failed'] + results['skipped_no_ticker']

    print(f"\nSynkade: {results['synced']}/{total} rekommendationer")

    if results['skipped_no_ticker'] > 0:
        print(f"Hoppade over (ingen ticker): {results['skipped_no_ticker']} st")

    if results['failed'] > 0:
        print(f"Misslyckades: {results['failed']} st")
        for error in results['errors'][:5]:
            print(f"  - {error}")
        if len(results['errors']) > 5:
            print(f"  ... och {len(results['errors']) - 5} till")

    if results['returns']:
        import statistics
        returns = results['returns']
        avg_return = statistics.mean(returns)
        median_return = statistics.median(returns)
        best = max(returns)
        worst = min(returns)

        print(f"\nAvkastningsstatistik (return_current):")
        print(f"  - Genomsnitt: {avg_return:+.1f}%")
        print(f"  - Median: {median_return:+.1f}%")
        print(f"  - Bast: {best:+.1f}%")
        print(f"  - Samst: {worst:+.1f}%")

    print("=" * 60)


# Korning
if __name__ == "__main__":
    results = sync_prices(verbose=True)
    print_price_summary(results)
```

## Update Current Prices Only

For snabb uppdatering av bara aktuella priser (utan historiska):

```python
def update_current_prices(verbose: bool = True):
    """Uppdatera bara price_current for alla som redan har price_at_rec."""
    db_path = Path("data/podstock.db")
    yahoo = YahooFinanceClient(rate_limit_delay=0.5)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Hamta unika tickers som redan har prisdata
    query = """
        SELECT DISTINCT rp.ticker_used, COUNT(*) as count
        FROM recommendation_performance rp
        WHERE rp.ticker_used IS NOT NULL AND rp.price_at_rec IS NOT NULL
        GROUP BY rp.ticker_used
    """

    tickers = conn.execute(query).fetchall()

    if verbose:
        print(f"Uppdaterar current price for {len(tickers)} tickers...")

    updated = 0
    failed = 0
    current_date = datetime.now().strftime("%Y-%m-%d")

    for i, row in enumerate(tickers, 1):
        ticker = row['ticker_used']

        if verbose and i % 10 == 0:
            print(f"  [{i}/{len(tickers)}] {ticker}...")

        try:
            snapshot = yahoo.get_current_price(ticker)
            if snapshot:
                # Uppdatera alla recs med denna ticker
                update_sql = """
                    UPDATE recommendation_performance
                    SET price_current = ?,
                        price_current_date = ?,
                        return_current = CASE
                            WHEN price_at_rec > 0 THEN ((? - price_at_rec) / price_at_rec) * 100
                            ELSE NULL
                        END
                    WHERE ticker_used = ?
                """
                conn.execute(update_sql, (
                    snapshot.price,
                    current_date,
                    snapshot.price,
                    ticker
                ))
                updated += row['count']
            else:
                failed += row['count']
        except Exception as e:
            failed += row['count']
            if verbose:
                print(f"  [!] {ticker}: {e}")

    conn.commit()
    conn.close()

    if verbose:
        print(f"\nUppdaterade: {updated} rekommendationer")
        print(f"Misslyckades: {failed}")

    return {'updated': updated, 'failed': failed}
```

## Interactive Ticker Mapping

Anvands i Step 2 for att mappa okanda tickers interaktivt:

```python
def add_ticker_mapping_interactive(stock_name: str, ticker: str):
    """Lagg till ny ticker-mapping och spara."""
    mapper = TickerMapper(Path("data/prices/ticker_mapping.json"))
    mapper.add_mapping(stock_name, ticker)
    print(f"Sparade: '{stock_name}' -> '{ticker}'")
    return True
```

## Get Statistics

```python
def get_price_statistics():
    """Hamta statistik over alla synkade priser."""
    db_path = Path("data/podstock.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    stats = {}

    # Totalt antal
    stats['total'] = conn.execute(
        "SELECT COUNT(*) FROM recommendation_performance WHERE price_at_rec IS NOT NULL"
    ).fetchone()[0]

    # Per kalla
    query = """
        SELECT s.type, COUNT(*) as count,
               AVG(rp.return_current) as avg_return,
               AVG(rp.return_30d) as avg_return_30d
        FROM recommendation_performance rp
        JOIN recommendations r ON rp.recommendation_id = r.id
        JOIN analyses a ON r.analysis_id = a.id
        JOIN content c ON a.content_id = c.id
        JOIN sources s ON c.source_id = s.id
        WHERE rp.price_at_rec IS NOT NULL
        GROUP BY s.type
    """

    stats['by_source'] = {}
    for row in conn.execute(query):
        stats['by_source'][row['type']] = {
            'count': row['count'],
            'avg_return_current': round(row['avg_return'] or 0, 2),
            'avg_return_30d': round(row['avg_return_30d'] or 0, 2)
        }

    # Top performers
    query = """
        SELECT r.raw_stock_name, rp.ticker_used, rp.return_current
        FROM recommendation_performance rp
        JOIN recommendations r ON rp.recommendation_id = r.id
        WHERE rp.return_current IS NOT NULL
        ORDER BY rp.return_current DESC
        LIMIT 10
    """
    stats['top_performers'] = [
        {'name': row['raw_stock_name'], 'ticker': row['ticker_used'], 'return': round(row['return_current'], 1)}
        for row in conn.execute(query)
    ]

    conn.close()
    return stats
```

## Rate Limiting Notes

Yahoo Finance API har rate limits. Klienten har inbyggd delay pa 0.5s.

**Optimeringar:**
1. Cacha priser per ticker+datum under sessionen
2. Hamta current price en gang per ticker (delas av alla recs)
3. Commit var 100:e ticker for robusthet

**Uppskattad tid:**
- 500 tickers x 7 datumpunkter x 0.5s = ~30 min forsta gangen
- Update current only: 500 tickers x 0.5s = ~4 min
