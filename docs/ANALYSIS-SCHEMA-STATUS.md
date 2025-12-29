# Analys-schema Status och Omanalys-plan

## Sammanfattning

Dashboarden har uppdaterats för att visa detaljerad data från `stock_segments` (thesis, bull/bear case, citat, finansiella nyckeltal). **Men**: Endast ~24% av analyserna innehåller denna data. Resterande ~76% (2,483 avsnitt) behöver omanalyseras med det nya schemat.

---

## Schema-versioner

### Old Schema (ingen version)
- **Antal**: 2,483 avsnitt
- **Analyserades**: 25 december 2024
- **Saknar**: `schema_version`, `stock_segments`, `insights`, `crypto_mentions`
- **Innehåller**: Grundläggande recommendations med `action`, `confidence`, `quote`, `reasoning`

### Schema 2.0
- **Antal**: 763 avsnitt
- **Analyserades**: 27-28 december 2024
- **Nytt**: `stock_segments` med:
  - `discussion_summary` (3-5 meningar per aktie)
  - `thesis` (bull_case, bear_case, catalysts, risks)
  - `quotes` array (flera citat med context)
  - `financial_metrics` (P/E, EV/EBITDA, etc.)
  - `position_disclosure` (owns, none, etc.)

### Schema 2.1
- **Antal**: 17 avsnitt
- **Nytt utöver 2.0**: `insights` (investeringsvisdom) + `crypto_mentions`

---

## Statistik per podcast

| Podcast | Gammalt schema | Nytt schema | Status |
|---------|---------------|-------------|--------|
| kortochlang | 536 | 0 | ❌ Behöver omanalys |
| fillorkill | 400 | 0 | ❌ Behöver omanalys |
| borspodden | 260 | 0 | ❌ Behöver omanalys |
| aktiepodden | 244 | 0 | ❌ Behöver omanalys |
| kvalitetsaktiepodden | 179 | 0 | ❌ Behöver omanalys |
| ettrikareliv | 108 | 0 | ❌ Behöver omanalys |
| avanzapodden | 72 | 0 | ❌ Behöver omanalys |
| gotttjot | 61 | 0 | ❌ Behöver omanalys |
| marketmakers | 336 | 1 | ⚠️ Nästan alla behöver omanalys |
| borsensfinest | 37 | 0 | ❌ Behöver omanalys |
| kvalitetforpengarna | 36 | 0 | ❌ Behöver omanalys |
| veckanstrade | 35 | 0 | ❌ Behöver omanalys |
| borsmagasinet | 29 | 0 | ❌ Behöver omanalys |
| igborssnack | 25 | 0 | ❌ Behöver omanalys |
| bullochbjorn | 23 | 0 | ❌ Behöver omanalys |
| globalgains | 21 | 0 | ❌ Behöver omanalys |
| montrosepodden | 20 | 0 | ❌ Behöver omanalys |
| **sparpodden** | 0 | **443** | ✅ Komplett |
| **marknaden** | 53 | **262** | ⚠️ Delvis |
| **smaspararpodden** | 0 | **48** | ✅ Komplett |
| analyspodden | 3 | 9 | ⚠️ Delvis |
| borsmaklarna | 0 | 7 | ✅ Komplett |
| affarvarlden | 0 | 1 | ✅ Komplett |

**Totalt**: 2,483 gamla + 778 nya = 3,261 avsnitt

---

## Vad som visas på dashboarden

### Med gammalt schema
- Rekommendationer: stock_name, action, confidence, quote (kort), reasoning
- **Saknas**: Bull/bear case, catalysts, risks, financial_metrics, position disclosure

### Med nytt schema (2.0+)
- **Allt ovan PLUS**:
- Thesis-breakdown med bull_case, bear_case, catalysts, risks
- Flera citat med context (thesis, bull_case, bear_case, conclusion)
- Finansiella nyckeltal (P/E, marginaler, skuldsättning)
- Position disclosure (äger talaren aktien?)
- Tidsstämplar (start/slut för diskussion)
- Discussion summary per aktie

---

## Skillnad i prompt

### Gammalt (docs/GLM-ANALYSIS-INSTRUCTIONS.md)
```
Din uppgift är att noggrant läsa podcast-transkript och identifiera:
1. KONKRETA aktie-rekommendationer (köp, sälj, bevaka, undvik)
2. Vem som ger rekommendationen (host eller gäst)
3. Argumenten bakom rekommendationen
4. Eventuella kursmål eller tidshorisonter
```
→ Genererar enkel `recommendations` array

### Nytt (src/podstock/extract/models.py)
Använder fullständig EpisodeAnalysis-modell med:
- `StockSegment` för djupanalys
- `ThesisComponents` (bull_case, bear_case, catalysts, risks)
- `FinancialMetrics` (P/E, EV/EBITDA, etc.)
- `SegmentQuote` med context

---

## Filsökvägar

| Typ | Sökväg |
|-----|--------|
| Podcast-transkript | `data/podcasts/raw/{podcast_id}/transcripts/*.txt` |
| Podcast-analyser | `data/podcasts/analyses/{episode_id}.json` |
| Dashboard-export | `data/dashboard/data/podcasts.json` |
| Models (Pydantic) | `src/podstock/extract/models.py` |
| Prompt-templates | `src/podstock/extract/prompt_templates.py` |

---

## Re-analys Plan

### Steg 1: Test-körning (1 avsnitt)
- [ ] Välj senaste Gött Tjöt-avsnittet
- [ ] Analysera med nya prompten
- [ ] Verifiera att stock_segments genereras
- [ ] Jämför med gammal analys

### Steg 2: Batch-körning (parallella sessioner)

**Metod A: OpenCode/GLM-4.7 (gratis)**
```bash
# Starta 3-4 parallella terminaler
# Varje terminal kör 3-4 transkript per session
# Följ docs/GLM-ANALYSIS-INSTRUCTIONS.md men med NYTT schema
```

**Metod B: Claude Code (snabbare, kostar credits)**
```python
# Använd /analyze skill med Claude Code-metod
# ~$0.05 per transkript
# Estimerad kostnad för 2,500 avsnitt: ~$125
```

### Steg 3: Prioriteringsordning

1. **Gött Tjöt om Aktier** (61 avsnitt) - Testvänligt, populär podcast
2. **Fill or Kill** (400 avsnitt) - Mycket innehåll, viktigt
3. **Börspodden** (260 avsnitt) - Klassiker
4. **Kort och Långt** (536 avsnitt) - Störst backlog
5. **Övriga** efter popularitet/relevans

### Steg 4: Regenerera dashboard
```bash
python -m podstock.dashboard.generator
```

---

## Tidslinje för analyser

| Datum | Händelse |
|-------|----------|
| Dec 25 | Initial batch med gammalt schema (2,483 avsnitt) |
| Dec 27-28 | Sparpodden, Marknaden, etc. med schema 2.0 |
| Dec 28 | Dashboard uppdaterad för stock_segments |
| Dec 29 | Upptäckt att gammalt schema saknar data |
| Dec 29 | prompt_templates.py uppdaterad till Schema 2.0 |

---

## Checklista

- [x] Dokumentera nuvarande status
- [x] Identifiera vilka podcasts som behöver omanalys
- [x] Uppdatera prompt_templates.py till Schema 2.0
- [x] Test-analysera 1 Gött Tjöt-avsnitt med nytt schema (gotttjot-2025-12-23-c440)
- [x] Verifiera resultat i dashboarden (3 stock_segments med thesis/quotes)
- [ ] Planera batch-körning
- [ ] Köra omanalys (2,483 avsnitt)
- [ ] Regenerera dashboard
- [ ] Verifiera komplett data

---

## ÅTGÄRD GENOMFÖRD: Prompt uppdaterad!

**Löst 2024-12-29**: `src/podstock/extract/prompt_templates.py` har uppdaterats till Schema 2.0.

**Ändringar gjorda**:
1. ✅ System prompt ber nu om `stock_segments` för aktier diskuterade >2 minuter
2. ✅ User prompt specificerar fullständigt Schema 2.0-format
3. ✅ Few-shot example inkluderar komplett `stock_segments` med thesis, quotes, financial_metrics
4. ✅ Instruktioner för `position_disclosure` (owns/none/unknown)

**Filen**: `src/podstock/extract/prompt_templates.py`

---

## Nästa steg

1. ~~UPPDATERA prompt_templates.py~~ ✅ KLART

2. **Test-körning**
   - Välj: `gotttjot-2025-12-16-545b.txt` (eller senaste)
   - Kör analys med Claude Code eller OpenCode
   - Verifiera output

3. **Batch-strategi**
   - Skapa uppdaterad `transcript-queue.txt` med bara gamla analyser
   - Konfigurera parallella sessioner

---

## Frågor att besvara

1. **Ska insights (schema 2.1) också inkluderas?**
   - Nuvarande: Endast 17 avsnitt har insights
   - Rekommendation: Ja, inkludera för framtida analyser

2. **Ska gamla analyser sparas som backup?**
   - Förslag: Ja, flytta till `data/podcasts/analyses/legacy/`

3. **Prioritering: Kvalitet eller kvantitet?**
   - Claude Code: Bättre kvalitet, kostar ~$125 totalt
   - OpenCode: Gratis, varierande kvalitet

---

## ÅTGÄRD GENOMFÖRD: Dashboard Expansion (Dec 29)

**Dashboard nu visar ALL tillgänglig data:**
1. ✅ `stock_segments` med thesis-breakdown (bull/bear/catalysts/risks)
2. ✅ Flera citat per aktie med context-färgkodning
3. ✅ Finansiella nyckeltal (P/E, EV/EBITDA, marginaler)
4. ✅ Position disclosure filter ("Äger aktien" / "Äger inte")
5. ✅ Insights-sektion (investeringsvisdom)
6. ✅ YouTube recommendation type filter (Active Position / Commentary)

**Filer modifierade:**
- `src/podstock/dashboard/exporters.py` - Exporterar stock_segments, insights, timestamps
- `src/podstock/dashboard/templates/index.html` - Full UI för all data
- `data/dashboard/` - Regenererad med inline data

---

## PÅGÅENDE: Schema 2.1+ Förbättringar

### Identifierade Problem

| Problem | Status | Lösning |
|---------|--------|---------|
| Timestamps extraheras inkonsekvent | 🔄 | Starkare prompt-instruktioner |
| Speaker-ID 40-70% träffsäkerhet | 🔄 | Hosts-hints i prompt + podcasts.json |
| Insights saknas (17 av 3,261) | 🔄 | Synka prompt_templates.py med glm_driver.py |
| Alfa-fält outnyttjade | 🔄 | position_context, downside_note, catalyst_timing |

### Planerade Förbättringar

**1. Timestamp-extraktion**
- 97.8% av transkript har `[MM:SS]` format (Apple Podcasts)
- Varje citat och rekommendation SKA ha timestamp

**2. Speaker-identifiering**
- Endast 5 av 24 podcasts har hosts definierade
- Behöver: hosts i podcasts.json + speaker-hints i prompt

**3. Insights (investeringsvisdom)**
- `prompt_templates.py` saknar insights-instruktioner
- `scripts/glm_driver.py` har dem (rad 241-260) - behöver synkas

**4. Extra alfa-fält**
- `position_context`: "50% av portföljen", "Största positionen"
- `downside_note`: "30% downside", "Risk/reward 3:1"
- `catalyst_timing`: "Rapport 2025-02-15", "Q2-lansering"

---

## Uppdaterad Checklista

### Genomfört ✅
- [x] Dokumentera nuvarande status
- [x] Identifiera vilka podcasts som behöver omanalys
- [x] Uppdatera prompt_templates.py till Schema 2.0
- [x] Test-analysera Gött Tjöt-avsnitt (gotttjot-2025-12-23-c440)
- [x] Dashboard visar stock_segments, thesis, quotes
- [x] Position disclosure filter implementerat
- [x] YouTube recommendation type filter implementerat

### Nyligen Genomfört ✅ (Dec 29)
- [x] Förbättrat prompt_templates.py med:
  - [x] Starkare timestamp-instruktioner (KRITISKT-sektion)
  - [x] Insights-extraktion (kopierat från glm_driver.py)
  - [x] Speaker-hints med kända hosts ({hosts} placeholder)
  - [x] Extra alfa-fält (position_context, downside_note, catalyst_timing)
  - [x] Schema uppdaterat till 2.1 med komplett few-shot example
- [x] Uppdaterat podcasts.json med hosts för ALLA 22 podcasts
- [x] Lagt till host_aliases för smeknamn (Klas→Niklas, etc.)

### Kvarstår 📋
- [ ] Omanalysera 2,483 avsnitt med förbättrad prompt
- [ ] Regenerera dashboard efter omanalys
- [ ] Verifiera komplett data
- [ ] Utvärdera träffsäkerhet för speaker-ID

---

*Senast uppdaterad: 2024-12-29*
