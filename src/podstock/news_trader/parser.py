"""Fast rule-based press release parser for trading signals.

Designed for minimal latency analysis of Swedish regulatory news.
Target: < 1ms analysis time per press release.

Example usage::

    from podstock.news_trader.parser import PressReleaseParser, TradingSignal

    parser = PressReleaseParser()
    signal = parser.analyze(title, description)

    if signal.action == "BUY" and signal.confidence == "HIGH":
        # Execute trade
        pass
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Action(Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"
    SKIP = "SKIP"  # Not relevant for trading


class Confidence(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class NewsType(Enum):
    EARNINGS_SURPRISE = "EARNINGS_SURPRISE"  # Vinstvarning (pos/neg)
    PRELIMINARY_RESULTS = "PRELIMINARY_RESULTS"
    QUARTERLY_REPORT = "QUARTERLY_REPORT"
    ACQUISITION = "ACQUISITION"
    DIVESTITURE = "DIVESTITURE"
    INSIDER_TRADE = "INSIDER_TRADE"
    SHARE_BUYBACK = "SHARE_BUYBACK"
    DIVIDEND = "DIVIDEND"
    GUIDANCE_CHANGE = "GUIDANCE_CHANGE"
    CONTRACT_WIN = "CONTRACT_WIN"
    MANAGEMENT_CHANGE = "MANAGEMENT_CHANGE"
    OTHER = "OTHER"


@dataclass
class TradingSignal:
    """Trading signal from press release analysis."""
    action: Action
    confidence: Confidence
    news_type: NewsType
    reason: str
    metrics: dict  # Extracted numbers and comparisons
    ticker_hint: Optional[str] = None  # If we can extract ticker


@dataclass
class ExtractedMetrics:
    """Extracted financial metrics from text."""
    current_value: Optional[float] = None
    previous_value: Optional[float] = None
    change_percent: Optional[float] = None
    metric_type: Optional[str] = None  # EBIT, revenue, etc.


class PressReleaseParser:
    """Fast rule-based parser for Swedish press releases.

    Optimized for speed - all analysis happens in-memory with
    pre-compiled regex patterns.
    """

    # Pre-compiled patterns for speed
    PATTERNS = {
        # Numbers with comparison: "36,8 MSEK (29.4)" or "36,8 (29,4) MSEK"
        'number_comparison': re.compile(
            r'(\d+[,.]?\d*)\s*(?:MSEK|MSEK|mkr|Mkr|miljoner)?\s*\((\d+[,.]?\d*)\)',
            re.IGNORECASE
        ),
        # Percentage changes
        'percentage': re.compile(
            r'([+-]?\d+[,.]?\d*)\s*(?:procent|%)',
            re.IGNORECASE
        ),
        # Ticker in parentheses: "(ticker: CHEF)" or "(CHEF)"
        'ticker': re.compile(
            r'\((?:ticker:?\s*)?([A-ZÅÄÖ]{2,6})\)',
            re.IGNORECASE
        ),
    }

    # Keyword signals (Swedish + English)
    POSITIVE_KEYWORDS = [
        # Swedish
        'ökat', 'ökning', 'ökar', 'ökade',
        'högre', 'höjer', 'höjd', 'höjning',
        'bättre', 'förbättrad', 'förbättring',
        'överträffar', 'överträffade', 'slår',
        'rekord', 'rekordhög',
        'vinst', 'vinstökning',
        'tillväxt', 'växer',
        'positivt', 'positiv',
        'stark', 'starkt', 'stärkt',
        'framgång', 'framgångsrik',
        'omvänd vinstvarning',  # Positive profit warning
        # English
        'increased', 'increase', 'growth',
        'higher', 'raised', 'better',
        'exceeds', 'exceeded', 'beat',
        'record', 'profit', 'strong',
    ]

    NEGATIVE_KEYWORDS = [
        # Swedish
        'vinstvarning', 'resultatvarning',  # Profit warning (negative)
        'minskat', 'minskning', 'minskar',
        'lägre', 'sänker', 'sänkt',
        'sämre', 'försämrad', 'försämring',
        'förlust', 'förluster',
        'nedskrivning', 'nedskrivningar',
        'negativt', 'negativ',
        'svag', 'svagt', 'försvagad',
        'varning', 'varnar',
        'risk', 'risker',
        'nedgång', 'nedåt',
        # English
        'decreased', 'decrease', 'decline',
        'lower', 'reduced', 'worse',
        'loss', 'losses', 'warning',
        'impairment', 'writedown',
        'weak', 'negative', 'risk',
    ]

    SURPRISE_INDICATORS = [
        'tidigare än aviserat',
        'tidigare än planerat',
        'högre än förväntad',
        'högre än väntat',
        'lägre än förväntad',
        'lägre än väntat',
        'preliminär',
        'reviderar',
        'justerar prognos',
        'ahead of schedule',
        'higher than expected',
        'lower than expected',
        'preliminary',
        'revises guidance',
    ]

    # News type detection
    NEWS_TYPE_PATTERNS = {
        NewsType.PRELIMINARY_RESULTS: [
            'preliminär', 'preliminärt', 'preliminary',
        ],
        NewsType.QUARTERLY_REPORT: [
            'kvartalsrapport', 'delårsrapport', 'q1', 'q2', 'q3', 'q4',
            'quarterly report', 'interim report',
        ],
        NewsType.ACQUISITION: [
            'förvärv', 'förvärvar', 'köper', 'övertar',
            'acquisition', 'acquires', 'to acquire',
        ],
        NewsType.INSIDER_TRADE: [
            'insynshandel', 'insiderhandel', 'insynsperson',
            'insider', 'pdmr',
        ],
        NewsType.SHARE_BUYBACK: [
            'återköp', 'aktieåterköp',
            'buyback', 'share repurchase',
        ],
        NewsType.DIVIDEND: [
            'utdelning', 'extrautdelning',
            'dividend',
        ],
        NewsType.CONTRACT_WIN: [
            'order', 'kontrakt', 'avtal', 'tilldelad',
            'contract', 'awarded', 'wins order',
        ],
        NewsType.MANAGEMENT_CHANGE: [
            'vd', 'ceo', 'cfo', 'styrelse', 'avgår', 'tillträder',
            'appoints', 'resigns', 'board',
        ],
    }

    def __init__(self):
        """Initialize parser with pre-compiled patterns."""
        # Pre-compile keyword sets for O(1) lookup
        self._positive_set = set(self.POSITIVE_KEYWORDS)
        self._negative_set = set(self.NEGATIVE_KEYWORDS)

    def analyze(self, title: str, description: str = "") -> TradingSignal:
        """Analyze press release and return trading signal.

        Args:
            title: Press release title
            description: Press release body/description

        Returns:
            TradingSignal with action, confidence, and reasoning
        """
        text = f"{title} {description}".lower()

        # 1. Detect news type
        news_type = self._detect_news_type(text)

        # 2. Count sentiment signals
        pos_count, neg_count, pos_words, neg_words = self._count_signals(text)

        # 3. Check for surprise indicators
        has_surprise = self._has_surprise(text)

        # 4. Extract metrics
        metrics = self._extract_metrics(text)

        # 5. Try to find ticker
        ticker = self._extract_ticker(title)

        # 6. Determine action and confidence
        action, confidence, reason = self._determine_action(
            pos_count, neg_count,
            pos_words, neg_words,
            has_surprise,
            metrics,
            news_type
        )

        return TradingSignal(
            action=action,
            confidence=confidence,
            news_type=news_type,
            reason=reason,
            metrics={
                'positive_signals': pos_count,
                'negative_signals': neg_count,
                'positive_words': pos_words,
                'negative_words': neg_words,
                'has_surprise': has_surprise,
                'extracted_metrics': metrics.__dict__ if metrics else {},
            },
            ticker_hint=ticker,
        )

    def _detect_news_type(self, text: str) -> NewsType:
        """Detect the type of news from text."""
        for news_type, patterns in self.NEWS_TYPE_PATTERNS.items():
            for pattern in patterns:
                if pattern in text:
                    return news_type
        return NewsType.OTHER

    def _count_signals(self, text: str) -> tuple[int, int, list[str], list[str]]:
        """Count positive and negative signal words."""
        words = set(re.findall(r'\b\w+\b', text))

        pos_found = [w for w in self.POSITIVE_KEYWORDS if w in text]
        neg_found = [w for w in self.NEGATIVE_KEYWORDS if w in text]

        # Special case: "omvänd vinstvarning" is positive
        if 'omvänd vinstvarning' in text or 'omvänd resultatvarning' in text:
            if 'vinstvarning' in neg_found:
                neg_found.remove('vinstvarning')
            if 'resultatvarning' in neg_found:
                neg_found.remove('resultatvarning')
            pos_found.append('omvänd vinstvarning')

        return len(pos_found), len(neg_found), pos_found, neg_found

    def _has_surprise(self, text: str) -> bool:
        """Check if text indicates surprise/unexpected results."""
        return any(indicator in text for indicator in self.SURPRISE_INDICATORS)

    def _extract_metrics(self, text: str) -> Optional[ExtractedMetrics]:
        """Extract financial metrics with YoY comparison."""
        matches = self.PATTERNS['number_comparison'].findall(text)

        if not matches:
            return None

        # Take first match (usually most important)
        current_str, previous_str = matches[0]

        try:
            current = float(current_str.replace(',', '.'))
            previous = float(previous_str.replace(',', '.'))

            if previous != 0:
                change_pct = ((current - previous) / previous) * 100
            else:
                change_pct = 100.0 if current > 0 else -100.0

            return ExtractedMetrics(
                current_value=current,
                previous_value=previous,
                change_percent=change_pct,
            )
        except (ValueError, ZeroDivisionError):
            return None

    def _extract_ticker(self, title: str) -> Optional[str]:
        """Try to extract ticker symbol from title."""
        match = self.PATTERNS['ticker'].search(title)
        if match:
            return match.group(1).upper()
        return None

    def _determine_action(
        self,
        pos_count: int,
        neg_count: int,
        pos_words: list[str],
        neg_words: list[str],
        has_surprise: bool,
        metrics: Optional[ExtractedMetrics],
        news_type: NewsType,
    ) -> tuple[Action, Confidence, str]:
        """Determine trading action based on all signals."""

        # Skip non-trading news
        if news_type in [NewsType.MANAGEMENT_CHANGE, NewsType.OTHER]:
            if not metrics and pos_count == 0 and neg_count == 0:
                return Action.SKIP, Confidence.LOW, "Ej handelsrelevant nyhet"

        # Strong signals from metrics
        if metrics and metrics.change_percent is not None:
            pct = metrics.change_percent

            if pct > 20 and has_surprise:
                return (
                    Action.STRONG_BUY,
                    Confidence.HIGH,
                    f"Stark överraskning: +{pct:.1f}% YoY, publicerat i förtid"
                )
            elif pct > 15:
                return (
                    Action.STRONG_BUY,
                    Confidence.HIGH,
                    f"Kraftig ökning: +{pct:.1f}% YoY"
                )
            elif pct > 5:
                conf = Confidence.HIGH if has_surprise else Confidence.MEDIUM
                return (
                    Action.BUY,
                    conf,
                    f"Positiv utveckling: +{pct:.1f}% YoY"
                )
            elif pct > -5:
                return (
                    Action.HOLD,
                    Confidence.MEDIUM,
                    f"Stabil utveckling: {pct:+.1f}% YoY"
                )
            elif pct > -15:
                conf = Confidence.HIGH if has_surprise else Confidence.MEDIUM
                return (
                    Action.SELL,
                    conf,
                    f"Negativ utveckling: {pct:.1f}% YoY"
                )
            else:
                return (
                    Action.STRONG_SELL,
                    Confidence.HIGH,
                    f"Kraftig nedgång: {pct:.1f}% YoY"
                )

        # Fallback to keyword analysis
        if pos_count > neg_count + 2:
            conf = Confidence.HIGH if has_surprise else Confidence.MEDIUM
            return (
                Action.BUY,
                conf,
                f"Positiva signaler: {', '.join(pos_words[:3])}"
            )
        elif neg_count > pos_count + 2:
            conf = Confidence.HIGH if has_surprise else Confidence.MEDIUM
            return (
                Action.SELL,
                conf,
                f"Negativa signaler: {', '.join(neg_words[:3])}"
            )
        elif pos_count > neg_count:
            return (
                Action.BUY,
                Confidence.LOW,
                f"Svagt positiva signaler"
            )
        elif neg_count > pos_count:
            return (
                Action.SELL,
                Confidence.LOW,
                f"Svagt negativa signaler"
            )
        else:
            return (
                Action.HOLD,
                Confidence.LOW,
                "Neutral/oklar signal"
            )
