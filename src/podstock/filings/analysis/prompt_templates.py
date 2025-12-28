"""Prompt templates for financial filing analysis.

These templates are designed for multi-pass analysis of financial reports,
with specialized prompts for different analysis tasks.
"""

# =============================================================================
# Document Structure Analysis
# =============================================================================

TOC_EXTRACTION_PROMPT = """Analyze this document and identify the main sections.

You are looking at the beginning of a financial report ({filing_type}) from {company_name}.

Identify the following sections and their approximate page numbers:
- Executive Summary / Letter to Shareholders
- Business Description
- Risk Factors
- Management Discussion & Analysis (MD&A)
- Financial Statements (Income Statement, Balance Sheet, Cash Flow)
- Notes to Financial Statements

Return a JSON object with section names as keys and page ranges as values.
If a section is not found, omit it from the output.

Example output:
{{
  "executive_summary": {{"start": 1, "end": 3}},
  "risk_factors": {{"start": 15, "end": 25}},
  "financial_statements": {{"start": 50, "end": 75}}
}}
"""


# =============================================================================
# Financial Metrics Extraction
# =============================================================================

METRICS_EXTRACTION_PROMPT = """Extract financial metrics from this section of a {filing_type} from {company_name}.

Language: {language}

Extract the following metrics if present (use null if not found):

INCOME STATEMENT:
- revenue (Nettoomsättning / Net Revenue / Total Revenue)
- gross_profit (Bruttoresultat / Gross Profit)
- operating_income (Rörelseresultat / Operating Income / EBIT)
- net_income (Årets resultat / Net Income)
- eps (Vinst per aktie / Earnings Per Share)
- eps_diluted (Utspädd vinst per aktie)

BALANCE SHEET:
- total_assets (Balansomslutning / Total Assets)
- total_equity (Eget kapital / Total Equity)
- total_debt (Totala skulder / Total Debt)
- cash_and_equivalents (Likvida medel / Cash and Equivalents)

CASH FLOW:
- operating_cash_flow (Kassaflöde från löpande verksamhet)
- capex (Investeringar / Capital Expenditures) - typically negative
- free_cash_flow (Fritt kassaflöde)

IMPORTANT:
- All values should be in the report's currency ({currency})
- Include the full number (not in millions/billions unless specified)
- For Swedish reports, MSEK means millions of SEK
- For US reports, values are typically in thousands or millions (check footnotes)

Return as JSON:
{{
  "currency": "{currency}",
  "revenue": <number or null>,
  "gross_profit": <number or null>,
  ...
}}
"""


# =============================================================================
# Chunk Analysis (Per-Section)
# =============================================================================

CHUNK_ANALYSIS_PROMPT = """Analyze this section of a financial report.

DOCUMENT CONTEXT:
{document_metadata}

CURRENT SECTION:
{section_content}

Extract the following information:

1. KEY POINTS (3-5 bullet points):
   - What are the main takeaways from this section?
   - Focus on financial implications and business developments

2. RISKS MENTIONED:
   - List any risks or concerns mentioned
   - Include both explicit risk factors and implied challenges

3. METRICS MENTIONED:
   - Note any specific numbers, percentages, or financial metrics
   - Format: {{"metric_name": "value or change"}}

4. SENTIMENT:
   - What is the overall tone? (positive, neutral, cautious, negative)

5. NOTABLE QUOTES:
   - Include 1-2 significant quotes that capture key messages

Return as JSON:
{{
  "key_points": ["...", "..."],
  "risks": ["...", "..."],
  "metrics_mentioned": {{"revenue_growth": "+5%", "...": "..."}},
  "sentiment": "positive|neutral|cautious|negative",
  "notable_quotes": ["...", "..."]
}}
"""


# =============================================================================
# Synthesis (Combining Chunk Analyses)
# =============================================================================

SYNTHESIS_PROMPT = """Synthesize a comprehensive analysis of this financial report.

COMPANY: {company_name}
FILING TYPE: {filing_type}
FISCAL PERIOD: {fiscal_period}

You have analyzed {chunk_count} sections of this document. Here are the individual analyses:

{chunk_analyses}

Create a unified analysis with:

1. EXECUTIVE SUMMARY (3-5 sentences):
   - Overall assessment of the company's performance
   - Key changes from the prior period
   - Forward-looking outlook

2. KEY HIGHLIGHTS (5-7 bullet points):
   - Most important takeaways for investors
   - Mix of financial results and strategic developments

3. RISKS:
   - Consolidated list of key risks (deduplicated)
   - Prioritize by significance

4. OPPORTUNITIES:
   - Growth opportunities mentioned
   - Strategic initiatives

5. YEAR-OVER-YEAR CHANGES:
   - Key metrics with YoY comparison
   - Format: {{"metric": "change description"}}

6. GUIDANCE:
   - Any forward guidance provided
   - Management's outlook

7. MANAGEMENT TONE:
   - Overall sentiment (positive, neutral, cautious, negative)
   - Reasoning for this assessment

Return as JSON:
{{
  "executive_summary": "...",
  "key_highlights": ["...", "..."],
  "risks_mentioned": ["...", "..."],
  "opportunities_mentioned": ["...", "..."],
  "yoy_changes": {{"revenue": "+5% to $X billion", "...": "..."}},
  "guidance": "..." or null,
  "management_tone": "positive|neutral|cautious|negative"
}}
"""


# =============================================================================
# Swedish-specific Templates
# =============================================================================

SWEDISH_METRICS_EXTRACTION_PROMPT = """Extrahera finansiella nyckeltal från denna svenska årsredovisning.

BOLAG: {company_name}
RÄKENSKAPSÅR: {fiscal_year}

Extrahera följande nyckeltal (använd null om ej tillgängligt):

RESULTATRÄKNING:
- nettoomsattning (Nettoomsättning)
- bruttovinst (Bruttoresultat)
- rorelseresultat (Rörelseresultat / EBIT)
- finansnetto (Finansnetto)
- resultat_fore_skatt (Resultat före skatt)
- arets_resultat (Årets resultat)

BALANSRÄKNING:
- balansomslutning (Summa tillgångar)
- eget_kapital (Eget kapital)
- kortfristiga_skulder (Kortfristiga skulder)
- langfristiga_skulder (Långfristiga skulder)
- likvida_medel (Kassa och bank)

KASSAFLÖDE:
- kassaflode_lopande (Kassaflöde från löpande verksamhet)
- investeringar (Kassaflöde från investeringsverksamhet)
- finansiering (Kassaflöde från finansieringsverksamhet)

NYCKELTAL:
- soliditet (Soliditet i %)
- vinstmarginal (Vinstmarginal i %)
- avkastning_eget_kapital (Avkastning på eget kapital i %)
- medelantal_anstallda (Medelantal anställda)

VIKTIGT:
- Alla belopp i SEK (eller TSEK/MSEK beroende på rapport)
- Ange enheten i valutafältet
- Notera om rapporten använder K3 eller IFRS

Returnera som JSON:
{{
  "currency": "SEK",
  "unit": "MSEK" eller "TSEK" eller "SEK",
  "accounting_standard": "K3" eller "IFRS",
  "nettoomsattning": <nummer eller null>,
  ...
}}
"""


SWEDISH_ANALYSIS_PROMPT = """Analysera denna del av en svensk årsredovisning.

BOLAG: {company_name}
AVSNITT: {section_type}

Extrahera:

1. HUVUDPUNKTER (3-5 punkter):
   - Viktigaste insikterna från detta avsnitt
   - Fokusera på finansiell utveckling och verksamhetsförändringar

2. RISKER:
   - Risker och utmaningar som nämns
   - Både explicita riskfaktorer och underförstådda problem

3. FRAMTIDSUTSIKTER:
   - Styrelsens/VD:s syn på framtiden
   - Eventuella prognoser eller mål

4. TON:
   - Hur är den övergripande tonen? (positiv, neutral, försiktig, negativ)

Returnera som JSON:
{{
  "huvudpunkter": ["...", "..."],
  "risker": ["...", "..."],
  "framtidsutsikter": "...",
  "ton": "positiv|neutral|försiktig|negativ"
}}
"""


# =============================================================================
# Utility Functions
# =============================================================================

def get_metrics_prompt(language: str = "en", **kwargs) -> str:
    """Get the appropriate metrics extraction prompt for the language.

    Args:
        language: Language code ('en', 'sv').
        **kwargs: Template variables.

    Returns:
        Formatted prompt string.
    """
    if language == "sv":
        template = SWEDISH_METRICS_EXTRACTION_PROMPT
    else:
        template = METRICS_EXTRACTION_PROMPT

    return template.format(**kwargs)


def get_analysis_prompt(language: str = "en", **kwargs) -> str:
    """Get the appropriate analysis prompt for the language.

    Args:
        language: Language code ('en', 'sv').
        **kwargs: Template variables.

    Returns:
        Formatted prompt string.
    """
    if language == "sv":
        template = SWEDISH_ANALYSIS_PROMPT
    else:
        template = CHUNK_ANALYSIS_PROMPT

    return template.format(**kwargs)
