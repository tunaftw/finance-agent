# Prices Module - Prisverifiering för rekommendationer

Denna modul hanterar prisspårning och verifiering av aktie- och kryptorekommendationer från podcasts, Twitter och YouTube.

## Översikt

```
src/podstock/prices/
├── __init__.py          # Modulexporter och dokumentation
├── tracker.py           # Huvudservice (PriceTracker)
├── models.py            # Datamodeller (Pydantic)
├── storage.py           # JSONL-lagring
├── ticker_mapping.py    # Namnuppslag till ticker
├── exceptions.py        # Anpassade exceptions
└── clients/
    ├── base.py          # Abstrakt basklass
    ├── yahoo.py         # Yahoo Finance-klient
    └── coingecko.py     # CoinGecko-adapter (legacy)
```

## Snabbstart

### CLI-kommandon

```bash
# Importera rekommendationer från extraherade avsnitt
podstock prices import --podcast "Fill or Kill" --action buy

# Dry-run för att se vad som importeras
podstock prices import --dry-run --since 2024-06-01

# Manuell spårning
podstock prices track "Evolution" buy --date 2024-06-15 --source "Fill or Kill"

# Verifiera mot aktuella priser
podstock prices verify --today

# Visa alla spårade rekommendationer
podstock prices list

# Visa träffsäkerhetsstatistik
podstock prices accuracy --podcast "Fill or Kill"

# Hantera ticker-mappningar
podstock prices mapping list
podstock prices mapping add "Paradox" "PDX.ST"
podstock prices mapping search "evol"
```

### Python API

```python
from pathlib import Path
from datetime import datetime
from podstock.prices import PriceTracker

# Initiera tracker
tracker = PriceTracker(Path("data"))

# Importera från extraherade rekommendationer
result = tracker.import_from_extractions(
    podcast="fill or kill",
    since_date=datetime(2024, 6, 1),
    actions=["buy"],
)
print(f"Importerade: {result.imported}")

# Manuell spårning
rec = tracker.track_recommendation(
    source_type="podcast",
    source_id="fillorkill-2024-06-15",
    source_name="Fill or Kill",
    asset_name="Evolution",
    action="buy",
    recommendation_date=datetime(2024, 6, 15),
)

# Verifiera mot aktuella priser
results = tracker.verify_today()
for rec, result in results:
    print(f"{rec.asset_name}: {result.percentage_return:+.1f}%")

# Hämta statistik
stats = tracker.get_accuracy_stats(source_name="Fill or Kill")
print(f"Träffsäkerhet: {stats.hit_rate}")
```

## Datakällor

### Aktier
- **Yahoo Finance** (yfinance) för svenska (.ST), finska (.HE), danska (.CO), norska (.OL) och amerikanska aktier
- Automatisk suffix-hantering baserat på marknad

### Krypto
- **Yahoo Finance** med -USD suffix (BTC-USD, ETH-USD, SOL-USD, etc.)
- Stödjer historiska priser och aktuella kurser

## Ticker-mappning

Mappningsfilen (`data/prices/ticker_mapping.json`) innehåller:
- **Direkta mappningar**: "Evolution" → "EVO.ST"
- **Alias**: "evo" → "Evolution" (löses sedan till ticker)
- **Kryptosymboler**: Lista med kända krypto-tickers

Fuzzy matching stöds för ungefärliga namnuppslag.

## Verifieringsintervall

Som standard verifieras rekommendationer vid:
- 1 månad
- 3 månader
- 6 månader
- 12 månader
- "Idag" (intervall 0)

## Lagring

Rekommendationer lagras i JSONL-format:
- `data/prices/verified_recommendations.jsonl`
- En JSON-rad per rekommendation
- Uppdateras vid verifiering

## Interaktiv import

Vid import kan saknade tickers läggas till interaktivt:

```
⚠ Saknar ticker för 'Stillfront'
  Podcast: Fill or Kill (2024-06-15)
  Speaker: Johan
  Action: buy

  Ange ticker (s=skippa, q=avbryt): SF.ST

  ✓ Sparade: Stillfront → SF.ST
```

## Modeller

| Modell | Beskrivning |
|--------|-------------|
| `TrackedRecommendation` | Rekommendation kopplad till prisspårning |
| `VerificationResult` | Prisverifiering vid ett intervall |
| `PriceSnapshot` | Prisdata vid en tidpunkt (OHLCV) |
| `AccuracyStats` | Aggregerad träffsäkerhetsstatistik |
| `ImportResult` | Resultat av import |
| `AssetType` | Enum: STOCK eller CRYPTO |

## Exceptions

| Exception | När den kastas |
|-----------|----------------|
| `TickerNotFoundError` | Ticker kan inte lösas från namn |
| `PriceNotAvailableError` | Prisdata kan inte hämtas |
| `InvalidTickerError` | Ogiltig ticker-symbol |
