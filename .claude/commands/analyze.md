# Transcript Analyze

Analysera transkript (podcast/twitter/youtube) för att extrahera aktie- och crypto-rekommendationer samt investeringsinsikter.

## Argument
$ARGUMENTS - Valfritt: source type (podcast/twitter/youtube), --backlog, eller specifik fil

## Workflow

### Steg 1: Visa Backlog (kör alltid först)

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

    analyzed_podcasts = set(p.stem for p in Path('data/extracted/glm-batch').glob('*.json'))
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

### Steg 2: Fråga användaren

Använd AskUserQuestion:
1. **Metod?** Claude Code (direkt) eller OpenCode/GLM-4.7 (separat terminal)
2. **Källa?** Podcast, Twitter, YouTube
3. **Vad extrahera?** Aktier, crypto, insights, eller allt
4. **Vilka?** Alla oanalyserade, specifik fil, eller nya sedan datum

### Steg 3: Kör analys

**Claude Code:**
Läs transkript och analysera direkt i konversationen.

**OpenCode/GLM-4.7:**
```bash
# Enskild fil
python scripts/glm_driver.py <transcript_path> data/extracted/glm-batch/

# Batch (alla oanalyserade)
bash scripts/run_glm_auto.sh
```

### Steg 4: Visa resultat

Rapportera:
- Antal transkript analyserade
- Antal rekommendationer (buy/sell/hold/watch/avoid)
- Antal crypto-mentions
- Antal insights (philosophy/lesson/wisdom)
- Extra alfa-fält fångade (position_context, downside_note, catalyst_timing)

## Extraction Types

### Stocks
- Actions: buy, sell, hold, watch, avoid
- Confidence: high, medium, low, speculative
- Extra alfa: position_context, downside_note, catalyst_timing

### Crypto
- Symbols: BTC, ETH, SOL, etc.
- Sentiment: bullish, bearish, neutral, mixed

### Insights
- Categories: philosophy, lesson, wisdom
- Confidence: high, medium, low

## Sökvägar

| Källa | Transkript | Analys |
|-------|------------|--------|
| Podcast | `data/podcasts/raw/{id}/transcripts/*.txt` | `data/extracted/glm-batch/{id}.json` |
| Twitter | `data/twitter/raw/{handle}/tweets.jsonl` | `data/twitter/analyses/{handle}-analysis.json` |
| YouTube | `data/youtube/raw/{channel}/*.txt` | `data/youtube/analyses/{video_id}.json` |

## Mer info

Se `.claude/skills/analyze/SKILL.md` för detaljerad dokumentation.
