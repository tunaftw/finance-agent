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

Visa automatiskt tillgangliga filings - bade raw PDFs och extraherade:

```python
from pathlib import Path

def get_filings_backlog():
    """Returnerar filings status per bolag: raw PDFs, extracted MDs, analyzed."""

    backlog = {}
    raw_dir = Path('data/filings/raw')
    extracted_dir = Path('data/filings/extracted')
    analysis_dir = Path('data/filings/analysis')

    # Gather all companies from both raw and extracted
    companies = set()
    if raw_dir.exists():
        companies.update(d.name for d in raw_dir.iterdir() if d.is_dir() and d.name != 'presentations')
    if extracted_dir.exists():
        companies.update(d.name for d in extracted_dir.iterdir() if d.is_dir())

    for company in sorted(companies):
        # Raw PDFs
        raw_pdfs = set()
        company_raw_dir = raw_dir / company
        if company_raw_dir.exists():
            raw_pdfs = set(p.stem for p in company_raw_dir.glob('*.pdf'))

        # Extracted MDs
        extracted_mds = set()
        company_extracted_dir = extracted_dir / company
        if company_extracted_dir.exists():
            extracted_mds = set(p.stem for p in company_extracted_dir.glob('*.md'))

        # Analyzed JSONs
        analyzed = set()
        company_analysis_dir = analysis_dir / company
        if company_analysis_dir.exists():
            analyzed = set(p.stem for p in company_analysis_dir.glob('*.json'))

        # Calculate states
        needs_extraction = raw_pdfs - extracted_mds  # PDFs without matching MD
        needs_analysis = extracted_mds - analyzed    # MDs without matching JSON

        backlog[company] = {
            'raw_pdfs': len(raw_pdfs),
            'extracted': len(extracted_mds),
            'analyzed': len(analyzed),
            'needs_extraction': sorted(needs_extraction)[:5],
            'needs_analysis': sorted(needs_analysis)[:5],
            'pending_extraction_count': len(needs_extraction),
            'pending_analysis_count': len(needs_analysis),
        }

    return backlog

# Display
backlog = get_filings_backlog()
print("FILINGS BACKLOG")
print("=" * 60)
for company, data in sorted(backlog.items()):
    ext_pending = data['pending_extraction_count']
    ana_pending = data['pending_analysis_count']
    total_raw = data['raw_pdfs']
    total_analyzed = data['analyzed']

    if ext_pending == 0 and ana_pending == 0:
        emoji = "[OK]"
    elif ext_pending > 0:
        emoji = "[PDF]"  # Has PDFs needing extraction
    else:
        emoji = "[MD]"   # Has MDs needing analysis

    print(f"{emoji} {company.upper()}: {total_raw} PDFs, {data['extracted']} extracted, {total_analyzed} analyzed")

    if ext_pending > 0:
        print(f"      Needs extraction ({ext_pending}):")
        for f in data['needs_extraction'][:3]:
            print(f"        - {f}.pdf")

    if ana_pending > 0:
        print(f"      Needs analysis ({ana_pending}):")
        for f in data['needs_analysis'][:3]:
            print(f"        - {f}.md")

print("=" * 60)
```

## PDF Extraction (Automatisk)

Extraktion sker automatiskt nar en filing valjs for analys. Anvand denna funktion:

```python
from pathlib import Path

def ensure_extracted(company: str, filing_stem: str) -> Path:
    """
    Saker att en filing ar extraherad till markdown.
    Returnerar sokvag till markdown-filen.

    Args:
        company: Bolagsnamn (t.ex. 'getinge')
        filing_stem: Filnamn utan extension (t.ex. 'annual-2024')

    Returns:
        Path till markdown-filen
    """
    raw_dir = Path('data/filings/raw')
    extracted_dir = Path('data/filings/extracted')

    pdf_path = raw_dir / company / f"{filing_stem}.pdf"
    md_path = extracted_dir / company / f"{filing_stem}.md"

    # Redan extraherad?
    if md_path.exists():
        return md_path

    # Kolla att PDF finns
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Extrahera
    print(f"Extracting {pdf_path.name} to markdown...")
    from podstock.filings.pdf.parser import PDFParser
    parser = PDFParser()
    markdown = parser.to_markdown(pdf_path)

    # Spara
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown, encoding='utf-8')
    print(f"Extracted: {md_path} ({len(markdown):,} chars)")

    return md_path
```

## Method Selection

| Metod | Nar anvanda |
|-------|-------------|
| **Claude Code** | Default. Kor direkt i konversationen. Anvander Claude API-credits. |
| **OpenCode/GLM-4.7** | Script i separat terminal. Gratis med OpenCode. Bra for batch. |

## Knowledge Library References

This skill leverages the investment philosophy knowledge library for systematic analysis:

| Framework | File | Purpose |
|-----------|------|---------|
| **Piotroski F-Score** | `data/investment-philosophy/frameworks/piotroski-f-score.md` | 9-signal financial health scoring |
| **Schilit 7 Shenanigans** | `data/investment-philosophy/frameworks/schilit-7-shenanigans.md` | Fraud/manipulation detection |
| **Sloan Accruals** | `data/investment-philosophy/frameworks/sloan-accruals.md` | Earnings quality assessment |
| **Buffett 10-K Method** | `data/investment-philosophy/frameworks/buffett-10k-method.md` | Qualitative analysis approach |
| **Red Flags Checklist** | `data/investment-philosophy/techniques/red-flags-checklist.md` | Comprehensive warning signs |
| **Efficiency Metrics** | `data/investment-philosophy/basics/key-metrics/efficiency.md` | DSO, DIO, DPO, CCC |
| **Swedish Glossary** | `data/investment-philosophy/basics/glossary.md` | Swedish/English terminology |

## Reading Order (Buffett Method)

When analyzing a filing, follow this sequence for maximum insight:

1. **Business Overview** (Item 1 / Verksamheten)
   - Understand what the company does before looking at numbers
   - Can you explain it simply?

2. **Risk Factors** (Item 1A / Risker)
   - What could kill the business?
   - Compare to prior year - what's new or escalated?

3. **MD&A** (Item 7 / Förvaltningsberättelse)
   - Management's story and candor assessment
   - Are they honest about problems?

4. **Cash Flow Statement** (Kassaflödesanalys)
   - "Truth serum" - compare to reported earnings
   - Is OCF > Net Income? (earnings quality)

5. **Footnotes** (Noter)
   - Where manipulation hides
   - Related parties, contingencies, off-balance sheet

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
- **Honesty Signals**: Indikatorer pa transparent kommunikation (Buffett Candor Test)

#### Buffett Candor Test (for CEO Letters)

**Positive Signals (Green Flags):**
- Acknowledges failures, mistakes, or missed targets
- Addresses previous promises explicitly (met or missed)
- Provides context for shortfalls without excessive excuses
- Uses specific rather than vague language
- Attributes challenges to internal factors when appropriate
- Discusses competitive threats honestly
- Admits uncertainty where it exists

**Warning Signals (Red Flags):**
- Only discusses positives, ignores problems
- Blames externals for all problems (market, economy, weather)
- Excessive non-GAAP adjustments highlighted
- Vague forward-looking statements without metrics
- Avoids addressing previously stated targets
- Frequent use of "challenging environment" without specifics
- Corporate buzzwords without substance ("synergies", "transformation")

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

### Quantitative Analysis (NEW)

These metrics should be calculated for every filing:

**Piotroski F-Score (0-9)**
- 9 binary signals: profitability, leverage, efficiency
- 8-9: Strong | 5-7: Average | 2-4: Weak | 0-1: Very Weak
- See `data/investment-philosophy/frameworks/piotroski-f-score.md`

**Earnings Quality (Sloan Accruals)**
- Accruals Ratio = (Net Income - OCF) / Total Assets
- < 0.05: High quality | 0.05-0.10: Medium | > 0.10: Low (investigate)
- OCF/NI Ratio: > 1.0 is excellent
- See `data/investment-philosophy/frameworks/sloan-accruals.md`

**Schilit Shenanigans Check**
- 7 manipulation patterns to evaluate
- Flag: none | low | medium | high risk per category
- See `data/investment-philosophy/frameworks/schilit-7-shenanigans.md`

**Working Capital Efficiency**
- DSO: Days Sales Outstanding (AR collection speed)
- DIO: Days Inventory Outstanding (inventory turnover)
- DPO: Days Payables Outstanding (supplier payment)
- CCC: Cash Conversion Cycle = DIO + DSO - DPO
- See `data/investment-philosophy/basics/key-metrics/efficiency.md`

## File Paths

| Typ | Sokvag |
|-----|--------|
| Raw PDFs | `data/filings/raw/{company}/*.pdf` |
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
