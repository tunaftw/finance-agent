"""Specialized detector for profit warnings (vinstvarningar).

Focused on detecting:
- Negative profit warnings (vinstvarning) - company warns of lower results
- Positive profit warnings (omvänd vinstvarning) - company announces better than expected

Swedish regulatory framework requires listed companies to publish
profit warnings when results deviate significantly from expectations.

Example usage::

    from podstock.news_trader.profit_warning_detector import ProfitWarningDetector

    detector = ProfitWarningDetector()
    result = detector.analyze(title, description)

    if result.is_profit_warning:
        print(f"{'POSITIVE' if result.is_positive else 'NEGATIVE'}: {result.summary}")
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class WarningType(Enum):
    POSITIVE = "POSITIVE"  # Omvänd vinstvarning - better than expected
    NEGATIVE = "NEGATIVE"  # Vinstvarning - worse than expected
    NOT_WARNING = "NOT_WARNING"


class Metric(Enum):
    EBIT = "EBIT"
    EBITDA = "EBITDA"
    NET_PROFIT = "NET_PROFIT"  # Nettoresultat
    REVENUE = "REVENUE"  # Omsättning
    EPS = "EPS"  # Vinst per aktie
    MARGIN = "MARGIN"
    OTHER = "OTHER"


@dataclass
class ProfitWarningResult:
    """Result from profit warning analysis."""
    is_profit_warning: bool
    warning_type: WarningType
    confidence: float  # 0.0 to 1.0

    # Extracted metrics
    metric_type: Optional[Metric] = None
    current_value: Optional[float] = None
    previous_value: Optional[float] = None
    expected_value: Optional[float] = None
    change_percent: Optional[float] = None

    # Context
    is_preliminary: bool = False
    is_ahead_of_schedule: bool = False
    quarter: Optional[str] = None  # Q1, Q2, Q3, Q4
    year: Optional[int] = None

    # Recommendation
    action: str = "HOLD"  # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    summary: str = ""
    reasoning: list[str] = None

    def __post_init__(self):
        if self.reasoning is None:
            self.reasoning = []


class ProfitWarningDetector:
    """Specialized detector for Swedish profit warnings.

    Optimized for speed and accuracy on vinstvarning detection.
    """

    # Title patterns that strongly indicate profit warning
    TITLE_PATTERNS = {
        # Explicit profit warnings
        'vinstvarning': (WarningType.NEGATIVE, 0.95),
        'resultatvarning': (WarningType.NEGATIVE, 0.95),
        'profit warning': (WarningType.NEGATIVE, 0.95),
        'earnings warning': (WarningType.NEGATIVE, 0.95),

        # Positive reversals
        'omvänd vinstvarning': (WarningType.POSITIVE, 0.95),
        'positiv vinstvarning': (WarningType.POSITIVE, 0.95),
        'positive profit warning': (WarningType.POSITIVE, 0.95),

        # Preliminary results (often signals surprise)
        'preliminär ebit': (None, 0.7),  # Need to check direction
        'preliminärt resultat': (None, 0.7),
        'preliminary results': (None, 0.7),
        'preliminary ebit': (None, 0.7),

        # Guidance changes
        'höjer prognos': (WarningType.POSITIVE, 0.85),
        'höjer helårsprognos': (WarningType.POSITIVE, 0.85),
        'raises guidance': (WarningType.POSITIVE, 0.85),
        'upgrades guidance': (WarningType.POSITIVE, 0.85),
        'sänker prognos': (WarningType.NEGATIVE, 0.85),
        'sänker helårsprognos': (WarningType.NEGATIVE, 0.85),
        'lowers guidance': (WarningType.NEGATIVE, 0.85),
        'cuts guidance': (WarningType.NEGATIVE, 0.85),

        # Result announcements (need to check direction)
        'ökat rörelseresultat': (WarningType.POSITIVE, 0.8),
        'ökad vinst': (WarningType.POSITIVE, 0.8),
        'kraftigt förbättrat resultat': (WarningType.POSITIVE, 0.85),
        'minskat rörelseresultat': (WarningType.NEGATIVE, 0.8),
        'minskad vinst': (WarningType.NEGATIVE, 0.8),
        'kraftigt försämrat resultat': (WarningType.NEGATIVE, 0.85),

        # Strong beat/miss signals
        'överträffar förväntningarna': (WarningType.POSITIVE, 0.85),
        'beats expectations': (WarningType.POSITIVE, 0.85),
        'exceeds expectations': (WarningType.POSITIVE, 0.85),
        'understiger förväntningarna': (WarningType.NEGATIVE, 0.85),
        'misses expectations': (WarningType.NEGATIVE, 0.85),
        'below expectations': (WarningType.NEGATIVE, 0.85),
    }

    # Body patterns that confirm/strengthen signal
    BODY_POSITIVE_PATTERNS = [
        r'högre än (?:tidigare |)(?:förväntad?|väntat|kommunicerat)',
        r'bättre än (?:tidigare |)(?:förväntad?|väntat)',
        r'överträffar',
        r'ökning med',
        r'ökat med',
        r'förbättring',
        r'tidigare än aviserat',  # Publishing early = usually positive
        r'higher than (?:previously |)expected',
        r'better than (?:previously |)expected',
        r'ahead of schedule',
    ]

    BODY_NEGATIVE_PATTERNS = [
        r'lägre än (?:tidigare |)(?:förväntad?|väntat|kommunicerat)',
        r'sämre än (?:tidigare |)(?:förväntad?|väntat)',
        r'understiger',
        r'minskning med',
        r'minskat med',
        r'försämring',
        r'svagare (?:efterfrågan|marknad|utveckling)',
        r'lower than (?:previously |)expected',
        r'worse than (?:previously |)expected',
        r'weaker (?:demand|market)',
    ]

    # Metric extraction patterns
    METRIC_PATTERNS = {
        Metric.EBIT: re.compile(
            r'(?:rörelseresultat(?:et)?|ebit)\s*(?:för\s+)?(?:q\d|kvartal|helår|perioden)?\s*'
            r'(?:uppgår till|uppgick till|blev|är|på)?\s*(?:cirka\s+)?'
            r'(-?\d+[,.]?\d*)\s*(?:msek|mkr|miljoner)',
            re.IGNORECASE
        ),
        Metric.REVENUE: re.compile(
            r'(?:omsättning(?:en)?|intäkter(?:na)?|nettoomsättning)\s*'
            r'(?:uppgår till|uppgick till|blev|är|på)?\s*(?:cirka\s+)?'
            r'(-?\d+[,.]?\d*)\s*(?:msek|mkr|miljoner|mdr)',
            re.IGNORECASE
        ),
        Metric.NET_PROFIT: re.compile(
            r'(?:nettoresultat(?:et)?|resultat efter skatt)\s*'
            r'(?:uppgår till|uppgick till|blev|är|på)?\s*(?:cirka\s+)?'
            r'(-?\d+[,.]?\d*)\s*(?:msek|mkr|miljoner)',
            re.IGNORECASE
        ),
    }

    # Comparison pattern: "36,8 MSEK (29.4)" extracts current and previous
    COMPARISON_PATTERN = re.compile(
        r'(-?\d+[,.]?\d*)\s*(?:msek|mkr|miljoner|mdr|%)?\s*\((-?\d+[,.]?\d*)\)',
        re.IGNORECASE
    )

    # Quarter detection
    QUARTER_PATTERN = re.compile(
        r'(?:q(\d)|(?:första|andra|tredje|fjärde)\s+kvartalet|kvartal\s*(\d))',
        re.IGNORECASE
    )

    # Year detection
    YEAR_PATTERN = re.compile(r'20(\d{2})')

    def __init__(self):
        """Initialize detector with pre-compiled patterns."""
        self._positive_body_patterns = [re.compile(p, re.IGNORECASE) for p in self.BODY_POSITIVE_PATTERNS]
        self._negative_body_patterns = [re.compile(p, re.IGNORECASE) for p in self.BODY_NEGATIVE_PATTERNS]

    def analyze(self, title: str, description: str = "") -> ProfitWarningResult:
        """Analyze text for profit warning signals.

        Args:
            title: Press release title
            description: Press release body

        Returns:
            ProfitWarningResult with analysis
        """
        text = f"{title} {description}"
        text_lower = text.lower()
        title_lower = title.lower()

        reasoning = []

        # 1. Check title for strong patterns
        warning_type = WarningType.NOT_WARNING
        confidence = 0.0

        for pattern, (wtype, conf) in self.TITLE_PATTERNS.items():
            if pattern in title_lower:
                if wtype is not None:
                    warning_type = wtype
                    confidence = max(confidence, conf)
                    reasoning.append(f"Titel innehåller '{pattern}'")
                else:
                    # Pattern found but need to determine direction
                    confidence = max(confidence, conf)
                break

        # 2. Check body patterns to determine/confirm direction
        pos_matches = sum(1 for p in self._positive_body_patterns if p.search(text_lower))
        neg_matches = sum(1 for p in self._negative_body_patterns if p.search(text_lower))

        if pos_matches > neg_matches:
            if warning_type == WarningType.NOT_WARNING or warning_type is None:
                warning_type = WarningType.POSITIVE
                confidence = max(confidence, 0.6 + pos_matches * 0.1)
            reasoning.append(f"Positiva mönster i text: {pos_matches}")
        elif neg_matches > pos_matches:
            if warning_type == WarningType.NOT_WARNING or warning_type is None:
                warning_type = WarningType.NEGATIVE
                confidence = max(confidence, 0.6 + neg_matches * 0.1)
            reasoning.append(f"Negativa mönster i text: {neg_matches}")

        # 3. Extract metrics with comparison
        current_value = None
        previous_value = None
        change_percent = None
        metric_type = None

        comparisons = self.COMPARISON_PATTERN.findall(text)
        if comparisons:
            try:
                current_str, previous_str = comparisons[0]
                current_value = float(current_str.replace(',', '.'))
                previous_value = float(previous_str.replace(',', '.'))

                if previous_value != 0:
                    change_percent = ((current_value - previous_value) / abs(previous_value)) * 100

                    # Update warning type based on numbers
                    if change_percent > 10:
                        if warning_type == WarningType.NOT_WARNING:
                            warning_type = WarningType.POSITIVE
                        confidence = max(confidence, 0.85)
                        reasoning.append(f"Stark positiv förändring: {change_percent:+.1f}%")
                    elif change_percent < -10:
                        if warning_type == WarningType.NOT_WARNING:
                            warning_type = WarningType.NEGATIVE
                        confidence = max(confidence, 0.85)
                        reasoning.append(f"Stark negativ förändring: {change_percent:+.1f}%")

                # Determine metric type
                for mtype, pattern in self.METRIC_PATTERNS.items():
                    if pattern.search(text):
                        metric_type = mtype
                        break

            except (ValueError, IndexError):
                pass

        # 4. Check for preliminary/early release (strengthens signal)
        is_preliminary = 'preliminär' in text_lower or 'preliminary' in text_lower
        is_ahead_of_schedule = 'tidigare än aviserat' in text_lower or 'ahead of schedule' in text_lower

        if is_ahead_of_schedule and warning_type != WarningType.NOT_WARNING:
            confidence = min(confidence + 0.1, 1.0)
            reasoning.append("Publicerat tidigare än planerat")

        # 5. Extract quarter and year
        quarter = None
        quarter_match = self.QUARTER_PATTERN.search(text)
        if quarter_match:
            q = quarter_match.group(1) or quarter_match.group(2)
            if q:
                quarter = f"Q{q}"

        year = None
        year_match = self.YEAR_PATTERN.search(text)
        if year_match:
            year = 2000 + int(year_match.group(1))

        # 6. Determine action
        is_profit_warning = warning_type != WarningType.NOT_WARNING and confidence >= 0.5
        action = self._determine_action(warning_type, confidence, change_percent)

        # 7. Generate summary
        summary = self._generate_summary(
            warning_type, metric_type, current_value, previous_value,
            change_percent, is_preliminary, is_ahead_of_schedule
        )

        return ProfitWarningResult(
            is_profit_warning=is_profit_warning,
            warning_type=warning_type,
            confidence=confidence,
            metric_type=metric_type,
            current_value=current_value,
            previous_value=previous_value,
            change_percent=change_percent,
            is_preliminary=is_preliminary,
            is_ahead_of_schedule=is_ahead_of_schedule,
            quarter=quarter,
            year=year,
            action=action,
            summary=summary,
            reasoning=reasoning,
        )

    def _determine_action(
        self,
        warning_type: WarningType,
        confidence: float,
        change_percent: Optional[float]
    ) -> str:
        """Determine trading action."""
        if warning_type == WarningType.NOT_WARNING:
            return "HOLD"

        if warning_type == WarningType.POSITIVE:
            if confidence >= 0.85 or (change_percent and change_percent > 20):
                return "STRONG_BUY"
            elif confidence >= 0.6:
                return "BUY"
            else:
                return "HOLD"

        elif warning_type == WarningType.NEGATIVE:
            if confidence >= 0.85 or (change_percent and change_percent < -20):
                return "STRONG_SELL"
            elif confidence >= 0.6:
                return "SELL"
            else:
                return "HOLD"

        return "HOLD"

    def _generate_summary(
        self,
        warning_type: WarningType,
        metric_type: Optional[Metric],
        current: Optional[float],
        previous: Optional[float],
        change_pct: Optional[float],
        is_preliminary: bool,
        is_ahead: bool,
    ) -> str:
        """Generate human-readable summary."""
        if warning_type == WarningType.NOT_WARNING:
            return "Ingen vinstvarning detekterad"

        parts = []

        if warning_type == WarningType.POSITIVE:
            parts.append("POSITIV vinstvarning")
        else:
            parts.append("NEGATIV vinstvarning")

        if is_preliminary:
            parts.append("(preliminärt)")

        if metric_type and current is not None and previous is not None:
            metric_name = {
                Metric.EBIT: "EBIT",
                Metric.REVENUE: "Omsättning",
                Metric.NET_PROFIT: "Nettoresultat",
            }.get(metric_type, "Resultat")

            parts.append(f"- {metric_name}: {current:.1f} MSEK (fg år: {previous:.1f})")

        if change_pct is not None:
            parts.append(f"({change_pct:+.1f}% YoY)")

        if is_ahead:
            parts.append("- publicerat i förtid")

        return " ".join(parts)


def main():
    """Test the detector."""
    detector = ProfitWarningDetector()

    test_cases = [
        (
            "Cheffelo publicerar preliminär EBIT för fjärde kvartalet till följd av ökat rörelseresultat",
            """Cheffelo, en lönsam skandinavisk leverantör av matkassar, publicerar i dag,
            tidigare än aviserat, en preliminär EBIT för fjärde kvartalet. Det preliminära
            rörelseresultatet (EBIT) för Q4 2025 uppgår till cirka 36,8 MSEK (29.4)."""
        ),
        (
            "ABC AB vinstvarnar - sänker prognos för helåret",
            """ABC AB meddelar att rörelseresultatet förväntas uppgå till 15 MSEK (25)
            vilket är lägre än tidigare kommunicerat på grund av svagare efterfrågan."""
        ),
        (
            "Kvartalsrapport Q3 2025",
            """Bolaget rapporterar omsättning om 100 MSEK (98) och rörelseresultat om 10 MSEK (10)."""
        ),
    ]

    for title, desc in test_cases:
        print("=" * 60)
        result = detector.analyze(title, desc)
        print(f"Title: {title[:50]}...")
        print(f"Is profit warning: {result.is_profit_warning}")
        print(f"Type: {result.warning_type.value}")
        print(f"Confidence: {result.confidence:.0%}")
        print(f"Action: {result.action}")
        print(f"Summary: {result.summary}")
        print(f"Reasoning: {result.reasoning}")
        print()


if __name__ == '__main__':
    main()
