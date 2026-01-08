# Claude Code Method

Analysera transkript direkt i Claude Code-konversationen.

## Fördelar
- Snabbt och interaktivt
- Kan ställa följdfrågor
- Ingen extra terminal behövs

## Nackdelar
- Kostar Claude API-credits (~$0.05/transkript)
- Långsammare för batch-körning

## Workflow

### 1. Läs transkriptet

```python
# Läs transkriptet
transcript_path = Path("data/podcasts/raw/{podcast_id}/transcripts/{episode_id}.txt")
content = transcript_path.read_text(encoding="utf-8")
word_count = len(content.split())
print(f"Transkript: {word_count} ord")
```

### 2. Bygg prompt

Använd extract-modulens prompt-template:

```python
from podstock.extract.prompt_templates import build_comprehensive_prompt

prompt = build_comprehensive_prompt(
    transcript_content=content,
    episode_id=episode_id,
    extract_types=["stocks", "crypto", "insights"]
)
```

### 3. Analysera

Skicka till Claude och parsa JSON-responsen:

```python
# Claude Code analyserar direkt
# Resultatet sparas i:
output_path = Path(f"data/podcasts/analyses-v2/{episode_id}.json")
```

### 4. Validera och spara

```python
from podstock.extract.models import EpisodeAnalysis

# Validera med Pydantic
analysis = EpisodeAnalysis(**result_json)

# Spara
output_path.write_text(
    analysis.model_dump_json(indent=2),
    encoding="utf-8"
)
```

## Exempel: Analysera enstaka transkript

```
Användare: /analyze
Claude: [frågar om metod -> Claude Code]
Claude: [frågar om källa -> podcast]
Claude: [frågar om vad -> allt]
Claude: [frågar om fil -> data/podcasts/raw/borspodden/transcripts/borspodden-2025-01-15.txt]

Claude: Analyserar transkript...
  📖 Läser: borspodden-2025-01-15.txt (5,234 ord)
  🔍 Extraherar: aktier, crypto, insights
  ✅ Klar!

  Resultat:
  - 4 aktierekommendationer (2 buy, 1 hold, 1 watch)
  - 1 crypto-omnämnande (BTC - bullish)
  - 3 insights (1 philosophy, 2 lesson)

  Sparad: data/podcasts/analyses-v2/borspodden-2025-01-15.json
```

## Batch-körning med Claude Code

För att analysera flera transkript i följd:

```python
from pathlib import Path

transcripts_dir = Path("data/podcasts/raw/borspodden/transcripts")
output_dir = Path("data/podcasts/analyses-v2")
output_dir.mkdir(parents=True, exist_ok=True)

# Hitta oanalyserade
analyzed = set(p.stem for p in output_dir.glob("*.json"))
pending = [p for p in transcripts_dir.glob("*.txt") if p.stem not in analyzed]

print(f"Oanalyserade: {len(pending)}")
for i, transcript in enumerate(pending[:5], 1):  # Max 5 åt gången
    print(f"[{i}/{min(5, len(pending))}] {transcript.name}")
    # Analysera här...
```

## Tips

- Börja med 1-2 transkript för att verifiera att allt fungerar
- Kolla att insights inte överlappar med recommendations
- Verifiera att crypto_mentions bara inkluderar faktiska kryptovalutor
