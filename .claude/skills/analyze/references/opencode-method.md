# OpenCode/GLM-4.7 Method

Analysera transkript med OpenCode CLI och GLM-4.7-modellen i en separat terminal.

## Fördelar
- Gratis (ingår i OpenCode)
- Bra för batch-körning
- Kör i bakgrunden

## Nackdelar
- Kräver separat terminal
- Långsammare (~2-3 min/transkript)
- Mindre flexibel prompt-tuning

## Förutsättningar

1. OpenCode installerat: `/Users/pontus/.opencode/bin/opencode`
2. GLM-4.7 modell tillgänglig: `opencode/glm-4.7-free`

## Enskild analys

Kör i terminal:

```bash
python scripts/glm_driver.py \
  data/podcasts/raw/borspodden/transcripts/borspodden-2025-01-15.txt \
  data/extracted/glm-batch/
```

Output:
```
📝 Analyserar: borspodden-2025-01-15.txt (5,234 ord) [försök 1/3]
✅ Analys klar! Tokens: 7,500 in / 2,100 out | Rek: 4
💾 Sparade: data/extracted/glm-batch/borspodden-2025-01-15.json
```

## Batch-körning

### Automatisk batch med shell-script

```bash
# Kör automatisk batch-analys
bash scripts/run_glm_auto.sh
```

Scriptet:
- Hittar alla oanalyserade transkript
- Kör i batchar om 8 stycken
- Pausar 2 sekunder mellan batchar
- Sparar progress i `completion-log.json`

### Manuell batch

```bash
# Hitta oanalyserade
ls data/podcasts/raw/*/transcripts/*.txt | wc -l
ls data/extracted/glm-batch/*.json | wc -l

# Kör på specifika filer
for f in data/podcasts/raw/borspodden/transcripts/*.txt; do
  if [[ ! -f "data/extracted/glm-batch/$(basename ${f%.txt}).json" ]]; then
    echo "Analyserar: $f"
    python scripts/glm_driver.py "$f" data/extracted/glm-batch/
  fi
done
```

## Progress-spårning

Kolla completion-log:

```bash
cat data/extracted/glm-batch/completion-log.json | python -m json.tool
```

```json
{
  "completed": [
    "borspodden-2025-01-15.txt",
    "veckanstrade-2025-01-14.txt"
  ],
  "failed": [],
  "last_updated": "2025-01-15T10:30:00",
  "total_processed": 42
}
```

## Felhantering

### Timeout
Om analysen tar för lång tid (>180s), försöker scriptet automatiskt igen (max 3 gånger).

```
⚠️  Timeout efter 180 sekunder - försöker igen...
```

### JSON-parsning misslyckades
Om GLM returnerar ogiltig JSON, försöker scriptet igen.

```
⚠️  Kunde inte parsa JSON-respons - försöker igen...
```

### Valideringsfel
Om JSON saknar obligatoriska fält:

```
⚠️  Validation error: insights[0] missing field: category - försöker igen...
```

## Output-format

Analyserna sparas i `data/extracted/glm-batch/{episode_id}.json`:

```json
{
  "schema_version": "2.1",
  "episode_id": "borspodden-2025-01-15",
  "podcast_name": "Börspodden",
  "recommendations": [...],
  "insights": [
    {
      "quote": "Det viktigaste jag lärt mig...",
      "summary": "Tålamod belönas",
      "category": "philosophy",
      "speaker": "Johan",
      "confidence": "high",
      "tags": ["patience"]
    }
  ],
  "crypto_mentions": [
    {
      "asset_symbol": "BTC",
      "sentiment": "bullish",
      "speaker": "Erik",
      "quote": "Bitcoin ser intressant ut..."
    }
  ],
  "model_used": "glm-4.7"
}
```

## Tips

- Kör batch-analysen över natten för stora mängder
- Kolla `completion-log.json` regelbundet för progress
- Vid upprepade fel på samma fil, kolla transkriptets format
- GLM-4.7 är bra på svenska finanstermer
