# Podcast Sync

Synka nya podcast-avsnitt (hämta transcripts, transkribera om nödvändigt).

## Argument
$ARGUMENTS - Valfritt: podcast-id, --list <list_id>, eller --latest N

## Workflow

### Steg 1: Kontrollera vad som skulle synkas
```bash
podstock sync --dry-run
```

Om en specifik podcast eller lista angetts:
```bash
podstock sync --podcast {podcast_id} --dry-run
podstock sync --list {list_id} --dry-run
```

### Steg 2: Kör sync
```bash
podstock sync --latest 1
```

Med argument:
```bash
podstock sync --podcast {podcast_id} --latest 3
podstock sync --list broad --latest 1
```

### Steg 3: Visa resultat
```bash
podstock status
```

## Exempel

Synka senaste avsnittet från alla podcasts:
```bash
podstock sync
```

Synka senaste 3 avsnitten från Börspodden:
```bash
podstock sync --podcast borspodden --latest 3
```

Synka alla podcasts i "broad"-listan:
```bash
podstock sync --list broad
```

## Transkriberingskällor

Synk försöker alltid hämta transcript i följande ordning:
1. Apple Podcasts cache (om tillgängligt)
2. Whisper-transkribering (laddar ner audio först)

Varje podcast har en `transcript_source` inställning:
- `auto` (default): Prova Apple först, fallback till Whisper
- `apple`: Endast Apple Podcasts transcripts
- `whisper`: Alltid använd Whisper-transkribering
