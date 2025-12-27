"""IR page scraper for Swedish companies.

Crawls investor relations pages to find and download financial reports.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from podstock.filings.exceptions import FilingsError
from podstock.filings.models import FilingType

if TYPE_CHECKING:
    from podstock.filings.swedish.ir_registry import CompanyIRInfo

logger = logging.getLogger(__name__)


@dataclass
class FoundReport:
    """A report found on an IR page."""

    url: str
    title: str
    filing_type: FilingType
    year: int
    quarter: int | None = None
    language: str = "en"
    file_size: int | None = None


class IRScraper:
    """Scrapes IR pages to find financial reports.

    Example:
        >>> from podstock.filings.swedish.ir_registry import IRRegistry
        >>> registry = IRRegistry()
        >>> scraper = IRScraper()
        >>> company = registry.get("evolution")
        >>> reports = scraper.find_reports(company)
        >>> for report in reports:
        ...     print(f"{report.filing_type}: {report.year} Q{report.quarter or ''}")
    """

    # Patterns for identifying report types
    ANNUAL_PATTERNS = [
        r"annual[\s_-]*report",
        r"årsredovisning",
        r"årsrapport",
        r"year[\s_-]*end",
        r"full[\s_-]*year",
    ]

    QUARTERLY_PATTERNS = [
        r"q[1-4][\s_-]*\d{4}",
        r"\d{4}[\s_-]*q[1-4]",
        r"quarterly[\s_-]*report",
        r"interim[\s_-]*report",
        r"delårsrapport",
        r"kvartalsrapport",
        r"jan[\s_-]*mar",
        r"apr[\s_-]*jun",
        r"jul[\s_-]*sep",
        r"oct[\s_-]*dec",
    ]

    # Year extraction patterns
    YEAR_PATTERNS = [
        r"20[12]\d",  # 2010-2029
    ]

    # Quarter extraction patterns
    QUARTER_PATTERNS = [
        (r"q1|jan.*mar|first[\s_-]*quarter", 1),
        (r"q2|apr.*jun|second[\s_-]*quarter", 2),
        (r"q3|jul.*sep|third[\s_-]*quarter", 3),
        (r"q4|oct.*dec|fourth[\s_-]*quarter", 4),
    ]

    def __init__(
        self,
        user_agent: str = "PodStock/1.0 (Swedish IR Scraper)",
        timeout: int = 30,
    ):
        """Initialize scraper.

        Args:
            user_agent: User agent string for HTTP requests.
            timeout: Request timeout in seconds.
        """
        self.user_agent = user_agent
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def find_reports(
        self,
        company: CompanyIRInfo,
        limit: int = 20,
    ) -> list[FoundReport]:
        """Find reports on a company's IR page.

        This method handles two common patterns:
        1. Direct PDF links on the main IR page
        2. Links to report pages that contain the actual PDFs

        If the primary URL fails, it will try backup URLs.

        Args:
            company: Company info with IR URL.
            limit: Maximum number of reports to return.

        Returns:
            List of found reports.
        """
        # Try primary URL, then backup URLs
        soup, working_url = self._fetch_with_fallback(company)

        try:
            # First try: find direct PDF links
            pdf_links = self._find_pdf_links(soup, working_url)

            # Second try: if no PDFs found, look for report page links
            if not pdf_links:
                report_page_links = self._find_report_page_links(soup, company)
                pdf_links = self._follow_report_pages(report_page_links, working_url)

            reports = []
            for url, text in pdf_links:
                report = self._classify_report(url, text, company)
                if report:
                    reports.append(report)

            # Sort by year desc, then annual before quarterly
            reports.sort(
                key=lambda r: (
                    -r.year,
                    0 if r.filing_type == FilingType.ANNUAL_REPORT else 1,
                    -(r.quarter or 0),
                ),
            )

            return reports[:limit]

        except Exception as e:
            logger.error(f"Failed to scrape {working_url}: {e}")
            raise FilingsError(f"Failed to scrape IR page for {company.name}: {e}") from e

    def _fetch_with_fallback(
        self,
        company: CompanyIRInfo,
    ) -> tuple[BeautifulSoup, str]:
        """Fetch company IR page, trying backup URLs if primary fails.

        Args:
            company: Company info with IR URLs.

        Returns:
            Tuple of (parsed page, URL that worked).

        Raises:
            FilingsError: If all URLs fail.
        """
        urls_to_try = [company.ir_url] + company.backup_urls
        last_error = None

        for url in urls_to_try:
            try:
                soup = self._fetch_page(url)
                if url != company.ir_url:
                    logger.info(f"Primary URL failed, using backup: {url}")
                return soup, url
            except Exception as e:
                logger.debug(f"URL failed: {url} - {e}")
                last_error = e
                continue

        # All URLs failed
        raise FilingsError(
            f"All IR URLs failed for {company.name}. "
            f"Primary: {company.ir_url}. Error: {last_error}"
        )

    def _find_report_page_links(
        self,
        soup: BeautifulSoup,
        company: CompanyIRInfo,
    ) -> list[tuple[str, str]]:
        """Find links to individual report pages.

        Many IR sites list reports as links to pages (not direct PDFs).
        This finds those page links based on patterns.
        """
        report_patterns = [
            r"annual.*report",
            r"årsredovisning",
            r"interim.*report",
            r"delårsrapport",
            r"q[1-4].*\d{4}",
            r"\d{4}.*q[1-4]",
            r"quarterly",
        ]

        page_links = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True)
            combined = f"{href} {text}".lower()

            # Skip PDFs (handled separately)
            if ".pdf" in href.lower():
                continue

            # Skip non-report links
            if not any(re.search(p, combined, re.IGNORECASE) for p in report_patterns):
                continue

            # Skip navigation/menu links
            if any(skip in href.lower() for skip in ["#", "javascript:", "mailto:"]):
                continue

            page_links.append((href, text))

        return page_links

    def _follow_report_pages(
        self,
        page_links: list[tuple[str, str]],
        base_url: str,
        max_pages: int = 10,
    ) -> list[tuple[str, str]]:
        """Follow report page links to find actual PDF URLs."""
        pdf_links = []
        seen_urls = set()

        for href, page_text in page_links[:max_pages]:
            full_url = urljoin(base_url, href)

            # Skip if already visited
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            try:
                page_soup = self._fetch_page(full_url)

                # Find PDFs on this page
                for link in page_soup.find_all("a", href=True):
                    pdf_href = link["href"]
                    if not self._is_pdf_link(pdf_href):
                        continue

                    pdf_url = urljoin(full_url, pdf_href)
                    pdf_text = f"{page_text} {self._get_link_context(link)}"
                    pdf_links.append((pdf_url, pdf_text))

            except Exception as e:
                logger.debug(f"Failed to fetch report page {full_url}: {e}")
                continue

        return pdf_links

    def download_report(
        self,
        report: FoundReport,
        output_dir: Path,
        company_id: str | None = None,
        filename: str | None = None,
    ) -> Path:
        """Download a report PDF.

        Args:
            report: Report to download.
            output_dir: Directory to save the file.
            company_id: Company ID for standardized naming.
            filename: Optional filename, overrides auto-generation.

        Returns:
            Path to downloaded file.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if filename is None:
            # Generate standardized filename: {company}_{year}_{type}[_q{quarter}][_{lang}].pdf
            parts = []
            if company_id:
                parts.append(company_id)
            parts.append(str(report.year))
            parts.append(report.filing_type.value)
            if report.quarter:
                parts.append(f"q{report.quarter}")
            if report.language != "en":
                parts.append(report.language)
            filename = "_".join(parts) + ".pdf"

        output_path = output_dir / filename

        try:
            response = self.session.get(report.url, timeout=self.timeout, stream=True)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Downloaded: {output_path}")
            return output_path

        except Exception as e:
            raise FilingsError(f"Failed to download {report.url}: {e}") from e

    def _fetch_page(self, url: str) -> BeautifulSoup:
        """Fetch and parse a web page."""
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    def _find_pdf_links(
        self,
        soup: BeautifulSoup,
        base_url: str,
    ) -> list[tuple[str, str]]:
        """Find PDF links on a page.

        Returns:
            List of (url, link_text) tuples.
        """
        pdf_links = []

        for link in soup.find_all("a", href=True):
            href = link["href"]

            # Check if it's a PDF link
            if not self._is_pdf_link(href):
                continue

            # Make URL absolute
            full_url = urljoin(base_url, href)

            # Get link text (including parent context)
            text = self._get_link_context(link)

            pdf_links.append((full_url, text))

        return pdf_links

    def _is_pdf_link(self, href: str) -> bool:
        """Check if a link points to a PDF."""
        href_lower = href.lower()

        # Direct PDF extension
        if href_lower.endswith(".pdf"):
            return True

        # PDF in URL path or query
        if "pdf" in href_lower and any(
            x in href_lower for x in ["download", "file", "document", "report"]
        ):
            return True

        return False

    def _get_link_context(self, link) -> str:
        """Get text context around a link."""
        parts = []

        # Link text itself
        if link.string:
            parts.append(link.string)
        elif link.get_text():
            parts.append(link.get_text())

        # Title attribute
        if link.get("title"):
            parts.append(link.get("title"))

        # Nearby text (parent and siblings)
        parent = link.parent
        if parent:
            # Check for nearby headings
            prev_heading = parent.find_previous(["h1", "h2", "h3", "h4"])
            if prev_heading and prev_heading.get_text():
                parts.append(prev_heading.get_text())

            # Parent text (if short)
            parent_text = parent.get_text(strip=True)
            if len(parent_text) < 200:
                parts.append(parent_text)

        return " ".join(parts)

    def _classify_report(
        self,
        url: str,
        text: str,
        company: CompanyIRInfo,
    ) -> FoundReport | None:
        """Classify a found PDF link as a report type.

        Returns:
            FoundReport if classified, None otherwise.
        """
        combined = f"{url} {text}".lower()

        # Try to extract year first
        year = self._extract_year(combined)
        if not year:
            return None

        # Check for annual report
        if self._matches_patterns(combined, self.ANNUAL_PATTERNS):
            return FoundReport(
                url=url,
                title=text.strip()[:200],
                filing_type=FilingType.ANNUAL_REPORT,
                year=year,
                quarter=None,
            )

        # Check for quarterly report
        if self._matches_patterns(combined, self.QUARTERLY_PATTERNS):
            quarter = self._extract_quarter(combined)

            # Fallback: try to infer quarter from month names
            if quarter is None:
                quarter = self._infer_quarter_from_months(combined)

            # Reject quarterly reports without a valid quarter
            if quarter is None:
                logger.warning(
                    f"Quarterly report without quarter, skipping: {text[:50]}..."
                )
                return None

            return FoundReport(
                url=url,
                title=text.strip()[:200],
                filing_type=FilingType.QUARTERLY_REPORT,
                year=year,
                quarter=quarter,
            )

        # Check company-specific patterns
        for pattern in company.report_patterns:
            if pattern.lower() in combined:
                # Determine type from pattern
                if any(q in pattern.lower() for q in ["annual", "årsred", "year"]):
                    return FoundReport(
                        url=url,
                        title=text.strip()[:200],
                        filing_type=FilingType.ANNUAL_REPORT,
                        year=year,
                        quarter=None,
                    )
                elif any(q in pattern.lower() for q in ["q", "quarter", "interim"]):
                    quarter = self._extract_quarter(combined)
                    if quarter is None:
                        quarter = self._infer_quarter_from_months(combined)
                    if quarter is None:
                        logger.warning(
                            f"Company pattern quarterly without quarter: {text[:50]}..."
                        )
                        return None
                    return FoundReport(
                        url=url,
                        title=text.strip()[:200],
                        filing_type=FilingType.QUARTERLY_REPORT,
                        year=year,
                        quarter=quarter,
                    )

        return None

    def _matches_patterns(self, text: str, patterns: list[str]) -> bool:
        """Check if text matches any pattern."""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _extract_year(self, text: str) -> int | None:
        """Extract year from text."""
        current_year = datetime.now().year

        for pattern in self.YEAR_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                year = int(match)
                # Sanity check: not in the future
                if year <= current_year + 1:
                    return year
        return None

    def _extract_quarter(self, text: str) -> int | None:
        """Extract quarter from text."""
        for pattern, quarter in self.QUARTER_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return quarter
        return None

    def _infer_quarter_from_months(self, text: str) -> int | None:
        """Infer quarter from month names in text.

        Used as fallback when explicit Q1-Q4 patterns aren't found.
        """
        text_lower = text.lower()

        # Swedish and English month patterns mapped to quarters
        month_to_quarter = {
            # Q1: Jan-Mar
            "januari": 1, "january": 1, "jan": 1,
            "februari": 1, "february": 1, "feb": 1,
            "mars": 1, "march": 1, "mar": 1,
            # Q2: Apr-Jun
            "april": 2, "apr": 2,
            "maj": 2, "may": 2,
            "juni": 2, "june": 2, "jun": 2,
            # Q3: Jul-Sep
            "juli": 3, "july": 3, "jul": 3,
            "augusti": 3, "august": 3, "aug": 3,
            "september": 3, "sep": 3,
            # Q4: Oct-Dec
            "oktober": 4, "october": 4, "oct": 4,
            "november": 4, "nov": 4,
            "december": 4, "dec": 4,
        }

        # Find end-of-period month (indicates which quarter the report covers)
        # Look for patterns like "januari-mars" or "january - march"
        period_patterns = [
            (r"jan\w*[\s\-–]+mar\w*", 1),
            (r"apr\w*[\s\-–]+jun\w*", 2),
            (r"jul\w*[\s\-–]+sep\w*", 3),
            (r"oct\w*[\s\-–]+dec\w*", 4),
            (r"okt\w*[\s\-–]+dec\w*", 4),
        ]

        for pattern, quarter in period_patterns:
            if re.search(pattern, text_lower):
                return quarter

        # Fallback: look for single month that might indicate report period
        # Prefer the last month found (typically indicates end of period)
        found_quarters = []
        for month, quarter in month_to_quarter.items():
            if month in text_lower:
                found_quarters.append(quarter)

        if found_quarters:
            # Return the most common quarter found
            return max(set(found_quarters), key=found_quarters.count)

        return None
