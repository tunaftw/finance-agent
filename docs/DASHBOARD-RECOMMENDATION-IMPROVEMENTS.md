# Dashboard Recommendation Improvements

> Beslutsdokument från 2025-12-29

## Bakgrund

Vid granskning av dashboard upptäcktes att podcast-rekommendationer saknar viktig kontextuell information som faktiskt redan finns i JSON-analyserna men inte visas i UI.

### Problemet

**Exempel: gotttjot-2025-12-23**
- Avsnittet diskuterar InfraCom, Vuxen och Delia positivt
- Men `recommendations: []` är tom i JSON
- Dashboard visar bara "Bolag diskuterade:" utan kontext

**Exempel: gotttjot-2025-12-16**
- Har 8 recommendations med detaljerad data:
  - `reasoning`: "EV/EBIT 10 på 2025e, 40% tillväxt i Q3..."
  - `quote`: Exakt citat från podden
  - `speaker`: Vem som sa det
  - `confidence`: high/medium/low
- Men dashboard visar BARA action-badge (BUY/SELL) + aktienamn

## Nuvarande UI vs önskad

```
NUVARANDE:
┌─────────────────────────────┐
│ 🟢 BUY Hexo  🟢 BUY Betsson │
└─────────────────────────────┘

ÖNSKAT:
┌─────────────────────────────────────────────────────┐
│ 🟢 BUY  Hexo                          ▼ Expandera  │
├─────────────────────────────────────────────────────┤
│ 📊 Pris: 85 SEK → 92 SEK (+8.2%)                   │
│ 🎯 Confidence: high | 🗣️ Erik (host)               │
│                                                     │
│ Motivering: EV/EBIT 10 på 2025e enligt konsensus,  │
│ EV/EBIT 7 på 2026e. 40% tillväxt i Q3...           │
│                                                     │
│ "Vi har egentligen sagt det redan men jag tycker   │
│ Hexo på EVB 10..."                                  │
└─────────────────────────────────────────────────────┘
```

## Analys av rotorsaker

### 1. UI-problemet (LÖSES NU)
Dashboard-koden i `index.html` rad 306-323 visar bara:
- `rec.action` (buy/sell/etc)
- `rec.stock_name`
- `rec.ticker`

Men hämtar INTE:
- `rec.reasoning`
- `rec.quote`
- `rec.speaker`
- `rec.confidence`

### 2. Analysproblemet (UTVÄRDERAS SENARE)
Prompten i `scripts/glm_driver.py` säger:
> "Var KONSERVATIV: Inkludera bara tydliga rekommendationer"

Detta gör att softa signaler (positiv diskussion utan explicit köp) inte fångas.

### 3. Prisdata saknas (LÖSES NU)
Ingen koppling mellan recommendations och prices-tabellen.

## Beslut: Fasad approach

### Fas 1: UI + Prisdata (NU)
1. **Expanderbar sektion** för varje recommendation
   - Visa reasoning, quote, speaker, confidence
2. **Prisdata**
   - Pris vid signal (från prices-tabell baserat på datum)
   - Nuvarande pris (senaste i prices-tabell)
   - Procentuell förändring

### Fas 2: Utvärdera analysförbättring (SENARE)
Efter Fas 1, utvärdera om:

**Alternativ A: Mjuka ribban**
- Ta bort "Var KONSERVATIV"
- Fånga även softa signaler
- Risk: Inflation av låg-kvalitets recommendations

**Alternativ B: stock_context per aktie**
- Ny datastruktur för diskuterade aktier
- Separat från recommendations
- Visar kontext även utan explicit köp/sälj

**Alternativ C: Förstärk stock_segments**
- Prompten ber redan om djupanalys
- GLM fyller inte i konsekvent
- Kan förstärkas eller ersättas

## Teknisk implementation Fas 1

### Filer att ändra

| Fil | Ändring |
|-----|---------|
| `src/podstock/dashboard/templates/index.html` | Expanderbar sektion med detaljer |
| `src/podstock/dashboard/templates/assets/app.js` | Toggle-logik för expand/collapse |
| `src/podstock/dashboard/exporters.py` | Inkludera prisdata i export |

### Prisdata-logik

```python
# Pseudokod för prisdata
def get_recommendation_prices(rec, episode_date):
    # Hämta pris vid signal
    price_at_signal = prices_table.get(
        ticker=rec.ticker,
        date=episode_date
    )

    # Hämta senaste pris
    latest_price = prices_table.get_latest(ticker=rec.ticker)

    return {
        "price_at_signal": price_at_signal,
        "latest_price": latest_price,
        "change_pct": calculate_change(price_at_signal, latest_price)
    }
```

## Avväganden dokumenterade

| Fråga | Beslut | Motivering |
|-------|--------|------------|
| Visa all data direkt vs expanderbar? | Expanderbar | Renare UI, användaren väljer detalj |
| Mjuka ribban för recommendations? | Nej (ännu) | Utvärdera efter UI-fix |
| Re-analysera gamla avsnitt? | Nej (ännu) | Befintlig data har redan bra kontext |
| Signal_strength 1-3 skala? | Parkerad | Utvärdera i Fas 2 |

## Relaterade filer

- Analysprompt: `scripts/glm_driver.py` (rad 200-415)
- Dashboard template: `src/podstock/dashboard/templates/index.html`
- Pydantic-modeller: `src/podstock/extract/models.py`
- Databasschema: `src/podstock/db/schema.sql`
- Analyze skill: `.claude/skills/analyze/SKILL.md`
