---
model: opus
description: Interview me about a spec/plan file to build a detailed specification through exhaustive questioning (40-75 questions)
---

# Interview

Läs spec-filen och intervjua mig på djupet med AskUserQuestion för att bygga en gedigen, välgenomtänkt specifikation.

## Argument
$ARGUMENTS - Sökväg till spec/plan-fil (t.ex. SPEC.md, plan.md)

## Workflow

### Steg 1: Läs spec-filen
Läs filen som anges i $ARGUMENTS. Om ingen fil anges, sök efter SPEC.md i projektroten.

### Steg 2: Analysera och förbered frågor
Identifiera:
- Oklarheter i teknisk implementation
- UI/UX-beslut som behöver tas
- Tradeoffs och kompromisser
- Risker och bekymmer
- Edge cases som inte är specificerade
- Arkitekturella val

### Steg 3: Uttömmande intervju med AskUserQuestion

Använd AskUserQuestion för att ställa **icke-uppenbara, djupgående** frågor.

**Intervju-filosofi:**
- Var UTTÖMMANDE - fortsätt tills VARJE aspekt är täckt
- Typiskt 40-75 frågor för komplexa features
- Varje svar kan generera 2-3 följdfrågor
- Sluta INTE förrän du verkligen inte kan komma på fler relevanta frågor

**Kategorier att systematiskt täcka:**

1. **Scope & Avgränsning**
   - Vad ingår? Vad ingår INTE?
   - Vad är MVP vs nice-to-have?
   - Vilka antaganden gör vi?

2. **Användarupplevelse (UX)**
   - Hur upptäcker användaren denna funktion?
   - Vad är det förväntade flödet?
   - Hur hanteras fel synligt för användaren?
   - Vad händer vid timeout/slow response?

3. **Teknisk arkitektur**
   - Var bor denna logik? (frontend/backend/databas)
   - Vilka befintliga komponenter påverkas?
   - Vilka nya abstraktioner behövs?
   - Hur integrerar det med existerande kod?

4. **Data & State**
   - Vilken data behövs? Var kommer den ifrån?
   - Hur persisteras state?
   - Vad händer vid data-migrering?
   - Cache-strategi?

5. **Edge cases & Felhantering**
   - Vad händer om [X] misslyckas?
   - Hur hanteras concurrent requests?
   - Vad om data är inkonsistent?
   - Rollback-strategi?

6. **Säkerhet & Privacy**
   - Autentisering/auktorisering?
   - Vilken data är känslig?
   - Audit logging?

7. **Prestanda & Skalbarhet**
   - Förväntad last?
   - Vad är acceptable latency?
   - Hur skalar det?

8. **Testbarhet**
   - Hur verifierar vi att det fungerar?
   - Vilka testfall är kritiska?
   - Mocking-strategi?

9. **Deployment & Operations**
   - Feature flags?
   - Rollout-strategi?
   - Monitoring/alerting?

10. **Tradeoffs & Beslut**
    - Var finns val mellan alternativ A vs B?
    - Vad offrar vi för enkelhet?
    - Teknisk skuld vi accepterar?

**Progress-tracking:**
- Håll räkning på antal ställda frågor
- Visa progress: "Fråga 15-18 av ~50 (täckt: Scope, UX, Arkitektur. Kvar: Data, Edge cases, Säkerhet...)"
- Ge användaren möjlighet att säga "hoppa över denna kategori" eller "tillräckligt, skriv specen"

**Per omgång:**
- 3-4 frågor är lagom (mer blir överväldigande)
- Varje fråga ska ha konkreta alternativ med för/nackdelar
- Frågor ska INTE vara uppenbara

**Exempel på bra frågor:**
- "Scenario: Användaren har dålig uppkoppling och submittar samma form två gånger. Ska vi [A] blocka duplicates på frontend, [B] hantera idempotency på backend, eller [C] acceptera duplicates och låta användaren ta bort?"
- "Du nämnde X, men hur interagerar det med Y i fall Z?"
- "Om vi väljer [arkitektur A], offrar vi [fördel B]. Är det acceptabelt?"

**Undvik uppenbara frågor som:**
- "Vill du ha det snabbt eller korrekt?"
- "Ska vi använda TypeScript?" (ja/nej utan kontext)

**Föredra frågor som:**
- "Med tanke på att X, hur vill du hantera Y när Z inträffar?"
- "Scenario: [beskrivning]. Ska systemet [A] eller [B]?"
- "Du nämnde X, men hur interagerar det med Y i fall Z?"

### Steg 4: Sammanfatta och skriv spec

När intervjun är klar (alla kategorier täckta eller användaren säger "skriv specen"):

1. Sammanfatta alla beslut som tagits
2. Skriv en detaljerad spec till `{original_filename}-detailed.md`
3. Spec ska inkludera:
   - Alla krav (funktionella och icke-funktionella)
   - Tekniska beslut med motivering
   - Edge cases och hur de hanteras
   - Acceptanskriterier
   - Implementation notes
   - Lista på frågor som ställdes och svar

## Användning

```bash
/interview SPEC.md
/interview docs/feature-plan.md
```

## Output

- Original-filen bevaras oförändrad
- Ny fil skapas: `{original_filename}-detailed.md`
- Kan köra flera gånger för att iterera vidare
