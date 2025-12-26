# PodStock CLI Reference

Komplett referens för alla PodStock-kommandon.

---

## Snabbguide

```bash
podstock --help                  # Visa alla kommandon
podstock <command> --help        # Hjälp för specifikt kommando
```

---

## Kommandoöversikt

| Kategori | Kommando | Beskrivning |
|----------|----------|-------------|
| **Podcast** | `podstock podcast` | Hantera podcast-konfiguration |
| **List** | `podstock list` | Hantera podcast-listor (broad/niche) |
| **Sync** | `podstock sync` | Synka nya avsnitt automatiskt |
| **Summary** | `podstock summary` | Generera periodsammanfattningar |
| **Download** | `podstock download` | Ladda ner podcast-avsnitt |
| **Transcribe** | `podstock transcribe` | Transkribera ljudfiler |
| **Analyze** | `podstock analyze` | Analysera transkript |
| **Report** | `podstock report` | Generera rekommendationsrapporter |
| **Status** | `podstock status` | Visa processingstatus |
| **Extract** | `podstock extract` | AI-baserad dataextraktion |
| **Guest Summary** | `podstock guest-summary` | Gäst-sammanfattning |
| **Twitter** | `podstock twitter` | Twitter/X-datasamling |

---

## podstock podcast

Hantera podcast-konfiguration.

### list
```bash
podstock podcast list
```
Visa alla konfigurerade podcasts.

### add
```bash
podstock podcast add "Podcast Namn" https://example.com/rss
podstock podcast add "Namn" URL --skip-validation
```
Lägg till ny podcast. RSS-flödet valideras som default.

| Flag | Beskrivning |
|------|-------------|
| `--skip-validation` | Hoppa över RSS-validering |

### remove
```bash
podstock podcast remove <podcast_id>
```
Ta bort en podcast.

### info
```bash
podstock podcast info <podcast_id>
```
Visa detaljer om en podcast.

---

## podstock list

Hantera podcast-listor för gruppering och synkronisering.

### show
```bash
podstock list show                    # Visa alla listor
podstock list show broad              # Visa podcasts i "broad"
podstock list show niche              # Visa podcasts i "niche"
```

### create
```bash
podstock list create <name> --type <type>
podstock list create "My Favorites" --type custom --description "Mina favoriter"
```

| Argument | Beskrivning |
|----------|-------------|
| `name` | Listans namn |
| `--type` | `broad`, `niche`, eller `custom` |
| `--description` | Valfri beskrivning |

### add
```bash
podstock list add <list_id> <podcast_id>
podstock list add broad borspodden
podstock list add niche fillorkill
```
Lägg till podcast i en lista.

### remove
```bash
podstock list remove <list_id> <podcast_id>
podstock list remove niche borspodden
```
Ta bort podcast från en lista.

### delete
```bash
podstock list delete <list_id>
```
Radera en lista. Fungerar ej för `broad` och `niche`.

---

## podstock sync

Synka nya podcast-avsnitt (hämta transcripts, transkribera vid behov).

```bash
podstock sync                           # Synka senaste från alla
podstock sync --latest 3                # Senaste 3 per podcast
podstock sync --podcast borspodden      # Synka specifik podcast
podstock sync --list broad              # Synka podcasts i lista
podstock sync --dry-run                 # Visa utan att köra
podstock sync --force                   # Tvinga om-sync
```

| Flag | Beskrivning |
|------|-------------|
| `--latest N` | Antal avsnitt att synka per podcast (default: 1) |
| `--podcast ID` | Synka specifik podcast |
| `--list ID` | Synka alla podcasts i en lista |
| `--dry-run` | Visa vad som skulle synkas utan att köra |
| `--force` | Synka även redan transkriberade avsnitt |

### Transkriberingskällor

Sync provar i denna ordning:
1. **Apple Podcasts** - Hämtar cachade transcripts (gratis, snabbt)
2. **Whisper** - Laddar ner audio och transkriberar lokalt

Varje podcast har en `transcript_source` i `podcasts.json`:
- `auto` (default): Apple först, Whisper fallback
- `apple`: Endast Apple transcripts
- `whisper`: Alltid lokal Whisper

---

## podstock summary

Generera sammanfattningar av podcast-innehåll.

### prepare
```bash
# Bred analys för Claude Code
podstock summary prepare --from 2025-12-20 --to 2025-12-26

# Detaljerad analys med niche-lista
podstock summary prepare --from 2025-12-01 --to 2025-12-31 --type detailed --list niche

# Exportera för Opencode/GLM-4.7
podstock summary prepare --from 2025-12-20 --to 2025-12-26 --opencode
```

| Flag | Beskrivning |
|------|-------------|
| `--from YYYY-MM-DD` | Startdatum (obligatorisk) |
| `--to YYYY-MM-DD` | Slutdatum (obligatorisk) |
| `--type` | `broad` (default) eller `detailed` |
| `--list` | Lista att använda (default: `broad` för bred, `niche` för detailed) |
| `--opencode` | Exportera JSON för Opencode/GLM-4.7 |

### info
```bash
podstock summary info --from 2025-12-20 --to 2025-12-26
podstock summary info --from 2025-12-20 --to 2025-12-26 --list niche
```
Visa tillgänglig data för en period.

### save
```bash
podstock summary save --output rapport.md
podstock summary save --input rapport.txt --output vecka-52.md
```
Spara genererad rapport.

| Flag | Beskrivning |
|------|-------------|
| `--output` | Filnamn för rapport |
| `--input` | Läs från fil istället för stdin |

---

## podstock download

Ladda ner podcast-avsnitt.

```bash
podstock download                        # Alla nya från alla podcasts
podstock download --podcast borspodden   # Specifik podcast
podstock download --latest 5             # Senaste 5 avsnitt
podstock download --force                # Ladda ner igen
```

| Flag | Beskrivning |
|------|-------------|
| `--podcast ID` | Specifik podcast |
| `--latest N` | Antal avsnitt (default: 1) |
| `--force` | Skriv över redan nedladdade |

---

## podstock transcribe

Transkribera ljudfiler.

### Whisper (default)
```bash
podstock transcribe                      # Alla väntande
podstock transcribe --podcast borspodden # Specifik podcast
podstock transcribe --episode <id>       # Specifikt avsnitt
podstock transcribe --model large-v3     # Ange modell
podstock transcribe --force              # Skriv över
```

### Apple Podcasts
```bash
podstock transcribe --list-apple         # Visa tillgängliga Apple-transcripts
podstock transcribe --source apple       # Extrahera från Apple
podstock transcribe --source apple --no-timestamps
```

| Flag | Beskrivning |
|------|-------------|
| `--podcast ID` | Specifik podcast |
| `--episode ID` | Specifikt avsnitt |
| `--model` | Whisper-modell (default: large-v3) |
| `--source` | `whisper` (default) eller `apple` |
| `--list-apple` | Lista Apple Podcasts transcripts |
| `--no-timestamps` | Exkludera tidsstämplar (Apple) |
| `--force` | Skriv över befintlig |

---

## podstock analyze

Analysera transkript för aktierekommendationer.

### Generera prompt
```bash
podstock analyze <episode_id>
```
Genererar en prompt att köra i Claude.

### Parsa svar
```bash
podstock analyze <episode_id> --input response.txt
podstock analyze <episode_id> --input response.txt --force
```

| Flag | Beskrivning |
|------|-------------|
| `--input FILE` | Claude-svar att parsa |
| `--force` | Skriv över befintlig analys |

---

## podstock report

Generera Markdown-rapport med rekommendationer.

```bash
podstock report                          # Visa i terminal
podstock report --output rapport.md      # Spara till fil
podstock report --podcast borspodden     # Filter på podcast
podstock report --since 2024-01-01       # Filter på datum
```

| Flag | Beskrivning |
|------|-------------|
| `--output FILE` | Spara till fil |
| `--podcast ID` | Filter på podcast |
| `--since YYYY-MM-DD` | Endast från datum |

---

## podstock status

Visa övergripande processingstatus.

```bash
podstock status
```

Visar per podcast:
- Nedladdade avsnitt
- Transkriberade avsnitt
- Analyserade avsnitt
- Väntande arbete

---

## podstock extract

AI-baserad dataextraktion från transkript.

### process
```bash
podstock extract process                 # Batch-processa alla
podstock extract process --file fil.txt  # Enskild fil
podstock extract process --podcast X     # Filter på podcast
podstock extract process --max 10        # Max antal
podstock extract process --model ollama:llama3.3  # Lokal modell
```

| Flag | Beskrivning |
|------|-------------|
| `--file` | Processa enskild fil |
| `--podcast` | Filter på podcast |
| `--max` | Max antal filer |
| `--delay` | Delay mellan API-anrop (sekunder) |
| `--model` | LLM-modell (default: claude-3-haiku) |

### search
```bash
podstock extract search --stock "Novo Nordisk"
podstock extract search --speaker "Johan"
podstock extract search --podcast borspodden
podstock extract search --action buy
podstock extract search --recent 30
podstock extract search --top 20
```

| Flag | Beskrivning |
|------|-------------|
| `--stock` | Sök på aktie |
| `--speaker` | Sök på talare |
| `--podcast` | Filter på podcast |
| `--action` | Filter: buy/sell/hold/watch/avoid |
| `--recent N` | Senaste N dagarna |
| `--top N` | Topp N mest omnämnda |

### stats
```bash
podstock extract stats
```
Visa statistik över extraherad data.

### rebuild-index
```bash
podstock extract rebuild-index
```
Bygg om sökindex från JSON-filer.

### list
```bash
podstock extract list                    # Alla transkript
podstock extract list --pending          # Endast väntande
```

---

## podstock guest-summary

Generera sammanfattning med fokus på gäster.

```bash
podstock guest-summary
podstock guest-summary --podcast borspodden
podstock guest-summary --output rapport.md
```

| Flag | Beskrivning |
|------|-------------|
| `--podcast` | Filter på podcast |
| `--output` | Anpassat filnamn |

---

## podstock twitter

Twitter/X-datasamling.

### add
```bash
podstock twitter add @username
podstock twitter add @user --category analyst
podstock twitter add @user --description "Beskrivning"
```

### list
```bash
podstock twitter list
```

### remove
```bash
podstock twitter remove <source_id>
```

### collect
```bash
podstock twitter collect                 # Alla aktiva källor
podstock twitter collect --source X      # Specifik källa
podstock twitter collect --max 500       # Max tweets
podstock twitter collect --full          # Hämta allt (ej inkrementell)
podstock twitter collect --all           # Inkludera inaktiva
```

### coverage
```bash
podstock twitter coverage --source <id>
```
Visa täckningsanalys för en källa.

### stats
```bash
podstock twitter stats
```

### search
```bash
podstock twitter search --query "keyword"
```

### rebuild-index
```bash
podstock twitter rebuild-index
```

### analyze
```bash
podstock twitter analyze
```

### report
```bash
podstock twitter report
```

---

## Globala flaggor

Dessa flaggor fungerar för alla kommandon:

| Flag | Beskrivning |
|------|-------------|
| `--data-dir PATH` | Anpassad data-katalog |
| `--help` | Visa hjälp |

---

## Environment Variables

| Variabel | Beskrivning |
|----------|-------------|
| `ANTHROPIC_API_KEY` | API-nyckel för Claude (krävs för extract process) |
| `TWITTER_API_KEY` | API-nyckel för twitterapi.io |

---

## Exempel-workflows

### Daglig synk
```bash
podstock sync --list broad
podstock status
```

### Veckosammanfattning
```bash
podstock summary info --from 2025-12-16 --to 2025-12-22
podstock summary prepare --from 2025-12-16 --to 2025-12-22
# Kör i Claude Code, sedan:
podstock summary save --output vecka-51.md
```

### Historisk analys
```bash
podstock download --podcast borspodden --latest 10
podstock transcribe --podcast borspodden
podstock analyze borspodden-2025-12-20-abc1
# Kopiera prompt till Claude, spara svar som svar.txt
podstock analyze borspodden-2025-12-20-abc1 --input svar.txt
podstock report --podcast borspodden
```

### AI-extraktion (batch)
```bash
export ANTHROPIC_API_KEY=sk-...
podstock extract process --max 5
podstock extract rebuild-index
podstock extract search --top 10
```
