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
| **YouTube** | `podstock youtube` | YouTube-transkriptsamling |
| **Prices** | `podstock prices` | Prisverifiering och spårning |
| **Crypto** | `podstock crypto` | Krypto-sentimentanalys |
| **Database** | `podstock db` | SQLite-databas för frågor |

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

## podstock youtube

YouTube-transkriptsamling för crypto-analys.

### add
```bash
podstock youtube add <channel_url>
podstock youtube add https://youtube.com/@TechnicalRoundup --category crypto
podstock youtube add <url> --language en --description "Beskrivning"
```

| Flag | Beskrivning |
|------|-------------|
| `--category` | Kategori (t.ex. crypto, finance) |
| `--language` | Språk (default: en) |
| `--description` | Valfri beskrivning |

### list
```bash
podstock youtube list
```
Visa alla konfigurerade YouTube-kanaler med status.

### remove
```bash
podstock youtube remove <channel_id>
```

### collect
```bash
podstock youtube collect                 # Alla aktiva kanaler
podstock youtube collect --channel X     # Specifik kanal
podstock youtube collect --max 100       # Max videos per kanal
podstock youtube collect --all           # Inkludera inaktiva
```

| Flag | Beskrivning |
|------|-------------|
| `--channel ID` | Specifik kanal |
| `--max N` | Max videos per kanal (default: 50) |
| `--all` | Inkludera inaktiva kanaler |

### stats
```bash
podstock youtube stats
```
Visa statistik: kanaler, videos, transkript.

---

## podstock prices

Prisverifiering och rekommendationsspårning.

### mapping
```bash
podstock prices mapping list             # Visa alla mappningar
podstock prices mapping add "Aktie" TICK # Lägg till mapping
podstock prices mapping search "query"   # Sök mappningar
podstock prices mapping stats            # Visa statistik
```

### verify
```bash
podstock prices verify                   # Visa väntande verifieringar
podstock prices verify --all             # Verifiera alla förfallna
podstock prices verify --today           # Visa dagens priser
podstock prices verify --id <id>         # Verifiera specifik
```

| Flag | Beskrivning |
|------|-------------|
| `--all` | Verifiera alla förfallna rekommendationer |
| `--today` | Visa aktuell avkastning |
| `--id ID` | Verifiera specifik rekommendation |

### accuracy
```bash
podstock prices accuracy                 # Alla
podstock prices accuracy --podcast X     # Filter på podcast
podstock prices accuracy --speaker Y     # Filter på talare
podstock prices accuracy --action buy    # Filter på action
```

### list
```bash
podstock prices list
```
Lista alla spårade rekommendationer med senaste avkastning.

### track
```bash
podstock prices track "Aktie" buy --source "Podcast" --speaker "Namn"
podstock prices track "Aktie" sell --date 2025-01-15
```

| Flag | Beskrivning |
|------|-------------|
| `--source` | Källnamn (default: Manual) |
| `--speaker` | Talarnamn |
| `--date` | Datum YYYY-MM-DD (default: idag) |

### import
```bash
podstock prices import                   # Importera från extraktioner
podstock prices import --episode <id>    # Specifikt avsnitt
podstock prices import --podcast X       # Filter på podcast
podstock prices import --since 2025-01-01  # Från datum
podstock prices import --stock "Aktie"   # Specifik aktie
podstock prices import --action buy      # Filter på action
podstock prices import --dry-run         # Visa utan att köra
```

---

## podstock crypto

Krypto-sentimentanalys från YouTube-transkript.

### prepare-batch
```bash
podstock crypto prepare-batch --channel technicalroundup
podstock crypto prepare-batch --source youtube --all
podstock crypto prepare-batch --channel X --max 20
```

Förbereder transkript för GLM-batch-analys. Genererar instructions.md och JSON-filer.

| Flag | Beskrivning |
|------|-------------|
| `--channel ID` | Specifik YouTube-kanal |
| `--source youtube` | Källa (youtube) |
| `--all` | Alla kanaler |
| `--max N` | Max transkript |

### search
```bash
podstock crypto search --coin BTC
podstock crypto search --channel technicalroundup
podstock crypto search --action buy
podstock crypto search --top 20
```

Sök i analyserade krypto-prediktioner.

| Flag | Beskrivning |
|------|-------------|
| `--coin` | Sök på coin/token |
| `--channel` | Filter på kanal |
| `--action` | buy/sell/hold |
| `--top N` | Topp N mest omnämnda |

### predictions
```bash
podstock crypto predictions
podstock crypto predictions --coin ETH
podstock crypto predictions --channel X
```

Visa aktiva prediktioner med tidsramar.

### report
```bash
podstock crypto report
podstock crypto report --output rapport.md
```

Generera sammanfattningsrapport.

### bias
```bash
podstock crypto bias
podstock crypto bias --channel X
```

Analysera bias per kanal/influencer.

### stats
```bash
podstock crypto stats
```

Visa statistik: analyserade videos, prediktioner, täckning.

---

## podstock db

SQLite-databas för strukturerad sökning och prestanda-spårning.

### init
```bash
podstock db init                         # Skapa databas
podstock db init --force                 # Återskapa (raderar befintlig)
```

### status
```bash
podstock db status
```

Visa databasstatistik: sources, content, recommendations, securities.

### seed-securities
```bash
podstock db seed-securities
```

Ladda aktier från `ticker_mapping.json` till securities-tabellen.

### load
```bash
podstock db load                         # Ladda podcast-analyser
podstock db load --type twitter          # Ladda Twitter-analyser
podstock db load --verbose               # Visa detaljer
```

Importerar JSON-analyser till databasen. Idempotent (skippar redan laddade).

| Flag | Beskrivning |
|------|-------------|
| `--type` | `podcast` (default) eller `twitter` |
| `--verbose` | Visa detaljerad output |

### search
```bash
podstock db search "Evolution"           # Sök på aktienamn
podstock db search --ticker EVO          # Sök på ticker
podstock db search --action buy          # Filter på action
podstock db search --speaker "Johan"     # Filter på talare
podstock db search --since 2025-01-01    # Från datum
podstock db search --source borspodden   # Filter på källa
podstock db search --limit 50            # Max resultat
```

### pending
```bash
podstock db pending list                 # Visa omatchade aktier
podstock db pending list --limit 20      # Begränsa antal
```

Visa aktier som inte kunde matchas mot securities-tabellen.

### performance
```bash
podstock db performance update           # Beräkna avkastning
podstock db performance update --force   # Omberäkna alla
podstock db performance update --limit 100  # Begränsa antal
```

Beräknar avkastning (1d, 7d, 30d, 90d, 365d) för rekommendationer.

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
| `YAHOO_FINANCE_API_KEY` | API-nyckel för Yahoo Finance (optional, för premium) |

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
