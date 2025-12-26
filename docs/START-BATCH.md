# STARTA BATCH-KÖRNING

## ETT KOMMANDO

```bash
cd /Users/pontus/Developer/podcast-transcriber && python3 scripts/batch_runner.py
```

**Det är allt.** Scriptet:
- Hittar automatiskt nästa obehandlade transkript
- Analyserar med GLM-4.7
- Sparar resultat till `data/extracted/glm-batch/`
- Uppdaterar progress i `completion-log.json`
- Fortsätter tills alla ~3000 är klara

---

## STOPPA OCH ÅTERUPPTA

**Stoppa:** `Ctrl+C`

**Återuppta:** Kör samma kommando igen - scriptet fortsätter där det slutade.

---

## KOLLA PROGRESS

```bash
cat data/extracted/glm-batch/completion-log.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Klara: {d[\"total_processed\"]} / 3058')"
```

---

## OM DET KRÅNGLAR

1. **Timeout?** Vänta, stora transkript tar 2-3 minuter
2. **JSON-fel?** Scriptet försöker 3 gånger automatiskt
3. **Vill pausa?** Ctrl+C - progress är sparat

---

## KÖR I BAKGRUNDEN (OPTIONAL)

```bash
cd /Users/pontus/Developer/podcast-transcriber
nohup python3 scripts/batch_runner.py > batch.log 2>&1 &
tail -f batch.log  # Följ progress
```
