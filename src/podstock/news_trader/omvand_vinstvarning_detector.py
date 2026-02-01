"""Specialized detector for "omvänd vinstvarning" (positive profit warnings).

Strictly focused on detecting preliminary results published ahead of schedule,
NOT regular quarterly reports.

Key signals:
- "preliminär" + "tidigare än aviserat/planerat"
- "omvänd vinstvarning"
- "höjer prognos" / "uppjusterar"
- Unscheduled positive announcements

This detector is intentionally strict to minimize false positives.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class OmvandVinstvarningResult:
    """Result from omvänd vinstvarning detection."""
    is_omvand_vinstvarning: bool
    confidence: float  # 0.0 to 1.0

    # Signal details
    signal_type: str  # "PRELIMINARY_AHEAD", "RAISES_GUIDANCE", "EXPLICIT_WARNING", "NONE"
    action: str  # "STRONG_BUY", "BUY", "SKIP"

    # Extracted data
    is_preliminary: bool
    is_ahead_of_schedule: bool
    has_positive_surprise: bool
    change_percent: Optional[float]

    # Reasoning
    triggers: list[str]
    summary: str


class OmvandVinstvarningDetector:
    """Strict detector for omvänd vinstvarning only.

    Does NOT trigger on:
    - Regular scheduled quarterly reports
    - Annual reports
    - Trading updates without surprise element
    - News with negative changes

    ONLY triggers on:
    - Preliminary results published ahead of schedule
    - Explicit "omvänd vinstvarning" announcements
    - Guidance raises ("höjer prognos")
    """

    # === MUST HAVE patterns (at least one required) ===

    # Preliminary results
    PRELIMINARY_PATTERNS = [
        r'preliminär\w*\s+(?:ebit|resultat|vinst|omsättning)',
        r'preliminary\s+(?:ebit|results?|profit|revenue)',
        r'publicerar\s+preliminär',
        r'announces?\s+preliminary',
    ]

    # Ahead of schedule indicators
    AHEAD_OF_SCHEDULE_PATTERNS = [
        r'tidigare\s+än\s+(?:aviserat|planerat|kommunicerat|förväntat)',
        r'ahead\s+of\s+schedule',
        r'earlier\s+than\s+(?:planned|expected|announced)',
        r'i\s+förtid',
        r'före\s+(?:plan|schema)',
    ]

    # Explicit profit warning reversal
    EXPLICIT_WARNING_PATTERNS = [
        r'omvänd\s+vinstvarning',
        r'positiv\s+vinstvarning',
        r'positive\s+profit\s+warning',
        r'reverse\s+profit\s+warning',
    ]

    # Guidance raises
    GUIDANCE_RAISE_PATTERNS = [
        r'höjer\s+(?:prognos|guidance|helårsprognos|utsikter)',
        r'raises?\s+(?:guidance|outlook|forecast)',
        r'uppjusterar\s+(?:prognos|guidance)',
        r'upgrades?\s+(?:guidance|outlook)',
        r'justerar\s+upp',
        r'reviderar\s+upp',
    ]

    # === MUST NOT HAVE patterns (disqualifiers) ===

    DISQUALIFIER_PATTERNS = [
        r'kvartalsrapport',
        r'delårsrapport',
        r'quarterly\s+report',
        r'interim\s+report',
        r'årsredovisning',
        r'annual\s+report',
        r'bokslutskommuniké',
        r'year-end\s+report',
        # Scheduled report titles
        r'januari\s*[-–]\s*(?:mars|juni|september|december)',
        r'q[1-4]\s+\d{4}\s*$',  # "Q3 2025" at end of title (scheduled)
    ]

    # === POSITIVE indicators (boost confidence) ===

    POSITIVE_PATTERNS = [
        r'ökat\s+rörelseresultat',
        r'ökad\s+(?:vinst|omsättning|försäljning)',
        r'förbättrat\s+resultat',
        r'högre\s+än\s+(?:förväntad?|väntat)',
        r'överträffar',
        r'bättre\s+än\s+(?:förväntad?|väntat)',
        r'increased\s+(?:profit|revenue|sales)',
        r'better\s+than\s+expected',
        r'exceeds?\s+expectations?',
    ]

    # Number comparison pattern
    COMPARISON_PATTERN = re.compile(
        r'(\d+[,.]?\d*)\s*(?:msek|mkr|miljoner|mdr|%)?\s*\((\d+[,.]?\d*)\)',
        re.IGNORECASE
    )

    def __init__(self):
        """Initialize with pre-compiled patterns."""
        self._preliminary = [re.compile(p, re.IGNORECASE) for p in self.PRELIMINARY_PATTERNS]
        self._ahead = [re.compile(p, re.IGNORECASE) for p in self.AHEAD_OF_SCHEDULE_PATTERNS]
        self._explicit = [re.compile(p, re.IGNORECASE) for p in self.EXPLICIT_WARNING_PATTERNS]
        self._guidance = [re.compile(p, re.IGNORECASE) for p in self.GUIDANCE_RAISE_PATTERNS]
        self._disqualifiers = [re.compile(p, re.IGNORECASE) for p in self.DISQUALIFIER_PATTERNS]
        self._positive = [re.compile(p, re.IGNORECASE) for p in self.POSITIVE_PATTERNS]

    def analyze(self, title: str, description: str = "") -> OmvandVinstvarningResult:
        """Analyze text for omvänd vinstvarning signals.

        Args:
            title: Press release title
            description: Press release body

        Returns:
            OmvandVinstvarningResult with detection results
        """
        text = f"{title} {description}"
        title_lower = title.lower()
        text_lower = text.lower()

        triggers = []

        # 1. Check for disqualifiers first
        for pattern in self._disqualifiers:
            if pattern.search(title_lower):
                return OmvandVinstvarningResult(
                    is_omvand_vinstvarning=False,
                    confidence=0.0,
                    signal_type="NONE",
                    action="SKIP",
                    is_preliminary=False,
                    is_ahead_of_schedule=False,
                    has_positive_surprise=False,
                    change_percent=None,
                    triggers=["Disqualified: scheduled report"],
                    summary="Schemalagd rapport - ej omvänd vinstvarning"
                )

        # 2. Check for explicit warning patterns (highest confidence)
        for pattern in self._explicit:
            if pattern.search(text_lower):
                triggers.append(f"Explicit: {pattern.pattern}")
                return self._build_result(
                    signal_type="EXPLICIT_WARNING",
                    confidence=0.95,
                    triggers=triggers,
                    text=text
                )

        # 3. Check for guidance raise
        for pattern in self._guidance:
            if pattern.search(text_lower):
                triggers.append(f"Guidance raise: {pattern.pattern}")
                return self._build_result(
                    signal_type="RAISES_GUIDANCE",
                    confidence=0.85,
                    triggers=triggers,
                    text=text
                )

        # 4. Check for preliminary + ahead of schedule (the classic combo)
        is_preliminary = any(p.search(text_lower) for p in self._preliminary)
        is_ahead = any(p.search(text_lower) for p in self._ahead)

        if is_preliminary:
            triggers.append("Preliminary results")
        if is_ahead:
            triggers.append("Ahead of schedule")

        if is_preliminary and is_ahead:
            # This is the classic omvänd vinstvarning pattern
            return self._build_result(
                signal_type="PRELIMINARY_AHEAD",
                confidence=0.90,
                triggers=triggers,
                text=text,
                is_preliminary=True,
                is_ahead=True
            )

        # 5. Check for preliminary + positive surprise (without explicit "ahead of schedule")
        if is_preliminary:
            positive_matches = sum(1 for p in self._positive if p.search(text_lower))
            change_pct = self._extract_change(text)

            if positive_matches >= 2 or (change_pct and change_pct > 15):
                triggers.append(f"Positive patterns: {positive_matches}")
                if change_pct:
                    triggers.append(f"Change: +{change_pct:.1f}%")

                return self._build_result(
                    signal_type="PRELIMINARY_AHEAD",
                    confidence=0.75,
                    triggers=triggers,
                    text=text,
                    is_preliminary=True,
                    is_ahead=False,
                    change_pct=change_pct
                )

        # 6. No match
        return OmvandVinstvarningResult(
            is_omvand_vinstvarning=False,
            confidence=0.0,
            signal_type="NONE",
            action="SKIP",
            is_preliminary=is_preliminary,
            is_ahead_of_schedule=is_ahead,
            has_positive_surprise=False,
            change_percent=None,
            triggers=triggers if triggers else ["No qualifying patterns found"],
            summary="Ej omvänd vinstvarning"
        )

    def _extract_change(self, text: str) -> Optional[float]:
        """Extract YoY change percentage from text."""
        matches = self.COMPARISON_PATTERN.findall(text)
        if not matches:
            return None

        try:
            current = float(matches[0][0].replace(',', '.'))
            previous = float(matches[0][1].replace(',', '.'))
            if previous != 0:
                return ((current - previous) / abs(previous)) * 100
        except (ValueError, ZeroDivisionError):
            pass

        return None

    def _build_result(
        self,
        signal_type: str,
        confidence: float,
        triggers: list[str],
        text: str,
        is_preliminary: bool = False,
        is_ahead: bool = False,
        change_pct: Optional[float] = None,
    ) -> OmvandVinstvarningResult:
        """Build a positive result."""

        # Extract change if not provided
        if change_pct is None:
            change_pct = self._extract_change(text)

        # Check for positive indicators
        has_positive = any(p.search(text.lower()) for p in self._positive)
        if change_pct and change_pct > 0:
            has_positive = True

        # Determine action
        if confidence >= 0.85:
            action = "STRONG_BUY"
        elif confidence >= 0.70:
            action = "BUY"
        else:
            action = "SKIP"

        # Build summary
        summary_parts = ["OMVÄND VINSTVARNING DETEKTERAD"]
        if is_preliminary:
            summary_parts.append("preliminärt resultat")
        if is_ahead:
            summary_parts.append("publicerat i förtid")
        if change_pct:
            summary_parts.append(f"+{change_pct:.1f}% YoY")

        return OmvandVinstvarningResult(
            is_omvand_vinstvarning=True,
            confidence=confidence,
            signal_type=signal_type,
            action=action,
            is_preliminary=is_preliminary,
            is_ahead_of_schedule=is_ahead,
            has_positive_surprise=has_positive,
            change_percent=change_pct,
            triggers=triggers,
            summary=" - ".join(summary_parts)
        )


def main():
    """Test the detector."""
    detector = OmvandVinstvarningDetector()

    test_cases = [
        # Should trigger (omvänd vinstvarning)
        {
            "name": "Cheffelo Jan 2026 (SHOULD TRIGGER)",
            "title": "Cheffelo publicerar preliminär EBIT för fjärde kvartalet till följd av ökat rörelseresultat",
            "description": "Cheffelo publicerar i dag, tidigare än aviserat, en preliminär EBIT. Det preliminära rörelseresultatet uppgår till cirka 36,8 MSEK (29.4).",
        },
        {
            "name": "Höjer prognos (SHOULD TRIGGER)",
            "title": "XYZ AB höjer helårsprognosen efter starkt kvartal",
            "description": "XYZ AB höjer sin prognos för rörelseresultatet till 200-220 MSEK från tidigare 150-170 MSEK.",
        },
        # Should NOT trigger (regular reports)
        {
            "name": "Vanlig Q3 rapport (SHOULD NOT TRIGGER)",
            "title": "Cheffelo presenterar resultat för tredje kvartalet 2025",
            "description": "Nettoomsättningen ökade med 23.3% till 266.4 MSEK (216.0).",
        },
        {
            "name": "Kvartalsrapport (SHOULD NOT TRIGGER)",
            "title": "Kinneviks delårsrapport 1 januari – 31 mars 2025",
            "description": "Kinnevik redovisar ett NAV om 45 miljarder kronor.",
        },
        {
            "name": "Volvo Q1 (SHOULD NOT TRIGGER)",
            "title": "AB Volvo: Volvokoncernen - det första kvartalet 2025",
            "description": "Nettoomsättningen minskade med 21% till 120 MSEK (152).",
        },
    ]

    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'

    print("=" * 70)
    print("OMVÄND VINSTVARNING DETECTOR - TEST")
    print("=" * 70)
    print()

    for case in test_cases:
        result = detector.analyze(case["title"], case["description"])

        if result.is_omvand_vinstvarning:
            status = f"{GREEN}✅ TRIGGERED{RESET}"
        else:
            status = f"{YELLOW}⏭️  SKIPPED{RESET}"

        should_trigger = "SHOULD TRIGGER" in case["name"]
        correct = (result.is_omvand_vinstvarning == should_trigger)

        if not correct:
            status += f" {RED}(WRONG!){RESET}"

        print(f"{case['name']}")
        print(f"  Title: {case['title'][:50]}...")
        print(f"  Result: {status}")
        print(f"  Confidence: {result.confidence:.0%}")
        print(f"  Action: {result.action}")
        print(f"  Triggers: {result.triggers}")
        print()

    print("=" * 70)


if __name__ == '__main__':
    main()
