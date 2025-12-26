# PodStock 🎙️📈

**Track stock recommendations from Swedish financial podcasts**

---

## TL;DR – Vad är detta?

PodStock är ett CLI-verktyg som:
1. **Laddar ner** podcast-avsnitt från RSS-flöden
2. **Transkriberar** ljudet med Whisper (optimerat för Apple Silicon)
3. **Analyserar** transkriptet via Claude för att extrahera aktierekommendationer
4. **Genererar rapporter** i Markdown-format

**Målet:** Mäta "signal-to-noise ratio" hos olika podcastvärdar genom att spåra deras rekommendationer mot faktiska utfall.

---

## ⚡ Snabbkommando-referens

| Vad vill du göra? | Kommando |
|-------------------|----------|
| Lista podcasts | `podstock podcast list` |
| Ladda ner senaste | `podstock download --podcast borspodden --latest 2` |
| Transkribera | `podstock transcribe` |
| Få analysprompt | `podstock analyze <episode-id>` |
| Parsa Claude-svar | `podstock analyze <episode-id> --input svar.txt` |
| Generera rapport | `podstock report --output rapport.md` |
| Se status | `podstock status` |
| Sök aktie | `podstock extract search --stock "Novo Nordisk"` |
| Gäst-sammanfattning | `podstock guest-summary` |

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
│   ├── transcribe/      # Whisper integration
│   ├── analyze/         # Prompt building, result parsing
│   ├── extract/         # AI-based extraction from transcripts
│   ├── summary/         # Guest summary report generation
│   └── report/          # Markdown report generation
├── data/                # Runtime data (gitignored)
│   ├── audio/           # Downloaded MP3 files
│   ├── transcripts/     # Transcribed text
│   ├── extracted/       # AI-extracted recommendations (JSON)
│   └── reports/         # Generated reports
│       └── summaries/   # Dated guest summary reports
├── prompts/             # Claude prompt templates
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

---

## 🔄 Workflow

1. **Download** → Fetches MP3 from RSS feed
2. **Transcribe** → Runs mlx-whisper locally (~10-15x realtime on M4)
3. **Analyze** → Generates prompt, user runs in Claude, parses result
4. **Report** → Creates Markdown summary of recommendations

The system is **idempotent** – running the same command twice won't duplicate work.

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

- [ ] Automatic price data integration (Yahoo Finance)
- [ ] Performance tracking dashboard
- [ ] Claude API integration (automated analysis)
- [ ] Web UI

---

## 📄 License

MIT

---

## 🤝 Contributing

See `IMPLEMENTATION.md` for current development status and next steps.
