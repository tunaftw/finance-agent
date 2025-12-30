# Analyze Filings

Perform deep "Buffett-class" analysis of financial filings (quarterly reports, annual reports). Extracts CEO letter tone, management promises, strategic themes, risk factors, guidance, and segment performance.

## Argument
$ARGUMENTS - Company ID, filing type, or specific filing path

## Usage Examples

```bash
# Analyze a specific company's filings
/analyze-filings getinge

# Analyze a specific filing
/analyze-filings data/filings/extracted/getinge/getinge_annual_report_2024.md

# List available filings
/analyze-filings --list
```

## Workflow

**IMPORTANT:** This skill uses TWO methods (no API key required):
1. **Claude Code** - I analyze directly in conversation
2. **OpenCode/GLM-4.7** - Driver script in separate terminal

See @.claude/skills/analyze-filings/ for full skill documentation.

### Quick Start

1. Check backlog (run Python snippet from SKILL.md)
2. Ask user: Claude Code or OpenCode method?
3. Ask user: Which company/filing?
4. Run analysis
5. Save to `data/filings/analysis/{company}/{filing_id}.json`

### Claude Code Method

For interactive analysis in this conversation:

1. Read the filing with Read tool
2. Use section finders to extract relevant sections
3. Analyze each section (CEO letter, MD&A, risk factors, etc.)
4. Build JSON output and save

```python
from podstock.filings.analysis.ceo_letter import find_ceo_letter_section
from podstock.filings.analysis.deep_analysis import (
    find_mda_section,
    find_risk_factors_section,
    find_guidance_section,
    find_segment_section,
)

# Read and extract sections
content = Path("data/filings/extracted/getinge/getinge_annual_report_2024.md").read_text()
ceo_section = find_ceo_letter_section(content)
# ... analyze each section
```

### OpenCode/GLM-4.7 Method

For batch processing in separate terminal:

```bash
# Single filing
python scripts/filings_glm_driver.py \
  data/filings/extracted/getinge/getinge_annual_report_2024.md

# Batch - all pending for company
python scripts/filings_glm_driver.py --batch getinge

# Batch - all pending
python scripts/filings_glm_driver.py --batch-all

# List pending
python scripts/filings_glm_driver.py --list
```

## Analysis Structure

### CEO Letter Analysis
- **Tone**: optimistic | cautiously_optimistic | neutral | cautious | defensive
- **Confidence**: high | medium | low
- **Promises**: Specific trackable commitments with targets and timeframes
- **Themes**: Strategic topics with emphasis level
- **Challenges**: How management addresses difficulties
- **Honesty Signals**: Indicators of transparent communication

### Other Sections
- **MD&A**: Key narratives, segment commentary
- **Risk Factors**: New/escalated/de-escalated risks, boilerplate ratio
- **Guidance**: Targets and vs-previous comparison
- **Segments**: Revenue, growth, margin by business area

## File Paths

| Type | Location |
|------|----------|
| Extracted filings | `data/filings/extracted/{company}/*.md` |
| Analysis output | `data/filings/analysis/{company}/*.json` |

## Related Files

- `.claude/skills/analyze-filings/SKILL.md` - Full skill documentation
- `src/podstock/filings/analysis/ceo_letter.py` - CEO letter extractor
- `src/podstock/filings/analysis/deep_analysis.py` - Section finders & prompts
- `scripts/filings_glm_driver.py` - OpenCode driver script
