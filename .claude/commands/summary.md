# Podcast Summary

Generera sammanfattning av podcast-innehåll för en tidsperiod.

## Argument
$ARGUMENTS - Datumintervall och valfritt typ (--from YYYY-MM-DD --to YYYY-MM-DD [--type broad|detailed])

## Workflow

### Alternativ 1: Claude Code (högre kvalitet, kostar tokens)

#### 1. Kontrollera tillgänglig data
```bash
podstock summary info --from {start_date} --to {end_date}
```

#### 2. Förbered prompt
```bash
podstock summary prepare --from {start_date} --to {end_date} --type broad
```

Eller för detaljerad analys:
```bash
podstock summary prepare --from {start_date} --to {end_date} --type detailed --list niche
```

#### 3. Läs den genererade prompt-filen
Filen sparas i `data/reports/prompts/`. Läs filen och analysera datan enligt instruktionerna.

#### 4. Spara rapporten
```bash
podstock summary save --output rapport.md
```

---

### Alternativ 2: Opencode/GLM-4.7 (gratis)

#### 1. Exportera för Opencode
```bash
podstock summary prepare --from {start_date} --to {end_date} --type broad --opencode
```

#### 2. Instruktioner till användaren
Öppna den genererade JSON-filen i Opencode och be:
"Läs filen och generera rapporten enligt instruktionerna"

---

## Rapporttyper

### Bred analys (`--type broad`)
- Använder "broad"-listan (alla podcasts)
- Övergripande teman
- Kortfattade rekommendationer
- Marknadssentiment

### Detaljerad analys (`--type detailed`)
- Använder "niche"-listan (utvalda podcasts)
- Utförliga citat
- Gäst-insikter
- Jämförelse mellan podcasts

## Listor

Visa tillgängliga listor:
```bash
podstock list show
```

Lägg till podcast i lista:
```bash
podstock list add broad {podcast_id}
podstock list add niche {podcast_id}
```

## Exempel

Veckosammanfattning (senaste veckan):
```bash
podstock summary prepare --from 2025-12-20 --to 2025-12-26 --type broad
```

Detaljerad månadsanalys:
```bash
podstock summary prepare --from 2025-12-01 --to 2025-12-31 --type detailed
```

Exportera för Opencode:
```bash
podstock summary prepare --from 2025-12-20 --to 2025-12-26 --type broad --opencode
```
