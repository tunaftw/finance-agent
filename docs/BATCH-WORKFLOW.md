# Batch-körning Arbetsflöde

## Översikt

```
~3,000 transkript ÷ 3-4 per session = ~750-1000 sessioner
```

**Varför så få per session?** Context window fylls efter ~4 transkript.
Varje ny session = fresh context.

---

## Starta första sessionen

### 1. I OpenCode, skriv:

```
Läs docs/GLM-ANALYSIS-INSTRUCTIONS.md och börja batch-körningen.
```

### 2. GLM 4.7 kommer:
1. Läsa instruktionerna
2. Läsa completion-log.json (tom första gången)
3. Läsa transcript-queue.txt
4. Börja med de första 10 transkripten
5. STOPPA efter 10 och meddela dig

---

## Fortsätta efter stopp

### 1. Starta NY konversation i OpenCode

### 2. Skriv:

```
Fortsätt batch-körningen. Läs docs/GLM-ANALYSIS-INSTRUCTIONS.md
```

### 3. GLM 4.7 kommer:
1. Läsa completion-log.json
2. Se vilka som redan är klara
3. Fortsätta med nästa 10
4. STOPPA efter 10

---

## Övervaka progress

### Kolla antal klara:

```bash
cat data/extracted/glm-batch/completion-log.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Klara: {d[\"total_processed\"]} / 3000')"
```

### Kolla senaste:

```bash
ls -lt data/extracted/glm-batch/*.json | head -5
```

---

## Vid fel

### Om GLM 4.7 fastnar:

1. Starta ny session
2. Skriv: "Fortsätt batch-körningen"
3. Den läser completion-log och fortsätter

### Om JSON-fel upptäcks:

1. Lägg till filnamnet i `failed`-arrayen i completion-log.json
2. Fortsätt med nästa

### Om du behöver pausa:

- Bara stäng OpenCode
- Progress sparas i completion-log.json
- Återuppta när som helst

---

## Tiduppskattning

| Per session | Tid |
|-------------|-----|
| 3-4 transkript | ~10-15 min |
| Starta ny session | ~1 min |

| Totalt | Sessioner | Uppskattad tid |
|--------|-----------|----------------|
| 100 transkript | ~30 | ~6-8 timmar |
| 500 transkript | ~150 | ~30-40 timmar |
| 3000 transkript | ~900 | ~150-200 timmar |

**Tips:**
- Kör 10-20 sessioner per dag (~40-80 transkript)
- Det tar några veckor att köra allt
- Progress sparas - du kan pausa när som helst

---

## Checklista

- [ ] Första sessionen startad
- [ ] completion-log.json uppdateras
- [ ] JSON-filer sparas korrekt
- [ ] Inga sponsor-rekommendationer
- [ ] Progress ökar för varje session
