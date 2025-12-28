# JSON-schema för Podcast-analys

## Komplett EpisodeAnalysis-schema

```json
{
  "episode_id": "string (REQUIRED) - Unikt ID baserat på filnamn, t.ex. 'borspodden-2025-02-19-26e5'",
  "podcast_name": "string (REQUIRED) - Podcastens namn, t.ex. 'Börspodden', 'Veckans Trade'",
  "episode_title": "string | null - Avsnittets titel om känd",
  "episode_number": "integer | null - Avsnittsnummer om känt",
  "date": "string (REQUIRED) - ISO-format YYYY-MM-DD",

  "hosts": ["string"] - "Lista med hostnamn",
  "guests": ["string"] - "Lista med gästnamn",

  "main_topics": ["string"] - "Max 5 huvudämnen som diskuteras",
  "stocks_discussed": ["string"] - "Alla aktier/bolag som nämns",

  "recommendations": [
    {
      "stock_name": "string (REQUIRED) - Aktiens namn",
      "ticker": "string | null - Ticker om nämnt",
      "action": "buy | sell | hold | watch | avoid (REQUIRED)",
      "confidence": "high | medium | low | speculative (REQUIRED)",
      "speaker": "string | null - Vem gav rekommendationen",
      "speaker_role": "host | guest | unknown",
      "timestamp": "string | null - Format HH:MM:SS",
      "reasoning": "string (REQUIRED) - 1-3 meningar",
      "price_target": "string | null - Kursmål, t.ex. '1400 SEK'",
      "time_horizon": "string | null - 'kort sikt', 'lång sikt', '6 månader'",
      "quote": "string (REQUIRED) - Exakt citat, max 100 ord",
      "sector": "string | null - Bransch: tech, fastigheter, finans, gaming, etc.",
      "market": "sweden | us | europe | other | unknown"
    }
  ],

  "market_sentiment": "bullish | bearish | neutral | mixed (REQUIRED)",
  "summary": "string (REQUIRED) - 3-5 meningar som sammanfattar avsnittet",
  "key_takeaways": ["string"] - "3-5 huvudpunkter för investerare",

  "transcript_file": "string (REQUIRED) - Sökväg till transkriptfil",
  "transcript_word_count": "integer (REQUIRED) - Antal ord i transkriptet",
  "has_timestamps": "boolean - Finns [HH:MM:SS] i transkriptet?",
  "processed_at": "string - ISO-timestamp för när analysen gjordes",
  "model_used": "string - 'glm-4.7'"
}
```

---

## Action-definitioner

| Action | Betydelse | Exempel-fraser |
|--------|-----------|----------------|
| `buy` | Stark köprekommendation | "köpläge", "vi köper", "stark köp", "undervärderad" |
| `sell` | Säljrekommendation | "säljläge", "ta hem vinst", "vi säljer", "övervärderad" |
| `hold` | Behåll position | "vi äger", "behåll", "sitter still" |
| `watch` | Bevaka, ej köp ännu | "intressant", "håll koll på", "kan bli köpvärd" |
| `avoid` | Undvik aktien | "håll dig borta", "undvik", "för riskfyllt" |

---

## Confidence-nivåer

| Nivå | Betydelse |
|------|-----------|
| `high` | Stark övertygelse, tydliga argument |
| `medium` | Rimlig övertygelse, vissa förbehåll |
| `low` | Osäker, vag rekommendation |
| `speculative` | Spekulativ, hög risk |

---

## Exempel: Komplett JSON-output

```json
{
  "episode_id": "veckanstrade-2025-12-23-c289",
  "podcast_name": "Veckans Trade",
  "episode_title": "Richard Bråse gästar",
  "episode_number": 36,
  "date": "2025-12-23",

  "hosts": ["Viktor", "Martin"],
  "guests": ["Richard Bråse"],

  "main_topics": [
    "Anti-momentum som strategi",
    "Novo Nordisk analys",
    "Pharma-sektorn",
    "Portföljstrategi",
    "Lärdomar från finansjournalistik"
  ],

  "stocks_discussed": [
    "Novo Nordisk",
    "Millicom",
    "East Nine",
    "Castellum"
  ],

  "recommendations": [
    {
      "stock_name": "Novo Nordisk",
      "ticker": "NOVO-B",
      "action": "sell",
      "confidence": "high",
      "speaker": "Richard Bråse",
      "speaker_role": "guest",
      "timestamp": "00:23:15",
      "reasoning": "Sålde hela positionen efter att aktien tappat 40%. Anser att marknaden överskattar GLP-1 potentialen och att konkurrensen ökar.",
      "price_target": null,
      "time_horizon": null,
      "quote": "Jag har sålt hela min position i Novo. När något tappar 40% och hela marknaden fortfarande är bullish, då måste man fråga sig vad man missar.",
      "sector": "pharma",
      "market": "europe"
    }
  ],

  "market_sentiment": "mixed",

  "summary": "Richard Bråse, legendarisk finansjournalist, diskuterar sin anti-momentum strategi där han går emot konsensus. Han har sålt hela sin Novo-position och föredrar mindre bolag där han ser value-case. Avsnittet fokuserar på vikten av att tänka konträrt och inte följa flocken.",

  "key_takeaways": [
    "Anti-momentum kan ge alfa när konsensus har fel",
    "Novo Nordisk: Bråse har sålt allt efter 40% nedgång",
    "Fokus på bolag där du kan se något marknaden missar",
    "Var skeptisk mot konsensus-narrativ",
    "Långsiktighet viktigare än att tajma marknaden"
  ],

  "transcript_file": "data/transcripts/veckanstrade/veckanstrade-2025-12-23-c289.txt",
  "transcript_word_count": 9000,
  "has_timestamps": true,
  "processed_at": "2025-12-25T14:30:00",
  "model_used": "glm-4.7"
}
```

---

## Vanliga misstag att undvika

1. **Inkludera INTE vaga diskussioner** - Endast tydliga rekommendationer
2. **Glöm inte citat** - Varje rekommendation MÅSTE ha ett citat
3. **Fel action** - "Intressant bolag" = `watch`, inte `buy`
4. **Saknad speaker** - Identifiera alltid vem som pratar
5. **Inkonsekvent format** - Följ exakt samma struktur

---

## Sektorer (vanliga)

- `tech` - Teknologi
- `fastigheter` - Real estate
- `finans` - Bank, försäkring
- `gaming` - Spel, casino
- `pharma` - Läkemedel
- `retail` - Detaljhandel
- `industri` - Industri, verkstad
- `konsument` - Konsumentvaror
- `energi` - Energi, olja
- `telekom` - Telekommunikation
