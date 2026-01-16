# Design: Omanalysera Inkompletta 2025-2026 Analyser

## Sammanfattning

10 analysfiler från 2025-2026 saknar `stock_segments` (det fullständiga Schema 2.1). Dessa ska omanalyseras med GLM-4.7 via befintlig `glm_driver.py`.

## Scope

**Filer att omanalysera (10 st):**
- avanzapodden-2026-01-13-1a5f.json
- borsmaklarna-2026-01-13-c639.json
- borspodden-2025-02-19-66d4.json
- borspodden-2025-02-19-819f.json
- fillorkill-2026-01-13-6f41.json
- fillorkill-2026-01-13-7564.json
- globalgains-2026-01-10-44de.json
- gotttjot-2026-01-13-2db8.json
- kortochlang-2025-01-03-da7d.json
- kortochlang-2026-01-12-4fdd.json

**Exkluderad (korrekt Q&A-podd utan aktier):**
- avanzapodden-2026-01-13-b24b.json

## Design

### Nytt Script: `scripts/reanalyze_incomplete.py`

```
Användning:
  python3 scripts/reanalyze_incomplete.py           # Kör omanalys
  python3 scripts/reanalyze_incomplete.py --dry-run # Visa vad som skulle köras
  python3 scripts/reanalyze_incomplete.py --status  # Visa status
```

### Flöde

1. **Identifiera inkompletta:** Scanna `analyses-v2/` för 2025-2026 filer utan `stock_segments`
2. **För varje fil:**
   - Extrahera podcast_id och episode_id från filnamn
   - Hitta transkript: `raw/{podcast_id}/transcripts/{episode_id}.txt`
   - Backup gammal analys → `analyses-v2/backup/{filename}`
   - Kör `glm_driver.analyze_transcript()`
   - Spara ny analys (överskriver gammal)
3. **Logga resultat** till `data/extracted/glm-batch/reanalyze-log.json`

### Beroenden

```
scripts/reanalyze_incomplete.py
  └── scripts/glm_driver.py
        └── src/podstock/extract/prompt_templates.py
              └── Schema 2.1 prompt
```

### Säkerhet

- **Backup:** Alla gamla filer kopieras till `backup/` innan överskrivning
- **Dry-run:** `--dry-run` visar vad som skulle köras utan att ändra något
- **Retry:** glm_driver har 3 försök per fil
- **Completion log:** Kan återuppta vid avbrott

### Uppskattad körtid

- 10 filer × ~5 min/fil = ~50 minuter
- Kan avbrytas med Ctrl+C och återupptas

## Verifiering

Efter körning:
1. Kontrollera att alla 10 filer nu har `stock_segments`
2. Stickprova 2-3 filer för kvalitet
3. Regenerera dashboard: `podstock dashboard generate`

## Implementation

1. [ ] Skapa `scripts/reanalyze_incomplete.py`
2. [ ] Testa med `--dry-run`
3. [ ] Kör omanalys
4. [ ] Verifiera resultat
5. [ ] Regenerera dashboard
