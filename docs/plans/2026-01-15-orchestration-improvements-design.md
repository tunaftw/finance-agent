# Design: Orchestration Workflow Improvements

**Datum:** 2026-01-15
**Status:** Godkänd för implementation

## Bakgrund

Användaren vill kunna köra orchestration-skillen dagligen med felfritt resultat. Följande problem har identifierats:

1. **Saknade insights** - Nyare analyser har fel schema (`topic/insight` istället för `quote/summary/category/tags`)
2. **Engelska istället för svenska** - GLM-drivern har separat prompt, output blir inkonsekvent
3. **Ingen körningsrapport** - Svårt att se vad som hänt efter körning
4. **Ingen självläkande mekanism** - Problem upptäcks inte automatiskt

## Beslut från Brainstorming

- **Modellval:** Promptas varje gång (Claude eller GLM)
- **Prompt-arkitektur:** En gemensam prompt för båda modeller
- **Stock segments:** Ingen minimumtröskel - fånga alla aktiediskussioner
- **Förbättringsförslag:** Presenteras i slutet av varje körning
- **Förbättringstyper:** Alla (kritiska + kvalitet + optimeringar)

---

## Implementation

### Del 1: Enhetlig Prompt-Arkitektur

**Mål:** En enda prompt-källa som båda modellerna använder.

**Master-prompt baseras på GLM-prompten** (mer "matnyttighet") med tillägg:
- Few-shot exempel från Claude-prompten
- Speaker-ID guidance från Claude-prompten
- **Ingen tröskel** för stock_segments (fånga alla aktiediskussioner)

**Filändringar:**

```
src/podstock/extract/prompt_templates.py
```
- Slå ihop bästa delarna från GLM + Claude prompt
- Behåll "MAXIMAL MATNYTTIGHET" sektion
- Behåll sponsor-filter och ticker-guide
- Lägg till few-shot exempel
- Ändra ">1 min" till "alla aktiediskussioner"

```
scripts/glm_driver.py
```
- Ta bort hårdkodad prompt (rad 216-442)
- Importera från `prompt_templates.py`:
```python
from src.podstock.extract.prompt_templates import get_analysis_prompt

system_prompt, user_prompt = get_analysis_prompt(
    transcript=content,
    podcast_name=podcast_name,
    date=date,
    filename=transcript_path.name,
    podcast_id=podcast_id
)
prompt = f"{system_prompt}\n\n{user_prompt}"
```

---

### Del 2: Schema-validering och Insight-fix

**Problem:** Nyare analyser har fel insight-format.

**Lösning:** Normaliseringsfunktion som körs efter modell-response.

**Fil:** `src/podstock/extract/process_transcript.py`

```python
def normalize_insight(ins: dict) -> dict:
    """Transformera fel insight-format till korrekt v2.1 schema."""
    if "summary" not in ins and "insight" in ins:
        return {
            "quote": ins.get("insight", ""),
            "summary": ins.get("insight", ""),
            "category": "wisdom",
            "speaker": ins.get("speaker", ""),
            "speaker_role": ins.get("speaker_role", "unknown"),
            "timestamp": ins.get("timestamp"),
            "confidence": "medium",
            "tags": []
        }
    return ins

def normalize_analysis(data: dict) -> dict:
    """Normalisera hela analysen."""
    if "insights" in data:
        data["insights"] = [normalize_insight(ins) for ins in data["insights"]]
    return data
```

**Fil:** `src/podstock/dashboard/exporters.py`

Lägg till samma normalisering vid dashboard-export (rad ~489).

---

### Del 3: Körningsrapport

**Visas i terminal + sparas som markdown.**

**Ny mapp:**
```
logs/orchestration/
├── 2026-01-15T14-32-00.md
├── 2026-01-14T09-15-00.md
└── latest.md
```

**Rapport innehåller:**
- Nedladdade transkript (fil + destination)
- Analyser (fil + antal recs/segments/insights)
- Sammanfattning (totaler, nya tickers)
- Timing per steg
- Eventuella förbättringsförslag

**Implementation:**

```python
@dataclass
class OrchestrationReport:
    timestamp: datetime
    transcripts_downloaded: list[dict]  # {file, destination}
    analyses_created: list[dict]        # {file, recs, segments, insights}
    total_recommendations: int
    total_segments: int
    total_insights: int
    new_tickers: list[str]
    timing: dict[str, float]
    improvements: list[ImprovementObservation]

    def to_terminal(self) -> str:
        """Formatera för terminal-output."""
        ...

    def to_markdown(self) -> str:
        """Formatera för .md fil."""
        ...

    def save(self):
        """Spara till logs/orchestration/"""
        ...
```

---

### Del 4: Självläkande Mekanism

**Samla observationer under körning, presentera i slutet.**

**Kategorier:**
| Kategori | Exempel | Auto-fix? |
|----------|---------|-----------|
| critical | Schema-fel, trasig pipeline | Ja |
| quality | Saknade insights, dåliga citat | Ja |
| optimization | Timeout-justering, cache-miss | Ja |
| skill | Prompt kunde vara tydligare | Fråga först |

**Datastruktur:**
```python
@dataclass
class ImprovementObservation:
    category: str           # critical/quality/optimization/skill
    description: str        # Vad som observerades
    suggested_fix: str      # Föreslaget åtgärd
    file_path: str | None   # Vilken fil som berörs
    auto_fixable: bool      # Kan fixas automatiskt?
    evidence: str           # Konkret bevis/logg
```

**Flöde:**
1. Collector samlar issues under körning
2. Efter pipeline: "Jag observerade X potentiella förbättringar"
3. Lista förbättringar med kategori
4. "Vill du att jag åtgärdar dessa? [Ja/Nej/Visa detaljer]"
5. Användaren godkänner → Applicera → Logga

**Viktigt:** Inga förslag om inget finns att förbättra.

---

### Del 5: Modellval i Orchestration

**Uppdatera skill:** `.claude/skills/orchestrate-podcast-publish/SKILL.md`

**Nytt steg efter pre-flight:**
```
"X nya transkript att analysera."
"Vilken modell vill du använda?"
  [1] Claude (rekommenderas för kvalitet)
  [2] GLM-4.7 (snabbare, gratis)
```

---

### Del 6: Retroaktiv Fix

**Ny fil:** `scripts/fix_insight_schema.py`

**Funktion:**
1. Skanna `data/podcasts/analyses-v2/*.json`
2. Hitta filer med fel insight-format
3. Transformera till rätt format
4. Spara med backup (`.bak`)
5. Rapportera antal fixade

**Körs en gång efter implementation.**

---

## Filer att Ändra

| Fil | Ändring |
|-----|---------|
| `src/podstock/extract/prompt_templates.py` | Slå ihop GLM+Claude prompts, ta bort tröskel |
| `scripts/glm_driver.py` | Importera prompt istället för hårdkodad |
| `src/podstock/extract/process_transcript.py` | Lägg till `normalize_insight()` |
| `src/podstock/dashboard/exporters.py` | Lägg till schema-normalisering |
| `.claude/skills/orchestrate-podcast-publish/SKILL.md` | Modellval + körningsrapport |
| `scripts/fix_insight_schema.py` | NY - retroaktiv fix |
| `logs/orchestration/` | NY mapp för körningshistorik |

---

## Verifiering

1. **Prompt-enhetlighet:** Kör analys med Claude OCH GLM, verifiera samma output-format
2. **Schema-validering:** Kör på fil med fel insight-format, verifiera normalisering
3. **Körningsrapport:** Kör orchestration, verifiera terminal-output + sparad .md
4. **Självläkning:** Introducera ett test-problem, verifiera att det upptäcks och föreslås fix
5. **Retroaktiv fix:** Kör script, verifiera att befintliga filer fixas korrekt

---

## Nästa Steg

1. Implementera enhetlig prompt (Del 1)
2. Implementera schema-validering (Del 2)
3. Implementera körningsrapport (Del 3)
4. Implementera självläkande mekanism (Del 4)
5. Uppdatera orchestration-skill (Del 5)
6. Kör retroaktiv fix (Del 6)
7. Testa hela flödet end-to-end
