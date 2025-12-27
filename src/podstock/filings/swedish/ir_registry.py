"""Registry of Swedish companies and their IR page URLs.

This module provides a curated database of Swedish listed companies
and their investor relations page URLs for scraping financial reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MarketSegment(str, Enum):
    """Nasdaq Stockholm market segments."""

    LARGE_CAP = "large_cap"
    MID_CAP = "mid_cap"
    SMALL_CAP = "small_cap"
    FIRST_NORTH = "first_north"


@dataclass
class CompanyIRInfo:
    """Information about a company's IR page."""

    id: str
    name: str
    ticker: str
    ir_url: str
    segment: MarketSegment
    report_patterns: list[str] = field(default_factory=list)
    backup_urls: list[str] = field(default_factory=list)  # Fallback URLs
    language: str = "en"  # Preferred language for reports
    notes: str = ""


# Large Cap companies (top ~100 by market cap)
# IR URLs verified December 2024
LARGE_CAP_COMPANIES: dict[str, CompanyIRInfo] = {
    "evolution": CompanyIRInfo(
        id="evolution",
        name="Evolution AB",
        ticker="EVO",
        ir_url="https://www.evolution.com/investors/reports/",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Interim Report", "Q"],
        backup_urls=["https://www.evolution.com/investors/"],
    ),
    "ericsson": CompanyIRInfo(
        id="ericsson",
        name="Telefonaktiebolaget LM Ericsson",
        ticker="ERIC B",
        ir_url="https://www.ericsson.com/en/investors/financial-reports",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
    ),
    "hm": CompanyIRInfo(
        id="hm",
        name="H & M Hennes & Mauritz AB",
        ticker="HM B",
        ir_url="https://hmgroup.com/investors/reports/",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
    ),
    "volvo": CompanyIRInfo(
        id="volvo",
        name="AB Volvo",
        ticker="VOLVO B",
        ir_url="https://www.volvogroup.com/en/investors/reports-and-presentations.html",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
    ),
    "atlas-copco": CompanyIRInfo(
        id="atlas-copco",
        name="Atlas Copco AB",
        ticker="ATCO A",
        ir_url="https://www.atlascopcogroup.com/en/investors/financial-publications",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
    ),
    "investor": CompanyIRInfo(
        id="investor",
        name="Investor AB",
        ticker="INVE B",
        ir_url="https://www.investorab.com/investors/reports-presentations/",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Interim Report"],
    ),
    "abb": CompanyIRInfo(
        id="abb",
        name="ABB Ltd",
        ticker="ABB",
        ir_url="https://global.abb/group/en/investors/results-and-reports",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
        notes="Swiss company listed on Nasdaq Stockholm",
    ),
    "sandvik": CompanyIRInfo(
        id="sandvik",
        name="Sandvik AB",
        ticker="SAND",
        ir_url="https://www.home.sandvik/en/investors/reports-and-presentations/",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
    ),
    "nordea": CompanyIRInfo(
        id="nordea",
        name="Nordea Bank Abp",
        ticker="NDA SE",
        ir_url="https://www.nordea.com/en/investors/reports-and-presentations",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
    ),
    "seb": CompanyIRInfo(
        id="seb",
        name="Skandinaviska Enskilda Banken AB",
        ticker="SEB A",
        ir_url="https://sebgroup.com/investor-relations/reports-and-publications",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
    ),
    "svenska-handelsbanken": CompanyIRInfo(
        id="svenska-handelsbanken",
        name="Svenska Handelsbanken AB",
        ticker="SHB A",
        ir_url="https://www.handelsbanken.com/en/investor-relations/financial-reports",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
    ),
    "swedbank": CompanyIRInfo(
        id="swedbank",
        name="Swedbank AB",
        ticker="SWED A",
        ir_url="https://www.swedbank.com/investor-relations/reports-and-publications.html",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
    ),
    "spotify": CompanyIRInfo(
        id="spotify",
        name="Spotify Technology S.A.",
        ticker="SPOT",
        ir_url="https://investors.spotify.com/financials/default.aspx",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
        notes="Listed on NYSE, originally Swedish",
    ),
    "assa-abloy": CompanyIRInfo(
        id="assa-abloy",
        name="ASSA ABLOY AB",
        ticker="ASSA B",
        ir_url="https://www.assaabloy.com/group/investors/financial-reports",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
    ),
    "hexagon": CompanyIRInfo(
        id="hexagon",
        name="Hexagon AB",
        ticker="HEXA B",
        ir_url="https://hexagon.com/company/investors/reports-and-presentations",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
    ),
    "epiroc": CompanyIRInfo(
        id="epiroc",
        name="Epiroc AB",
        ticker="EPI A",
        ir_url="https://www.epirocgroup.com/en/investors/reports-and-presentations",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
    ),
    "alfa-laval": CompanyIRInfo(
        id="alfa-laval",
        name="Alfa Laval AB",
        ticker="ALFA",
        ir_url="https://www.alfalaval.com/investors/reports/",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
    ),
    "electrolux": CompanyIRInfo(
        id="electrolux",
        name="AB Electrolux",
        ticker="ELUX B",
        ir_url="https://www.electroluxgroup.com/en/reports-and-presentations-702/",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
    ),
    "skf": CompanyIRInfo(
        id="skf",
        name="AB SKF",
        ticker="SKF B",
        ir_url="https://www.skf.com/group/investors/reports",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
    ),
    "essity": CompanyIRInfo(
        id="essity",
        name="Essity AB",
        ticker="ESSITY B",
        ir_url="https://www.essity.com/investors/reports/",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
    ),
    "telia": CompanyIRInfo(
        id="telia",
        name="Telia Company AB",
        ticker="TELIA",
        ir_url="https://www.teliacompany.com/en/investors/reports-and-presentations",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
    ),
    "avanza": CompanyIRInfo(
        id="avanza",
        name="Avanza Bank Holding AB",
        ticker="AZA",
        ir_url="https://investors.avanza.se/en/ir/reports/annual-and-interim-reports/",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Interim Report"],
    ),
    "kinnevik": CompanyIRInfo(
        id="kinnevik",
        name="Kinnevik AB",
        ticker="KINV B",
        ir_url="https://www.kinnevik.com/investors/reports-and-presentations",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
    ),
    "nibe": CompanyIRInfo(
        id="nibe",
        name="NIBE Industrier AB",
        ticker="NIBE B",
        ir_url="https://www.nibe.com/investors/financial-reports",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
    ),
    "latour": CompanyIRInfo(
        id="latour",
        name="Investment AB Latour",
        ticker="LATO B",
        ir_url="https://www.latour.se/en/investor-relations/reports",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Quarterly Report"],
    ),
    "hacksaw": CompanyIRInfo(
        id="hacksaw",
        name="Hacksaw AB",
        ticker="HACKSAW",
        ir_url="https://www.hacksawgroup.com/en/investor-relations/financial-report-and-presentations/",
        segment=MarketSegment.LARGE_CAP,
        report_patterns=["Annual Report", "Interim Report", "Q"],
        backup_urls=["https://www.hacksawgroup.com/en/investor-relations/"],
        notes="Listed on Nasdaq Stockholm June 2025",
    ),
}

# Combine all registries
ALL_COMPANIES: dict[str, CompanyIRInfo] = {
    **LARGE_CAP_COMPANIES,
}


class IRRegistry:
    """Registry for looking up company IR information.

    Example:
        >>> registry = IRRegistry()
        >>> info = registry.get("evolution")
        >>> print(info.ir_url)
        https://www.evolution.com/investors/reports-presentations/
    """

    def __init__(self, companies: dict[str, CompanyIRInfo] | None = None):
        """Initialize registry with optional custom companies."""
        self._companies = companies or ALL_COMPANIES

    def get(self, company_id: str) -> CompanyIRInfo | None:
        """Get company info by ID."""
        return self._companies.get(company_id.lower())

    def get_by_ticker(self, ticker: str) -> CompanyIRInfo | None:
        """Get company info by ticker symbol."""
        ticker_upper = ticker.upper()
        for company in self._companies.values():
            if company.ticker.upper() == ticker_upper:
                return company
        return None

    def search(self, query: str) -> list[CompanyIRInfo]:
        """Search companies by name, ticker, or ID."""
        query_lower = query.lower()
        results = []
        for company in self._companies.values():
            if (
                query_lower in company.id.lower()
                or query_lower in company.name.lower()
                or query_lower in company.ticker.lower()
            ):
                results.append(company)
        return results

    def list_by_segment(self, segment: MarketSegment) -> list[CompanyIRInfo]:
        """List all companies in a market segment."""
        return [c for c in self._companies.values() if c.segment == segment]

    def list_all(self) -> list[CompanyIRInfo]:
        """List all companies."""
        return list(self._companies.values())

    def add(self, company: CompanyIRInfo) -> None:
        """Add a company to the registry."""
        self._companies[company.id] = company

    def __len__(self) -> int:
        return len(self._companies)
