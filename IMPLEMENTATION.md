# PodStock – Implementation Checklist

**Version:** 1.0
**Senast uppdaterad:** 2024-12-21
**Status:** 🟢 Phase 1-6 Complete (MVP Ready)

---

## Instruktioner

Detta dokument är den **primära arbetslistan** för implementationen. Claude Code ska:

1. **Uppdatera detta dokument** efter varje genomförd uppgift
2. **Checka av** (`[x]`) när något är klart
3. **Lägga till datum och commit-referens** där tillämpligt
4. **Notera blockers eller frågor** i respektive sektion

### Statusindikering
- 🔴 Not Started
- 🟡 In Progress  
- 🟢 Complete
- ⏸️ Blocked
- ⏭️ Skipped (with reason)

---

## Phase 0: Project Setup 🟢

### P0.1 Repository Structure 🟢
- [x] Skapa projektmapp `podstock/`
- [x] Initiera git repository
- [x] Skapa `.gitignore` med Python-defaults + `data/`
- [x] Skapa `pyproject.toml` med projektmetadata
- [x] Skapa `requirements.txt`
- [x] Skapa `README.md` (basic) - fanns redan
- [x] Skapa mappstruktur enligt ARCHITECTURE.md

**Datum klart:** 2024-12-21
**Noteringar:** Komplett mappstruktur skapad med src/podstock/, tests/, prompts/, data/

### P0.2 Development Environment 🟢
- [x] Verifiera Python 3.11+ installerat (Python 3.11.14 via Homebrew)
- [x] Skapa virtual environment (.venv/)
- [x] Installera dependencies (feedparser, requests, pydantic, rich, pytest, ruff, mypy)
- [x] Verifiera mlx-whisper fungerar på M4
- [x] Konfigurera ruff för linting (i pyproject.toml)
- [x] Konfigurera mypy för type checking (i pyproject.toml)

**Datum klart:** 2024-12-21
**Noteringar:** Homebrew + Python 3.11.14 installerat. mlx-whisper 0.4.3 fungerar. Projektet installerat i utvecklingsläge.

### P0.3 Data Directory Setup 🟢
- [x] Skapa `data/` mappstruktur
- [x] Skapa `data/podcasts.json` med initiala podcasts (5 podcasts)
- [x] Skapa `data/config.json` med defaults
- [x] Skapa `data/state.json` (tom initial)

**Datum klart:** 2024-12-21
**Noteringar:** Alla 5 podcasts från PRD inkluderade. Prompt template kopierad till prompts/.

---

## Phase 1: Core Infrastructure 🟢

### P1.1 Data Models (`src/podstock/core/models.py`) 🟢
- [x] Implementera `Podcast` model
- [x] Implementera `Episode` model
- [x] Implementera `Recommendation` model
- [x] Implementera `EpisodeStatus` model
- [x] Lägg till validering via Pydantic
- [x] Skriv enhetstester för models (28 tester)

**Datum klart:** 2024-12-21
**Noteringar:** Alla modeller med full Pydantic-validering. Inkluderar PodcastsFile och StateFile för filscheman.

### P1.2 Configuration (`src/podstock/core/config.py`) 🟢
- [x] Implementera `Config` dataclass
- [x] Implementera `load_config()` funktion
- [x] Implementera `save_config()` funktion
- [x] Hantera default-värden
- [x] Hantera saknad config-fil (skapa default)
- [x] Skriv enhetstester (11 tester)

**Datum klart:** 2024-12-21
**Noteringar:** Atomisk write implementerad. Convenience properties för alla directories.

### P1.3 State Management (`src/podstock/core/state.py`) 🟢
- [x] Implementera `State` class
- [x] Implementera `load_state()`
- [x] Implementera `save_state()` (atomisk write)
- [x] Implementera `is_downloaded()`
- [x] Implementera `is_transcribed()`
- [x] Implementera `is_analyzed()`
- [x] Implementera `mark_downloaded()`
- [x] Implementera `mark_transcribed()`
- [x] Implementera `mark_analyzed()`
- [x] Skriv enhetstester (13 tester)

**Datum klart:** 2024-12-21
**Noteringar:** Inkluderar get_pending_transcription() och get_pending_analysis() för bulk-queries.

### P1.4 Exception Hierarchy (`src/podstock/core/exceptions.py`) 🟢
- [x] Definiera `PodStockError` base class
- [x] Definiera `ConfigError`
- [x] Definiera `RSSError`
- [x] Definiera `DownloadError`
- [x] Definiera `TranscribeError`
- [x] Definiera `AnalysisError`
- [x] Definiera `StateError` (extra)

**Datum klart:** 2024-12-21
**Noteringar:** La till StateError för state-specifika fel.

---

## Phase 2: RSS & Download 🟢

### P2.1 RSS Parser (`src/podstock/rss/parser.py`) 🟢
- [x] Implementera `fetch_feed(url)` → Feed
- [x] Implementera `parse_episode(item)` → Episode
- [x] Implementera `get_all_episodes(url)` → list[Episode]
- [x] Implementera `get_latest_episodes(url, n)` → list[Episode]
- [x] Hantera olika RSS-format (Libsyn vs Acast)
- [x] Robust error handling (timeout, invalid XML)
- [x] Skriv enhetstester med fixtures (24 tester)

**Datum klart:** 2024-12-21
**Noteringar:** Stöder enclosures och media:content. Duration-parsing för HH:MM:SS, MM:SS och sekunder.

### P2.2 Downloader (`src/podstock/rss/downloader.py`) 🟢
- [x] Implementera `download_episode(episode, dest_dir)` → Path
- [x] Implementera progress bar (rich)
- [x] Hantera resumed downloads (Range headers)
- [x] Verifiera filstorlek efter nedladdning
- [x] Hantera nätverksfel med retry (3x default)
- [x] Skriv integrationstester (11 tester)

**Datum klart:** 2024-12-21
**Noteringar:** Rich progress bar med hastighet och ETA. Atomisk write med temp-fil.

### P2.3 Podcast Manager (`src/podstock/rss/manager.py`) 🟢
- [x] Implementera `load_podcasts()` → list[Podcast]
- [x] Implementera `save_podcasts()`
- [x] Implementera `add_podcast(name, url)`
- [x] Implementera `remove_podcast(id)`
- [x] Implementera `get_podcast(id)` → Podcast
- [x] Validera RSS-URL vid tillägg
- [x] Extra: `update_podcast()`, `get_active_podcasts()`, `fetch_podcast_info()`

**Datum klart:** 2024-12-21
**Noteringar:** Auto-genererar slug-ID från namn. Stöder svenska tecken (å, ä, ö).

---

## Phase 3: Transcription 🟢

### P3.1 Whisper Integration (`src/podstock/transcribe/whisper.py`) 🟢
- [x] Implementera `transcribe(audio_path, model)` → str
- [x] Implementera `get_available_models()` → list[str]
- [x] Implementera progress/status callback
- [x] Hantera olika ljudformat (mp3, m4a)
- [x] Optimera för M4 (mlx-whisper)
- [x] Skriv enhetstester (14 tester)

**Datum klart:** 2024-12-21
**Noteringar:** Stöder alla whisper-modeller (tiny till large-v3). Progress callback för status. Fallback duration estimation från filstorlek.

### P3.2 Transcript Storage 🟢
- [x] Implementera `save_transcript(episode_id, text, path)`
- [x] Implementera `load_transcript(episode_id)` → str
- [x] Hantera encoding (UTF-8)
- [x] Inkludera metadata i transkript-fil (header)

**Datum klart:** 2024-12-21
**Noteringar:** Atomisk write. Header med episode-id, podcast-id och valfri metadata. Automatisk parsing av header vid load.

---

## Phase 4: Analysis 🟢

### P4.1 Prompt Builder (`src/podstock/analyze/prompt_builder.py`) 🟢
- [x] Implementera `build_analysis_prompt(transcript, metadata)` → str
- [x] Ladda template från `prompts/analyze_transcript.md`
- [x] Hantera för långa transkript (chunking)
- [x] Inkludera kontext (podcast, hosts, datum)

**Datum klart:** 2024-12-21
**Noteringar:** Template-baserad med placeholders. chunk_transcript() för långa avsnitt med overlap. build_summary_prompt() för deduplicering.

### P4.2 Result Parser (`src/podstock/analyze/result_parser.py`) 🟢
- [x] Implementera `parse_claude_response(response)` → list[Recommendation]
- [x] Hantera JSON-format från Claude
- [x] Validera parsed data mot Recommendation model
- [x] Robust mot oväntade format
- [x] Skriv enhetstester med exempel-responses (24 tester)

**Datum klart:** 2024-12-21
**Noteringar:** Extraherar JSON från markdown code blocks. save_recommendations() och load_recommendations() för persistens.

### P4.3 Prompt Template (`prompts/analyze_transcript.md`) 🟢
- [x] Skapa initial prompt template
- [x] Inkludera tydliga instruktioner för output-format
- [x] Inkludera exempel på vad som är/inte är köprek
- [ ] Testa med verkligt transkript (Phase 8)
- [ ] Iterera baserat på kvalitet (Phase 8)

**Datum klart:** 2024-12-21
**Noteringar:** Prompt template skapad. Full testning i Phase 8.

---

## Phase 5: Reporting 🟢

### P5.1 Markdown Reporter (`src/podstock/report/markdown.py`) 🟢
- [x] Implementera `generate_report(recommendations, output_path)`
- [x] Gruppera per podcast
- [x] Sortera kronologiskt
- [x] Inkludera metadata (genererat datum, antal recs)
- [x] Formatera snyggt med tabeller

**Datum klart:** 2024-12-21
**Noteringar:** generate_report(), save_report(), generate_and_save_report(). Confidence badges med emojis. Gruppering per podcast optional.

### P5.2 Statistics 🟢
- [x] Implementera `calculate_stats(recommendations)` → ReportStats
- [x] Räkna antal per podcast
- [x] Räkna antal per bolag
- [x] Visa tidsfördelning (date_range)
- [x] Skriv enhetstester (16 tester)

**Datum klart:** 2024-12-21
**Noteringar:** ReportStats dataclass med by_podcast, by_company, by_confidence och date_range.

---

## Phase 6: CLI 🟢

### P6.1 CLI Framework (`src/podstock/cli.py`) 🟢
- [x] Sätt upp argparse med subcommands
- [x] Implementera global `--verbose` flag
- [x] Implementera global `--data-dir` override
- [x] Snygga terminal-output med rich

**Datum klart:** 2024-12-21
**Noteringar:** Rich Console för output. Tabeller för listor. Status spinner för async operationer.

### P6.2 Podcast Commands 🟢
- [x] `podstock podcast add <name> <url>`
- [x] `podstock podcast list`
- [x] `podstock podcast remove <id>`
- [x] `podstock podcast info <id>`

**Datum klart:** 2024-12-21
**Noteringar:** add stöder --skip-validation. list visar tabell med hosts och active status.

### P6.3 Download Commands 🟢
- [x] `podstock download` (alla nya)
- [x] `podstock download --podcast <id>`
- [x] `podstock download --latest <n>`
- [x] `podstock download --force` (re-download)
- [x] Visa progress och summary

**Datum klart:** 2024-12-21
**Noteringar:** Progress bar per episode. Summary av totalt nedladdat.

### P6.4 Transcribe Commands 🟢
- [x] `podstock transcribe` (alla nedladdade)
- [x] `podstock transcribe --podcast <id>`
- [x] `podstock transcribe --episode <id>`
- [x] `podstock transcribe --model <model>`
- [x] `podstock transcribe --force` (re-transcribe)

**Datum klart:** 2024-12-21
**Noteringar:** Status output via progress_callback. Automatisk model-default från config.

### P6.5 Analyze Commands 🟢
- [x] `podstock analyze <episode_id>` → print prompt
- [x] `podstock analyze <episode_id> --input <file>` → parse result
- [ ] `podstock analyze --interactive` (framtida)

**Datum klart:** 2024-12-21
**Noteringar:** Workflow: kör utan --input för prompt, kopiera till Claude, spara svar i fil, kör med --input för att parsa.

### P6.6 Report Commands 🟢
- [x] `podstock report` → generate to stdout
- [x] `podstock report --output <file>`
- [x] `podstock report --podcast <id>`

**Datum klart:** 2024-12-21
**Noteringar:** Genererar markdown med all statistik och detaljer.

### P6.7 Status Command 🟢
- [x] `podstock status` → overview table
- [x] Visa per podcast: downloaded/transcribed/analyzed counts
- [x] Visa pending work

**Datum klart:** 2024-12-21
**Noteringar:** Rich table med räkningar. Pending transcription/analysis visas separat.

---

## Phase 7: Testing & Polish 🔴

### P7.1 Unit Tests
- [ ] >80% coverage på core/
- [ ] >80% coverage på rss/
- [ ] >80% coverage på analyze/
- [ ] Alla edge cases täckta

**Datum klart:** ___  
**Noteringar:** ___

### P7.2 Integration Tests
- [ ] Full download → transcribe → analyze flow
- [ ] Test med verklig podcast (1 avsnitt)
- [ ] Test av state persistence

**Datum klart:** ___  
**Noteringar:** ___

### P7.3 Documentation
- [ ] Komplett README med examples
- [ ] Docstrings på alla publika funktioner
- [ ] CHANGELOG.md

**Datum klart:** ___  
**Noteringar:** ___

### P7.4 Error Messages
- [ ] Alla fel har actionable messages
- [ ] Suggestions för vanliga problem
- [ ] Help text är tydlig

**Datum klart:** ___  
**Noteringar:** ___

---

## Phase 8: End-to-End Validation 🔴

### P8.1 Full Pipeline Test
- [ ] Ladda ner 1 avsnitt från varje podcast
- [ ] Transkribera alla 5
- [ ] Analysera alla 5
- [ ] Generera rapport
- [ ] Manuell validering av kvalitet

**Datum klart:** ___  
**Noteringar:** ___

### P8.2 Performance Validation
- [ ] Bekräfta ~10-15x realtime transcription
- [ ] Bekräfta rimlig minneanvändning
- [ ] Bekräfta stabil körning

**Datum klart:** ___  
**Noteringar:** ___

---

## Blockers & Open Questions

| ID | Beskrivning | Status | Lösning |
|----|-------------|--------|---------|
| B1 | ~~Python 3.11+ krävs~~ | ✅ Löst | Homebrew + Python 3.11.14 installerat |
| Q1 | | | |

---

## Change Log

| Datum | Ändring | Av |
|-------|---------|-----|
| 2024-12-21 | Initial version | Claude |
| 2024-12-21 | Phase 0.1 & 0.3 complete. P0.2 blocked on Python version. | Claude Code |
| 2024-12-21 | Phase 0 COMPLETE. Homebrew, Python 3.11.14, mlx-whisper installerat. | Claude Code |
| 2024-12-21 | Phase 1 COMPLETE. Core infrastructure: models, config, state, exceptions. 41 tester passerar. | Claude Code |
| 2024-12-21 | Phase 2 COMPLETE. RSS parser, downloader med progress, podcast manager. 96 tester passerar. | Claude Code |
| 2024-12-21 | Phase 3-6 COMPLETE. Transkribering, analys, rapporter och CLI. 188 tester passerar. MVP Ready! | Claude Code |
