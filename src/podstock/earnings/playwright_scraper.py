"""Playwright-based earnings call transcript scraper for Inderes.fi.

This module provides browser-based scraping for full transcript content,
which is loaded dynamically via JavaScript on Inderes.fi.

Requires: pip install playwright && playwright install chromium
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime

import requests

from podstock.earnings.models import (
    EarningsTranscript,
    Speaker,
    TranscriptListing,
)

logger = logging.getLogger(__name__)


# Mapping of company IDs to Inderes search terms
COMPANY_MAPPING: dict[str, list[str]] = {
    "nordea": ["Nordea", "Nordea Bank"],
    "nokia": ["Nokia", "Nokia Oyj"],
    "sampo": ["Sampo", "Sampo Oyj"],
    "stora-enso": ["Stora Enso"],
    "upm": ["UPM", "UPM-Kymmene"],
    "fortum": ["Fortum"],
    "kone": ["KONE", "Kone Oyj"],
    "neste": ["Neste", "Neste Oyj"],
    "wartsila": ["Wärtsilä", "Wartsila"],
    "metso": ["Metso"],
    "elisa": ["Elisa", "Elisa Oyj"],
    "finnair": ["Finnair"],
    "kesko": ["Kesko"],
    "huhtamaki": ["Huhtamäki", "Huhtamaki"],
    "citycon": ["Citycon"],
}


@dataclass
class PlaywrightConfig:
    """Configuration for Playwright scraper.

    Attributes:
        headless: Run browser without GUI window (default: True).
        timeout: Page load timeout in milliseconds (default: 30000).
        wait_for_content: Time to wait for dynamic content in ms (default: 5000).
        site: Target site - "fi" for inderes.fi, "se" for inderes.se (default: "fi").
    """

    headless: bool = True
    timeout: int = 30000  # ms
    wait_for_content: int = 5000  # ms to wait for dynamic content
    site: str = "fi"  # "fi" for Finnish site, "se" for Swedish site


class PlaywrightInderesScraper:
    """Scraper for Inderes earnings call transcripts.

    Supports both inderes.fi (Finnish) and inderes.se (Swedish) sites.
    Uses Playwright to render JavaScript and extract full transcript content.
    The find_transcripts() method uses HTTP (no browser needed) to list available
    transcripts, while fetch_transcript() uses Playwright to get full content.

    Example:
        >>> from podstock.earnings.playwright_scraper import PlaywrightInderesScraper, PlaywrightConfig
        >>> # Swedish site for Swedish companies
        >>> scraper = PlaywrightInderesScraper(PlaywrightConfig(site="se"))
        >>> listings = scraper.find_transcripts(company_name="Hacksaw")
        >>> for listing in listings:
        ...     transcript = scraper.fetch_transcript(listing)
        ...     if transcript:
        ...         print(f"{transcript.company_name}: {transcript.word_count} words")
        Hacksaw: 8000 words
    """

    SITES = {
        "fi": "https://www.inderes.fi",
        "se": "https://www.inderes.se",
    }

    def __init__(self, config: PlaywrightConfig | None = None):
        """Initialize the scraper.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or PlaywrightConfig()
        self._browser = None
        self._playwright = None

    @property
    def base_url(self) -> str:
        """Get base URL for configured site."""
        return self.SITES.get(self.config.site, self.SITES["fi"])

    def __enter__(self):
        """Context manager entry."""
        self._start_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self._close_browser()

    def _start_browser(self) -> None:
        """Start Playwright browser."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ImportError(
                "Playwright is required for full transcript extraction. "
                "Install with: pip install playwright && playwright install chromium"
            )

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.config.headless
        )
        logger.debug("Started Playwright browser")

    def _close_browser(self) -> None:
        """Close Playwright browser."""
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
        logger.debug("Closed Playwright browser")

    def fetch_transcript(
        self,
        listing: TranscriptListing,
        company_id: str | None = None,
    ) -> EarningsTranscript | None:
        """Fetch full transcript content using browser automation.

        Navigates to the transcript URL, handles cookie consent, extracts
        content from the transcript dialog, and parses speaker information.

        Args:
            listing: Transcript listing to fetch.
            company_id: Company ID to use (optional, derived from listing if not provided).

        Returns:
            EarningsTranscript with full content, or None if extraction failed.

        Raises:
            ImportError: If Playwright is not installed. Install with:
                pip install playwright && playwright install chromium
        """
        if not self._browser:
            self._start_browser()

        page = self._browser.new_page()

        try:
            # Navigate to transcript page
            logger.info(f"Loading transcript: {listing.url}")
            page.goto(listing.url, timeout=self.config.timeout)

            # Handle cookie consent if present
            self._handle_cookie_consent(page)

            # Wait for transcript modal/content to load
            page.wait_for_timeout(self.config.wait_for_content)

            # Try to find and click the transcript if it opens in a modal
            self._open_transcript_modal(page)

            # Extract full transcript content
            content = self._extract_transcript_content(page)

            if not content:
                logger.warning(f"Could not extract content from {listing.url}")
                return None

            # Extract speakers from content
            speakers = self._extract_speakers(content)

            # Generate IDs
            cid = company_id or self._slugify(listing.company_name)
            year = listing.year or datetime.now().year
            quarter = listing.quarter or 1

            transcript_id = EarningsTranscript.generate_id(cid, year, quarter)

            # Detect language
            language = self._detect_language(content)

            transcript = EarningsTranscript(
                id=transcript_id,
                company_id=cid,
                company_name=listing.company_name,
                fiscal_year=year,
                fiscal_quarter=quarter,
                call_date=listing.date or datetime.now(),
                language=language,
                full_text=content,
                speakers=speakers,
                source="inderes",
                source_url=listing.url,
            )
            transcript.compute_word_count()

            logger.info(
                f"Fetched full transcript: {transcript.id} "
                f"({transcript.word_count} words, {len(speakers)} speakers)"
            )

            return transcript

        except Exception as e:
            logger.error(f"Failed to fetch transcript: {e}")
            return None
        finally:
            page.close()

    def _handle_cookie_consent(self, page) -> None:
        """Handle cookie consent dialog if present."""
        try:
            # First try using get_by_text which works better for MUI dialogs
            consent_buttons = [
                ("Accept all", True),  # (text, exact)
                ("Only necessary", True),
                ("Hyväksy", False),  # Finnish
                ("Acceptera", False),  # Swedish
            ]

            for text, exact in consent_buttons:
                try:
                    btn = page.get_by_text(text, exact=exact)
                    if btn.count() > 0:
                        btn.first.click(force=True)
                        logger.debug(f"Closed consent dialog via '{text}'")
                        page.wait_for_timeout(1000)
                        return
                except Exception:
                    continue

            # Fallback: look for dialog and click any accept button
            try:
                dialog = page.locator('[role="dialog"]').first
                if dialog.is_visible(timeout=1000):
                    buttons = dialog.locator('button').all()
                    for btn in buttons:
                        try:
                            text = btn.inner_text(timeout=500)
                            if "accept" in text.lower() or "necessary" in text.lower():
                                btn.click(force=True)
                                logger.debug(f"Closed dialog via button: {text}")
                                page.wait_for_timeout(1000)
                                return
                        except Exception:
                            continue
            except Exception:
                pass

        except Exception as e:
            logger.debug(f"No cookie consent found or error: {e}")

    def _open_transcript_modal(self, page) -> None:
        """Open transcript modal if content is in a dialog."""
        try:
            # Check if transcript dialog is already open (not cookie consent)
            # Transcript dialog has aria-label="Dialog" or "Dialogue"
            transcript_dialog = page.locator('[role="dialog"][aria-label="Dialog"], [role="dialog"][aria-label="Dialogue"], section[role="dialog"]')
            if transcript_dialog.count() > 0 and transcript_dialog.first.is_visible(timeout=2000):
                logger.debug("Transcript modal already open")
                return

            # Try to click on transcript item to open modal
            transcript_link = page.locator('[class*="transcript"]').first
            if transcript_link.is_visible(timeout=2000):
                transcript_link.click()
                page.wait_for_timeout(2000)

        except Exception as e:
            logger.debug(f"No modal interaction needed or error: {e}")

    def _extract_transcript_content(self, page) -> str:
        """Extract transcript text from the page.

        Args:
            page: Playwright page object.

        Returns:
            Full transcript text.
        """
        content = ""

        # Try transcript dialog/modal first (Inderes uses modals)
        # Use specific selector to avoid matching cookie consent dialog
        try:
            # Transcript dialog has aria-label="Dialog" or "Dialogue" or is a section
            transcript_dialog = page.locator('section[role="dialog"], [role="dialog"][aria-label="Dialog"], [role="dialog"][aria-label="Dialogue"]')
            if transcript_dialog.count() > 0 and transcript_dialog.first.is_visible(timeout=2000):
                content = transcript_dialog.first.inner_text(timeout=5000)
                logger.debug(f"Extracted {len(content)} chars from transcript dialog")
                if content and len(content) > 500:
                    return self._clean_transcript(content)
        except Exception as e:
            logger.debug(f"No transcript dialog content: {e}")

        # Try article or main content
        selectors = [
            "article",
            "main",
            "[class*='transcript']",
            "[class*='content']",
            ".prose",
        ]

        for selector in selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=1000):
                    text = element.inner_text(timeout=5000)
                    if text and len(text) > len(content):
                        content = text
            except Exception:
                continue

        return self._clean_transcript(content) if content else ""

    def _clean_transcript(self, text: str) -> str:
        """Clean up transcript text.

        Args:
            text: Raw transcript text.

        Returns:
            Cleaned transcript text.
        """
        # Remove UI elements and metadata
        lines = text.split("\n")
        cleaned_lines = []

        skip_patterns = [
            r"^\d+ tykkää",  # Finnish like count
            r"^\d+ ei tykkää",  # Finnish dislike count
            r"^Huomio:",  # Finnish disclaimer
            r"^Note:",  # English disclaimer
            r"^klo \d+",  # Time only lines
        ]

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip UI elements
            skip = False
            for pattern in skip_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    skip = True
                    break

            if not skip:
                cleaned_lines.append(line)

        return "\n\n".join(cleaned_lines)

    def _extract_speakers(self, content: str) -> list[Speaker]:
        """Extract speaker information from transcript content.

        Args:
            content: Transcript text.

        Returns:
            List of identified speakers.
        """
        speakers: list[Speaker] = []
        seen_names: set[str] = set()

        # Pattern: "Name Lastname" followed by timestamp "00:00 - 00:00"
        # Example: "Frank Vang-Jensen\n01:10 - 20:05"
        pattern = r"^([A-Z][a-zA-Z\-\s]+)\n(\d{2}:\d{2}\s*-\s*\d{2}:\d{2})"

        for match in re.finditer(pattern, content, re.MULTILINE):
            name = match.group(1).strip()

            if name and name not in seen_names and len(name) < 50:
                # Try to infer role from common titles
                role = self._infer_speaker_role(name, content)
                speakers.append(Speaker(name=name, role=role))
                seen_names.add(name)

        return speakers

    def _infer_speaker_role(self, name: str, content: str) -> str | None:
        """Try to infer speaker role from context.

        Args:
            name: Speaker name.
            content: Full transcript content.

        Returns:
            Inferred role or None.
        """
        name_lower = name.lower()
        content_lower = content.lower()

        # Check for CEO/CFO mentions near the name
        if "ceo" in content_lower or "chief executive" in content_lower:
            # Check if name is associated with CEO
            ceo_pattern = rf"{re.escape(name)}.*(?:CEO|chief executive)"
            if re.search(ceo_pattern, content, re.IGNORECASE):
                return "CEO"

        if "cfo" in content_lower or "chief financial" in content_lower:
            cfo_pattern = rf"{re.escape(name)}.*(?:CFO|chief financial)"
            if re.search(cfo_pattern, content, re.IGNORECASE):
                return "CFO"

        # Check for investor relations
        if "investor relations" in name_lower or "ir " in name_lower:
            return "Investor Relations"

        # Check for analyst firms
        analyst_firms = [
            "goldman", "morgan stanley", "barclays", "citi", "jpmorgan",
            "ubs", "hsbc", "deutsche bank", "credit suisse", "kepler",
            "handelsbanken", "bnp", "exane", "jefferies", "bofa",
        ]
        for firm in analyst_firms:
            if firm in name_lower:
                return f"Analyst ({firm.title()})"

        return None

    def _detect_language(self, text: str) -> str:
        """Detect language of text.

        Args:
            text: Text to analyze.

        Returns:
            Language code ("en", "sv", "fi").
        """
        text_lower = text.lower()

        # Finnish indicators
        finnish_words = ["on", "ja", "että", "tämä", "oli", "kuten", "myös"]
        finnish_count = sum(1 for w in finnish_words if f" {w} " in text_lower)

        # Swedish indicators
        swedish_words = ["och", "att", "det", "är", "för", "som", "med"]
        swedish_count = sum(1 for w in swedish_words if f" {w} " in text_lower)

        # English indicators
        english_words = ["the", "and", "that", "this", "was", "for", "with"]
        english_count = sum(1 for w in english_words if f" {w} " in text_lower)

        if finnish_count > swedish_count and finnish_count > english_count:
            return "fi"
        elif swedish_count > finnish_count and swedish_count > english_count:
            return "sv"
        else:
            return "en"

    def _slugify(self, name: str) -> str:
        """Convert company name to slug ID.

        Args:
            name: Company name.

        Returns:
            Slug ID.
        """
        slug = name.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")
        return slug

    def find_transcripts(
        self,
        company_name: str | None = None,
        company_id: str | None = None,
        limit: int = 20,
    ) -> list[TranscriptListing]:
        """Find available transcripts from Inderes.

        This method uses HTTP requests to fetch the transcript listing page,
        which works without JavaScript since the data is in __NEXT_DATA__.

        Note:
            This method only returns transcripts from the first page (~20 items).
            For comprehensive search, use find_transcripts_with_search() instead.

        Args:
            company_name: Filter by company name (partial match).
            company_id: Filter by internal company ID (uses COMPANY_MAPPING).
            limit: Maximum number of listings to return.

        Returns:
            List of transcript listings. Returns empty list on network errors.
        """
        url = f"{self.base_url}/en/transcripts"

        try:
            response = requests.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                },
                timeout=30,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch transcripts list: {e}")
            return []

        listings: list[TranscriptListing] = []

        # Inderes uses Next.js - extract data from __NEXT_DATA__ script
        next_data_match = re.search(
            r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>',
            response.text,
            re.DOTALL,
        )
        if not next_data_match:
            logger.warning("Could not find __NEXT_DATA__ script")
            return []

        try:
            next_data = json.loads(next_data_match.group(1))
            edges = (
                next_data.get("props", {})
                .get("pageProps", {})
                .get("payload", {})
                .get("data", {})
                .get("transcriptsFeed", {})
                .get("edges", [])
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Next.js data: {e}")
            return []

        # Build search terms
        search_terms: list[str] = []
        if company_id and company_id in COMPANY_MAPPING:
            search_terms.extend(COMPANY_MAPPING[company_id])
        if company_name:
            search_terms.append(company_name)

        for edge in edges:
            node = edge.get("node", {})
            title = node.get("title", "")
            if not title:
                continue

            # Get company names from the companies array
            companies = node.get("companies", [])
            company_names_list = [c.get("name", "") for c in companies]

            # Filter by company if specified
            if search_terms:
                title_lower = title.lower()
                companies_lower = " ".join(company_names_list).lower()
                combined = title_lower + " " + companies_lower

                if not any(term.lower() in combined for term in search_terms):
                    continue

            # Extract period from title
            _, quarter, year = self._parse_title(title)

            # Parse date
            created_at = node.get("createdAt")
            date = None
            if created_at:
                try:
                    date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                except ValueError:
                    pass

            # Build URL
            page_url = node.get("pageUrl", "")
            if page_url.startswith("/"):
                full_url = f"{self.base_url}{page_url}"
            else:
                full_url = f"{self.base_url}/en/transcripts/{node.get('slug', '')}"

            # Get primary company name
            primary_company = company_names_list[0] if company_names_list else "Unknown"

            listing = TranscriptListing(
                url=full_url,
                title=title,
                company_name=primary_company,
                date=date,
                quarter=quarter,
                year=year,
            )
            listings.append(listing)

            if len(listings) >= limit:
                break

        logger.info(f"Found {len(listings)} transcript listings")
        return listings

    def _parse_title(self, title: str) -> tuple[str | None, int | None, int | None]:
        """Parse company name, quarter, and year from title.

        Args:
            title: Transcript title.

        Returns:
            Tuple of (company_name, quarter, year).
        """
        company = None
        quarter = None
        year = None

        # Extract quarter (Q1, Q2, Q3, Q4 or Q3'25 format or first, second, third, fourth)
        quarter_match = re.search(r"Q([1-4])(?:'?\d{2})?", title, re.IGNORECASE)
        if quarter_match:
            quarter = int(quarter_match.group(1))
        else:
            # Check for word-based quarters
            quarter_words = {
                "first": 1, "second": 2, "third": 3, "fourth": 4,
                "1st": 1, "2nd": 2, "3rd": 3, "4th": 4,
            }
            title_lower = title.lower()
            for word, q in quarter_words.items():
                if f"{word}-quarter" in title_lower or f"{word} quarter" in title_lower:
                    quarter = q
                    break

        # Extract year (2020-2030 or '25 format)
        year_match = re.search(r"20(2[0-9]|30)", title)
        if year_match:
            year = int(year_match.group(0))
        else:
            # Try short format like Q3'25
            short_year_match = re.search(r"'(2[0-9])", title)
            if short_year_match:
                year = 2000 + int(short_year_match.group(1))

        # Company - extract before quarter/results keywords
        company_match = re.match(
            r"^([A-Za-z][A-Za-z\s]*?)(?:\s+(?:first|second|third|fourth|Q[1-4]|annual|quarterly|results|earnings))",
            title,
            re.IGNORECASE,
        )
        if company_match:
            company = company_match.group(1).strip()
        else:
            # Fallback: split by comma or dash
            parts = re.split(r"[,\-–]", title)
            if parts:
                potential_company = parts[0].strip()
                # Remove common suffixes
                potential_company = re.sub(
                    r"\s+(Oyj|Ab|Abp|Corp|Inc|Ltd)\.?$", "",
                    potential_company, flags=re.IGNORECASE
                )
                if len(potential_company) > 2:
                    company = potential_company

        return company, quarter, year

    def search_company(self, query: str) -> list[TranscriptListing]:
        """Search for transcripts by company name using browser automation.

        This method uses Playwright to perform a search on the Inderes website,
        which finds transcripts that may not be on the first page of results.

        Args:
            query: Company name to search for.

        Returns:
            List of matching transcript listings.
        """
        return self.find_transcripts_with_search(query)

    def find_transcripts_with_search(
        self,
        search_query: str,
        limit: int = 50,
    ) -> list[TranscriptListing]:
        """Find transcripts using browser-based search.

        This method uses Playwright to search the transcripts page,
        which allows finding transcripts beyond the first page of results.
        Use this for comprehensive searches; use find_transcripts() for
        quick lookups when the transcript is likely in recent results.

        Args:
            search_query: Search term (company name, etc.).
            limit: Maximum number of listings to return.

        Returns:
            List of transcript listings matching the search.
            Returns empty list on errors.

        Raises:
            ImportError: If Playwright is not installed.
        """
        if not self._browser:
            self._start_browser()

        page = self._browser.new_page()
        listings: list[TranscriptListing] = []

        try:
            # Navigate to transcripts page
            url = f"{self.base_url}/en/transcripts"
            logger.info(f"Searching transcripts for: {search_query}")
            page.goto(url, timeout=self.config.timeout)

            # Wait for page to fully load
            page.wait_for_timeout(3000)

            # Handle cookie consent - click "Accept all" or "Only necessary"
            try:
                accept_btn = page.get_by_text("Accept all", exact=True)
                if accept_btn.count() > 0:
                    accept_btn.first.click(force=True)
                    logger.debug("Clicked 'Accept all' button")
                    page.wait_for_timeout(1000)
            except Exception as e:
                logger.debug(f"No Accept all button: {e}")

            # Wait for consent dialog to close
            page.wait_for_timeout(500)

            # Find and click the search input
            search_input = page.locator('input[placeholder*="Search"]').first
            if not search_input.is_visible(timeout=5000):
                logger.warning("Search input not found")
                return self.find_transcripts(company_name=search_query, limit=limit)

            # Type search query
            search_input.click()
            search_input.fill(search_query)

            # Wait for search results to filter
            page.wait_for_timeout(1500)

            # Extract results from the transcript list
            # Items are divs with class containing "TranscriptList_transcriptItem"
            items = page.locator('[class*="TranscriptList_transcriptItem"]').all()
            logger.debug(f"Found {len(items)} transcript items on page")

            for item in items[:limit]:
                try:
                    # Get title from TranscriptList_transcriptTitle element
                    title_el = item.locator('[class*="TranscriptList_transcriptTitle"]').first
                    title = title_el.inner_text(timeout=2000) if title_el.count() > 0 else ""

                    if not title:
                        continue

                    # Skip if search query not in title (case-insensitive)
                    if search_query.lower() not in title.lower():
                        continue

                    # Get metadata (date) from TranscriptList_metadata element
                    metadata_el = item.locator('[class*="TranscriptList_metadata"]').first
                    metadata = metadata_el.inner_text(timeout=1000) if metadata_el.count() > 0 else ""

                    # Parse date from metadata like "Language: English | 11/4/2025, 9:30 AM"
                    date = None
                    date_match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", metadata)
                    if date_match:
                        month, day, year_str = date_match.groups()
                        try:
                            date = datetime(int(year_str), int(month), int(day))
                        except ValueError:
                            pass

                    # Parse quarter and year from title like "Hacksaw , Audiocast , Q3'25"
                    _, quarter, year = self._parse_title(title)

                    # Click the item to navigate and get the URL
                    item.click()
                    page.wait_for_timeout(1500)

                    # Get the current URL after navigation
                    current_url = page.url

                    # Go back to search results
                    page.go_back()
                    page.wait_for_timeout(1000)

                    # Re-enter search query (page state is reset)
                    search_input = page.locator('input[placeholder*="Search"]').first
                    if search_input.is_visible(timeout=2000):
                        search_input.click()
                        search_input.fill(search_query)
                        page.wait_for_timeout(1000)

                    # Extract company name from title (before comma)
                    company_name = title.split(",")[0].strip() if "," in title else title

                    listing = TranscriptListing(
                        url=current_url,
                        title=title,
                        company_name=company_name,
                        date=date,
                        quarter=quarter,
                        year=year,
                    )
                    listings.append(listing)
                    logger.debug(f"Found transcript: {title} -> {current_url}")

                except Exception as e:
                    logger.debug(f"Failed to parse item: {e}")
                    continue

            # Remove duplicates based on URL
            seen_urls = set()
            unique_listings = []
            for listing in listings:
                if listing.url not in seen_urls:
                    seen_urls.add(listing.url)
                    unique_listings.append(listing)

            logger.info(f"Found {len(unique_listings)} transcripts for '{search_query}'")
            return unique_listings

        except Exception as e:
            logger.error(f"Failed to search transcripts: {e}")
            return []
        finally:
            page.close()
