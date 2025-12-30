# Claude Code Method

Analysera filings direkt i Claude Code-konversationen.

## Fordelar
- Snabbt och interaktivt
- Kan stalla foldfragor
- Ingen extra terminal behovs
- Hog kvalitet med Claude Sonnet/Opus

## Nackdelar
- Kostar Claude API-credits (~$0.10-0.50/filing)
- Langsammare for batch-korning

## Workflow

### 1. Las filingen

```python
from pathlib import Path

filing_path = Path("data/filings/extracted/{company}/{filing_id}.md")
content = filing_path.read_text(encoding="utf-8")
word_count = len(content.split())
print(f"Filing: {word_count} ord")
```

### 2. Extrahera sektioner

Anvand section finder utilities:

```python
from podstock.filings.analysis.ceo_letter import find_ceo_letter_section
from podstock.filings.analysis.deep_analysis import (
    find_mda_section,
    find_risk_factors_section,
    find_guidance_section,
    find_segment_section,
)

ceo_section = find_ceo_letter_section(content)
mda_section = find_mda_section(content)
risk_section = find_risk_factors_section(content)
guidance_section = find_guidance_section(content)
segment_section = find_segment_section(content)

print(f"CEO Letter: {len(ceo_section.split()) if ceo_section else 0} ord")
print(f"MD&A: {len(mda_section.split()) if mda_section else 0} ord")
print(f"Risk Factors: {len(risk_section.split()) if risk_section else 0} ord")
print(f"Guidance: {len(guidance_section.split()) if guidance_section else 0} ord")
print(f"Segments: {len(segment_section.split()) if segment_section else 0} ord")
```

### 3. Analysera varje sektion

Claude Code analyserar direkt i konversationen. For varje sektion:

#### CEO Letter Analysis

Analysera CEO-brevet med fokus pa:
- **Ton**: optimistic | cautiously_optimistic | neutral | cautious | defensive
- **Konfidensgrad**: high | medium | low
- **Loften**: Specifika, trackbara ataganden med mal och tidsram
- **Teman**: Strategiska teman med betoningsgrad
- **Utmaningar**: Hur de addresseras (extern vs intern attribution)
- **Arlighetssignaler**: Indikatorer pa transparent kommunikation
- **Nyckelcitat**: 2-3 citat som fangar essensen

#### MD&A Analysis

- Nyckelnarrativ (vilken historia berattar ledningen?)
- Ledningens tolkning av resultaten
- Segmentkommentarer
- Operativa highlights
- Namnda bekymmer

#### Risk Factors

- Nya risker
- Andrade risker (eskalerade eller nedtonade)
- Borttagna risker
- Boilerplate-andel (generiska vs specifika)
- Topp-riskkategorier

#### Guidance

- Specifika mal (metric, value, period)
- Jamforelse mot tidigare (raised | maintained | lowered)
- Ledningens konfidensgrad

#### Segments

For varje affaromrade:
- Revenue och tillvaxt
- Operativ marginal
- Ledningens fokus och outlook

### 4. Strukturera output

Bygg JSON-struktur enligt output-schema:

```python
import json
from datetime import datetime
from pathlib import Path

analysis = {
    "filing_id": "getinge-annual-2024",
    "company_id": "getinge",
    "filing_type": "annual",
    "fiscal_year": 2024,
    "fiscal_quarter": None,
    "analyzed_at": datetime.now().isoformat(),
    "model_used": "claude-sonnet-4-20250514",

    "ceo_letter": {
        "author": "...",
        "title": "CEO",
        "word_count": 1850,
        "tone": "cautiously_optimistic",
        "confidence_level": "medium",
        "promises": [...],
        "themes": [...],
        "challenges": [...],
        "honesty_signals": [...],
        "key_quotes": [...]
    },

    "mda_analysis": {...},
    "risk_factors": {...},
    "guidance": {...},
    "segments": [...],
    "executive_summary": "...",
    "key_highlights": [...]
}

# Spara
output_dir = Path("data/filings/analysis/getinge")
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / "getinge-annual-2024.json"
output_path.write_text(json.dumps(analysis, indent=2, ensure_ascii=False))
print(f"Sparad: {output_path}")
```

## Exempel: Analysera Getinge Annual Report

```
Anvandare: /analyze-filings
Claude: [visar backlog - Getinge har 5 filings, 0 analyserade]
Claude: [fragar om metod -> Claude Code]
Claude: [fragar om bolag -> Getinge]
Claude: [fragar om filing -> Annual Report 2024]

Claude: Analyserar Getinge Annual Report 2024...

  📖 Laser: getinge_annual_report_2024.md (45,000 ord)
  🔍 Extraherar sektioner...
     - CEO Letter: 1,850 ord
     - MD&A: 8,500 ord
     - Risk Factors: 4,200 ord
     - Guidance: 1,200 ord
     - Segments: 3,800 ord

  📊 Analyserar CEO Letter...
     Ton: cautiously_optimistic
     Konfidensgrad: medium
     Loften: 3 specifika ataganden
     Nyckelcitat: "We remain committed to..."

  📊 Analyserar Risk Factors...
     Nya risker: 2
     Eskalerade: 1
     Boilerplate-andel: 65%

  ✅ Klar!

  Sparad: data/filings/analysis/getinge/getinge-annual-2024.json
```

## Tips

- Borja med CEO Letter - det ger bast oversikt
- Notera om nagon sektion saknas i filingen
- For svenska filings, anvand svenska prompts fran ceo_letter.py
- Jamfor med tidigare filings for att spara promise_tracker
