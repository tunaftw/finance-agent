# PodStock 🎙️📈

**Track stock recommendations from Swedish financial podcasts**

---

## TL;DR – Vad är detta?

PodStock är ett CLI-verktyg som:
1. **Laddar ner** podcast-avsnitt från RSS-flöden
2. **Transkriberar** ljudet med Whisper (optimerat för Apple Silicon) eller hämtar från Apple Podcasts
3. **Analyserar** transkriptet via Claude för att extrahera aktierekommendationer
4. **Genererar rapporter** i Markdown-format
5. **Real-time monitoring** – synka nya avsnitt och generera periodiska sammanfattningar

**Målet:** Mäta "signal-to-noise ratio" hos olika podcastvärdar genom att spåra deras rekommendationer mot faktiska utfall.

---

## ⚡ Snabbkommando-referens

| Vad vill du göra? | Kommando |
|-------------------|----------|
| **Listor & Organisation** | |
| Visa podcast-listor | `podstock list show` |
| Lägg till i lista | `podstock list add broad borspodden` |
| **Synkronisering** | |
| Synka nya avsnitt | `podstock sync --list broad` |
| Dry-run (visa vad som synkas) | `podstock sync --dry-run` |
| **Sammanfattningar** | |
| Förbered sammanfattning | `podstock summary prepare --from 2025-12-01 --to 2025-12-26` |
| Visa tillgänglig data | `podstock summary info --from 2025-12-01 --to 2025-12-26` |
| **Historisk analys** | |
| Lista podcasts | `podstock podcast list` |
| Ladda ner senaste | `podstock download --podcast borspodden --latest 2` |
| Transkribera | `podstock transcribe` |
| Få analysprompt | `podstock analyze <episode-id>` |
| Parsa Claude-svar | `podstock analyze <episode-id> --input svar.txt` |
| Generera rapport | `podstock report --output rapport.md` |
| Se status | `podstock status` |
| Sök aktie | `podstock extract search --stock "Novo Nordisk"` |
| Gäst-sammanfattning | `podstock guest-summary` |
| **Twitter** | |
| Lägg till källa | `podstock twitter add @username` |
| Samla tweets | `podstock twitter collect` |
| Visa statistik | `podstock twitter stats` |
| **YouTube** | |
| Lägg till kanal | `podstock youtube add <channel_url>` |
| Samla transkript | `podstock youtube collect` |
| **Crypto** | |
| Förbered batch | `podstock crypto prepare-batch --channel technicalroundup` |
| Sök prediktioner | `podstock crypto search --coin BTC` |
| Visa bias | `podstock crypto bias` |
| **Prisverifiering** | |
| Lista spårade | `podstock prices list` |
| Verifiera | `podstock prices verify --all` |
| Visa träffsäkerhet | `podstock prices accuracy` |
| **Databas** | |
| Initiera databas | `podstock db init` |
| Ladda analyser | `podstock db load` |
| Sök i databas | `podstock db search "Evolution"` |
| Beräkna avkastning | `podstock db performance update` |

---

## 🚀 Quick Start

```bash
# Clone and setup
git clone <repo>
cd podstock
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# For transcription on Apple Silicon (M1/M2/M3/M4)
pip install mlx-whisper

# List available podcasts
podstock podcast list

# Download latest episode from Börspodden
podstock download --podcast borspodden --latest 1

# Transcribe downloaded episodes
podstock transcribe --podcast borspodden

# Generate analysis prompt (copy to Claude)
podstock analyze bp-2024-12-18

# Parse Claude's response
podstock analyze bp-2024-12-18 --input response.txt

# Generate report
podstock report
```

---

## 📖 Komplett Exempel: Börspodden

Här är ett fullständigt exempel på hela arbetsflödet:

```bash
# 1. Kontrollera vilka podcasts som finns
podstock podcast list

# 2. Ladda ner de 2 senaste avsnitten från Börspodden
podstock download --podcast borspodden --latest 2

# 3. Kolla status - se vilka avsnitt som laddats ner
podstock status

# 4. Transkribera alla nedladdade avsnitt (tar ~5-10 min per timme ljud)
podstock transcribe --podcast borspodden

# 5. Generera analysprompt för ett specifikt avsnitt
#    (episode-id visas i status, t.ex. "borspodden-2024-12-20-a1b2c3")
podstock analyze borspodden-2024-12-20-a1b2c3

# 6. Kopiera prompten till Claude, få svar, spara som "svar.txt"

# 7. Parsa Claude's svar
podstock analyze borspodden-2024-12-20-a1b2c3 --input svar.txt

# 8. Generera rapport med alla extraherade rekommendationer
podstock report --output data/reports/december-2024.md
```

**Tips:** Systemet är idempotent – samma kommando kan köras flera gånger utan att duplicera arbete.

---

## 📻 Supported Podcasts

| Podcast | Hosts | Focus |
|---------|-------|-------|
| **Börspodden** | Johan Isaksson, John Skogman | Swedish small/mid caps |
| **Börsmagasinet** | Jörns Bullmarknad, Brunsås Kapital | Deep dives, value investing |
| **Market Makers** | Fabian Franzén, Niklas Aldén, Magnus Skoog | Tech & growth stocks |
| **Fill or Kill** | @Phukettrader, @2ndtrader | Trading, Scandinavian markets |
| **Gött Tjöt om Aktier** | Markus Gedda, Erik Lundberg | Small caps, iGaming |

---

## 🛠️ Requirements

- **Python 3.11+**
- **macOS with Apple Silicon** (for mlx-whisper transcription)
- **~30GB disk space** for audio files (if keeping full history)

---

## 📁 Project Structure

```
podstock/
├── src/podstock/        # Source code
│   ├── cli.py           # Command-line interface
│   ├── core/            # Config, models, state
│   ├── rss/             # RSS parsing, downloading
│   ├── transcribe/      # Whisper & Apple Podcasts integration
│   ├── analyze/         # Prompt building, result parsing
│   ├── extract/         # AI-based extraction from transcripts
│   ├── summary/         # Guest summary report generation
│   ├── report/          # Markdown report generation
│   ├── lists/           # Podcast list management (broad/niche)
│   ├── sync/            # Real-time sync orchestration
│   ├── reports/         # Summary report generation
│   ├── twitter/         # Twitter/X data collection
│   ├── youtube/         # YouTube integration
│   ├── crypto/          # Crypto sentiment analysis
│   ├── prices/          # Price tracking and verification
│   ├── filings/         # Annual report analysis (library)
│   └── db/              # SQLite database layer
├── data/                # Runtime data (gitignored)
│   ├── audio/           # Downloaded MP3 files
│   ├── transcripts/     # Transcribed text
│   ├── extracted/       # AI-extracted recommendations (JSON)
│   ├── twitter/         # Twitter sources, tweets, analyses
│   ├── youtube/         # YouTube channels, transcripts
│   ├── crypto/          # Crypto analyses, GLM batch data
│   ├── prices/          # Ticker mappings, price history
│   ├── podstock.db      # SQLite database (gitignored)
│   ├── lists.json       # Podcast list configuration
│   ├── podcasts.json    # Podcast configuration
│   ├── state.json       # Processing state
│   └── reports/         # Generated reports
│       ├── prompts/     # LLM prompts for summaries
│       └── summaries/   # Dated summary reports
├── .claude/commands/    # Claude Code skills (/sync, /summary)
├── docs/                # Documentation
└── tests/               # Test suite
```

---

## 🔧 Commands

### Podcast Management
```bash
podstock podcast list                    # List all podcasts
podstock podcast add "Name" <rss_url>    # Add new podcast
podstock podcast info <id>               # Show podcast details
```

### Download
```bash
podstock download                        # Download all new episodes
podstock download --podcast <id>         # Download from specific podcast
podstock download --latest 5             # Download latest 5 episodes
```

### Transcribe
```bash
podstock transcribe                      # Transcribe all pending
podstock transcribe --podcast <id>       # Transcribe specific podcast
podstock transcribe --episode <id>       # Transcribe single episode
```

### Analyze
```bash
podstock analyze <episode_id>            # Generate prompt for Claude
podstock analyze <id> --input <file>     # Parse Claude's response
podstock analyze <id> --force            # Re-analyze (overwrite)
```

### Report
```bash
podstock report                          # Generate full report
podstock report --since 2024-01-01       # Filter by date
podstock report --podcast <id>           # Filter by podcast
```

### Status
```bash
podstock status                          # Overview of all episodes
```

### Extract (Sökning i rekommendationer)
```bash
podstock extract rebuild-index           # Bygg sökindex från JSON-filer
podstock extract stats                   # Visa statistik
podstock extract search --stock "X"      # Sök aktie
podstock extract search --speaker "Namn" # Sök per talare
podstock extract search --top 20         # Topp 20 mest omnämnda
podstock extract search --action buy     # Alla köprekar
```

### Guest Summary (Gäst-sammanfattning)
```bash
podstock guest-summary                   # Generera full rapport
podstock guest-summary --podcast "X"     # Filtrera på podcast
podstock guest-summary --output fil.md   # Anpassat filnamn
# Sparas till: data/reports/summaries/2025-12-25-guest-summary.md
```

### List Management (Podcast-listor)
```bash
podstock list show                       # Visa alla listor
podstock list show broad                 # Visa podcasts i "broad"-listan
podstock list create mylist --type custom  # Skapa ny lista
podstock list add broad borspodden       # Lägg till podcast i lista
podstock list remove niche fillorkill    # Ta bort podcast från lista
podstock list delete mylist              # Radera lista (ej broad/niche)
```

### Sync (Real-time synkronisering)
```bash
podstock sync                            # Synka senaste avsnittet från alla
podstock sync --podcast borspodden       # Synka specifik podcast
podstock sync --list broad               # Synka alla i en lista
podstock sync --latest 3                 # Hämta senaste 3 avsnitt
podstock sync --dry-run                  # Visa vad som skulle synkas
```

### Database (SQLite frågelager)
```bash
podstock db init                         # Skapa databas
podstock db init --force                 # Återskapa databas
podstock db status                       # Visa statistik
podstock db seed-securities              # Ladda aktier från ticker_mapping
podstock db load                         # Importera podcast-analyser
podstock db load --type twitter          # Importera Twitter-analyser
podstock db search "Evolution"           # Sök rekommendationer
podstock db search --action buy          # Filtrera på köprekar
podstock db pending list                 # Visa omatchade aktier
podstock db performance update           # Beräkna avkastning
```

### Summary (Sammanfattningar)
```bash
# Förbered prompt för Claude Code
podstock summary prepare --from 2025-12-20 --to 2025-12-26

# Detaljerad analys för niche-listan
podstock summary prepare --from 2025-12-01 --to 2025-12-31 --type detailed --list niche

# Exportera för Opencode/GLM-4.7 (gratis LLM)
podstock summary prepare --from 2025-12-20 --to 2025-12-26 --opencode

# Visa tillgänglig data för period
podstock summary info --from 2025-12-20 --to 2025-12-26

# Spara färdig rapport
podstock summary save --output rapport.md
```

---

## 🔄 Workflows

### Historisk Analys (manuellt)
1. **Download** → Hämtar MP3 från RSS-flöde
2. **Transcribe** → Kör mlx-whisper lokalt (~10-15x realtime på M4)
3. **Analyze** → Genererar prompt, användaren kör i Claude, parsar resultat
4. **Report** → Skapar Markdown-sammanfattning

### Real-time Monitoring (automatiserat)
1. **Sync** → Hämtar nya avsnitt och transkriberar automatiskt
   - Provar först Apple Podcasts transcripts (gratis, snabbt)
   - Fallback till Whisper om Apple inte tillgängligt
2. **Summary** → Genererar periodiska sammanfattningar
   - Bred analys: Alla podcasts, övergripande teman
   - Detaljerad: Utvalda podcasts, djupanalys

Systemet är **idempotent** – samma kommando kan köras flera gånger utan att duplicera arbete.

### Transcript Sources
Varje podcast har en `transcript_source`-inställning:
- `auto` (default): Prova Apple först, fallback till Whisper
- `apple`: Endast Apple Podcasts transcripts
- `whisper`: Alltid använd lokal Whisper-transkribering

---

## ⚙️ Configuration

Configuration is stored in `data/config.json`:

```json
{
  "whisper_model": "large-v3",
  "default_time_horizon": "6m",
  "auto_cleanup_audio": false
}
```

---

## 🧪 Development

```bash
# Run tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=src/podstock

# Lint
ruff check src/

# Type check
mypy src/
```

---

## 📊 Future Plans (Phase 2)

- [x] ~~Automatic price data integration (Yahoo Finance)~~ ✅ Implementerad
- [x] ~~Performance tracking dashboard~~ ✅ `podstock db performance`
- [ ] Claude API integration (automated analysis)
- [ ] Web UI

---

## 📄 License

MIT

---

## 🤝 Contributing

See `IMPLEMENTATION.md` for current development status and next steps.
