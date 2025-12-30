---
name: analyze-filings
description: Deep "Buffett-class" analysis of financial filings (quarterly/annual reports). Extracts CEO letter tone, management promises, strategic themes, risk factors, guidance, and segment performance. Two methods: Claude Code (in conversation) or OpenCode/GLM-4.7 (script in separate terminal).
---

# Analyze Filings Skill

Perform deep analysis of financial filings - quarterly reports, annual reports, and earnings transcripts.

## Quick Start

1. **Visa backlog** - Visa tillgangliga filings per bolag
2. Fraga anvandaren om **metod**: Claude Code eller OpenCode/GLM-4.7
3. Fraga om **bolag**: Vilket bolag ska analyseras
4. Fraga om **filing**: Vilken rapport (annual, quarterly Q1-Q4)
5. Kor analys och visa sammanfattning
6. Spara till `data/filings/analysis/{company}/{filing_id}.json`

## Backlog Check (Kor FORST)

Visa automatiskt tillgangliga och analyserade filings:

```python
from pathlib import Path

def get_filings_backlog():
    """Returnerar tillgangliga filings per bolag."""

    backlog = {}
    extracted_dir = Path('data/filings/extracted')
    analysis_dir = Path('data/filings/analysis')

    if extracted_dir.exists():
        for company_dir in extracted_dir.iterdir():
            if company_dir.is_dir():
                company = company_dir.name
                filings = list(company_dir.glob('*.md'))

                # Check analyzed
                analyzed = set()
                company_analysis_dir = analysis_dir / company
                if company_analysis_dir.exists():
                    analyzed = set(p.stem for p in company_analysis_dir.glob('*.json'))

                filing_names = [f.stem for f in filings]
                pending = [f for f in filing_names if f not in analyzed]

                backlog[company] = {
                    'total': len(filings),
                    'analyzed': len(analyzed),
                    'pending': len(pending),
                    'files': filing_names,
                    'pending_list': pending[:5]
                }

    return backlog

# Kor och visa
backlog = get_filings_backlog()
print("📊 FILINGS BACKLOG")
print("=" * 50)
for company, data in sorted(backlog.items()):
    pending = data['pending']
    total = data['total']
    emoji = "✅" if pending == 0 else "📋"
    print(f"{emoji} {company.upper()}: {pending} oanalyserade av {total} totalt")
    if pending > 0 and data['pending_list']:
        for f in data['pending_list'][:3]:
            print(f"   - {f}")
print("=" * 50)
```

## Method Selection

| Metod | Nar anvanda |
|-------|-------------|
| **Claude Code** | Default. Kor direkt i konversationen. Anvander Claude API-credits. |
| **OpenCode/GLM-4.7** | Script i separat terminal. Gratis med OpenCode. Bra for batch. |

## Workflow

### Step 1: Gather Requirements

Anvand AskUserQuestion:

```
1. Analysmetod?
   - Claude Code (Recommended) - kor har, anvander API-credits
   - OpenCode/GLM-4.7 - kor i separat terminal, gratis

2. Bolag?
   [Lista fran backlog]

3. Filing?
   - Annual report 2024
   - Quarterly Q1/Q2/Q3/Q4
   - Alla oanalyserade
```

### Step 2: Execute Analysis

**Claude Code-metod:** Se [references/claude-method.md](references/claude-method.md)

**OpenCode/GLM-4.7-metod:** Se [references/opencode-method.md](references/opencode-method.md)

### Step 3: Provide Summary

Efter analys, rapportera:
- CEO Letter: ton, konfidensgrad, nyckelcitat
- Guidance: targets och riktning
- Risk Factors: nya, andrade, borttagna risker
- Segments: prestation per affaromrade
- Sparad fil: `data/filings/analysis/{company}/{filing_id}.json`

## Analysis Structure

### CEO Letter Analysis
- **Author & Title**: Vem skrev det
- **Tone**: optimistic | cautiously_optimistic | neutral | cautious | defensive
- **Confidence**: high | medium | low
- **Promises**: Specifika trackbara ataganden med mal och tidsram
- **Themes**: Strategiska teman med betoningsgrad
- **Challenges**: Hur ledningen addresserar svarigheter (extern vs intern attribution)
- **Honesty Signals**: Indikatorer pa transparent kommunikation

### MD&A Analysis
- Key narratives (vilken historia berattar ledningen?)
- Management's interpretation of results
- Segment commentary
- Operational highlights
- Concerns mentioned

### Risk Factors
- New/escalated/de-escalated risks
- Boilerplate ratio (generiska vs specifika risker)
- Top risk categories

### Guidance
- Specific targets (metric, value, period)
- vs_previous: raised | maintained | lowered
- Management confidence level

### Segment Performance
- Revenue, growth, margin per segment
- Management focus and outlook

## File Paths

| Typ | Sokvag |
|-----|--------|
| Extracted filings | `data/filings/extracted/{company}/*.md` |
| Analysis output | `data/filings/analysis/{company}/*.json` |
| Evolution synthesis | `data/filings/analysis/{company}/evolution.json` |

## Output Schema

Se [references/output-schema.md](references/output-schema.md) for fullstandigt JSON-schema.

## Cost Estimation

### Claude Code
- ~$0.10-0.50 per filing (beroende pa storlek)
- Bast for enstaka analyser eller nar interaktivitet behovs

### OpenCode/GLM-4.7
- Gratis (ingar i OpenCode)
- Bast for batch-korning
- ~5-10 minuter per filing

## Error Handling

| Fel | Losning |
|-----|---------|
| `Timeout efter 300 sekunder` | Forsok igen, eller dela upp i sektioner |
| `Kunde inte parsa JSON` | Forsok igen (max 3 forsok) |
| `Section not found` | Filing saknar sektion - hoppa over eller notera |
| `No filings found` | Verifiera sokvag i extracted/ |

## Section Finder Utilities

Anvand utilities fran `src/podstock/filings/analysis/`:

```python
from podstock.filings.analysis.ceo_letter import find_ceo_letter_section
from podstock.filings.analysis.deep_analysis import (
    find_mda_section,
    find_risk_factors_section,
    find_guidance_section,
    find_segment_section,
)

# Extrahera sektioner
ceo_section = find_ceo_letter_section(document)
mda_section = find_mda_section(document)
risk_section = find_risk_factors_section(document)
guidance_section = find_guidance_section(document)
segment_section = find_segment_section(document)
```
