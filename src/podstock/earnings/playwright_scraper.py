"""Playwright-based earnings call transcript scraper for Inderes.

This module provides browser-based scraping for full transcript content,
which is loaded dynamically via JavaScript on Inderes.fi and Inderes.se.

Supports both /en/transcripts and /en/videos paths, and handles transcript
buttons that need to be clicked to reveal content.

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
    # Swedish companies (use .se site)
    "getinge": ["Getinge"],
    "evolution": ["Evolution", "Evolution Gaming"],
    "hacksaw": ["Hacksaw", "Hacksaw Gaming"],
    "castellum": ["Castellum"],
    "embracer": ["Embracer", "Embracer Group"],
    "atlas-copco": ["Atlas Copco"],
    "volvo": ["Volvo", "Volvo AB"],
    "ericsson": ["Ericsson", "Telefonaktiebolaget LM Ericsson"],
    "h-m": ["H&M", "Hennes & Mauritz"],
    "spotify": ["Spotify"],
    "sandvik": ["Sandvik"],
    "assa-abloy": ["ASSA ABLOY"],
    "hexagon": ["Hexagon"],
    "alfa-laval": ["Alfa Laval"],
    "epiroc": ["Epiroc"],
    "nibe": ["NIBE", "Nibe Industrier"],
    "essity": ["Essity"],
    "securitas": ["Securitas"],
    "skf": ["SKF"],
    "electrolux": ["Electrolux"],
    "telia": ["Telia", "Telia Company"],
    "swedish-match": ["Swedish Match"],
    "investor": ["Investor AB"],
    "kinnevik": ["Kinnevik"],
    "eqt": ["EQT"],
    "sweco": ["Sweco"],
    "afry": ["AFRY"],
    "bico": ["BICO", "BICO Group"],
    "camurus": ["Camurus"],
    "cellavision": ["CellaVision"],
}

# Swedish companies that should use inderes.se
SWEDISH_COMPANIES: set[str] = {
    "getinge", "evolution", "hacksaw", "castellum", "embracer",
    "atlas-copco", "volvo", "ericsson", "h-m", "spotify", "sandvik",
    "assa-abloy", "hexagon", "alfa-laval", "epiroc", "nibe", "essity",
    "securitas", "skf", "electrolux", "telia", "swedish-match",
    "investor", "kinnevik", "eqt", "sweco", "afry", "bico", "camurus",
    "cellavision", "alimak", "egetis", "viva-wine", "eolus", "asmodee",
    "sbb", "nyab", "zenicor", "enity", "enad-global-7", "yubico", "nordrest",
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

            # Check for "Transcript is not available" error
            if self._has_unavailable_error(page):
                logger.warning(f"Transcript not available at {listing.url}")
                return None

            # Extract full transcript content
            content = self._extract_transcript_content(page)

            if not content:
                logger.warning(f"Could not extract content from {listing.url}")
                return None

            # Validate that extracted content is actual transcript, not listing page
            if not self._validate_transcript_content(content, listing.company_name):
                logger.warning(
                    f"Extracted content appears to be listing page, not transcript "
                    f"for {listing.company_name} at {listing.url}"
                )
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
        """Open transcript modal if content is in a dialog.

        This handles both:
        1. Transcripts that are already in a modal (inderes.fi style)
        2. Video pages where you must click a "Transcript" button (inderes.se style)
        """
        try:
            # Check if transcript dialog is already open (not cookie consent)
            # Transcript dialog has aria-label="Dialog" or "Dialogue"
            transcript_dialog = page.locator('[role="dialog"][aria-label="Dialog"], [role="dialog"][aria-label="Dialogue"], section[role="dialog"]')
            if transcript_dialog.count() > 0 and transcript_dialog.first.is_visible(timeout=2000):
                logger.debug("Transcript modal already open")
                return

            # Try to click a "Transcript" button/tab (common on video pages)
            # This is needed for /en/videos/ pages on inderes.se
            transcript_buttons = [
                page.get_by_text("Transcript", exact=True),
                page.get_by_text("Transkript", exact=True),  # Swedish
                page.get_by_role("tab", name="Transcript"),
                page.locator('button:has-text("Transcript")'),
                page.locator('[class*="transcript"]').first,
            ]

            for btn in transcript_buttons:
                try:
                    if btn.count() > 0 and btn.first.is_visible(timeout=1000):
                        btn.first.click()
                        logger.debug("Clicked Transcript button")
                        page.wait_for_timeout(2000)
                        return
                except Exception:
                    continue

            # Fallback: Try to click on any transcript-related link
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

        # First, check if this is a video page with embedded videosync player
        # The transcript is often in the embed's __NEXT_DATA__
        embed_content = self._try_extract_from_videosync_embed(page)
        if embed_content and len(embed_content) > 500:
            logger.debug(f"Extracted {len(embed_content)} chars from videosync embed")
            return embed_content

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

    def _try_extract_from_videosync_embed(self, page) -> str:
        """Try to extract transcript from videosync.fi embed URL.

        Video pages on Inderes embed a videosync.fi player that contains
        the actual transcript in its __NEXT_DATA__.

        Args:
            page: Playwright page object.

        Returns:
            Transcript text if found, empty string otherwise.
        """
        try:
            # Get the current page HTML to find videoEmbedUrl
            html = page.content()

            # Parse __NEXT_DATA__ to find videoEmbedUrl
            next_data_match = re.search(
                r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>',
                html,
                re.DOTALL,
            )
            if not next_data_match:
                return ""

            next_data = json.loads(next_data_match.group(1))
            content_obj = (
                next_data.get("props", {})
                .get("pageProps", {})
                .get("payload", {})
                .get("data", {})
                .get("content", {})
            )

            embed_url = content_obj.get("videoEmbedUrl", "")
            if not embed_url or "videosync.fi" not in embed_url:
                return ""

            logger.debug(f"Found videosync embed URL: {embed_url}")

            # Fetch the embed page
            response = requests.get(
                embed_url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=30,
            )
            response.raise_for_status()

            # The transcript is in self.__next_f.push calls in script tags
            # These contain the presentation slides/transcript text
            transcript_parts = []

            # Pattern to find next_f.push content
            t_pattern = r'self\.__next_f\.push\(\[1,"([^"]+)"\]\)'
            logger.debug(f"Searching for transcript in {len(response.text)} chars of embed page")
            for match in re.finditer(t_pattern, response.text):
                text = match.group(1)

                # Unescape unicode escapes
                try:
                    text = text.encode().decode("unicode_escape")
                except Exception:
                    pass

                # Only keep substantial text blocks that look like transcript
                if len(text) > 300:
                    # Skip CSS, code, and JSON blocks
                    text_start = text.strip()[:100].lower()
                    if (
                        not text_start.startswith(".")
                        and "function" not in text_start
                        and not text_start.startswith("{")
                        and not text_start.startswith("[")
                        and not text_start.startswith("/*")
                    ):
                        # Check for transcript-like keywords
                        text_lower = text.lower()
                        if any(
                            kw in text_lower
                            for kw in ["sales", "margin", "quarter", "q1", "q2", "q3", "q4", "ceo", "cfo", "revenue"]
                        ):
                            transcript_parts.append(text)

            if transcript_parts:
                # Find the longest/most transcript-like part
                best_part = max(transcript_parts, key=len)
                logger.debug(f"Found transcript part with {len(best_part)} chars")
                return self._clean_transcript(best_part)

            logger.debug(f"No transcript parts found in {len(response.text)} chars of embed response")
            return ""

        except Exception as e:
            logger.error(f"Failed to extract from videosync embed: {e}")
            return ""

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

    def _has_unavailable_error(self, page) -> bool:
        """Check if the page shows 'Transcript is not available' error.

        Args:
            page: Playwright page object.

        Returns:
            True if error message is displayed, False otherwise.
        """
        try:
            # Look for the error message in any dialog or on the page
            error_texts = [
                "Transcript is not available",
                "Something went wrong",
                "can't be displayed",
            ]
            for error_text in error_texts:
                error_element = page.get_by_text(error_text, exact=False)
                if error_element.count() > 0 and error_element.first.is_visible(timeout=1000):
                    logger.debug(f"Found error message: '{error_text}'")
                    return True
            return False
        except Exception:
            return False

    def _validate_transcript_content(
        self, content: str, expected_company: str
    ) -> bool:
        """Validate that extracted content is actual transcript, not listing page.

        This prevents extracting listing/feed page content when a specific
        transcript doesn't exist at the URL.

        Args:
            content: Extracted content to validate.
            expected_company: Company name that should be in the transcript.

        Returns:
            True if content appears to be a valid transcript, False otherwise.
        """
        content_lower = content.lower()
        expected_lower = expected_company.lower()

        # Check for listing page indicators
        listing_indicators = [
            "ladda mer",  # Swedish "Load more" button
            "load more",  # English equivalent
            "senaste",  # Swedish "Latest"
            "populärt",  # Swedish "Popular"
            "trending",
            "followed",
        ]

        # If content has multiple listing indicators, it's likely a listing page
        indicator_count = sum(1 for ind in listing_indicators if ind in content_lower)
        if indicator_count >= 2:
            logger.debug(f"Content has {indicator_count} listing indicators")
            return False

        # Check if expected company name appears in the content
        # For valid transcripts, the company name should appear prominently
        if expected_lower not in content_lower:
            # Try common variations
            variations = [
                expected_lower.replace(" ", ""),
                expected_lower.replace("-", " "),
            ]
            if not any(var in content_lower for var in variations):
                logger.debug(f"Expected company '{expected_company}' not found in content")
                return False

        # Check for multiple different company names (indicates listing page)
        # This is a heuristic - listing pages typically mention many companies
        common_companies = [
            "castellum", "alimak", "egetis", "embracer", "camurus",
            "cellavision", "truecaller", "herantis", "hacksaw", "enity",
            "yubico", "bico", "eolus", "viva wine", "asmodee",
        ]
        other_companies = [
            c for c in common_companies
            if c in content_lower and c != expected_lower
        ]
        if len(other_companies) >= 3:
            logger.debug(
                f"Content mentions {len(other_companies)} other companies: "
                f"{other_companies[:5]}"
            )
            return False

        # Content seems valid
        return True

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

    def _is_swedish_company(self, company_name: str) -> bool:
        """Check if a company should use the Swedish site.

        Args:
            company_name: Company name to check.

        Returns:
            True if the company is Swedish and should use inderes.se.
        """
        name_lower = company_name.lower()
        slug = self._slugify(company_name)

        # Check against known Swedish companies
        if slug in SWEDISH_COMPANIES:
            return True

        # Check in COMPANY_MAPPING for Swedish entries
        for company_id, names in COMPANY_MAPPING.items():
            if company_id in SWEDISH_COMPANIES:
                if any(n.lower() in name_lower or name_lower in n.lower() for n in names):
                    return True

        return False

    def _get_site_for_company(self, company_name: str) -> str:
        """Get the appropriate Inderes site for a company.

        Args:
            company_name: Company name.

        Returns:
            Site code ("se" or "fi").
        """
        return "se" if self._is_swedish_company(company_name) else "fi"

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
            This method searches BOTH /en/transcripts and /en/videos paths.
            For comprehensive browser-based search, use find_transcripts_with_search().

        Args:
            company_name: Filter by company name (partial match).
            company_id: Filter by internal company ID (uses COMPANY_MAPPING).
            limit: Maximum number of listings to return.

        Returns:
            List of transcript listings. Returns empty list on network errors.
        """
        # Auto-detect site based on company name
        if company_name and self._is_swedish_company(company_name):
            effective_site = "se"
            base = self.SITES["se"]
            logger.info(f"Auto-detected Swedish company '{company_name}', using inderes.se")
        elif company_id and company_id in SWEDISH_COMPANIES:
            effective_site = "se"
            base = self.SITES["se"]
            logger.info(f"Auto-detected Swedish company ID '{company_id}', using inderes.se")
        else:
            effective_site = self.config.site
            base = self.base_url

        # Search both /en/transcripts and /en/videos paths
        all_listings: list[TranscriptListing] = []

        for path in ["/en/transcripts", "/en/videos"]:
            url = f"{base}{path}"
            listings = self._fetch_listings_from_path(
                url, base, company_name, company_id, limit
            )
            all_listings.extend(listings)
            if len(all_listings) >= limit:
                break

        # Deduplicate by URL
        seen_urls: set[str] = set()
        unique_listings: list[TranscriptListing] = []
        for listing in all_listings:
            if listing.url not in seen_urls:
                seen_urls.add(listing.url)
                unique_listings.append(listing)

        # If no listings found via feeds, try URL pattern guessing
        if not unique_listings and company_name:
            logger.info(f"No listings in feeds, trying URL patterns for '{company_name}'")
            pattern_listings = self.find_by_url_patterns(company_name)
            for listing in pattern_listings:
                if listing.url not in seen_urls:
                    seen_urls.add(listing.url)
                    unique_listings.append(listing)

        logger.info(f"Found {len(unique_listings)} total listings for '{company_name or company_id}'")
        return unique_listings[:limit]

    def _fetch_listings_from_path(
        self,
        url: str,
        base_url: str,
        company_name: str | None,
        company_id: str | None,
        limit: int,
    ) -> list[TranscriptListing]:
        """Fetch transcript/video listings from a specific path.

        Args:
            url: Full URL to fetch (e.g., https://www.inderes.se/en/videos)
            base_url: Base URL for building full links
            company_name: Filter by company name
            company_id: Filter by company ID
            limit: Max results

        Returns:
            List of transcript listings from this path.
        """
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
            logger.error(f"Failed to fetch from {url}: {e}")
            return []

        listings: list[TranscriptListing] = []

        # Inderes uses Next.js - extract data from __NEXT_DATA__ script
        next_data_match = re.search(
            r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>',
            response.text,
            re.DOTALL,
        )
        if not next_data_match:
            logger.debug(f"Could not find __NEXT_DATA__ script in {url}")
            return []

        try:
            next_data = json.loads(next_data_match.group(1))
            data_section = (
                next_data.get("props", {})
                .get("pageProps", {})
                .get("payload", {})
                .get("data", {})
            )

            # Try different feed names depending on page type
            # /en/transcripts uses "transcriptsFeed", /en/videos uses "videos"
            edges = []
            for feed_name in ["transcriptsFeed", "videos", "videosFeed"]:
                feed = data_section.get(feed_name, {})
                if feed and "edges" in feed:
                    edges = feed.get("edges", [])
                    logger.debug(f"Found {len(edges)} items in {feed_name} from {url}")
                    break

            if not edges:
                logger.debug(f"No edges found in any feed from {url}")
                return []

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Next.js data from {url}: {e}")
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

            # Get company names from the companies array (transcripts have this, videos don't)
            companies = node.get("companies", [])
            company_names_list = [c.get("name", "") for c in companies]

            # Filter by company if specified
            # For videos without companies array, match by title only
            if search_terms:
                title_lower = title.lower()
                companies_lower = " ".join(company_names_list).lower()
                slug = node.get("slug", "").lower()
                page_url = node.get("pageUrl", "").lower()
                combined = f"{title_lower} {companies_lower} {slug} {page_url}"

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
            slug = node.get("slug", "")
            if page_url.startswith("/"):
                full_url = f"{base_url}{page_url}"
            elif "/videos" in url:
                full_url = f"{base_url}/en/videos/{slug}"
            else:
                full_url = f"{base_url}/en/transcripts/{slug}"

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

        logger.debug(f"Found {len(listings)} listings from {url}")
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

    def find_by_url_patterns(
        self,
        company_name: str,
        years: list[int] | None = None,
        quarters: list[int] | None = None,
    ) -> list[TranscriptListing]:
        """Find transcripts by trying known URL patterns.

        This method constructs potential URLs based on common Inderes patterns
        and verifies they exist. Useful when feed-based search doesn't find
        older content.

        Args:
            company_name: Company name to search for.
            years: Years to search (default: current and previous year).
            quarters: Quarters to search (default: all quarters).

        Returns:
            List of verified transcript listings.
        """
        from datetime import datetime

        if years is None:
            current_year = datetime.now().year
            years = [current_year, current_year - 1]
        if quarters is None:
            quarters = [1, 2, 3, 4]

        # Determine site based on company
        if self._is_swedish_company(company_name):
            base = self.SITES["se"]
        else:
            base = self.base_url

        # Normalize company name for URL
        slug = self._slugify(company_name)

        listings: list[TranscriptListing] = []

        # Common URL patterns on Inderes
        patterns = [
            "/en/videos/{slug}-audiocast-q{q}{yy}",
            "/en/videos/{slug}-q{q}-{yyyy}",
            "/en/videos/{slug}-q{q}{yy}",
            "/en/transcripts/{slug}-q{q}-{yyyy}",
            "/en/transcripts/{slug}-audiocast-q{q}{yy}",
        ]

        for year in years:
            yy = str(year)[-2:]  # Last 2 digits
            yyyy = str(year)

            for quarter in quarters:
                for pattern in patterns:
                    url_path = pattern.format(
                        slug=slug,
                        q=quarter,
                        yy=yy,
                        yyyy=yyyy,
                    )
                    full_url = f"{base}{url_path}"

                    try:
                        response = requests.head(
                            full_url,
                            headers={"User-Agent": "Mozilla/5.0"},
                            timeout=5,
                            allow_redirects=True,
                        )
                        if response.status_code == 200:
                            logger.info(f"Found content at: {full_url}")
                            listing = TranscriptListing(
                                url=full_url,
                                title=f"{company_name} Q{quarter} {year}",
                                company_name=company_name,
                                date=None,
                                quarter=quarter,
                                year=year,
                            )
                            listings.append(listing)
                            break  # Found one pattern for this quarter, skip others
                    except requests.RequestException:
                        continue

        logger.info(f"Found {len(listings)} content via URL patterns for '{company_name}'")
        return listings

    def find_transcripts_with_search(
        self,
        search_query: str,
        limit: int = 50,
    ) -> list[TranscriptListing]:
        """Find transcripts using browser-based search.

        This method uses Playwright to search both transcripts and videos pages,
        which allows finding transcripts beyond the first page of results.
        Auto-detects if the company is Swedish and uses inderes.se accordingly.

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

        # Auto-detect site based on search query
        if self._is_swedish_company(search_query):
            base = self.SITES["se"]
            logger.info(f"Auto-detected Swedish company '{search_query}', using inderes.se")
        else:
            base = self.base_url

        all_listings: list[TranscriptListing] = []

        # Search both transcripts and videos pages
        for path in ["/en/transcripts", "/en/videos"]:
            url = f"{base}{path}"
            listings = self._search_page_with_browser(url, base, search_query, limit)
            all_listings.extend(listings)

        # Deduplicate by URL
        seen_urls: set[str] = set()
        unique_listings: list[TranscriptListing] = []
        for listing in all_listings:
            if listing.url not in seen_urls:
                seen_urls.add(listing.url)
                unique_listings.append(listing)

        logger.info(f"Found {len(unique_listings)} transcripts for '{search_query}'")
        return unique_listings[:limit]

    def _search_page_with_browser(
        self,
        url: str,
        base_url: str,
        search_query: str,
        limit: int,
    ) -> list[TranscriptListing]:
        """Search a specific page using browser automation.

        Args:
            url: Full URL to search (e.g., https://www.inderes.se/en/videos)
            base_url: Base URL for the site
            search_query: Search term
            limit: Max results

        Returns:
            List of transcript listings from this page.
        """
        page = self._browser.new_page()
        listings: list[TranscriptListing] = []

        try:
            logger.info(f"Searching {url} for: {search_query}")
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
                logger.debug(f"Search input not found on {url}")
                return []

            # Type search query
            search_input.click()
            search_input.fill(search_query)

            # Wait for search results to filter
            page.wait_for_timeout(1500)

            # Extract results from the transcript/video list
            # Items are divs with class containing TranscriptList or VideoList
            items = page.locator('[class*="TranscriptList_transcriptItem"], [class*="VideoList_videoItem"], [class*="ListItem"]').all()
            logger.debug(f"Found {len(items)} items on {url}")

            for item in items[:limit]:
                try:
                    # Get title from TranscriptList or VideoList title element
                    title_el = item.locator('[class*="transcriptTitle"], [class*="videoTitle"], [class*="Title"]').first
                    title = title_el.inner_text(timeout=2000) if title_el.count() > 0 else ""

                    # Fallback: try to get any heading or strong text
                    if not title:
                        heading = item.locator('h2, h3, h4, strong').first
                        title = heading.inner_text(timeout=1000) if heading.count() > 0 else ""

                    if not title:
                        continue

                    # Skip if search query not in title (case-insensitive)
                    if search_query.lower() not in title.lower():
                        continue

                    # Get metadata (date) from metadata element
                    metadata_el = item.locator('[class*="metadata"], [class*="Metadata"], time').first
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

            logger.debug(f"Found {len(listings)} listings from {url}")
            return listings

        except Exception as e:
            logger.error(f"Failed to search {url}: {e}")
            return []
        finally:
            page.close()
