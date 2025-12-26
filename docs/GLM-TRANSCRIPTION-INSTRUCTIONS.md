# GLM Podcast-transkribering: Automatisk Batch-körning

## Syfte

Ladda ner och transkribera podcast-avsnitt från Börsmagasinet och Gött Tjöt om Aktier
med MLX-Whisper. Helt automatiserat - ingen manuell input krävs.

---

## VIKTIGT: Context Window-hantering

**Batch-storlek:** 1 avsnitt per session (MAX 1)
**Varför:** Transkribering tar 30-60 minuter per avsnitt
**Efter avsnittet:** Uppdatera completion-log OMEDELBART
**Efter 1 avsnitt:** STOPPA och starta ny session

⚠️ **KRITISKT:** Transkribering körs i bakgrunden medan du väntar.
Efter transkribering är klar, uppdatera log och STOPPA.

---

## Starta en session

### 1. Läs completion-log

```
Läs: data/transcripts/glm-transcription/completion-log.json
```

Kontrollera:
- Vilken `current_phase` är aktiv? (1, 2 eller 3)
- Vilka avsnitt finns i `completed`?

### 2. Läs aktuell fas-kö

Baserat på `current_phase`, läs rätt fil:
- Fas 1: `data/transcripts/glm-transcription/phase1-queue.json`
- Fas 2: `data/transcripts/glm-transcription/phase2-queue.json`
- Fas 3: `data/transcripts/glm-transcription/phase3-queue.json`

### 3. Hitta nästa avsnitt (prioritera retries)

**VIKTIGT:** Kontrollera först `failed`-arrayen i completion-log!

**Om det finns episode_id i `failed`:**
1. Ta första episode_id från `failed`
2. Ljudfilen finns redan nedladdad - hoppa direkt till steg 5 (transkribering)
3. Om transkribering lyckas: flytta från `failed` till `completed`

**Om `failed` är tom:**
Hitta det första avsnittet i kön som INTE finns i `completed`.
Om alla i fasen är klara → meddela användaren att fasen är klar.

### 4. Ladda ner avsnittet (om det inte redan finns)

**Kontrollera först om ljudfilen redan finns:**
```bash
ls -la /Users/pontus/Developer/podcast-transcriber/data/audio/{PODCAST_ID}/{EPISODE_ID}.mp3
```

**Om filen finns:** Hoppa till steg 5.

**Om filen INTE finns:** Ladda ner med audio_url från queue-filen:

```bash
cd /Users/pontus/Developer/podcast-transcriber && python3 -c "
import requests
import os

audio_url = '{AUDIO_URL}'
podcast_id = '{PODCAST_ID}'
episode_id = '{EPISODE_ID}'

os.makedirs(f'data/audio/{podcast_id}', exist_ok=True)
filepath = f'data/audio/{podcast_id}/{episode_id}.mp3'

print(f'Laddar ner till {filepath}...')
resp = requests.get(audio_url, stream=True, timeout=300)
resp.raise_for_status()
with open(filepath, 'wb') as f:
    for chunk in resp.iter_content(chunk_size=8192):
        f.write(chunk)
print('Nedladdning klar!')
"
```

Ersätt `{AUDIO_URL}`, `{PODCAST_ID}` och `{EPISODE_ID}` med värden från queue-filen.

### 5. Transkribera avsnittet

⚠️ **TIMEOUT-VARNING:** Transkribering tar 30-60 minuter.
Ange en lång timeout (3600 sekunder = 1 timme) för bash-kommandot.

Kör kommando med lång timeout:
```bash
cd /Users/pontus/Developer/podcast-transcriber && python -m podstock.cli transcribe --podcast {PODCAST_ID} --episode {EPISODE_ID}
```

**Timeout-inställning:** Sätt bash timeout till minst 3600 sekunder (1 timme).

⏱️ **Detta tar 30-60 minuter.** Vänta tills det är klart - avbryt INTE!

### 6. Verifiera transkribering

Kontrollera att transkriptet skapades:
```bash
ls -la data/transcripts/{PODCAST_ID}/
```

Läs de första raderna för att verifiera:
```bash
head -20 data/transcripts/{PODCAST_ID}/{EPISODE_ID}.txt
```

### 7. Uppdatera completion-log

Läs `completion-log.json` och uppdatera:

**Om detta var en RETRY (episode fanns i `failed`):**
1. Ta bort `episode_id` från `failed`-arrayen
2. Lägg till `episode_id` i `completed`-arrayen
3. Öka `total_processed` med 1
4. Uppdatera `last_updated`

**Om detta var ett NYTT avsnitt:**
1. Lägg till `episode_id` i `completed`-arrayen
2. Öka `total_processed` med 1
3. Uppdatera `last_updated`

Spara filen.

### 8. STOPPA

```
⚠️ SESSION COMPLETE ⚠️

Du har transkriberat 1 avsnitt i denna session.
STOPPA NU och vänta på ny session.

Progress är sparad i completion-log.json.
Nästa session: Läs dessa instruktioner igen och fortsätt.
```

---

## Queue-format (JSON)

Varje phase-queue.json har formatet:
```json
{
  "phase": 1,
  "description": "Test - 1 avsnitt per podcast",
  "episodes": [
    {
      "podcast_id": "borsmagasinet",
      "episode_id": "borsmagasinet-2025-12-17-xxxx",
      "title": "#103: Avslutar året på botten",
      "pub_date": "2025-12-17",
      "audio_url": "https://..."
    }
  ]
}
```

---

## Completion-log format

```json
{
  "current_phase": 1,
  "phases": {
    "1": {"total": 2, "description": "Test"},
    "2": {"total": 78, "description": "2025 avsnitt"},
    "3": {"total": 293, "description": "Äldre avsnitt"}
  },
  "completed": [
    "borsmagasinet-2025-12-17-xxxx"
  ],
  "failed": [],
  "total_processed": 1,
  "last_updated": "2025-12-26T14:30:00"
}
```

---

## Podcast-information

| podcast_id | Namn | RSS Feed |
|------------|------|----------|
| borsmagasinet | Börsmagasinet | https://feeds.acast.com/public/shows/borsmagasinet |
| gotttjot | Gött Tjöt om Aktier | https://feeds.acast.com/public/shows/nantingomaktier |

---

## Filstruktur

```
podcast-transcriber/
├── data/
│   ├── audio/
│   │   ├── borsmagasinet/         # Nedladdade ljudfiler
│   │   └── gotttjot/
│   └── transcripts/
│       ├── borsmagasinet/         # Färdiga transkript
│       ├── gotttjot/
│       └── glm-transcription/     # Tracking
│           ├── completion-log.json
│           ├── phase1-queue.json
│           ├── phase2-queue.json
│           └── phase3-queue.json
└── docs/
    └── GLM-TRANSCRIPTION-INSTRUCTIONS.md
```

---

## Vanliga fel att undvika

1. **Mer än 1 per session** - STOPPA efter 1 avsnitt
2. **Glömd completion-log** - Uppdatera ALLTID efter transkribering
3. **Fel podcast_id** - Använd exakt `borsmagasinet` eller `gotttjot`
4. **För kort timeout** - Sätt bash timeout till 3600s (1 timme), inte 10 min!
5. **Fel episode_id** - Kopiera exakt från queue-filen
6. **Glömmer kolla `failed`** - Retries ska prioriteras före nya avsnitt

---

## Checklista per avsnitt

- [ ] Läst completion-log
- [ ] Kollat `failed`-arrayen först (retry har prioritet!)
- [ ] Hittat nästa avsnitt i kön (eller retry)
- [ ] Kollat om ljudfil redan finns
- [ ] Laddat ner ljudfil (om den inte fanns)
- [ ] Satt bash timeout till 3600s
- [ ] Transkriberat med Whisper (30-60 min)
- [ ] Verifierat att transkript skapades
- [ ] Uppdaterat completion-log (flytta från failed om retry)
- [ ] STOPPAT sessionen

---

## Fas-övergångar

När alla avsnitt i en fas är klara:

**Efter Fas 1 (Test):**
```
✅ FAS 1 KLAR!

Båda test-avsnitten är transkriberade.
Verifiera kvaliteten på transkripten.
Användaren behöver manuellt starta Fas 2 genom att uppdatera current_phase till 2.
```

**Efter Fas 2 (2025):**
```
✅ FAS 2 KLAR!

Alla 2025-avsnitt är transkriberade.
Användaren behöver manuellt starta Fas 3 genom att uppdatera current_phase till 3.
```

**Efter Fas 3 (Äldre):**
```
✅ ALLA FASER KLARA!

Samtliga 373 avsnitt är transkriberade.
```
