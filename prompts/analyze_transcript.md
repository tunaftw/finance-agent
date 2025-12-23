# Prompt Template: Podcast Stock Recommendation Analysis

## Instructions for Claude

Du ska analysera ett transkript från en svensk finanspodcast och identifiera **köprekommendationer**.

### Vad är en köprekommendation?

En köprekommendation är ett uttalande som indikerar att talaren har en **positiv syn på att köpa** en specifik aktie. Detta inkluderar:

**Tydliga köprekommendationer:**
- "Vi har köpt X"
- "Jag gillar X på de här nivåerna"
- "X är ett bra köp nu"
- "Vi har tagit en position i X"

**Implicita köprekommendationer:**
- "X ser väldigt intressant ut just nu" (i kombination med värdering/pris)
- "Jag tror X kommer gå bra härifrån"
- "Vi har ökat i X"
- "X är undervärderat"

**INTE köprekommendationer:**
- Neutral bolagsdiskussion utan åsikt
- "X är ett intressant bolag" (utan koppling till köp)
- Historiska kommentarer ("vi köpte X förra året")
- Generella branschkommentarer
- Säljrekommendationer (vi söker endast köp)

### Output Format

Svara ENDAST med JSON i följande format:

```json
{
  "analysis_metadata": {
    "podcast": "{{PODCAST_NAME}}",
    "episode": "{{EPISODE_TITLE}}",
    "date": "{{EPISODE_DATE}}",
    "analyzed_at": "{{ISO_TIMESTAMP}}"
  },
  "recommendations": [
    {
      "company_name": "Evolution Gaming",
      "ticker": "EVO",
      "market": "OMX Stockholm",
      "host": "Johan Isaksson",
      "quote": "Vi har ökat i Evolution, vi gillar verkligen caset på de här nivåerna efter rapporten.",
      "context": "Diskussion om Q3-rapporten och värdering efter kursnedgång",
      "timestamp_hint": "ca 23 minuter in",
      "time_horizon": "6m",
      "confidence": "high",
      "reasoning": "Explicit köputtryck: 'ökat' + 'gillar caset' + nivåreferens indikerar aktiv position"
    }
  ],
  "summary": {
    "total_recommendations": 1,
    "companies_mentioned": ["Evolution Gaming", "Volvo", "..."],
    "notes": "Avsnittet fokuserade främst på makro, få konkreta köprekommendationer"
  }
}
```

### Fältbeskrivningar

| Fält | Beskrivning | Obligatorisk |
|------|-------------|--------------|
| `company_name` | Fullständigt bolagsnamn | Ja |
| `ticker` | Börssymbol om känd, annars null | Nej |
| `market` | Börs/marknad om känd | Nej |
| `host` | Vem som sa det (om identifierbart) | Nej |
| `quote` | Ordagrant citat från transkriptet | Ja |
| `context` | Sammanfattning av kontexten | Ja |
| `timestamp_hint` | Ungefärlig tidpunkt om möjligt | Nej |
| `time_horizon` | "1m", "3m", "6m", "12m", "long-term", eller null | Nej |
| `confidence` | "high", "medium", "low" | Ja |
| `reasoning` | Varför detta tolkas som köprek | Ja |

### Confidence Levels

- **high**: Tydligt köputtalande, explicit position
- **medium**: Stark positiv syn, men inte explicit köp
- **low**: Möjlig köpindikation, men osäker tolkning

### Viktiga riktlinjer

1. **Var konservativ** - hellre missa en osäker rekommendation än inkludera något som inte är en köprek
2. **Citera ordagrant** - quote ska vara exakt från transkriptet
3. **Identifiera talare** - om podden har flera hosts, försök avgöra vem som pratar
4. **Kontext är viktigt** - samma mening kan vara köprek eller ej beroende på kontext
5. **Svenska aktier** - för svenska bolag, anta B-aktie om ej specificerat (t.ex. VOLV-B)
6. **Internationella aktier** - inkludera ticker och marknad om möjligt

---

## Input Data

**Podcast:** {{PODCAST_NAME}}
**Episode:** {{EPISODE_TITLE}}
**Date:** {{EPISODE_DATE}}
**Hosts:** {{HOSTS}}

---

## Transcript

```
{{TRANSCRIPT}}
```

---

## Your Analysis

Analysera transkriptet ovan och returnera JSON enligt formatet beskrivet ovan.
