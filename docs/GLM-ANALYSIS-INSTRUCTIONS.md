# GLM 4.7 Podcast-analys: Batch-körning

## Syfte

Extrahera aktierekommendationer från ~3,000 svenska finanspoddar och strukturera dem i JSON-format.

---

## VIKTIGT: Context Window-hantering

**Batch-storlek:** 3-4 transkript per session (MAX 4)
**Efter varje transkript:** Spara JSON + uppdatera completion-log OMEDELBART
**Efter 3-4 transkript:** STOPPA och starta ny session
**Progress:** Spåras automatiskt i `completion-log.json`

⚠️ **KRITISKT:** Om du känner att context blir fullt (svar blir långsamma,
saker glöms bort), STOPPA OMEDELBART även om du inte nått 3-4.
All progress är redan sparad efter varje transkript.

---

## Starta en session

### 1. Läs completion-log

```
Läs: data/extracted/glm-batch/completion-log.json
```

Kontrollera:
- Hur många är `completed`?
- Vilken `current_batch` är vi på?

### 2. Läs transkript-kön

```
Läs: data/extracted/glm-batch/transcript-queue.txt
```

Hitta de 3-4 nästa transkripten som INTE finns i `completed`-listan.

### 3. Analysera 3-4 transkript

Följ "Analysera ett transkript" nedan för varje fil.

**VIKTIGT:** Spara JSON och uppdatera completion-log EFTER VARJE transkript, inte i slutet!

### 4. Efter 3-4 transkript (eller om context känns fullt)

```
⚠️ BATCH COMPLETE ⚠️

Du har analyserat [antal] transkript i denna session.
STOPPA NU och vänta på ny session.

Progress är sparad i completion-log.json.
Användaren behöver starta en ny konversation för att fortsätta.

Nästa session: Läs instruktionerna igen och fortsätt där du slutade.
```

---

## Analysera ett transkript

### Steg 1: Läs transkriptet

Läs hela innehållet i transkriptfilen.

### Steg 2: Analysera med följande prompt

```
Du är en expert på att analysera svenska finanspoddar och extrahera investeringsrekommendationer.

Din uppgift är att noggrant läsa podcast-transkript och identifiera:
1. KONKRETA aktie-rekommendationer (köp, sälj, bevaka, undvik)
2. Vem som ger rekommendationen (host eller gäst)
3. Argumenten bakom rekommendationen
4. Eventuella kursmål eller tidshorisonter

VIKTIGA RIKTLINJER:
- Var KONSERVATIV: Inkludera bara tydliga rekommendationer, inte vag diskussion
- "Intressant bolag" eller "värt att titta på" = watch, INTE buy
- "Vi äger aktien" utan vidare kontext = hold
- "Stark köpkandidat", "köpläge", "vi köper" = buy
- "Dags att ta hem vinst", "sälj", "vi säljer" = sell
- Fånga EXAKTA citat som stödjer rekommendationen
- Om tidsstämplar finns [HH:MM:SS], inkludera dem
- Svenska bolag listas ofta utan ticker - det är OK att lämna ticker tom

⚠️ EXKLUDERA FÖLJANDE - DETTA ÄR INTE REKOMMENDATIONER:
- Sponsormeddelanden (Interactive Brokers, Avanza, Nordnet, Syn Society, etc.)
- Reklam och produktplaceringar
- Podcast-prenumerations-uppmaningar ("Prenumerera på...", "Följ oss på...")
- Sociala media-omnämnanden
- Mäklare/plattformar som omnämns i reklamsyfte
- Fondbolag som sponsrar (Protean, Carnegie, etc. OM de bara nämns som sponsor)

FINANSTERMINOLOGI ATT KÄNNA IGEN:
- Köpsignaler: "köpläge", "köpvärd", "attraktiv", "undervärderad", "vi köper", "stark köp"
- Säljsignaler: "säljläge", "övervärderad", "ta hem vinst", "vi säljer", "sälj"
- Watch: "bevaka", "intressant", "håll koll på", "kan bli köpvärd"
- Undvik: "håll dig borta", "undvik", "för riskfyllt"

OUTPUT:
Returnera ENDAST valid JSON enligt schemat. Ingen annan text.
```

### Steg 3: Generera JSON

Se `docs/JSON-SCHEMA.md` för komplett schema.

**Viktigast:**
- `episode_id`: Baserat på filnamn (utan .txt)
- `podcast_name`: Extrahera från katalog eller filnamn
- `date`: YYYY-MM-DD format
- `recommendations`: Array med rekommendationer
- `model_used`: "glm-4.7"

### Steg 4: Spara JSON

```
data/extracted/glm-batch/[filnamn].json
```

Exempel:
- Input: `veckanstrade-2025-06-11-2aae.txt`
- Output: `data/extracted/glm-batch/veckanstrade-2025-06-11-2aae.json`

### Steg 5: Uppdatera completion-log

Efter varje sparat transkript, uppdatera `completion-log.json`:

1. Lägg till filnamnet i `completed`-arrayen
2. Öka `total_processed` med 1
3. Uppdatera `last_updated` med aktuell timestamp

---

## Completion-log format

```json
{
  "completed": [
    "veckanstrade-2025-06-11-2aae.txt",
    "veckanstrade-2025-07-16-b028.txt"
  ],
  "failed": [],
  "last_updated": "2025-12-25T14:30:00",
  "total_processed": 2,
  "current_batch": 1
}
```

---

## Podcast-namn mapping

| Katalog/prefix | podcast_name |
|----------------|--------------|
| borspodden | Börspodden |
| veckanstrade | Veckans Trade |
| borsensfinest | Börsens Finest |
| fillorkill | Fill or Kill |
| marketmakers | Market Makers |
| sparpodden | Sparpodden |
| aktiepodden | Aktiepodden |
| avanzapodden | Avanzapodden |
| gotttjot | Gött Tjöt om Aktier |
| kortochlang | Kort och Långt |

---

## Filstruktur

```
podcast-transcriber/
├── data/
│   ├── transcripts/              # Input
│   │   ├── borspodden/
│   │   ├── veckanstrade/
│   │   └── ...
│   └── extracted/
│       ├── episodes/             # Claude-resultat (referens)
│       ├── glm-test/             # Test-resultat (Fas 1)
│       └── glm-batch/            # Batch-resultat (Fas 2)
│           ├── completion-log.json
│           ├── transcript-queue.txt
│           └── *.json
└── docs/
    ├── GLM-ANALYSIS-INSTRUCTIONS.md
    ├── JSON-SCHEMA.md
    └── BATCH-WORKFLOW.md
```

---

## Vanliga fel att undvika

1. **Sponsorer som rekommendationer** - Interactive Brokers, Avanza, etc. är INTE köprekommendationer
2. **Hosts vs Guests** - Kontrollera vem som faktiskt pratar
3. **JSON-syntaxfel** - Validera att JSON är korrekt innan du sparar
4. **Glömd completion-log** - Uppdatera ALLTID efter varje transkript
5. **Mer än 4 per session** - STOPPA efter 3-4, starta ny session (context-gräns!)

---

## Checklista per transkript

- [ ] Läst transkriptet
- [ ] Analyserat med prompt
- [ ] Genererat valid JSON
- [ ] Sparat till glm-batch/
- [ ] Uppdaterat completion-log.json
- [ ] (Efter 10: STOPPA)
