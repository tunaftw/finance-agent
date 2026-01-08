"""Deep filing analysis utilities.

This module provides:
1. Section finder utilities to extract specific sections from filings
2. Prompt templates for LLM analysis (used by Claude Code or OpenCode)

The actual LLM analysis is done by:
- Claude Code: Reading sections and analyzing in conversation
- OpenCode/GLM-4.7: Via scripts/filings_glm_driver.py

NO Anthropic API calls are made from this module.
"""

from __future__ import annotations

import json
import re


# =============================================================================
# Deep Analysis Prompts (for reference - used by Claude Code or OpenCode)
# =============================================================================

MDA_ANALYSIS_PROMPT = """Analyze the Management Discussion & Analysis (MD&A) section.

COMPANY: {company_name}
FISCAL PERIOD: {fiscal_period}

MD&A CONTENT:
{mda_content}

Extract:

1. KEY NARRATIVES (3-5 main themes management is emphasizing):
   - What story is management telling about the period?
   - Focus on explanations for performance, not just numbers

2. MANAGEMENT'S INTERPRETATION:
   - How does management explain the results?
   - Are they being realistic or spinning?

3. SEGMENT COMMENTARY:
   For each business segment mentioned, extract:
   - Segment name
   - Performance summary (strong, stable, weak, recovering)
   - Revenue or growth if mentioned
   - Operating margin if mentioned
   - Management's outlook (positive, neutral, cautious, negative)

4. OPERATIONAL HIGHLIGHTS:
   - Key operational achievements or milestones
   - New products, partnerships, or expansions

5. CONCERNS MENTIONED:
   - Any challenges or headwinds discussed
   - Market conditions affecting performance

Return as JSON:
{{
  "key_narratives": ["...", "..."],
  "management_interpretation": "...",
  "segment_commentary": {{
    "Acute Care Therapies": {{
      "name": "Acute Care Therapies",
      "performance": "strong",
      "revenue_growth_yoy": 0.08,
      "operating_margin": 0.18,
      "outlook": "positive",
      "management_commentary": "..."
    }}
  }},
  "operational_highlights": ["...", "..."],
  "concerns_mentioned": ["...", "..."]
}}
"""

RISK_FACTORS_PROMPT = """Analyze the Risk Factors section of this financial filing.

COMPANY: {company_name}
FISCAL PERIOD: {fiscal_period}

RISK FACTORS CONTENT:
{risk_content}

{previous_risks_context}

Extract:

1. RISK INVENTORY:
   For each significant risk factor:
   - Risk description (brief)
   - Severity: high | medium | low
   - Category: regulatory | operational | market | financial | legal | technology | other
   - Is this boilerplate (generic language used by many companies)?

2. CHANGES FROM PREVIOUS FILING (if previous risks provided):
   - New risks that weren't in previous filing
   - Risks that have been removed
   - Risks where language has escalated (more severe) or de-escalated

3. BOILERPLATE RATIO:
   - What percentage of risks are generic boilerplate vs specific to this company?

4. TOP RISK CATEGORIES:
   - Which categories have the most risks?

Return as JSON:
{{
  "risks": [
    {{
      "risk": "Regulatory changes in medical device approval",
      "severity": "high",
      "category": "regulatory",
      "change": "unchanged" | "new" | "escalated" | "de-escalated" | "removed",
      "is_boilerplate": false
    }}
  ],
  "new_risks_count": 2,
  "removed_risks_count": 0,
  "escalated_risks_count": 1,
  "boilerplate_ratio": 0.3,
  "top_risk_categories": ["regulatory", "operational"]
}}
"""

GUIDANCE_EXTRACTION_PROMPT = """Extract forward-looking guidance from this filing.

COMPANY: {company_name}
FISCAL PERIOD: {fiscal_period}

GUIDANCE SECTIONS:
{guidance_content}

Extract all specific, trackable guidance targets:

1. GUIDANCE TARGETS:
   For each specific target:
   - Metric: organic_growth | revenue | operating_margin | eps | ebitda_margin | other
   - Value: The specific target ("4-6%", ">12%", "SEK 5.00", etc.)
   - Period: When this applies ("FY 2024", "medium-term", "2024-2028", etc.)
   - Change vs previous guidance: raised | maintained | lowered | withdrawn | new

2. OVERALL DIRECTION:
   - Is management raising, maintaining, or lowering guidance overall?

3. COMMENTARY:
   - Any qualitative statements about outlook

4. MANAGEMENT CONFIDENCE:
   - How confident does management seem? (high, medium, low)
   - Look at language: "expect" vs "hope", specific vs vague

Return as JSON:
{{
  "targets": [
    {{
      "metric": "organic_growth",
      "value": "4-6%",
      "period": "FY 2024",
      "vs_previous": "maintained",
      "notes": null
    }},
    {{
      "metric": "eps_growth",
      "value": ">12%",
      "period": "2024-2028",
      "vs_previous": "new",
      "notes": "Average annual growth"
    }}
  ],
  "overall_direction": "maintained",
  "commentary": "Management maintains full year outlook despite Q3 headwinds",
  "management_confidence": "medium"
}}
"""

SEGMENT_ANALYSIS_PROMPT = """Analyze business segment performance from this filing.

COMPANY: {company_name}
FISCAL PERIOD: {fiscal_period}

SEGMENT DATA:
{segment_content}

For each business segment, extract:

1. SEGMENT DETAILS:
   - Name
   - Revenue (in local currency)
   - Revenue growth YoY (as decimal, e.g., 0.08 for 8%)
   - Operating margin (as decimal)
   - Order intake if mentioned
   - Order intake growth if mentioned

2. QUALITATIVE ASSESSMENT:
   - Management's commentary on this segment
   - Outlook: positive | neutral | cautious | negative
   - How much management focus does this segment get? high | medium | low

Return as JSON:
{{
  "segments": [
    {{
      "name": "Acute Care Therapies",
      "revenue": 3500000000,
      "revenue_growth_yoy": 0.08,
      "operating_margin": 0.18,
      "order_intake": 3800000000,
      "order_intake_growth_yoy": 0.05,
      "management_commentary": "Strong performance driven by...",
      "outlook": "positive",
      "management_focus": "high"
    }}
  ]
}}
"""


# =============================================================================
# Quantitative Analysis Prompts (Piotroski, Sloan, Schilit, Efficiency)
# =============================================================================

PIOTROSKI_F_SCORE_PROMPT = """Calculate the Piotroski F-Score for this company.

COMPANY: {company_name}
FISCAL PERIOD: {fiscal_period}

FINANCIAL DATA:
{financial_data}

Calculate each of the 9 Piotroski signals (1 point each if TRUE):

PROFITABILITY (4 signals):
1. Positive Net Income: Is net income > 0?
2. Positive OCF: Is operating cash flow > 0?
3. ROA Improving: Is ROA higher than prior year?
4. OCF > Net Income: Is operating cash flow > net income? (earnings quality)

LEVERAGE & LIQUIDITY (3 signals):
5. Leverage Declining: Has long-term debt / total assets decreased?
6. Current Ratio Improving: Has current ratio improved vs prior year?
7. No Dilution: Were no new shares issued during the year?

OPERATING EFFICIENCY (2 signals):
8. Margin Improving: Is gross margin higher than prior year?
9. Turnover Improving: Has asset turnover (revenue / assets) improved?

Return as JSON:
{{
  "total": <0-9>,
  "interpretation": "strong" | "average" | "weak" | "very_weak",
  "signals": {{
    "positive_net_income": true/false,
    "positive_ocf": true/false,
    "roa_improving": true/false,
    "ocf_greater_than_ni": true/false,
    "leverage_declining": true/false,
    "current_ratio_improving": true/false,
    "no_dilution": true/false,
    "margin_improving": true/false,
    "turnover_improving": true/false
  }},
  "notes": "Any relevant observations about the scoring"
}}

Interpretation guide:
- 8-9: Strong (buy candidates among value stocks)
- 5-7: Average
- 2-4: Weak (caution)
- 0-1: Very weak (avoid)
"""

EARNINGS_QUALITY_PROMPT = """Assess earnings quality using multiple indicators.

COMPANY: {company_name}
FISCAL PERIOD: {fiscal_period}

FINANCIAL DATA:
{financial_data}

Calculate and assess:

1. ACCRUALS RATIO (Sloan):
   Formula: (Net Income - Operating Cash Flow) / Total Assets
   - < 0.05: High quality (cash-backed)
   - 0.05-0.10: Medium quality
   - > 0.10: Low quality (manipulation risk)

2. OCF TO NET INCOME RATIO:
   Formula: Operating Cash Flow / Net Income
   - > 1.0: Excellent (cash exceeds accounting earnings)
   - 0.8-1.0: Good
   - < 0.8: Concerning (earnings not backed by cash)

3. ONE-TIME ITEMS:
   - Identify any one-time gains or charges
   - Asset sales, restructuring, legal settlements
   - Impact: none | minimal | moderate | significant

4. OWNER EARNINGS (Buffett):
   Formula: Net Income + D&A - Maintenance CapEx - Working Capital Changes
   Note: If maintenance CapEx not disclosed, estimate as 50-70% of total CapEx

Return as JSON:
{{
  "accruals_ratio": <float>,
  "quality_grade": "high" | "medium" | "low",
  "ocf_to_ni_ratio": <float>,
  "one_time_items_impact": "none" | "minimal" | "moderate" | "significant",
  "one_time_items_detail": ["..."],
  "owner_earnings": <number>,
  "owner_earnings_notes": "..."
}}
"""

SCHILIT_SHENANIGANS_PROMPT = """Check for accounting manipulation using Schilit's 7 Shenanigans framework.

COMPANY: {company_name}
FISCAL PERIOD: {fiscal_period}

FILING CONTENT:
{filing_content}

Evaluate each of the 7 Shenanigans for signs of earnings manipulation:

1. REVENUE RECORDED TOO SOON OR OF QUESTIONABLE QUALITY
   Red flags: Bill-and-hold sales, channel stuffing, aggressive % completion,
   revenue before delivery, round-trip transactions
   Check: Is AR growing faster than revenue? DSO increasing?

2. BOGUS REVENUE
   Red flags: Revenue from non-customers, loans recorded as sales,
   related party transactions, barter arrangements
   Check: Related party disclosures, unusual revenue sources

3. ONE-TIME GAINS BOOSTING INCOME
   Red flags: Asset sale gains, pension gains, reserve releases,
   litigation settlements in operating income
   Check: Gains classified as operating vs non-operating

4. EXPENSES SHIFTED TO LATER PERIODS
   Red flags: Improper capitalization of operating costs,
   extending depreciation lives, not writing down impaired assets
   Check: Capitalized R&D or software, depreciation policy changes

5. FAILING TO RECORD OR REDUCING LIABILITIES
   Red flags: Off-balance sheet obligations, understated contingencies,
   improper hedge accounting, missing pension liabilities
   Check: Footnotes for contingent liabilities, lease obligations

6. SHIFTING CURRENT REVENUE TO LATER (Cookie Jar Reserves)
   Red flags: Large provisions for future losses, overreserving,
   artificial revenue smoothing across periods
   Check: Unusual reserve movements, consistent quarterly patterns

7. SHIFTING FUTURE EXPENSES TO CURRENT PERIOD (Big Bath)
   Red flags: Kitchen-sink write-offs, restructuring charges,
   massive impairments that can be reversed later
   Check: Large one-time charges after management change

Return as JSON:
{{
  "overall_risk": "none" | "low" | "medium" | "high",
  "checks": {{
    "revenue_too_soon": {{"risk": "none"|"low"|"medium"|"high", "notes": "..."}},
    "bogus_revenue": {{"risk": "none"|"low"|"medium"|"high", "notes": "..."}},
    "one_time_gains": {{"risk": "none"|"low"|"medium"|"high", "notes": "..."}},
    "deferred_expenses": {{"risk": "none"|"low"|"medium"|"high", "notes": "..."}},
    "hidden_liabilities": {{"risk": "none"|"low"|"medium"|"high", "notes": "..."}},
    "cookie_jar_reserves": {{"risk": "none"|"low"|"medium"|"high", "notes": "..."}},
    "big_bath": {{"risk": "none"|"low"|"medium"|"high", "notes": "..."}}
  }},
  "red_flags": ["List of specific concerns found"],
  "requires_further_investigation": ["Areas needing deeper review"]
}}
"""

WORKING_CAPITAL_EFFICIENCY_PROMPT = """Analyze working capital efficiency metrics.

COMPANY: {company_name}
FISCAL PERIOD: {fiscal_period}

FINANCIAL DATA:
{financial_data}

Calculate working capital efficiency metrics:

1. DAYS SALES OUTSTANDING (DSO):
   Formula: (Accounts Receivable / Revenue) × 365
   - Measures average collection period
   - Compare to industry and prior year

2. DAYS INVENTORY OUTSTANDING (DIO):
   Formula: (Inventory / COGS) × 365
   - Measures how long inventory sits
   - Industry-dependent (retail: 15-30, manufacturing: 45-90)

3. DAYS PAYABLES OUTSTANDING (DPO):
   Formula: (Accounts Payable / COGS) × 365
   - Measures payment speed to suppliers
   - Higher = more supplier financing

4. CASH CONVERSION CYCLE (CCC):
   Formula: DIO + DSO - DPO
   - Lower is better (less cash tied up)
   - Negative CCC = excellent (collect before paying)

5. TREND ANALYSIS:
   - Compare each metric to prior year
   - Flag concerning trends

Red flags to check:
- DSO increasing faster than revenue growth
- Inventory building up (demand problems)
- DPO suddenly increasing (cash problems)
- CCC lengthening trend

Return as JSON:
{{
  "dso": <days>,
  "dso_yoy_change": "+X days" or "-X days",
  "dio": <days>,
  "dio_yoy_change": "+X days" or "-X days",
  "dpo": <days>,
  "dpo_yoy_change": "+X days" or "-X days",
  "cash_conversion_cycle": <days>,
  "ccc_yoy_change": "+X days" or "-X days",
  "ccc_trend": "improving" | "stable" | "worsening",
  "flags": ["List any concerning patterns"],
  "notes": "Additional observations"
}}
"""


# =============================================================================
# Full Filing Analysis Prompt (single comprehensive prompt)
# =============================================================================

FULL_FILING_ANALYSIS_PROMPT = """Analyze this financial filing comprehensively.

COMPANY: {company_name}
FISCAL PERIOD: {fiscal_period}
DOCUMENT TYPE: {document_type}

FILING CONTENT (key sections):
{filing_content}

Perform a "Buffett-class" analysis extracting:

1. CEO LETTER ANALYSIS (if present):
   - Author and title
   - Tone: optimistic | cautiously_optimistic | neutral | cautious | defensive
   - Confidence level: high | medium | low
   - Specific promises/commitments with targets and timeframes
   - Strategic themes with emphasis level
   - Challenges and how they're attributed (external vs internal)
   - Honesty signals (transparency indicators)
   - Key quotes

2. MD&A ANALYSIS:
   - Key narratives (what story is management telling?)
   - Management's interpretation of results
   - Segment commentary
   - Operational highlights
   - Concerns mentioned

3. RISK FACTORS:
   - Significant risks with severity and category
   - Boilerplate ratio (generic vs specific risks)
   - Top risk categories

4. GUIDANCE:
   - Specific targets (metric, value, period)
   - Overall direction: raised | maintained | lowered
   - Management confidence level

5. SEGMENT PERFORMANCE:
   - Each segment's revenue, growth, margin
   - Management focus and outlook per segment

6. EXECUTIVE SUMMARY:
   - 2-3 sentence summary of the filing
   - Key highlights (5-7 bullet points)

Return as JSON with this structure:
{{
  "ceo_letter": {{
    "author": "Name" or null,
    "title": "CEO" or null,
    "word_count": <number>,
    "tone": "cautiously_optimistic",
    "confidence_level": "medium",
    "promises": [...],
    "themes": [...],
    "challenges": [...],
    "honesty_signals": [...],
    "key_quotes": [...]
  }},
  "mda_analysis": {{
    "key_narratives": [...],
    "management_interpretation": "...",
    "segment_commentary": {{}},
    "operational_highlights": [...],
    "concerns_mentioned": [...]
  }},
  "risk_factors": {{
    "risks": [...],
    "boilerplate_ratio": 0.3,
    "top_risk_categories": [...]
  }},
  "guidance": {{
    "targets": [...],
    "overall_direction": "maintained",
    "commentary": "...",
    "management_confidence": "medium"
  }},
  "segments": [...],
  "executive_summary": "...",
  "key_highlights": [...]
}}
"""


# =============================================================================
# Section Finder Utilities
# =============================================================================


def find_section(
    document: str, patterns: list[str], max_length: int = 15000
) -> str | None:
    """Find a section in the document by patterns.

    Args:
        document: Full document text.
        patterns: List of regex patterns to match section headers.
        max_length: Maximum section length to return.

    Returns:
        Section text or None if not found.
    """
    best_match = None
    best_position = len(document)

    for pattern in patterns:
        match = re.search(pattern, document)
        if match and match.start() < best_position:
            best_match = match
            best_position = match.start()

    if not best_match:
        return None

    # Extract section (up to next major header or max_length)
    start = best_match.start()
    section = document[start : start + max_length]

    # Try to find natural section end
    next_header = re.search(r"\n#{1,3}\s+[A-Z]", section[1000:])
    if next_header:
        section = section[: 1000 + next_header.start()]

    return section.strip()


def find_mda_section(document: str) -> str | None:
    """Find MD&A section in a filing."""
    return find_section(
        document,
        [
            r"(?i)management\s+discussion",
            r"(?i)förvaltningsberättelse",
            r"(?i)administration\s+report",
            r"(?i)key\s+takeaways",
            r"(?i)business\s+areas?",
        ],
    )


def find_risk_factors_section(document: str) -> str | None:
    """Find risk factors section in a filing."""
    return find_section(
        document,
        [
            r"(?i)risk\s+factors?",
            r"(?i)risker\s+och\s+riskhantering",
            r"(?i)risks?\s+and\s+uncertainties",
        ],
    )


def find_guidance_section(document: str) -> str | None:
    """Find guidance/outlook section in a filing."""
    return find_section(
        document,
        [
            r"(?i)(?:financial\s+)?(?:outlook|guidance|targets?)",
            r"(?i)framtidsutsikter",
            r"(?i)forward[- ]looking",
        ],
    )


def find_segment_section(document: str) -> str | None:
    """Find segment reporting section in a filing."""
    return find_section(
        document,
        [
            r"(?i)segment\s+(?:reporting|information|results)",
            r"(?i)business\s+areas?\s+(?:performance|results)",
            r"(?i)affärsområden",
        ],
    )


def extract_json_from_response(response: str) -> dict | None:
    """Extract JSON from LLM response.

    Utility function for parsing JSON from markdown code blocks or raw text.
    """
    # Try to extract JSON from markdown code blocks
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
    if json_match:
        response = json_match.group(1)

    response = response.strip()

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # Try to find JSON object in response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(response[start:end])
            except json.JSONDecodeError:
                pass
        return None
