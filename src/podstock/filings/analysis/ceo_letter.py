"""CEO Letter / Words from the CEO extraction utilities.

This module provides:
1. Section finder to extract CEO letter from full documents
2. Prompt templates for LLM analysis (used by Claude Code or OpenCode)

The actual LLM analysis is done by:
- Claude Code: Reading the section and analyzing in conversation
- OpenCode/GLM-4.7: Via scripts/filings_glm_driver.py

NO Anthropic API calls are made from this module.
"""

from __future__ import annotations

import json
import re

# =============================================================================
# CEO Letter Extraction Prompts (for reference - used by Claude Code or OpenCode)
# =============================================================================

CEO_LETTER_EXTRACTION_PROMPT = """Analyze this CEO/Chairman letter from a financial report.

COMPANY: {company_name}
FISCAL PERIOD: {fiscal_period}
DOCUMENT TYPE: {document_type}

INSTRUCTIONS:
You are a financial analyst performing deep analysis of management communication.
Extract insights that would help an investor understand:
1. Management's true confidence level (not just spin)
2. Specific commitments that can be tracked
3. How management handles challenges (accountability vs blame-shifting)
4. Strategic priorities and what they're emphasizing

CEO LETTER CONTENT:
{letter_content}

EXTRACT THE FOLLOWING:

1. AUTHOR INFO:
   - Who wrote this? (Name, title)
   - Word count estimate

2. TONE ANALYSIS:
   - Overall tone: optimistic | cautiously_optimistic | neutral | cautious | defensive
   - Confidence level: high | medium | low
   - Look for defensive language, hedging, or excessive qualifiers

3. PROMISES / FORWARD-LOOKING STATEMENTS:
   For each specific commitment, extract:
   - The exact statement
   - What metric it relates to (organic_growth, operating_margin, revenue, eps, etc.)
   - The specific target if mentioned ("4-6%", "above 12%", etc.)
   - Timeframe ("FY 2024", "by 2025", "medium-term", etc.)
   - Confidence language used (expect, target, aim, hope, will, committed to)

   IMPORTANT: Only extract SPECIFIC, TRACKABLE commitments. Vague statements
   like "we will continue to improve" are NOT promises.

4. STRATEGIC THEMES:
   What topics dominate the letter? For each theme:
   - Topic name (e.g., "digital transformation", "cost optimization", "market expansion")
   - Emphasis level: high | medium | low
   - Sentiment: positive | neutral | negative | improving | declining

5. CHALLENGES & ATTRIBUTION:
   How does management discuss challenges? For each:
   - The challenge mentioned
   - Attribution: external (market, macro, competitors) | internal (execution, mistakes) | mixed
   - Tone: explanatory | defensive | dismissive | accountable

   RED FLAGS: Watch for excessive blame-shifting to external factors.

6. HONESTY SIGNALS:
   List positive indicators of transparent communication:
   - Acknowledging mistakes or missed targets
   - Discussing risks openly
   - Avoiding corporate fluff
   - Specific numbers rather than vague statements

7. KEY QUOTES:
   2-3 notable quotes that capture the letter's essence. Categorize each:
   - commitment, vision, warning, achievement, excuse

8. Q&A FORMAT:
   - Is this in interview/Q&A format? (common in Swedish reports)
   - If yes, list the questions addressed

Return as JSON:
{{
  "author": "Name" or null,
  "title": "CEO" | "President" | "Chairman" or null,
  "word_count": <number>,

  "tone": "optimistic" | "cautiously_optimistic" | "neutral" | "cautious" | "defensive",
  "confidence_level": "high" | "medium" | "low",

  "promises": [
    {{
      "statement": "We expect organic growth of 4-6% for full year 2024",
      "metric": "organic_growth",
      "target": "4-6%",
      "timeframe": "FY 2024",
      "confidence_language": "expect"
    }}
  ],

  "themes": [
    {{
      "topic": "operational efficiency",
      "emphasis": "high",
      "sentiment": "positive"
    }}
  ],

  "challenges": [
    {{
      "challenge": "Supply chain disruptions",
      "attribution": "external",
      "tone": "explanatory"
    }}
  ],

  "honesty_signals": [
    "Acknowledges margin pressure from inflation",
    "Admits product launch delay"
  ],

  "key_quotes": [
    {{
      "quote": "We remain committed to...",
      "category": "commitment"
    }}
  ],

  "is_qa_format": true | false,
  "questions_addressed": ["How do you see...?", "What are your priorities?"]
}}
"""


SWEDISH_CEO_LETTER_PROMPT = """Analysera detta VD-ord / ord från VD i en svensk årsredovisning.

BOLAG: {company_name}
RÄKENSKAPSPERIOD: {fiscal_period}
DOKUMENTTYP: {document_type}

INSTRUKTIONER:
Du är en finansanalytiker som gör djupanalys av ledningskommunikation.
Extrahera insikter som hjälper en investerare att förstå:
1. Ledningens verkliga konfidensgrad (inte bara spin)
2. Specifika åtaganden som kan följas upp
3. Hur ledningen hanterar utmaningar (ansvarstagande vs skuldförskjutning)
4. Strategiska prioriteringar och vad de betonar

VD-ORD INNEHÅLL:
{letter_content}

EXTRAHERA FÖLJANDE:

1. FÖRFATTARINFO:
   - Vem har skrivit detta? (Namn, titel)
   - Uppskattad ordräkning

2. TONANALYS:
   - Övergripande ton: optimistic | cautiously_optimistic | neutral | cautious | defensive
   - Konfidensgrad: high | medium | low
   - Leta efter defensivt språk, garderingar, eller överdrivet bruk av förbehåll

3. LÖFTEN / FRAMÅTBLICKANDE UTTALANDEN:
   För varje specifikt åtagande, extrahera:
   - Det exakta uttalandet
   - Vilket nyckeltal det gäller (organic_growth, operating_margin, revenue, eps, etc.)
   - Det specifika målet om det nämns ("4-6%", "över 12%", etc.)
   - Tidsram ("Helår 2024", "till 2025", "på medellång sikt", etc.)
   - Konfidensspråk som används (förväntar, siktar, strävar, hoppas, kommer att, åtar sig)

4. STRATEGISKA TEMAN:
   Vilka ämnen dominerar brevet? För varje tema:
   - Ämnesnamn (t.ex. "digital transformation", "kostnadsoptimering", "marknadsexpansion")
   - Betoning: high | medium | low
   - Sentiment: positive | neutral | negative | improving | declining

5. UTMANINGAR & ATTRIBUTION:
   Hur diskuterar ledningen utmaningar? För varje:
   - Utmaningen som nämns
   - Attribution: external | internal | mixed
   - Ton: explanatory | defensive | dismissive | accountable

6. ÄRLIGHETSSIGNALER:
   Lista positiva indikatorer på transparent kommunikation.

7. NYCKELCITAT:
   2-3 anmärkningsvärda citat. Kategorisera varje:
   - commitment, vision, warning, achievement, excuse

8. Q&A-FORMAT:
   - Är detta i intervju/Q&A-format? (vanligt i svenska rapporter)
   - Om ja, lista frågorna som adresseras

Returnera som JSON (använd engelska nycklar som i mall ovan).
"""


# =============================================================================
# Section Finder Utility
# =============================================================================


def find_ceo_letter_section(full_document: str) -> str | None:
    """Find and extract the CEO letter section from a full document.

    Args:
        full_document: Full document text.

    Returns:
        CEO letter section text, or None if not found.
    """
    # Patterns for actual section headers (formatted as headers, not nav)
    # Look for markdown bold (**) or heading (#) format
    main_patterns = [
        r"(?i)\*\*words?\s+from\s+the\s+ceo\*\*",
        r"(?i)#{1,3}\s*words?\s+from\s+the\s+ceo",
        r"(?i)\*\*(?:letter|message)\s+(?:from|to)\s+(?:the\s+)?(?:ceo|shareholders)\*\*",
        r"(?i)#{1,3}\s*(?:ceo['']?s?|president['']?s?)\s+(?:letter|message|statement)",
        r"(?i)\*\*vd[:-]?\s*ord\*\*",  # Swedish: VD-ord
        r"(?i)#{1,3}\s*(?:ord\s+från\s+vd|vd-ord)",
    ]

    # Find all potential section starts
    candidates = []
    for pattern in main_patterns:
        for match in re.finditer(pattern, full_document):
            # Check that this is followed by actual content (not just another header)
            after = full_document[match.end() : match.end() + 500]

            # Look for content indicators: questions, paragraphs, quotes
            has_content = (
                re.search(r"\?\s*\n", after)  # Q&A format
                or re.search(r"\n[A-Z][a-z]", after)  # Sentence start
                or len(after.split()) > 50  # Substantial text
            )

            if has_content:
                candidates.append((match.start(), match.end()))

    # If no formatted headers found, try plain text patterns
    if not candidates:
        plain_patterns = [
            r"(?i)(?<!\d\s)words?\s+from\s+the\s+ceo(?!\s+\d)",
            r"(?i)(?<!\d\s)vd[:-]?\s*ord(?!\s+\d)",
        ]
        for pattern in plain_patterns:
            for match in re.finditer(pattern, full_document):
                # Skip if this looks like a navigation entry (followed by page ref)
                after = full_document[match.end() : match.end() + 200]
                if re.match(r"^\s*\n\s*\n\s*[A-Z]", after):
                    # Followed by actual content
                    candidates.append((match.start(), match.end()))

    if not candidates:
        return None

    # Take the first candidate that appears to have real content
    start = candidates[0][0]

    # Common next section headers that end the CEO letter
    next_section_patterns = [
        r"\n\*\*(?:Strategy|Global\s+value|Getinge\s+as|External\s+trends)\*\*",
        r"\n#{1,3}\s*(?:Strategy|Governance|Financial|Risk|Sustainability)",
        r"\n\*\*\d+\*\*\s*\n",  # Page numbers like **8**
        r"\n2024\s+Annual\s+Report\s*\n",  # Repeated page footer
        r"\n\s*\n\*\*Introduction\*\*",  # Section marker
    ]

    # Find the end of CEO letter section
    section_text = full_document[start:]
    end = len(section_text)

    for pattern in next_section_patterns:
        # Skip the first 300 chars to avoid matching within header
        for match in re.finditer(pattern, section_text[300:]):
            potential_end = 300 + match.start()
            if potential_end < end:
                end = potential_end
            break  # Take first match for this pattern

    # Also limit by word count (CEO letters rarely exceed 3000 words)
    max_words = 3000
    words = section_text[:end].split()
    if len(words) > max_words:
        end = len(" ".join(words[:max_words]))

    result = section_text[:end].strip()

    # Final validation: should have substantial content
    if len(result.split()) < 100:
        # Too short, might be navigation - look for next occurrence
        if len(candidates) > 1:
            # Try next candidate
            start = candidates[1][0]
            return find_ceo_letter_section(full_document[start:])
        return None

    return result


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
