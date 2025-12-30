# Alpha Extractor - Design Document

**Datum:** 2025-12-30
**Status:** Godkänd design
**Syfte:** Aggregera all tillgänglig data om ett bolag för att landa i ett motiverat fair value

---

## 1. Översikt

### Vad är Alpha Extractor?

En Claude Code skill som sammanställer ALL tillgänglig data om ett bolag för att ge ett brutalt ärligt investeringsunderlag med ett motiverat fair value.

### Kärnprinciper

- **Objektiv, inte yes-sayer** - aktivt leta efter bear-case och risker
- **Pris är allt** - fantastiskt bolag till fel pris = dålig investering
- **Konsekvent metodik** - samma ramverk oavsett bransch, men anpassade multiplar
- **Ärlig om begränsningar** - flagga saknad data, tvinga inte fram slutsatser

### Användningslägen

1. **Screening** - nytt case, vill förstå om det är värt att gå vidare
2. **Djupanalys** - seriöst intresserad, vill ha full bild + fair value
3. **Uppdatering** - existerande innehav, vad har ändrats?

### Invokering

```
/alpha BETS "överväger att öka, fokus på regulatoriska risker"
/alpha Investor "nytt case, känner inte bolaget"
/alpha Evolution "har i portfölj, vill uppdatera min tes"
```

Skillen hanterar både ticker och bolagsnamn.

---

## 2. Datainsamling

### Intern data - ALLT från `data/`

Skillen skannar hela `data/`-katalogen och plockar upp allt relevant:

| Källa | Sökväg | Innehåll |
|-------|--------|----------|
| Finansiella rapporter | `filings/` | Kvartals/årsrapporter + djupanalyser |
| VD-ord över tid | Extraherat från `filings/` | Löften, tonfall, måluppfyllnad |
| Podcast-omnämningar | `podcasts/analyses/` | Alla mentions + sentiment + priskontext |
| Twitter-omnämningar | `twitter/` | Vem säger vad, trender, sentiment |
| YouTube-omnämningar | `youtube/` | Video-analyser, intervjuer, earning calls |
| Insiderdata | `insider/` | Köp/sälj, vem, belopp, kurs då vs nu |
| Nyheter | `news/` | Pressmeddelanden, regulatoriskt |
| Earnings transcripts | `earnings/` | Transkriberade earnings calls |
| Prishistorik | `prices/` | Historik för priskontext |
| Rekommendationer | `recommendations/` | Tidigare extraherade recs |
| Databas | `podstock.db` | Aggregerad data, sökbar |
| Dashboard-data | `dashboard/` | Befintlig visualiseringsdata |

**Princip:** Om det finns bearbetad JSON eller databaspost som nämner bolaget → ta med det.

### Adaptiva lägen

**Full analys** (all data finns):
- Djupanalys + extern sökning som komplement

**Partiell analys** (viss data saknas):
- Flaggar: *"Saknar: insiderdata, Twitter-mentions. Köra ändå?"*
- Viktar upp extern sökning för att kompensera

**Discovery mode** (nytt bolag, ingen intern data):
- *"Inget lokalt data för {bolag}. Kör discovery mode - primärt extern sökning + bygger grundbild."*

### Extern sökning

Körs alltid, djupet beror på vad som finns internt:

- Reddit (r/stocks, r/investing, svenska subreddits)
- Placera forum/nyheter
- Blankarrapporter (Breakit, DI, internationella)
- Google News för senaste händelser
- Bolagets egen IR-sida om relevant

**Principer:**
- Gräv djupare om intressant info hittas
- Annars ärligt: *"Extern sökning gav inget väsentligt."*
- Extra fokus på risker/bear-case som motvikt

---

## 3. Värderingsmetodik

### Steg 1: Bolagsklassificering

Skillen identifierar först bolagstyp för att välja rätt multiplar:

| Typ | Exempel | Primära multiplar |
|-----|---------|-------------------|
| Bank/Finans | SEB, Nordea | P/B, P/E, ROE |
| Gaming/Betting | Evolution, Betsson | EV/EBITDA, P/E, FCF yield |
| SaaS/Tech | Fortnox, Sinch | EV/Sales, Rule of 40, ARR-tillväxt |
| Industri/Cyklisk | Volvo, Sandvik | EV/EBITDA, P/E (normaliserad), ROIC |
| Fastighet | Balder, SBB | P/NAV, FFO yield, LTV |
| Konsument | H&M, Axfood | P/E, EV/EBIT, marginaltrend |

**Alltid med:** FCF yield, FCF/aktie-trend, nettoskuld/EBITDA

### Steg 2: Peer-jämförelse

1. Skillen föreslår 3-5 peers baserat på sektor, storlek, geografi
2. Du godkänner eller justerar: *"Föreslår: Kindred, 888, Entain. Ändra?"*
3. Hämtar multiplar för peers (från data eller extern källa)
4. Visar var bolaget handlas relativt peers + sin egen historik

**Exempel-output:**
```
BETS handlas till EV/EBITDA 6.2x
- Peers snitt: 7.8x
- Egen 5-års snitt: 7.1x
- Rabatt vs peers: -21%
- Rabatt vs historik: -13%
```

### Steg 3: Kvalitativ justering

Multipeln justeras baserat på:

- **Tillväxt** - växer snabbare/långsammare än peers?
- **Marginaltrend** - förbättras eller försämras?
- **Balansräkning** - skuldsättning, kassaposition
- **Moat** - konkurrensfördelar, switching costs
- **Management** - track record, insider-ägande
- **Risker** - regulatoriskt, koncentration, cyklikalitet

---

## 4. Scenariomodell (Bull/Base/Bear)

### Tre komponenter per scenario

**1. Fundamenta-antaganden**
- Omsättningstillväxt (CAGR närmaste 3 år)
- Marginaler (EBITDA, netto)
- Kassaflödeskonvertering

**2. Multipelförändring**
- Vad marknaden är villig att betala om X år
- Expansion vid omvärdering, kontraktion vid besvikelse

**3. Nyckelevents**
- Specifika triggers som kan realiseras
- T.ex. "vinner dansk licens", "M&A", "VD-byte", "räntesänkning"

### Exempelscenario

| | Bull (25%) | Base (55%) | Bear (20%) |
|---|------------|------------|------------|
| **Tillväxt** | 12% CAGR | 6% CAGR | 0% (flat) |
| **EBITDA-marginal** | 18% | 15% | 12% |
| **EV/EBITDA exit** | 8.5x | 7.0x | 5.5x |
| **Events** | Nya marknader, M&A | Status quo | Regulatorisk åtstramning |
| **Fair value** | 165 SEK | 120 SEK | 75 SEK |

**Viktat fair value:** 0.25×165 + 0.55×120 + 0.20×75 = **122 SEK**

### Sannolikhetssättning

Skillen föreslår vikter baserat på:

- **Historisk träffsäkerhet** - har bolaget levererat över/under förväntningar?
- **Sentiment i data** - vad säger podcasts, Twitter, nyheter?
- **Riskfaktorer** - hur sannolika är bear-case triggers?
- **Insider-signaler** - köper eller säljer insiders?

Du får alltid justera: *"Föreslår Bull 25%, Base 55%, Bear 20%. Justera?"*

---

## 5. Exekvering & Agenter

### Parallell agentarkitektur

```
/alpha BETS "överväger ökning"
         │
         ▼
    ┌─────────────────────────────────────────┐
    │         ORCHESTRATOR                     │
    │  - Inventerar tillgänglig data          │
    │  - Spawnar agenter baserat på vad finns │
    │  - Sammanställer till slutanalys        │
    └─────────────────────────────────────────┘
         │
         ├──► Agent 1: FUNDAMENTA
         │    - Rapportanalys, VD-ord, marginaler
         │    - Måluppfyllnad över tid
         │
         ├──► Agent 2: SENTIMENT
         │    - Podcasts, Twitter, YouTube mentions
         │    - Historisk priskontext för mentions
         │
         ├──► Agent 3: INSIDER & ÄGARE
         │    - Insynsköp/-sälj, kurs då vs nu
         │    - Ägarstruktur, institutionellt
         │
         ├──► Agent 4: EXTERN RESEARCH
         │    - Reddit, Placera, blankarrapporter
         │    - Nyheter, IR-sidor
         │
         └──► Agent 5: RISKER & BEAR CASE
              - Aktivt leta motargument
              - Vad kan gå fel?
              - Historiska exempel
         │
         ▼
    ┌─────────────────────────────────────────┐
    │         SYNTES & VÄRDERING              │
    │  - Väger samman alla agentrapporter     │
    │  - Bygger scenariomodell                │
    │  - Beräknar fair value                  │
    │  - Presenterar interaktivt              │
    └─────────────────────────────────────────┘
```

### Adaptiv spawning

- **Full data:** Alla 5 agenter körs parallellt
- **Partiell data:** Hoppar över agenter utan data, viktar upp andra
- **Discovery:** Agent 4 (extern) får huvudfokus, bygger grundbild

---

## 6. Output & Lagring

### Interaktiv dialog

Under körning presenteras analysen sektion för sektion med möjlighet till följdfrågor:

```
── ALPHA EXTRACTOR: Betsson ──────────────────────

📊 Datainventering...
✓ Finansiella rapporter: 8 st (2022-2024)
✓ Podcast-mentions: 23 st
✓ Twitter-mentions: 47 st
✓ Insiderdata: 5 transaktioner
✓ Nyheter: 12 st
○ YouTube: ingen data

Kör full analys. Spawnar 5 agenter...

[Agenter kör parallellt]

── FUNDAMENTA ────────────────────────────────────
[Sammanfattning av rapporter, VD-ord, trender...]

Följdfråga? (Enter för att fortsätta)
> Hur har marginalen utvecklats senaste 2 åren?

[Svarar, fortsätter sedan]
```

### Sparad analys

Strukturerad JSON: `data/bolagsanalys/{bolag}/{datum}-analysis.json`

```json
{
  "ticker": "BETS",
  "company": "Betsson",
  "date": "2025-12-30",
  "context": "överväger ökning",
  "data_sources": { ... },
  "fundamenta": { ... },
  "sentiment": { ... },
  "insider": { ... },
  "risks": [ ... ],
  "peers": { ... },
  "scenarios": {
    "bull": { "probability": 0.25, "fair_value": 165 },
    "base": { "probability": 0.55, "fair_value": 120 },
    "bear": { "probability": 0.20, "fair_value": 75 }
  },
  "weighted_fair_value": 122,
  "current_price": 98,
  "verdict": "UNDERVÄRDERAD",
  "upside": "+24%",
  "confidence": "HÖG",
  "key_risks": [ ... ],
  "recommendation": "Attraktiv risk/reward vid nuvarande nivå"
}
```

### Dashboard-integration

- Listar alla analyser per bolag med timestamp
- Jämför versioner över tid
- Visualiserar fair value vs aktuellt pris

---

## 7. Verdict & Objektiv Röst

### Tydligt verdict

```
── VERDICT ───────────────────────────────────────

Fair Value (viktat): 122 SEK
Aktuell kurs: 98 SEK
Uppsida: +24%

BEDÖMNING: KÖPVÄRD

Confidence: HÖG
├─ Stark datakvalitet (8 rapporter, 23 podcast-mentions)
├─ Tydlig historik av leverans
└─ Insiderköp senaste 6 mån stödjer tesen

MEN TÄNK PÅ:
├─ Regulatorisk risk i Nederländerna (Bear-trigger)
├─ Handlas redan 13% under historisk snittmultipel
└─ Om Bear-case: nedsida -23%

JÄMFÖRELSE MOT DINA KRAV:
├─ 15% ROE-mål: Bolaget levererar 22% ROE ✓
├─ Koncentrerad portfölj: Passar som 1 av 3-5 innehav
└─ Prismedvetenhet: Köp under 105 SEK ger margin of safety
```

### När skillen säger NEJ

```
BEDÖMNING: EJ KÖPVÄRD VID NUVARANDE PRIS

Fair Value: 85 SEK
Aktuell kurs: 112 SEK
Nedsida: -24%

Bolaget är kvalitet, men priset reflekterar redan Bull-case.
Risk/reward attraktiv först under 90 SEK.

BÄTTRE ALTERNATIV I DIN DATA:
├─ BETS: +24% uppsida, liknande kvalitet
└─ KIND: +18% uppsida, lägre risk
```

### Flaggning av osäkerhet

```
⚠️  LÅG CONFIDENCE

Begränsat underlag:
├─ Endast 2 rapporter tillgängliga
├─ Inga podcast-mentions senaste 12 mån
└─ Extern sökning gav motstridiga signaler

Fair value-spannet är brett: 75-140 SEK
Rekommendation: Samla mer data innan beslut
```

---

## 8. Sammanfattning

| Aspekt | Design |
|--------|--------|
| **Invokering** | `/alpha BOLAG "kontext"` |
| **Datakällor** | ALL bearbetad data i `data/` + extern sökning |
| **Lägen** | Full / Partiell / Discovery (adaptivt) |
| **Värdering** | Branschspecifika multiplar + FCF, alltid |
| **Peers** | Skillen föreslår, du godkänner |
| **Scenariomodell** | Bull/Base/Bear med sannolikhetsvikter |
| **Fair value** | Viktat snitt av scenarios |
| **Exekvering** | 5 parallella agenter |
| **Output** | Interaktiv dialog + sparad JSON |
| **Lagring** | `data/bolagsanalys/{bolag}/{datum}-analysis.json` |
| **Dashboard** | Versionerad historik, jämförelser |
| **Princip** | Objektiv, prisfokuserad, ärlig om begränsningar |

### Det som gör skillen unik

1. **Aggregerar ALLT** - ingen datakälla missas
2. **Aktivt bear-case** - letar efter motargument, inte bekräftelse
3. **Pris i centrum** - bra bolag ≠ bra investering
4. **Ärlig om osäkerhet** - flaggar låg confidence, föreslår alternativ
5. **Versionerad** - följ hur din tes utvecklas över tid

---

## Framtida utökningar

- **Jämförelseskill:** `/alpha-compare BETS vs EVO "12 månaders horisont"`
- **Portfolio-scan:** Kör alpha på alla innehav, ranka efter uppsida
- **Alert-integration:** Notifiera när fair value vs pris ändras signifikant
