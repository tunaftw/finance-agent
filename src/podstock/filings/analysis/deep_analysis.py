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
