---
name: analyze
description: Analysera transkript (podcast/twitter/youtube) för att extrahera aktie- och crypto-rekommendationer samt investeringsinsikter. Två metoder: Claude Code (direkt i konversation) eller OpenCode/GLM-4.7 (script i separat terminal). Stödjer enskilda filer och batch-körning.
---

# Analyze Skill

Extrahera investeringsrekommendationer, crypto-omnämnanden och visdomsinsikter från transkript.

## Quick Start

1. **Visa backlog** - Visa vad som är oanalyserat per källa
2. Fråga användaren om **metod**: Claude Code eller OpenCode/GLM-4.7
3. Fråga om **källa**: Podcast, Twitter, YouTube
4. Fråga om **vad som ska extraheras**: Aktier, crypto, insights, eller allt
5. Fråga om **vilka transkript**: Enskild fil, alla oanalyserade, eller nya sedan datum
6. Kör analys och visa sammanfattning

## Batch Mode (Snabbstart)

Om användaren säger "batch", "kör alla", "analysera alla oanalyserade", "synka analyser", eller liknande - hoppa över interaktiva frågor och kör direkt:

### Workflow

1. **Visa backlog** (använd get_analysis_backlog() nedan)
2. **Fråga bekräftelse** med AskUserQuestion: "Generera kö för X oanalyserade podcast-transkript?"
3. **Generera transcript-queue.txt**
4. **Visa terminalkommando**

### Generera kö-fil

```python
from pathlib import Path

# Hitta alla transkript
transcripts = []
for podcast_dir in Path('data/podcasts/raw').iterdir():
    if podcast_dir.is_dir():
        transcripts_dir = podcast_dir / 'transcripts'
        if transcripts_dir.exists():
            transcripts.extend(transcripts_dir.glob('*.txt'))

# Hitta redan analyserade (alla platser)
analyzed = set()

# Primary: data/podcasts/analyses-v2/
analyses_v2 = Path('data/podcasts/analyses-v2')
if analyses_v2.exists():
    analyzed.update(p.stem for p in analyses_v2.glob('*.json'))

# Legacy locations
for legacy_dir in ['data/extracted/glm-batch', 'data/podcasts/analyses']:
    legacy_path = Path(legacy_dir)
    if legacy_path.exists():
        analyzed.update(p.stem for p in legacy_path.glob('*.json'))

# Filtrera oanalyserade
unanalyzed = [t for t in transcripts if t.stem not in analyzed]

# Skriv kö-fil
queue_file = Path('data/podcasts/analyses-v2/transcript-queue.txt')
queue_file.parent.mkdir(parents=True, exist_ok=True)
queue_file.write_text('\n'.join(str(t) for t in sorted(unanalyzed)))

print(f"Skrev {len(unanalyzed)} transkript till {queue_file}")
```

### Visa terminalinstruktioner

Efter kö-generering, visa:

```
================================================================================
KÖ GENERERAD
================================================================================

Transkript att analysera: {antal}
Kö-fil: data/podcasts/analyses-v2/transcript-queue.txt

Kör i separat terminal:

  cd /Users/pontus/Developer/podcast-transcriber
  bash scripts/run_glm_auto.sh

Eller Python-version:

  python3 scripts/batch_runner.py

Följ progress:

  watch -n 5 'jq ".total_processed, (.failed | length)" data/podcasts/analyses-v2/completion-log.json'

================================================================================
```

## Backlog Check (Kör FÖRST)

Visa automatiskt vad som ännu inte är analyserat:

```python
from pathlib import Path

def get_analysis_backlog():
    """Returnerar antal oanalyserade items per källa."""

    backlog = {}

    # Podcasts
    podcast_transcripts = set()
    for podcast_dir in Path('data/podcasts/raw').iterdir():
        if podcast_dir.is_dir():
            transcripts_dir = podcast_dir / 'transcripts'
            if transcripts_dir.exists():
                podcast_transcripts.update(p.stem for p in transcripts_dir.glob('*.txt'))

    # Check all analysis locations
    analyzed_podcasts = set()

    # Primary location: data/podcasts/analyses-v2/
    analyses_v2_dir = Path('data/podcasts/analyses-v2')
    if analyses_v2_dir.exists():
        analyzed_podcasts.update(p.stem for p in analyses_v2_dir.glob('*.json'))

    # Legacy locations
    for legacy_dir in ['data/extracted/glm-batch', 'data/podcasts/analyses']:
        legacy_path = Path(legacy_dir)
        if legacy_path.exists():
            analyzed_podcasts.update(p.stem for p in legacy_path.glob('*.json'))

    backlog['podcasts'] = {
        'total': len(podcast_transcripts),
        'analyzed': len(analyzed_podcasts & podcast_transcripts),
        'pending': len(podcast_transcripts - analyzed_podcasts),
        'pending_list': sorted(list(podcast_transcripts - analyzed_podcasts))[:10]
    }

    # Twitter
    twitter_handles = set()
    twitter_raw = Path('data/twitter/raw')
    if twitter_raw.exists():
        twitter_handles = set(d.name for d in twitter_raw.iterdir() if d.is_dir())

    analyzed_twitter = set()
    twitter_analyses = Path('data/twitter/analyses')
    if twitter_analyses.exists():
        analyzed_twitter = set(
            p.stem.replace('-analysis', '').replace('-tweet-analyses', '')
            for p in twitter_analyses.glob('*.json')
        )

    backlog['twitter'] = {
        'total': len(twitter_handles),
        'analyzed': len(analyzed_twitter),
        'pending': len(twitter_handles - analyzed_twitter),
        'pending_list': sorted(list(twitter_handles - analyzed_twitter))[:10]
    }

    # YouTube
    youtube_videos = set()
    youtube_raw = Path('data/youtube/raw')
    if youtube_raw.exists():
        for channel_dir in youtube_raw.iterdir():
            if channel_dir.is_dir():
                youtube_videos.update(p.stem for p in channel_dir.rglob('*.txt'))

    analyzed_youtube = set(p.stem for p in Path('data/youtube/analyses').glob('*.json'))
    backlog['youtube'] = {
        'total': len(youtube_videos),
        'analyzed': len(analyzed_youtube),
        'pending': len(youtube_videos - analyzed_youtube),
        'pending_list': sorted(list(youtube_videos - analyzed_youtube))[:10]
    }

    return backlog

# Kör och visa
backlog = get_analysis_backlog()
print("📊 ANALYS-BACKLOG")
print("=" * 40)
for source, data in backlog.items():
    pending = data['pending']
    total = data['total']
    emoji = "✅" if pending == 0 else "📋"
    print(f"{emoji} {source.upper()}: {pending} oanalyserade av {total} totalt")
    if pending > 0 and data['pending_list']:
        print(f"   Exempel: {', '.join(data['pending_list'][:3])}...")
print("=" * 40)
```

**Output-exempel:**
```
📊 ANALYS-BACKLOG
========================================
📋 PODCASTS: 15 oanalyserade av 120 totalt
   Exempel: borspodden-2025-01-20, veckanstrade-2025-01-19...
✅ TWITTER: 0 oanalyserade av 8 totalt
📋 YOUTUBE: 5 oanalyserade av 268 totalt
   Exempel: abc123, def456...
========================================
```

## Method Selection

| Metod | När använda |
|-------|-------------|
| **Claude Code** | Default. Kör direkt i konversationen. Använder Claude API-credits. |
| **OpenCode/GLM-4.7** | Script i separat terminal. Gratis med OpenCode. Bra för batch. |

## Workflow

### Step 1: Gather Requirements

Använd AskUserQuestion med följande frågor:

```
1. Analysmetod?
   - Claude Code (Recommended) - kör här, använder API-credits
   - OpenCode/GLM-4.7 - kör i separat terminal, gratis

2. Källtyp?
   - Podcast-transkript
   - Twitter-tråd
   - YouTube-transkript

3. Vad ska extraheras?
   - Aktie-rekommendationer
   - Crypto-omnämnanden
   - Investment insights
   - Allt (comprehensive)

4. Vilka transkript?
   - Specifik fil (ange sökväg eller episode_id)
   - Alla oanalyserade
   - Nya sedan [datum]
   - Specifik podcast/källa
```

### Step 2: Check Analysis Status

Kontrollera vad som redan analyserats:

```bash
# Kolla befintliga analyser
ls data/podcasts/analyses-v2/ | wc -l

# Hitta oanalyserade podcast-transkript
python -c "
from pathlib import Path
import json

analyzed = set(p.stem for p in Path('data/podcasts/analyses-v2').glob('*.json'))
transcripts = set(p.stem for p in Path('data/podcasts/raw').rglob('*.txt'))
unanalyzed = transcripts - analyzed
print(f'Analyserade: {len(analyzed)}')
print(f'Oanalyserade: {len(unanalyzed)}')
if unanalyzed:
    print('Första 5 oanalyserade:')
    for t in list(unanalyzed)[:5]:
        print(f'  - {t}')
"
```

### Step 3: Execute Analysis

**Claude Code-metod:** Se [references/claude-method.md](references/claude-method.md)

**OpenCode/GLM-4.7-metod:** Se [references/opencode-method.md](references/opencode-method.md)

### Step 4: Provide Summary

Efter analys, rapportera:
- Antal transkript analyserade
- Antal rekommendationer (buy/sell/hold/watch/avoid)
- Antal crypto-omnämnanden
- Antal insights (philosophy/lesson/wisdom)
- Sparade filer: `data/podcasts/analyses-v2/{episode_id}.json`

## Extraction Types

### Aktie-rekommendationer (stocks)
- buy, sell, hold, watch, avoid
- Konfidens: high, medium, low, speculative
- Inkluderar: citat, motivering, talare, kursmål
- **Extra alfa-fält (optional, fylls i om det nämns explicit):**
  - `position_context`: "50% av portföljen", "största positionen"
  - `downside_note`: "30% neddida", "värsta fall 50 SEK"
  - `catalyst_timing`: "Rapport 15 feb", "produktlansering Q2"

### Crypto-omnämnanden (crypto)
- BTC, ETH, SOL, och andra kryptovalutor
- Sentiment: bullish, bearish, neutral, mixed
- Inkluderar: prisnivåer, tidshorisont

### Investment Insights (insights)
- **philosophy**: Investeringsfilosofi, grundprinciper
- **lesson**: Lärdomar från misstag/erfarenheter
- **wisdom**: Marknadsvisdom, psykologi, timing

## Storage Format

Analyser sparas i JSON format:

```json
{
  "schema_version": "2.1",
  "episode_id": "borspodden-2025-01-15-abc1",
  "source_type": "podcast",
  "podcast_name": "Börspodden",
  "date": "2025-01-15",
  "hosts": ["Johan Isaksson"],
  "guests": ["Erik Gäst"],
  "recommendations": [
    {
      "stock_name": "Evolution",
      "ticker": "EVO",
      "action": "buy",
      "confidence": "high",
      "speaker": "Johan Isaksson",
      "reasoning": "Stark tillväxt och höga marginaler...",
      "quote": "Evolution är ett fantastiskt bolag...",
      "position_context": "Största positionen i portföljen",
      "downside_note": "Max 15% neddida på dessa nivåer",
      "catalyst_timing": "Rapport Q1 2025"
    }
  ],
  "crypto_mentions": [
    {
      "asset_symbol": "BTC",
      "sentiment": "bullish",
      "speaker": "Erik Gäst",
      "confidence": "medium",
      "quote": "Bitcoin ser intressant ut på dessa nivåer..."
    }
  ],
  "insights": [
    {
      "quote": "Det viktigaste jag lärt mig är att ha tålamod...",
      "summary": "Tålamod belönas av marknaden",
      "category": "philosophy",
      "speaker": "Johan Isaksson",
      "confidence": "high",
      "tags": ["patience", "long-term"]
    }
  ],
  "market_sentiment": "bullish",
  "summary": "Avsnittet fokuserade på...",
  "key_takeaways": ["punkt1", "punkt2"]
}
```

## Source Locations

| Källa | Transkript-sökväg |
|-------|-------------------|
| Podcasts | `data/podcasts/raw/{podcast_id}/transcripts/*.txt` |
| Twitter | `data/twitter/raw/{handle}/tweets.jsonl` |
| YouTube | `data/youtube/raw/{channel}/transcripts/*.txt` |

## Output Locations

| Källa | Analys-sökväg |
|-------|---------------|
| Podcast analyses | `data/podcasts/analyses-v2/{episode_id}.json` |
| Twitter analyses | `data/twitter/analyses/{handle}-analysis.json` |
| YouTube analyses | `data/youtube/analyses/{video_id}.json` |

## Cost Estimation

### Claude Code
- ~$0.05 per transkript (5000 ord genomsnitt)
- Bäst för enstaka analyser eller när snabbhet behövs

### OpenCode/GLM-4.7
- Gratis (ingår i OpenCode)
- Bäst för batch-körning av många transkript
- ~2-3 minuter per transkript

## Error Handling

| Fel | Lösning |
|-----|---------|
| `Timeout efter 180 sekunder` | Försök igen, eller använd kortare transkript |
| `Kunde inte parsa JSON` | Försök igen (max 3 försök) |
| `Validation error` | Kontrollera att alla fält finns |
| `No transcripts found` | Verifiera sökväg och filformat |
