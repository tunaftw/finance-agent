---
name: analyze-sentiment
description: Aggregera all sentiment-data för ett bolag från podcasts, Twitter, YouTube och pressmeddelanden. Explicit triage av alla källor med confidence scoring.
---

# Analyze Sentiment

Samla och kritiskt utvärdera all sentiment-data för ett specifikt bolag.

## Quick Start

```
/analyze-sentiment CARA
/analyze-sentiment Betsson "senaste 6 mån"
```

## Kärnprinciper

- **Explicit triage** - varje källa granskas och beslut dokumenteras
- **Kritisk granskning** - podcast-påståenden är åsikter, inte fakta
- **Confidence scoring** - strukturerad poängsättning av rekommendationer
- **Cache-aware** - använd befintlig analys om tillräckligt färsk

---

## Workflow

### Step 1: Check Cache

```python
from pathlib import Path
from datetime import datetime
import json

def check_sentiment_cache(ticker: str, max_age_days: int = 7):
    cache_path = Path(f'data/sentiment/{ticker}-analysis.json')

    if not cache_path.exists():
        return {"status": "needs_analysis", "path": str(cache_path)}

    cached = json.loads(cache_path.read_text())
    analyzed_at = datetime.fromisoformat(cached['analyzed_at'].replace('Z', '+00:00'))
    age_days = (datetime.now(analyzed_at.tzinfo) - analyzed_at).days

    if age_days <= max_age_days:
        return {
            "status": "cached",
            "age_days": age_days,
            "data": cached,
            "path": str(cache_path)
        }

    return {"status": "stale", "age_days": age_days, "path": str(cache_path)}
```

Om cached och färsk: fråga användaren om den ska användas eller uppdateras.

### Step 2: Gather Sources

Samla ALLA källor som nämner bolaget:

```python
def gather_sources(ticker: str, company_name: str):
    sources = {
        "podcasts": [],      # data/podcasts/analyses-v2/*.json
        "transcripts": [],   # data/transcripts/*/*.txt (för djupdykning)
        "twitter": [],       # data/twitter/analyses/*.json
        "youtube": [],       # data/youtube/analyses/*.json
        "press_releases": [] # data/news/raw/{company}/press-releases/*.json
    }

    # Sök i podcast-analyser efter ticker/company mentions
    for analysis_file in Path('data/podcasts/analyses-v2').glob('*.json'):
        analysis = json.loads(analysis_file.read_text())
        mentions = [r for r in analysis.get('recommendations', [])
                   if ticker in r.get('ticker', '') or
                      company_name.lower() in r.get('stock_name', '').lower()]
        if mentions:
            sources['podcasts'].append({
                "file": str(analysis_file),
                "episode_id": analysis.get('episode_id'),
                "date": analysis.get('date'),
                "mentions": mentions
            })

    # Similar logic for twitter, youtube, press releases...
    return sources
```

### Step 3: Triage Each Source

För varje källa, fatta explicit beslut:

| Decision | Meaning |
|----------|---------|
| `analyzed` | Relevant, inkluderas i analys |
| `ignored` | Granskad men inte relevant |
| `to_fundamenta` | Finansiell info, skickas till FUNDAMENTA |

Se: `references/triage-rules.md`

### Step 4: Extract Quotes & Recommendations

För varje `analyzed` källa, extrahera:
- Citat (exakt text)
- Talare (namn, affiliation)
- Stance (bullish/bearish/neutral)
- Äger position? (bias-flagga)
- Claims (fakta vs åsikter)

### Step 5: Apply Confidence Scoring

Varje quote får poäng på 4 kriterier (1-3 per kriterie):

| Kriterie | 1p | 2p | 3p |
|----------|----|----|-------|
| Specificity | Vag | Moderat | Precis |
| Reasoning | Bara åsikt | Viss logik | Full tes med siffror |
| Risk-awareness | Inga risker | Vissa förbehåll | Explicit bear case |
| Recency | >6 mån | 1-6 mån | <1 mån |

Total: 4-12 poäng → High (10-12), Medium (7-9), Low (4-6)

Se: `references/confidence-scoring.md`

### Step 6: Aggregate & Synthesize

Kombinera till:
- `notable_speakers[]` - de viktigaste rösterna
- `bull_arguments[]` - sammanfattade bull-argument
- `bear_arguments[]` - sammanfattade bear-argument
- `quotes[]` - alla citat med scoring
- `overall_score` - viktat sentiment (0-10)
- `label` - bullish/neutral/bearish

### Step 7: Save Analysis

```python
output_path = Path(f'data/sentiment/{ticker}-analysis.json')
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(analysis, indent=2, ensure_ascii=False))
```

---

## Output Schema

Se: `references/output-schema.md`

---

## Integration med Alpha

Alpha's SENTIMENT agent kallar denna skill:

```
1. Kolla cache: check_sentiment_cache(ticker)
2. Om cached och färsk: fråga användaren
3. Om needs_analysis: kör full workflow
4. Returnera strukturerad sentiment-data till Alpha
```

---

## Exempel

```
User: /analyze-sentiment CARA

Claude: Kollar cache...
        Ingen befintlig analys hittad.

        Samlar källor...
        - Podcasts: 26 episoder med CARA-omnämnanden
        - Press releases: 25 pressmeddelanden
        - Twitter: 0 konton

        Triagar källor...
        - 18 podcasts analyserade
        - 8 podcasts ignorerade (inget substantiellt)
        - 12 PRs till FUNDAMENTA (finansiella)
        - 13 PRs till timeline

        Extraherar quotes...
        - 12 quotes med confidence scoring

        Sparar till: data/sentiment/CARA-analysis.json

        Sammanfattning:
        Overall: BULLISH (7.5/10)
        Notable speakers: Per Johansson (Origo), Carnegie Analyst
        Top quote: "Turnaround story med låg churn" (8/12 confidence)
```
