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

### 2. Analysera

Claude läser transkriptet och extraherar direkt enligt schemat i SKILL.md
(schema_version 2.1: recommendations, crypto_mentions, insights,
market_sentiment, summary, key_takeaways).

**Talarattribution:** Transkript extraherade med `scripts/extract_ttml.py` har
`[SPEAKER_N]`-block (från Apples TTML-diarisering). Använd dessa som `speaker`
i rekommendationer/insights — de är verifierbara, till skillnad från gissade
namn. Mappa gärna talare till innehav via ägar-disclaimern i slutet av avsnittet.

**Talaridentifiering (SPEAKER_N → riktigt namn/alias):** Försök ALLTID mappa
SPEAKER_N till kända värdnamn. Kända värdar och identifieringsledtrådar finns i
`data/podcast_mapping.json` under `hosts.{podcast_id}` — kolla där först.
Bevishierarki (starkast först):

1. **Självintroduktion**: "med mig Puketrader", "jag är Lone Wolf" — inuti ett
   SPEAKER_N-block = definitiv mappning av det blocket.
2. **Tilltal**: "Vad säger du, Lone Wolf?" — talaren som SVARAR i nästa block
   är den tilltalade (inte den som frågar).
3. **Ägar-disclaimern** i slutet av avsnittet: koppla "jag äger X" per
   SPEAKER-block till kända innehav i `identification_hints`.
4. **Persona-kontinuitet**: tradingstil, portföljprofil, boendeort, återkommande
   teser (svagast — kräver flera oberoende träffar).

Skriv resultatet i analysens `speaker_mapping`-fält med bevis och konfidens:

```json
"speaker_mapping": {
  "SPEAKER_1": {"name": "Lone Wolf", "confidence": "high", "evidence": "Tilltalad 'Lone Wolf' vid [12:30], svarar i nästa block"},
  "SPEAKER_2": {"name": "Puketrader", "confidence": "medium", "evidence": "Äger Cardano enligt disclaimer, matchar identification_hints"}
}
```

Behåll `SPEAKER_N` som `speaker`-värde i recommendations/insights (verifierbart
mot transkriptet) — mappningen till namn görs i `speaker_mapping`. Vid
`confidence: high` får namn användas direkt i `speaker`-fälten. Mappa ALDRIG
utan bevis; lämna hellre `speaker_mapping` tom. Uppdatera gärna
`identification_hints` i podcast_mapping.json när nya stabila ledtrådar
upptäcks (nya innehav, flytt, etc). VARNING för falska vänner: "Phuket"/"varit
i Pucket" i Fill or Kill = ön i Thailand, inte namnet Puketrader.

### 3. Spara och validera

```python
import json
output_path = Path(f"data/podcasts/analyses-v2/{episode_id}.json")
output_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2))
# Sanity check: json.load(open(output_path)) ska fungera och ha alla toppnivåfält
```

**NOTE:** `podstock`-paketet finns i `src/podstock/` som editable install i
`.venv` — det kräver `.venv/bin/python`, INTE systemets `python3`. Vill man
använda prompt-mallar/Pydantic-validering finns
`podstock.extract.prompt_templates` och `podstock.extract.models` där.

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
