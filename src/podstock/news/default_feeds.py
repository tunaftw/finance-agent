"""Default RSS feed configurations for Stockholm Stock Exchange news.

This module provides built-in feed configurations for:
- Nasdaq Nordic regulatory news (Main Market, First North)
- Swedish financial media (Dagens Industri)
"""

from podstock.news.models import FeedConfig, NewsSource, NewsType


def get_default_feeds() -> list[FeedConfig]:
    """Get the list of default feed configurations.

    Returns:
        List of FeedConfig objects for standard news sources.
    """
    return [
        # Nasdaq Nordic - Main Market regulatory notices
        FeedConfig(
            id="nasdaq-main-market",
            name="Nasdaq Main Market Notices",
            url="https://api.news.eu.nasdaq.com/news/rss/mainMarketNotices",
            news_type=NewsType.REGULATORY,
            source=NewsSource.NASDAQ_NORDIC,
            polling_interval_seconds=300,  # 5 min
        ),
        # Nasdaq Nordic - First North notices
        FeedConfig(
            id="nasdaq-first-north",
            name="Nasdaq First North Notices",
            url="https://api.news.eu.nasdaq.com/news/rss/firstNorthNotices",
            news_type=NewsType.REGULATORY,
            source=NewsSource.NASDAQ_NORDIC,
            polling_interval_seconds=300,  # 5 min
        ),
        # Nasdaq Nordic - Company news releases
        FeedConfig(
            id="nasdaq-news-releases",
            name="Nasdaq Nordic News Releases",
            url="https://api.news.eu.nasdaq.com/news/rss/nasdaqNordicNews",
            news_type=NewsType.PRESS_RELEASE,
            source=NewsSource.NASDAQ_NORDIC,
            polling_interval_seconds=300,  # 5 min
        ),
        # GlobeNewswire - Regulatory filings
        FeedConfig(
            id="globenewswire-regulatory",
            name="GlobeNewswire Regulatory Filings",
            url="https://www.globenewswire.com/RssFeed/subjectcode/10-Company%20Regulatory%20Filings/feedTitle/GlobeNewswire",
            news_type=NewsType.REGULATORY,
            source=NewsSource.GLOBENEWSWIRE,
            polling_interval_seconds=600,  # 10 min
        ),
        # Dagens Industri - Business news
        FeedConfig(
            id="di-se",
            name="Dagens Industri",
            url="https://digital.di.se/rss",
            news_type=NewsType.EDITORIAL,
            source=NewsSource.DI_SE,
            polling_interval_seconds=600,  # 10 min
        ),
    ]


# Source to human-readable name mapping
SOURCE_NAMES: dict[NewsSource, str] = {
    NewsSource.NASDAQ_NORDIC: "Nasdaq Nordic",
    NewsSource.GLOBENEWSWIRE: "GlobeNewswire",
    NewsSource.DI_SE: "Dagens Industri",
    NewsSource.CISION: "Cision/MFN",
    NewsSource.OTHER: "Other",
}
