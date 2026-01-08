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

### 1. Las filingen (med automatisk extraktion)

```python
from pathlib import Path

# Configuration
company = "getinge"  # User-selected
filing_stem = "annual-2024"  # User-selected

def ensure_extracted(company: str, filing_stem: str) -> Path:
    """Extraherar PDF till markdown om det behovs."""
    raw_dir = Path('data/filings/raw')
    extracted_dir = Path('data/filings/extracted')

    pdf_path = raw_dir / company / f"{filing_stem}.pdf"
    md_path = extracted_dir / company / f"{filing_stem}.md"

    if md_path.exists():
        return md_path

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    print(f"Extracting {pdf_path.name}...")
    from podstock.filings.pdf.parser import PDFParser
    markdown = PDFParser().to_markdown(pdf_path)

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown, encoding='utf-8')
    print(f"Extracted: {md_path}")

    return md_path

# Get filing path (extracts if needed)
filing_path = ensure_extracted(company, filing_stem)
content = filing_path.read_text(encoding="utf-8")
word_count = len(content.split())
print(f"Filing: {filing_path.name} ({word_count:,} words)")
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

### 3b. Quantitative Analysis (NEW)

After section analysis, calculate these metrics:

#### Piotroski F-Score (0-9)

Use financial data to calculate 9 signals:
- Profitability (4): Net Income > 0, OCF > 0, ROA improving, OCF > NI
- Leverage (3): Debt ratio declining, Current ratio improving, No dilution
- Efficiency (2): Gross margin improving, Asset turnover improving

Score: 8-9 Strong | 5-7 Average | 2-4 Weak | 0-1 Very Weak

#### Earnings Quality (Sloan Accruals)

```
Accruals Ratio = (Net Income - OCF) / Total Assets
```
- < 0.05: High quality
- 0.05-0.10: Medium quality
- > 0.10: Low quality (investigate)

Also calculate:
- OCF/NI Ratio (>1.0 = excellent)
- Owner Earnings = NI + D&A - Maintenance CapEx - WC changes

#### Schilit Shenanigans Check

Evaluate each of the 7 shenanigans:
1. Revenue too soon? (DSO increasing, AR growing faster than revenue)
2. Bogus revenue? (Related party, non-customer sales)
3. One-time gains? (Asset sales, reserve releases in operating income)
4. Deferred expenses? (Improper capitalization, extended depreciation)
5. Hidden liabilities? (Off-balance sheet, understated contingencies)
6. Cookie jar reserves? (Over-reserving for future release)
7. Big bath? (Kitchen-sink write-offs after management change)

Flag: none | low | medium | high for each

#### Working Capital Efficiency

Calculate:
- DSO = (AR / Revenue) × 365
- DIO = (Inventory / COGS) × 365
- DPO = (AP / COGS) × 365
- CCC = DIO + DSO - DPO

Flag concerning trends (DSO increasing faster than revenue, etc.)

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
    "financial_metrics": {...},

    "piotroski_f_score": {
        "total": 7,
        "interpretation": "average",
        "signals": {...}
    },

    "earnings_quality": {
        "accruals_ratio": 0.04,
        "quality_grade": "high",
        "ocf_to_ni_ratio": 1.08,
        "owner_earnings": 780000000
    },

    "schilit_shenanigans": {
        "overall_risk": "low",
        "checks": {...},
        "red_flags": []
    },

    "working_capital_efficiency": {
        "dso": 45,
        "dio": 65,
        "dpo": 52,
        "cash_conversion_cycle": 58,
        "ccc_trend": "stable"
    },

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
