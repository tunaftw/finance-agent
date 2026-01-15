# Stock Segments Quality Improvement

**Datum:** 2026-01-15
**Status:** Fas 1 & 1.5 klar, Fas 2 redo för körning
**Commits:** `01ed10a` (prompt fix), `53e17a5` (stock_name fix)

## Bakgrund

Användaren upptäckte att vissa rekommendationer på hemsidan visas med detaljerad struktur (bull_case, bear_case, catalysts, key_metrics) medan andra bara visar basic info (reasoning + quote). Målet är att säkerställa att alla analyser fångar maximal detalj.

## Utredning (Klar)

### Grundorsak identifierad

**Prompt-bugg i `src/podstock/extract/prompt_templates.py`:**

- **System prompt (rad 10, 63):** "för ALLA aktier som diskuteras (ingen minimumtröskel)"
- **User prompt (rad 166):** "för varje aktie med >2 min diskussion"

Denna motsättning gav LLM:en en "ursäkt" att skippa `stock_segments`.

### Kartläggning av entry points

Alla analysvägar använder rätt Schema 2.1, men några har output till fel plats:

| Entry Point | Model | Output | Status |
|-------------|-------|--------|--------|
| `/analyze` (Claude) | Claude | analyses-v2/ | ✅ OK |
| `/analyze` (GLM) | GLM-4.7 | analyses-v2/ | ✅ OK |
| `/orchestrate` | Valfri | analyses-v2/ | ✅ OK |
| `batch_runner.py` | GLM-4.7 | extracted/glm-batch/ | ⚠️ Fel plats |

### Statistik (senaste 3 månader)

| Månad | Saknar/Totalt | Andel |
|-------|---------------|-------|
| Okt 2025 | 29/94 | 31% |
| Nov 2025 | 28/84 | 33% |
| Dec 2025 | 27/77 | 35% |
| **Jan 2026** | **20/30** | **67%** |

## Genomförda åtgärder (Fas 1)

### 1. Prompt-fix (commit `01ed10a`)

**Ändring i `src/podstock/extract/prompt_templates.py`:**

```diff
- 3. **Stock Segments** (VIKTIGT - för varje aktie med >2 min diskussion)
+ 3. **Stock Segments** (OBLIGATORISKT - för VARJE aktie i stocks_discussed, oavsett längd)
```

**Tillagd validerings-instruktion:**

```
⚠️ VALIDERING FÖRE OUTPUT:
- Kontrollera att VARJE aktie i stocks_discussed har ett motsvarande stock_segment
- Om en aktie saknar stock_segment: SKAPA ETT, även om diskussionen var kort
- Tom stock_segments-array är ENDAST OK om inga aktier diskuterades
```

### 2. Manuell berikning av Market Makers 2026-01-15

Hacksaw Gaming-segmentet berikades manuellt med:
- 7 bull_case points
- 7 bear_case points
- 3 catalysts
- 3 risks
- 6 quotes med context
- Financial metrics (EV/EBIT, tillväxt, marginaler)

## Genomförda åtgärder (Fas 1.5 - stock_name fix)

### Problem identifierat

Dashboard visade "(HACSO)" istället för "Hacksaw Gaming (HACSO)" - aktienamn saknades.

**Grundorsaker:**
1. `marketmakers-2026-01-15-78d2.json` använde `"company"` istället för `"stock_name"` (schema-mismatch)
2. Prompten var otydlig om att `stock_name` måste vara fullständigt bolagsnamn (aldrig ticker)

### 3. Förbättrad prompt för stock_name/ticker (Fas 1.5)

**Ändring i `src/podstock/extract/prompt_templates.py`:**

```diff
2. **Recommendations** (för tydliga köp/sälj/watch)
-  - stock_name, ticker, action, confidence, speaker, speaker_role
+  - stock_name: FULLSTÄNDIGT bolagsnamn (t.ex. "Evolution Gaming", "Hacksaw Gaming", "Saab AB") - ALDRIG tom
+  - ticker: Börsticker (t.ex. "EVO", "HACSO", "SAAB-B")
+  - action, confidence, speaker, speaker_role

3. **Stock Segments** (OBLIGATORISKT...)
-  - stock_name, ticker
+  - stock_name: FULLSTÄNDIGT bolagsnamn (samma som ovan - ALDRIG tom)
+  - ticker: Börsticker
```

**Ny validerings-instruktion:**

```
⚠️ KRITISKT: stock_name får ALDRIG vara tomt eller lika med ticker
  - FEL: stock_name="" ticker="HACSO" → RÄTT: stock_name="Hacksaw Gaming" ticker="HACSO"
  - FEL: stock_name="EVO" ticker="EVO" → RÄTT: stock_name="Evolution Gaming" ticker="EVO"
```

### 4. Fixad marketmakers-fil

Schema-mismatch fixat: `"company"` → `"stock_name"` för alla 11 rekommendationer.

**Verifiering:**
```
rec[0]: stock_name='Ovzon' ticker='OVZON'
rec[1]: stock_name='Saab' ticker='SAAB B'
rec[2]: stock_name='Google (Alphabet)' ticker='GOOGL'
rec[4]: stock_name='Hacksaw Gaming' ticker='HACSO'
... (alla 11 korrekta)
```

## Episoder som behöver re-analyseras (Fas 2)

### Januari 2026 (20 st)

```
Datum        Podcast              Recs  Saknar
----------------------------------------------------------------------
2026-01-14   Veckans Trade        5     stock_segments
2026-01-14   Börsens Finest       1     stock_segments
2026-01-14   IG Börssnack         3     stock_segments
2026-01-13   Gott & Blandat       19    stock_segments
2026-01-13   Fill or Kill         14    stock_segments
2026-01-13   Fill or Kill         11    stock_segments, model_used
2026-01-13   Avanzapodden         5     stock_segments
2026-01-13   Avanzapodden         0     stock_segments, model_used
2026-01-13   Börsmäklarna         10    stock_segments
2026-01-12   Kort och Lång        9     stock_segments
2026-01-10   Global Gains         12    stock_segments
2026-01-09   Kort och Lång        4     stock_segments
2026-01-09   Småspararpodden      0     stock_segments
2026-01-08   Kvalitet för pengar  3     stock_segments
2026-01-08   Ett rikare liv       1     stock_segments
2026-01-07   Börsens Finest       9     stock_segments
2026-01-06   Avanzapodden         2     stock_segments
2026-01-04   Global Games         11    stock_segments
2026-01-01   Kvalitet för pengar  4     stock_segments
2026-01-01   Veckans Trade        12    stock_segments
```

### Prioritering

**Hög prioritet (5+ rekommendationer):**
- Gott & Blandat 2026-01-13 (19 recs)
- Fill or Kill 2026-01-13 (14 recs)
- Veckans Trade 2026-01-01 (12 recs)
- Global Gains 2026-01-10 (12 recs)
- Global Games 2026-01-04 (11 recs)
- Fill or Kill 2026-01-13 (11 recs)
- Börsmäklarna 2026-01-13 (10 recs)
- Kort och Lång 2026-01-12 (9 recs)
- Börsens Finest 2026-01-07 (9 recs)

## Nästa steg (Fas 2 - Väntar på beslut)

### Alternativ A: Re-analysera med Claude (Rekommenderat för kvalitet)

```bash
# Manuellt i Claude Code
/analyze
# Välj: Claude Code
# Välj: Podcast
# Välj: Specifika filer (lista ovan)
```

**Fördelar:** Högsta kvalitet, bäst för detaljerade segment
**Nackdelar:** Kostar API-credits (~$0.05/transkript × 20 = ~$1)

### Alternativ B: Batch med GLM-4.7 (Snabbare, gratis)

```bash
# Skapa kö-fil
cat > data/podcasts/analyses-v2/reanalyze-queue.txt << 'EOF'
data/transcripts/veckanstrade/veckanstrade-2026-01-14-*.txt
data/transcripts/borsensfinest/borsensfinest-2026-01-14-*.txt
data/transcripts/igborssnack/igborssnack-2026-01-14-*.txt
# ... (lägg till alla 20)
EOF

# Kör i separat terminal
cd /Users/pontusskog/Documents/Developer/Finance-agent
source .venv/bin/activate
python3 scripts/glm_driver.py <transcript> data/podcasts/analyses-v2/
```

**Fördelar:** Gratis, snabbare för batch
**Nackdelar:** Något lägre kvalitet än Claude

### Alternativ C: Vänta på nästa synk

Framtida episoder kommer automatiskt använda den fixade prompten.

**Fördelar:** Inget extra arbete
**Nackdelar:** Januari-episoder förblir ofullständiga

## Kommando för att hitta episoder som saknar detaljer

```python
# Kör i Python eller som script
import json
from pathlib import Path

analyses_dir = Path('data/podcasts/analyses-v2')

for f in analyses_dir.glob('*-2026-01-*.json'):
    if 'progress' in f.name:
        continue
    data = json.loads(f.read_text())

    has_segments = bool(data.get('stock_segments'))
    has_thesis = any(
        seg.get('thesis', {}).get('bull_case') or seg.get('thesis', {}).get('bear_case')
        for seg in data.get('stock_segments', [])
    ) if has_segments else False

    if not has_segments or not has_thesis:
        print(f"{data.get('date')} - {data.get('podcast_name')} - {f.name}")
```

## Relaterade filer

- **Prompt:** `src/podstock/extract/prompt_templates.py`
- **Processor:** `src/podstock/extract/process_transcript.py`
- **GLM driver:** `scripts/glm_driver.py`
- **Analyser:** `data/podcasts/analyses-v2/*.json`
- **Transkript:** `data/transcripts/{podcast}/*.txt`

## Historik

| Datum | Åtgärd | Commit |
|-------|--------|--------|
| 2026-01-15 | Prompt-fix: Tog bort 2-min tröskel, lade till validering | `01ed10a` |
| 2026-01-15 | Manuell berikning: Market Makers Hacksaw Gaming | `f9ea709` |
| 2026-01-15 | Header-fix: 0 avsnitt → podcast_episodes | `c5a3d8c` |
| 2026-01-15 | stock_name-fix: Tydligare prompt + fixad marketmakers-fil | `53e17a5` |
