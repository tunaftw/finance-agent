# Real-Time Podcast Monitoring

Dokumentation för PodStocks real-time monitoring-system som hanterar automatisk synkronisering och sammanfattning av podcast-innehåll.

---

## Översikt

Real-time monitoring-systemet består av tre huvudkomponenter:

1. **List Management** (`podstock list`) - Organisera podcasts i listor
2. **Sync** (`podstock sync`) - Automatisk hämtning och transkribering
3. **Summary** (`podstock summary`) - Generera periodiska sammanfattningar

### Arkitektur

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI (cli.py)                              │
├──────────────┬──────────────────┬───────────────────────────────┤
│  list        │      sync        │          summary              │
│  commands    │   orchestrator   │         generator             │
├──────────────┼──────────────────┼───────────────────────────────┤
│              │                  │                               │
│  lists/      │     sync/        │         reports/              │
│  manager.py  │  orchestrator.py │        generator.py           │
│  models.py   │     models.py    │      data_loader.py           │
│              │                  │        prompts.py             │
├──────────────┴──────────────────┴───────────────────────────────┤
│                     Core (state.py, models.py)                   │
├─────────────────────────────────────────────────────────────────┤
│           Data (lists.json, state.json, transcripts/)            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. List Management

### Koncept

Podcast-listor grupperar podcasts för olika ändamål:

| Lista | Typ | Användning |
|-------|-----|------------|
| **broad** | bred | Alla finanspodcasts för övergripande marknadsöversikt |
| **niche** | nischad | Utvalda podcasts för djupanalys |
| *custom* | anpassad | Egna listor för specifika behov |

### Kommandon

```bash
# Visa alla listor med antal podcasts
podstock list show

# Visa innehållet i en specifik lista
podstock list show broad
podstock list show niche

# Skapa ny lista
podstock list create favorites --type custom --description "Mina favoriter"

# Lägg till podcast i lista
podstock list add broad borspodden
podstock list add niche fillorkill

# Ta bort podcast från lista
podstock list remove broad borspodden

# Radera lista (fungerar ej för broad/niche)
podstock list delete favorites
```

### Dataformat

Listor lagras i `data/lists.json`:

```json
{
  "version": 1,
  "updated_at": "2025-12-26T12:00:00",
  "lists": [
    {
      "id": "broad",
      "name": "Bred Analys",
      "description": "Alla podcasts för övergripande marknadsöversikt",
      "type": "broad",
      "podcast_ids": ["borspodden", "marketmakers", "aktiepodden"],
      "created_at": "2025-12-26T12:00:00",
      "active": true
    }
  ]
}
```

---

## 2. Sync (Synkronisering)

### Koncept

Sync-funktionen hämtar nya avsnitt och transkriberar dem automatiskt.

**Transkriberingskällor:**
1. **Apple Podcasts** - Hämtar cachade transcripts (gratis, snabbt)
2. **Whisper** - Lokal transkribering med mlx-whisper (kräver nedladdning)

### Transcript Source Flag

Varje podcast har en `transcript_source`-inställning i `data/podcasts.json`:

| Värde | Beteende |
|-------|----------|
| `auto` (default) | Prova Apple först, fallback till Whisper |
| `apple` | Endast Apple Podcasts transcripts |
| `whisper` | Alltid använd Whisper |

### Kommandon

```bash
# Dry-run: Visa vad som skulle synkas utan att göra något
podstock sync --dry-run

# Synka senaste avsnittet från alla podcasts
podstock sync

# Synka senaste 3 avsnitten
podstock sync --latest 3

# Synka specifik podcast
podstock sync --podcast borspodden

# Synka alla podcasts i en lista
podstock sync --list broad
podstock sync --list niche --latest 2
```

### Sync-flöde

```
1. HÄMTA RSS
   └── Parsa RSS-feed, identifiera nya avsnitt

2. FILTRERA
   └── Hoppa över redan transkriberade (finns i state.json)

3. TRANSKRIBERA
   ├── Om source = "apple" eller "auto":
   │   └── Prova Apple Podcasts cache
   │       ├── Hittat → Spara transcript, uppdatera state
   │       └── Ej hittat + auto → Gå till Whisper
   │
   └── Om source = "whisper" eller fallback:
       ├── Ladda ner audio
       ├── Transkribera med mlx-whisper
       └── Spara transcript, uppdatera state

4. RESULTAT
   └── Visa sammanfattning: synkade/hoppade/misslyckade
```

### Output

```
$ podstock sync --list broad --latest 1

Synkar 5 podcasts från lista: broad

Börspodden:
  ✓ borspodden-2025-12-26-abc1 (Apple)

Market Makers:
  ✓ marketmakers-2025-12-25-def2 (Whisper)

Aktiepodden:
  ⊘ Inga nya avsnitt

───────────────────────────────────
Synkade: 2 | Hoppade: 3 | Misslyckade: 0
```

---

## 3. Summary (Sammanfattningar)

### Koncept

Summary-funktionen genererar LLM-baserade sammanfattningar av podcast-innehåll för en vald tidsperiod.

**Två rapporttyper:**

| Typ | Innehåll | Användning |
|-----|----------|------------|
| `broad` | Övergripande teman, kort per podcast | Veckoöversikt |
| `detailed` | Utförliga citat, gäst-insikter, motsägelser | Djupanalys |

**Två LLM-alternativ:**

| Alternativ | Kostnad | Kvalitet | Metod |
|------------|---------|----------|-------|
| Claude Code | Tokens | Högre | Generera prompt, kör direkt |
| Opencode/GLM-4.7 | Gratis | Bra | Exportera JSON, öppna i Opencode |

### Kommandon

```bash
# Visa tillgänglig data för en period
podstock summary info --from 2025-12-20 --to 2025-12-26

# Förbered prompt för Claude Code
podstock summary prepare --from 2025-12-20 --to 2025-12-26

# Detaljerad rapport med niche-listan
podstock summary prepare --from 2025-12-01 --to 2025-12-31 --type detailed --list niche

# Exportera för Opencode (gratis LLM)
podstock summary prepare --from 2025-12-20 --to 2025-12-26 --opencode

# Spara färdig rapport (efter manuell generering)
podstock summary save --output 2025-w52-summary.md
```

### Workflow: Claude Code

1. **Förbered data:**
   ```bash
   podstock summary prepare --from 2025-12-20 --to 2025-12-26 --type broad
   ```
   Skapar prompt-fil i `data/reports/prompts/`

2. **Läs prompt-filen i Claude Code:**
   ```bash
   # Claude Code läser filen och analyserar datan
   ```

3. **Spara rapporten:**
   ```bash
   podstock summary save --output vecka-52.md
   ```

### Workflow: Opencode/GLM-4.7

1. **Exportera JSON:**
   ```bash
   podstock summary prepare --from 2025-12-20 --to 2025-12-26 --opencode
   ```
   Skapar JSON-fil i `data/reports/prompts/`

2. **Öppna i Opencode:**
   ```
   Läs filen och generera rapporten enligt instruktionerna
   ```

3. **Kopiera resultatet till rapport-fil**

### Rapport-format

```markdown
# Podcast-sammanfattning 2025-12-20 till 2025-12-26

## Översikt
- Tema 1: Marknaden osäker inför Fed-beslut
- Tema 2: Fokus på defensiva aktier
- Tema 3: Cryptocurrency volatilitet

## Aktierekommendationer

| Aktie | Podcast | Talare | Typ | Motivering |
|-------|---------|--------|-----|------------|
| Novo Nordisk | Börspodden | Johan | Köp | GLP-1 momentum |
| H&M | Market Makers | Niklas | Sälj | Marginalpress |

## Per Podcast

### Börspodden
Fokus på small caps med potential...

### Market Makers
Diskuterade tech-rotation...

## Marknadssentiment
**Neutral** - Avvaktande inför årsskiftet med blandade signaler.
```

---

## Claude Code Skills

### /sync

Kör `/sync` i Claude Code för att synka nya avsnitt.

**Användning:**
```
/sync
/sync --podcast borspodden
/sync --list broad --latest 3
```

**Workflow:**
1. Dry-run för att se vad som synkas
2. Kör sync
3. Visa status

### /summary

Kör `/summary` i Claude Code för att generera sammanfattningar.

**Användning:**
```
/summary --from 2025-12-20 --to 2025-12-26
/summary --from 2025-12-01 --to 2025-12-31 --type detailed
```

**Workflow:**
1. Förbered data
2. Läs prompt-filen
3. Analysera och generera rapport
4. Spara resultatet

---

## Filstruktur

```
data/
├── lists.json              # Podcast-listor (broad, niche, custom)
├── state.json              # Processingsstatus per avsnitt
├── podcasts.json           # Podcast-konfiguration inkl. transcript_source
├── transcripts/            # Transkriberade avsnitt
│   ├── borspodden/
│   ├── marketmakers/
│   └── ...
└── reports/
    ├── prompts/            # Genererade LLM-prompts
    │   ├── 2025-12-26-1200-broad-prompt.md
    │   └── 2025-12-26-1200-broad-opencode.json
    └── summaries/          # Färdiga rapporter
        └── 2025-12-26-summary.md

src/podstock/
├── lists/                  # List management
│   ├── models.py           # PodcastList, ListsFile
│   └── manager.py          # CRUD-operationer
├── sync/                   # Synkronisering
│   ├── models.py           # SyncSummary, EpisodeSyncResult
│   └── orchestrator.py     # SyncOrchestrator
└── reports/                # Sammanfattningar
    ├── models.py           # SummaryConfig, ReportData
    ├── prompts.py          # LLM prompt-templates
    ├── data_loader.py      # ReportDataLoader
    └── generator.py        # SummaryReportGenerator
```

---

## Vanliga användningsfall

### Daglig rutin

```bash
# 1. Synka nya avsnitt (tar ~1 min)
podstock sync --list broad

# 2. Se status
podstock status

# 3. Vid behov: Generera veckosammanfattning
podstock summary prepare --from 2025-12-20 --to 2025-12-26
```

### Veckosammanfattning

```bash
# Se tillgänglig data
podstock summary info --from 2025-12-16 --to 2025-12-22

# Generera bred sammanfattning
podstock summary prepare --from 2025-12-16 --to 2025-12-22 --type broad

# Läs prompten och generera rapport i Claude Code
# Spara rapporten
podstock summary save --output vecka-51.md
```

### Djupanalys av specifika podcasts

```bash
# Synka niche-listan med fler avsnitt
podstock sync --list niche --latest 5

# Detaljerad analys
podstock summary prepare --from 2025-12-01 --to 2025-12-31 --type detailed --list niche
```

---

## Felsökning

### Sync hittar inga avsnitt

1. Kontrollera att podcast finns i listan:
   ```bash
   podstock list show broad
   ```

2. Kontrollera RSS-flödet:
   ```bash
   podstock podcast info borspodden
   ```

3. Prova dry-run:
   ```bash
   podstock sync --podcast borspodden --dry-run
   ```

### Apple transcript hittas inte

- Kontrollera att podcasten finns på Apple Podcasts
- Prova med `transcript_source: "whisper"` i podcasts.json
- Verifiera att avsnittstiteln matchar

### Summary visar "0 avsnitt"

1. Kontrollera datumintervallet:
   ```bash
   podstock summary info --from 2025-12-01 --to 2025-12-31
   ```

2. Verifiera att avsnitt är transkriberade:
   ```bash
   podstock status
   ```

3. Kör sync för perioden:
   ```bash
   podstock sync --list broad --latest 10
   ```
