"""Detector for both positive and negative profit warnings (vinstvarningar).

Detects:
- Omvänd vinstvarning (positive): Better than expected results
- Negativ vinstvarning (negative): Worse than expected, impairments, lowered guidance

Strictly filters out regular scheduled reports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class VinstvarningResult:
    """Result from profit warning detection."""
    is_profit_warning: bool
    direction: str  # "POSITIVE", "NEGATIVE", "NONE"
    confidence: float  # 0.0 to 1.0
    signal_type: str  # "PRELIMINARY_POSITIVE", "PRELIMINARY_NEGATIVE", "GUIDANCE_UP", "GUIDANCE_DOWN", etc.
    action: str  # "STRONG_BUY", "BUY", "STRONG_SELL", "SELL", "SKIP"

    # Details
    is_preliminary: bool
    is_ahead_of_schedule: bool
    change_percent: Optional[float]

    triggers: list[str]
    summary: str


class VinstvarningDetector:
    """Detector for both positive and negative profit warnings."""

    # === POSITIVE patterns ===
    POSITIVE_PRELIMINARY = [
        r'preliminär\w*\s+(?:ebit|resultat|vinst).*(?:öka|förbättr|högre)',
        r'publicerar\s+preliminär.*(?:ökat|förbättrat)',
    ]

    POSITIVE_GUIDANCE = [
        r'höjer\s+(?:prognos|guidance|helårsprognos|utsikter)',
        r'uppjusterar\s+(?:prognos|guidance)',
        r'uppgradering\s+av\s+\w*prognos',  # "uppgradering av marginalprognos"
        r'reviderar\s+upp',
    ]

    POSITIVE_GENERAL = [
        r'omvänd\s+vinstvarning',
        r'positiv\s+vinstvarning',
        r'överträffar\s+förväntning',
        r'överstiger\s+(?:marknadens\s+)?förväntning',  # "överstiger marknadens förväntningar"
        r'bättre\s+än\s+(?:förväntad?|väntat)',
    ]

    AHEAD_OF_SCHEDULE = [
        r'tidigare\s+än\s+(?:aviserat|planerat|kommunicerat)',
        r'i\s+förtid',
    ]

    # === NEGATIVE patterns ===
    NEGATIVE_WARNING = [
        r'vinstvarning',  # Generic profit warning (usually negative)
        r'resultatvarning',
        r'profit\s+warning',
    ]

    NEGATIVE_GUIDANCE = [
        r'sänker\s+(?:prognos|guidance|helårsprognos|utsikter)',
        r'justerar\s+ned',
        r'reviderar\s+ned',
        r'lowers?\s+guidance',
    ]

    NEGATIVE_IMPAIRMENT = [
        r'nedskrivning',
        r'impairment',
        r'write-?down',
        r'goodwillnedskrivning',
    ]

    NEGATIVE_PRELIMINARY = [
        r'preliminär\w*.*(?:nedskrivning|förlust|minska|försämr|lägre)',
        r'preliminär\w*.*(?:sämre|negativ)',
    ]

    NEGATIVE_GENERAL = [
        r'lägre\s+än\s+(?:förväntad?|väntat)',
        r'sämre\s+än\s+(?:förväntad?|väntat)',
        r'understiger\s+förväntning',
        r'svagare\s+(?:resultat|utveckling)',
    ]

    # === DISQUALIFIERS (skip these) ===
    DISQUALIFIERS = [
        r'^kvartalsrapport',
        r'^delårsrapport',
        r'^bokslutskommuniké',
        r'^årsredovisning',
        r'januari\s*[-–]\s*(?:mars|juni|september|december)',
        r'(?:första|andra|tredje|fjärde)\s+kvartalet\s+\d{4}$',
        # Emissions, not profit warnings
        r'företrädesemission',
        r'nyemission',
        r'utfall\s+i.*emission',
    ]

    # === DESCRIPTION DISQUALIFIERS (check description too) ===
    DESC_DISQUALIFIERS = [
        r'bokslutskommuniké',
        r'delårsrapport',
        r'kvartalsrapport',
    ]

    # Number comparison
    COMPARISON_PATTERN = re.compile(
        r'(-?\d+[,.]?\d*)\s*(?:msek|mkr|miljoner|mdr|%)?\s*\((-?\d+[,.]?\d*)\)',
        re.IGNORECASE
    )

    def __init__(self):
        """Initialize with pre-compiled patterns."""
        # Positive
        self._pos_prelim = [re.compile(p, re.IGNORECASE) for p in self.POSITIVE_PRELIMINARY]
        self._pos_guidance = [re.compile(p, re.IGNORECASE) for p in self.POSITIVE_GUIDANCE]
        self._pos_general = [re.compile(p, re.IGNORECASE) for p in self.POSITIVE_GENERAL]
        self._ahead = [re.compile(p, re.IGNORECASE) for p in self.AHEAD_OF_SCHEDULE]

        # Negative
        self._neg_warning = [re.compile(p, re.IGNORECASE) for p in self.NEGATIVE_WARNING]
        self._neg_guidance = [re.compile(p, re.IGNORECASE) for p in self.NEGATIVE_GUIDANCE]
        self._neg_impairment = [re.compile(p, re.IGNORECASE) for p in self.NEGATIVE_IMPAIRMENT]
        self._neg_prelim = [re.compile(p, re.IGNORECASE) for p in self.NEGATIVE_PRELIMINARY]
        self._neg_general = [re.compile(p, re.IGNORECASE) for p in self.NEGATIVE_GENERAL]

        # Disqualifiers
        self._disqualifiers = [re.compile(p, re.IGNORECASE) for p in self.DISQUALIFIERS]
        self._desc_disqualifiers = [re.compile(p, re.IGNORECASE) for p in self.DESC_DISQUALIFIERS]

    def analyze(self, title: str, description: str = "") -> VinstvarningResult:
        """Analyze text for profit warning signals."""
        text = f"{title} {description}"
        title_lower = title.lower()
        text_lower = text.lower()

        triggers = []

        # 1. Check disqualifiers (in title)
        for pattern in self._disqualifiers:
            if pattern.search(title_lower):
                return VinstvarningResult(
                    is_profit_warning=False,
                    direction="NONE",
                    confidence=0.0,
                    signal_type="DISQUALIFIED",
                    action="SKIP",
                    is_preliminary=False,
                    is_ahead_of_schedule=False,
                    change_percent=None,
                    triggers=["Disqualified: scheduled/emission"],
                    summary="Schemalagd rapport eller emission"
                )

        # 1b. Check disqualifiers (in description - catches misleading titles)
        desc_lower = description.lower()
        for pattern in self._desc_disqualifiers:
            if pattern.search(desc_lower):
                return VinstvarningResult(
                    is_profit_warning=False,
                    direction="NONE",
                    confidence=0.0,
                    signal_type="DISQUALIFIED",
                    action="SKIP",
                    is_preliminary=False,
                    is_ahead_of_schedule=False,
                    change_percent=None,
                    triggers=["Disqualified: scheduled report in description"],
                    summary="Schemalagd rapport (identifierad i beskrivning)"
                )

        # Check for ahead of schedule
        is_ahead = any(p.search(text_lower) for p in self._ahead)
        is_preliminary = 'preliminär' in text_lower

        # 2. Check NEGATIVE patterns first (more dangerous to miss)

        # Negative impairment (very strong signal)
        for p in self._neg_impairment:
            if p.search(text_lower):
                triggers.append(f"Impairment: {p.pattern}")
                return self._build_result("NEGATIVE", "IMPAIRMENT", 0.90, triggers, text, is_preliminary, is_ahead)

        # Negative explicit warning
        for p in self._neg_warning:
            if p.search(title_lower):  # Only in title
                # Check it's not "omvänd vinstvarning"
                if 'omvänd' not in text_lower and 'positiv' not in text_lower:
                    triggers.append(f"Explicit warning: {p.pattern}")
                    return self._build_result("NEGATIVE", "EXPLICIT_WARNING", 0.95, triggers, text, is_preliminary, is_ahead)

        # Negative guidance
        for p in self._neg_guidance:
            if p.search(text_lower):
                triggers.append(f"Guidance down: {p.pattern}")
                return self._build_result("NEGATIVE", "GUIDANCE_DOWN", 0.85, triggers, text, is_preliminary, is_ahead)

        # Negative preliminary
        for p in self._neg_prelim:
            if p.search(text_lower):
                triggers.append(f"Preliminary negative: {p.pattern}")
                return self._build_result("NEGATIVE", "PRELIMINARY_NEGATIVE", 0.85, triggers, text, is_preliminary, is_ahead)

        # 3. Check POSITIVE patterns

        # Positive explicit
        for p in self._pos_general:
            if p.search(text_lower):
                triggers.append(f"Positive explicit: {p.pattern}")
                return self._build_result("POSITIVE", "EXPLICIT_POSITIVE", 0.90, triggers, text, is_preliminary, is_ahead)

        # Positive guidance
        for p in self._pos_guidance:
            if p.search(text_lower):
                triggers.append(f"Guidance up: {p.pattern}")
                return self._build_result("POSITIVE", "GUIDANCE_UP", 0.85, triggers, text, is_preliminary, is_ahead)

        # Positive preliminary with ahead of schedule
        if is_preliminary and is_ahead:
            # Check for positive indicators
            positive_words = ['ökat', 'ökning', 'förbättr', 'högre', 'stark']
            if any(w in text_lower for w in positive_words):
                triggers.append("Preliminary + ahead of schedule + positive words")
                return self._build_result("POSITIVE", "PRELIMINARY_AHEAD", 0.90, triggers, text, True, True)

        # 4. No match
        return VinstvarningResult(
            is_profit_warning=False,
            direction="NONE",
            confidence=0.0,
            signal_type="NONE",
            action="SKIP",
            is_preliminary=is_preliminary,
            is_ahead_of_schedule=is_ahead,
            change_percent=None,
            triggers=triggers if triggers else ["No patterns matched"],
            summary="Ej vinstvarning"
        )

    def _extract_change(self, text: str) -> Optional[float]:
        """Extract YoY change percentage."""
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
        direction: str,
        signal_type: str,
        confidence: float,
        triggers: list[str],
        text: str,
        is_preliminary: bool,
        is_ahead: bool,
    ) -> VinstvarningResult:
        """Build result object."""
        change_pct = self._extract_change(text)

        if direction == "POSITIVE":
            action = "STRONG_BUY" if confidence >= 0.85 else "BUY"
            summary = f"POSITIV VINSTVARNING ({signal_type})"
        else:
            action = "STRONG_SELL" if confidence >= 0.85 else "SELL"
            summary = f"NEGATIV VINSTVARNING ({signal_type})"

        if change_pct:
            summary += f" - {change_pct:+.1f}% YoY"

        return VinstvarningResult(
            is_profit_warning=True,
            direction=direction,
            confidence=confidence,
            signal_type=signal_type,
            action=action,
            is_preliminary=is_preliminary,
            is_ahead_of_schedule=is_ahead,
            change_percent=change_pct,
            triggers=triggers,
            summary=summary
        )


def main():
    """Test the detector."""
    detector = VinstvarningDetector()

    test_cases = [
        ("Cheffelo omvänd", "Cheffelo publicerar preliminär EBIT till följd av ökat rörelseresultat", "tidigare än aviserat. 36,8 MSEK (29.4)"),
        ("BICO nedskrivning", "BICO lämnar preliminära siffror för Q3 2025 och meddelar nedskrivning", ""),
        ("Höjer prognos", "XYZ höjer helårsprognosen", ""),
        ("Sänker prognos", "ABC sänker prognosen för helåret", "lägre än väntat"),
        ("Vinstvarning", "DEF AB vinstvarnar", ""),
        ("Kvartalsrapport", "Kvartalsrapport Q3 2025", "omsättning ökade 20%"),
        ("Emission", "Qliro offentliggör preliminärt utfall i företrädesemission", ""),
    ]

    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'

    print("=" * 70)
    print("VINSTVARNING DETECTOR TEST (POSITIVA + NEGATIVA)")
    print("=" * 70)
    print()

    for name, title, desc in test_cases:
        result = detector.analyze(title, desc)

        if result.direction == "POSITIVE":
            color = GREEN
            icon = "🚀"
        elif result.direction == "NEGATIVE":
            color = RED
            icon = "⚠️"
        else:
            color = YELLOW
            icon = "⏭️"

        print(f"{icon} {name}")
        print(f"   Title: {title[:50]}...")
        print(f"   Result: {color}{result.action}{RESET} ({result.direction})")
        print(f"   Type: {result.signal_type}")
        print(f"   Confidence: {result.confidence:.0%}")
        print()


if __name__ == '__main__':
    main()
