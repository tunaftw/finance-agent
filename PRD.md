# PodStock – Product Requirements Document (PRD)

**Version:** 1.0  
**Datum:** 2024-12-21  
**Status:** Ready for Implementation

---

## 1. Executive Summary

### 1.1 Vision
PodStock är ett verktyg för att extrahera och analysera aktierekommendationer från svenska finanspodcasts. Syftet är att mäta "signal-to-noise ratio" hos olika podcast-hosts genom att tracka deras rekommendationer och jämföra med faktiskt utfall.

### 1.2 Problem
Svenska finanspodcasts (Börspodden, Fill or Kill, etc.) ger regelbundet åsikter om aktier, men det finns inget systematiskt sätt att:
- Spåra vilka rekommendationer som ges
- Mäta hur bra dessa rekommendationer presterar över tid
- Jämföra träffsäkerhet mellan olika podcasts/hosts

### 1.3 Lösning
Ett CLI-verktyg som:
1. Laddar ner podcast-avsnitt via RSS
2. Transkriberar lokalt med Whisper
3. Analyserar transkript med Claude för att identifiera köprekommendationer
4. Sparar strukturerad data för framtida utfallsanalys

---

## 2. Scope

### 2.1 In Scope (MVP)
- [x] Ladda ner podcast-ljud via RSS-flöden
- [x] Transkribera med mlx-whisper (lokalt, M4-optimerat)
- [x] Analysera transkript via Claude (manuellt via Claude Code)
- [x] Extrahera: bolag, datum, citat, ev. tidshorisont
- [x] Spara till JSON + generera Markdown-rapport
- [x] Idempotent: redan analyserade avsnitt hoppas över
- [x] Terminal-baserat UI

### 2.2 Out of Scope (Fas 2)
- Automatisk prisdata-integration
- Webb-UI
- Automatisk analys via Claude API
- Säljrekommendationer (endast köp i MVP)
- Push-notifikationer för nya avsnitt

### 2.3 Initiala Podcasts

| Podcast | RSS-URL |
|---------|---------|
| Börspodden | `https://borspodden.libsyn.com/rss` |
| Börsmagasinet | `https://feeds.acast.com/public/shows/borsmagasinet` |
| Market Makers | `https://feeds.acast.com/public/shows/marketmakers` |
| Fill or Kill | `https://fillorkill.libsyn.com/rss` |
| Gött Tjöt om Aktier | `https://feeds.acast.com/public/shows/nantingomaktier` |

---

## 3. User Stories

### US-1: Lägga till ny podcast
**Som** användare  
**Vill jag** kunna lägga till en ny podcast via dess RSS-URL  
**Så att** jag kan inkludera nya källor i min analys

**Acceptanskriterier:**
- Kan ange podcast-namn och RSS-URL
- Systemet validerar att RSS:en är giltig
- Podcasten läggs till i konfigurationen

---

### US-2: Ladda ner avsnitt
**Som** användare  
**Vill jag** kunna ladda ner specifika avsnitt eller alla nya avsnitt  
**Så att** jag har ljudfilerna lokalt för transkribering

**Acceptanskriterier:**
- Kan ladda ner enskilt avsnitt via ID eller URL
- Kan ladda ner alla avsnitt som inte redan finns lokalt
- Visar progress under nedladdning
- Hoppar över redan nedladdade filer

---

### US-3: Transkribera avsnitt
**Som** användare  
**Vill jag** kunna transkribera nedladdade avsnitt  
**Så att** jag får textversioner att analysera

**Acceptanskriterier:**
- Kör mlx-whisper lokalt
- Sparar transkript som .txt eller .json
- Visar progress (tid kvar)
- Hoppar över redan transkriberade avsnitt

---

### US-4: Analysera för köprekommendationer
**Som** användare  
**Vill jag** kunna analysera transkript för köprekommendationer  
**Så att** jag får strukturerad data om vilka aktier som rekommenderas

**Acceptanskriterier:**
- Genererar en prompt med transkriptet för Claude
- Output inkluderar: bolag, citat, kontext, ev. tidshorisont
- Visar motivering för varför något tolkas som köprek
- Sparar resultat till JSON

---

### US-5: Generera rapport
**Som** användare  
**Vill jag** kunna generera en sammanfattande rapport  
**Så att** jag kan se alla rekommendationer överskådligt

**Acceptanskriterier:**
- Markdown-format
- Grupperat per podcast
- Inkluderar datum, bolag, citat
- Sparas med timestamp i filnamn

---

### US-6: Undvika dubbelarbete
**Som** användare  
**Vill jag** att systemet kommer ihåg vad som redan är analyserat  
**Så att** jag inte gör samma jobb två gånger

**Acceptanskriterier:**
- Systemet kollar status innan varje steg
- Frågar användaren om de vill köra om (om redan gjort)
- Tydlig loggning av vad som hoppas över

---

## 4. Data Model

### 4.1 Podcast
```json
{
  "id": "borspodden",
  "name": "Börspodden",
  "rss_url": "https://borspodden.libsyn.com/rss",
  "hosts": ["Johan Isaksson", "John Skogman"],
  "added_at": "2024-12-21T10:00:00Z"
}
```

### 4.2 Episode
```json
{
  "id": "bp-2024-12-18",
  "podcast_id": "borspodden",
  "title": "Avsnitt 598 - Julspecial",
  "published_at": "2024-12-18T10:00:00Z",
  "duration_seconds": 3600,
  "audio_url": "https://...",
  "audio_path": "data/audio/borspodden/bp-2024-12-18.mp3",
  "transcript_path": "data/transcripts/borspodden/bp-2024-12-18.txt",
  "status": {
    "downloaded": true,
    "transcribed": true,
    "analyzed": true
  }
}
```

### 4.3 Recommendation
```json
{
  "id": "rec-001",
  "episode_id": "bp-2024-12-18",
  "podcast_id": "borspodden",
  "host": "Johan Isaksson",
  "company": {
    "name": "Evolution Gaming",
    "ticker": "EVO",
    "market": "OMX Stockholm"
  },
  "quote": "Jag gillar verkligen caset på de här nivåerna, vi har tagit en position.",
  "context": "Diskussion om Q3-rapporten och värdering",
  "timestamp_seconds": 1847,
  "recommendation_date": "2024-12-18",
  "time_horizon": "6m",
  "confidence": "high",
  "analysis_reasoning": "Explicit köputtryck: 'tagit en position' + positiv värdering",
  "created_at": "2024-12-21T14:30:00Z"
}
```

---

## 5. Non-Functional Requirements

### 5.1 Performance
- Transkribering: ~10-15x realtid på M4 (60 min → 4-6 min)
- Nedladdning: begränsas inte, följer normal bandbredd

### 5.2 Lagring
- Audio: ~1 MB/minut → ~60 MB per avsnitt
- Transkript: ~100 KB per avsnitt
- 500 avsnitt totalt ≈ 30 GB audio + 50 MB text

### 5.3 Tillförlitlighet
- Alla operationer ska vara idempotent
- Ingen data får förloras vid avbrott
- Progress ska sparas inkrementellt

### 5.4 Utökningsbarhet
- Lätt att lägga till nya podcasts
- Lätt att ändra analys-prompten
- Dokumenterad kodstruktur

---

## 6. Technical Constraints

### 6.1 Miljö
- macOS med Apple Silicon (M4)
- Python 3.11+
- Lokal körning (ingen molntjänst)

### 6.2 Dependencies
- `mlx-whisper` – transkribering
- `feedparser` – RSS-parsing
- `requests` – HTTP
- Standard library för resten

### 6.3 Claude-integration
- MVP: Manuell copy-paste till Claude.ai/Claude Code
- Prompten genereras av verktyget, användaren kör den

---

## 7. Success Metrics

### MVP Success
- [x] Kan ladda ner 5 avsnitt från 5 olika podcasts
- [x] Kan transkribera alla 5 med mlx-whisper
- [x] Kan generera analys-prompt som identifierar köprekar
- [x] Sparar strukturerad data i JSON
- [x] Genererar läsbar Markdown-rapport

### Framtida KPIs
- Antal podcasts som trackas
- Antal rekommendationer i databasen
- Träffsäkerhet per host (kräver prisdata)

---

## 8. Risks & Mitigations

| Risk | Sannolikhet | Impact | Mitigation |
|------|-------------|--------|------------|
| Whisper ger dålig svenska transkribering | Låg | Hög | Använd `large-v3` modellen |
| RSS-format ändras | Låg | Medium | Flexibel parsing, validering |
| Rekommendationer är för vaga | Hög | Medium | Iterera på prompten, manuell validering initialt |
| Lagring tar slut | Låg | Medium | Rensa audio efter transkribering (optional) |

---

## 9. Glossary

| Term | Definition |
|------|------------|
| **Köprekommendation** | Ett uttalande som indikerar positiv syn på att köpa en aktie |
| **Tidshorisont** | Förväntad period för investeringen (1m, 3m, 6m, 12m+) |
| **Idempotent** | Samma operation kan köras flera gånger utan sidoeffekter |
| **RSS** | Really Simple Syndication – format för podcast-flöden |

---

## 10. Appendix

### A. Exempelprompt för Claude-analys
Se filen `prompts/analyze_transcript.md`

### B. RSS-flödesstruktur
Se filen `docs/RSS_FORMAT.md`
