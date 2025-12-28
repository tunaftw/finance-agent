#!/usr/bin/env python3
"""Extract full transcript from Chrome and save to earnings storage.

This script uses Playwright to extract the full transcript content
from an Inderes.fi transcript page.

Usage:
    python scripts/extract_transcript_chrome.py <url> [--company-id <id>]

Example:
    python scripts/extract_transcript_chrome.py \
        "https://www.inderes.fi/transcripts?transcript=nordea-third-quarter-results-2025" \
        --company-id nordea-bank
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from podstock.core.config import load_config
from podstock.earnings.models import EarningsTranscript, Speaker
from podstock.earnings.storage import EarningsStorage


def extract_transcript_with_playwright(url: str) -> tuple[str, dict]:
    """Extract full transcript using Playwright.

    Args:
        url: URL to the transcript page.

    Returns:
        Tuple of (full_text, metadata).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed. Install with: pip install playwright")
        print("Then run: playwright install chromium")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Show browser
        page = browser.new_page()

        print(f"Loading: {url}")
        page.goto(url, timeout=30000)

        # Wait for page to load
        page.wait_for_timeout(3000)

        # Handle cookie consent
        try:
            accept_btn = page.locator("text=Hyväksy").first
            if accept_btn.is_visible(timeout=2000):
                accept_btn.click()
                print("Dismissed cookie consent")
                page.wait_for_timeout(1000)
        except Exception:
            pass

        # Wait for transcript modal
        page.wait_for_timeout(2000)

        # Extract content from transcript dialog (not cookie consent)
        # The transcript dialog has aria-label="Dialogue"
        dialog = page.locator('[role="dialog"][aria-label="Dialogue"]')
        if dialog.is_visible(timeout=5000):
            content = dialog.inner_text(timeout=10000)
            print(f"Extracted {len(content)} characters from dialog")
        else:
            # Try the section-based dialog
            dialog = page.locator('section[role="dialog"]')
            if dialog.is_visible(timeout=5000):
                content = dialog.inner_text(timeout=10000)
                print(f"Extracted {len(content)} characters from section dialog")
            else:
                print("No dialog found, trying main content")
                content = page.locator("main").inner_text(timeout=10000)

        # Extract metadata
        metadata = {
            "url": url,
            "extracted_at": datetime.now().isoformat(),
        }

        # Try to get title
        title_match = content.split("\n")[0] if content else ""
        metadata["title"] = title_match

        # Try to get date
        date_match = re.search(r"(\d{2}\.\d{2}\.\d{4})", content)
        if date_match:
            metadata["date"] = date_match.group(1)

        browser.close()

        return content, metadata


def parse_speakers(content: str) -> list[Speaker]:
    """Parse speakers from transcript content."""
    speakers = []
    seen = set()

    # Pattern: "Name\nTimestamp"
    pattern = r"^([A-Z][a-zA-Z\-\s]+)\n(\d{2}:\d{2}\s*-\s*\d{2}:\d{2})"

    for match in re.finditer(pattern, content, re.MULTILINE):
        name = match.group(1).strip()
        if name and name not in seen and len(name) < 50:
            speakers.append(Speaker(name=name))
            seen.add(name)

    return speakers


def clean_transcript(text: str) -> str:
    """Clean transcript text."""
    lines = text.split("\n")
    cleaned = []

    skip_patterns = [
        r"^\d+ tykkää",
        r"^\d+ ei tykkää",
        r"^Huomio:",
        r"^klo \d+",
    ]

    for line in lines:
        line = line.strip()
        if not line:
            continue

        skip = False
        for pattern in skip_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                skip = True
                break

        if not skip:
            cleaned.append(line)

    return "\n\n".join(cleaned)


def parse_title_info(title: str) -> tuple[str, int | None, int | None]:
    """Parse company name, quarter and year from title."""
    company = None
    quarter = None
    year = None

    # Quarter
    q_match = re.search(r"Q([1-4])", title, re.IGNORECASE)
    if q_match:
        quarter = int(q_match.group(1))
    else:
        quarter_words = {
            "first": 1, "second": 2, "third": 3, "fourth": 4,
            "1st": 1, "2nd": 2, "3rd": 3, "4th": 4,
        }
        title_lower = title.lower()
        for word, q in quarter_words.items():
            if f"{word}-quarter" in title_lower or f"{word} quarter" in title_lower:
                quarter = q
                break

    # Year
    year_match = re.search(r"20(2[0-9]|30)", title)
    if year_match:
        year = int(year_match.group(0))

    # Company - extract before quarter/results keywords
    # E.g., "Nordea third-quarter results 2025" -> "Nordea"
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
            company = parts[0].strip()

    return company, quarter, year


def main():
    parser = argparse.ArgumentParser(description="Extract transcript from Inderes.fi")
    parser.add_argument("url", help="URL to transcript page")
    parser.add_argument("--company-id", help="Company ID to use")
    parser.add_argument("--dry-run", action="store_true", help="Don't save, just print")

    args = parser.parse_args()

    # Extract content
    content, metadata = extract_transcript_with_playwright(args.url)

    if not content:
        print("Failed to extract content")
        sys.exit(1)

    # Clean content
    cleaned = clean_transcript(content)

    # Parse info
    title = metadata.get("title", "")
    company_name, quarter, year = parse_title_info(title)

    # Get speakers
    speakers = parse_speakers(content)

    # Create company ID
    company_id = args.company_id
    if not company_id and company_name:
        company_id = re.sub(r"[^a-z0-9]+", "-", company_name.lower()).strip("-")

    if not company_id:
        company_id = "unknown"

    if not quarter:
        quarter = 1
    if not year:
        year = datetime.now().year

    # Parse date
    call_date = datetime.now()
    if "date" in metadata:
        try:
            call_date = datetime.strptime(metadata["date"], "%d.%m.%Y")
        except ValueError:
            pass

    # Create transcript
    transcript_id = EarningsTranscript.generate_id(company_id, year, quarter)

    transcript = EarningsTranscript(
        id=transcript_id,
        company_id=company_id,
        company_name=company_name or "Unknown",
        fiscal_year=year,
        fiscal_quarter=quarter,
        call_date=call_date,
        language="en",
        full_text=cleaned,
        speakers=speakers,
        source="inderes",
        source_url=args.url,
    )
    transcript.compute_word_count()

    print(f"\nExtracted transcript:")
    print(f"  ID: {transcript.id}")
    print(f"  Company: {transcript.company_name}")
    print(f"  Period: Q{transcript.fiscal_quarter} {transcript.fiscal_year}")
    print(f"  Words: {transcript.word_count}")
    print(f"  Speakers: {len(speakers)}")

    if args.dry_run:
        print("\n[Dry run - not saving]")
        print(f"\nFirst 500 chars:\n{cleaned[:500]}")
        return

    # Save
    config = load_config()
    storage = EarningsStorage(config)
    storage.save_transcript(transcript)

    print(f"\nSaved to storage!")
    print(f"  State file: {config.earnings_state_file}")


if __name__ == "__main__":
    main()
