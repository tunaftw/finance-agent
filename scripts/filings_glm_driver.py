#!/usr/bin/env python3
"""
GLM Driver for financial filings analysis.

Calls OpenCode CLI with GLM-4.7 to analyze financial filings
and extract CEO letter tone, promises, risk factors, guidance, etc.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from podstock.filings.analysis.ceo_letter import find_ceo_letter_section
from podstock.filings.analysis.deep_analysis import (
    FULL_FILING_ANALYSIS_PROMPT,
    extract_json_from_response,
    find_guidance_section,
    find_mda_section,
    find_risk_factors_section,
    find_segment_section,
)
from podstock.filings.pdf.parser import PDFParser

# Configuration
OPENCODE_CLI = "/Users/pontus/.opencode/bin/opencode"
GLM_MODEL = "opencode/glm-4.7-free"


def ensure_filing_extracted(company: str, filing_stem: str) -> Path:
    """Ensure PDF is extracted to markdown, return path to MD file.

    Args:
        company: Company ID (e.g., 'getinge')
        filing_stem: Filename without extension (e.g., 'annual-2024')

    Returns:
        Path to the markdown file
    """
    project_root = Path(__file__).parent.parent
    raw_dir = project_root / "data" / "filings" / "raw"
    extracted_dir = project_root / "data" / "filings" / "extracted"

    pdf_path = raw_dir / company / f"{filing_stem}.pdf"
    md_path = extracted_dir / company / f"{filing_stem}.md"

    if md_path.exists():
        return md_path

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    print(f"  Extracting {pdf_path.name}...")
    parser = PDFParser()
    markdown = parser.to_markdown(pdf_path)

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown, encoding='utf-8')
    print(f"  Extracted: {md_path.name} ({len(markdown):,} chars)")

    return md_path


def extract_filing_metadata(filepath: Path) -> dict:
    """Extract metadata from filing filename."""
    stem = filepath.stem

    # Parse filename pattern: {company}_{type}_{year}[_q{quarter}]
    # e.g., getinge_annual_report_2024, getinge_quarterly_q3_2024

    metadata = {
        "company_id": None,
        "filing_type": None,
        "fiscal_year": None,
        "fiscal_quarter": None,
    }

    # Try to extract company name (first part)
    parts = stem.lower().split("_")
    if parts:
        metadata["company_id"] = parts[0]

    # Detect filing type
    if "annual" in stem.lower():
        metadata["filing_type"] = "annual"
    elif "quarterly" in stem.lower() or "_q" in stem.lower():
        metadata["filing_type"] = "quarterly"

    # Extract year (4-digit number)
    year_match = re.search(r"20\d{2}", stem)
    if year_match:
        metadata["fiscal_year"] = int(year_match.group())

    # Extract quarter if quarterly
    quarter_match = re.search(r"q(\d)", stem.lower())
    if quarter_match:
        metadata["fiscal_quarter"] = int(quarter_match.group(1))

    return metadata


def extract_sections(content: str) -> dict:
    """Extract all relevant sections from filing."""
    sections = {}

    ceo_section = find_ceo_letter_section(content)
    if ceo_section:
        sections["ceo_letter"] = ceo_section[:15000]  # Limit size
        print(f"   - CEO Letter: {len(ceo_section.split()):,} ord")

    mda_section = find_mda_section(content)
    if mda_section:
        sections["mda"] = mda_section[:20000]
        print(f"   - MD&A: {len(mda_section.split()):,} ord")

    risk_section = find_risk_factors_section(content)
    if risk_section:
        sections["risk_factors"] = risk_section[:15000]
        print(f"   - Risk Factors: {len(risk_section.split()):,} ord")

    guidance_section = find_guidance_section(content)
    if guidance_section:
        sections["guidance"] = guidance_section[:10000]
        print(f"   - Guidance: {len(guidance_section.split()):,} ord")

    segment_section = find_segment_section(content)
    if segment_section:
        sections["segments"] = segment_section[:15000]
        print(f"   - Segments: {len(segment_section.split()):,} ord")

    return sections


def build_analysis_prompt(
    sections: dict,
    company_name: str,
    fiscal_period: str,
    document_type: str,
) -> str:
    """Build the analysis prompt with sections."""

    # Build filing content from sections
    filing_content_parts = []

    if "ceo_letter" in sections:
        filing_content_parts.append(f"## CEO LETTER\n\n{sections['ceo_letter']}")

    if "mda" in sections:
        filing_content_parts.append(f"## MD&A (MANAGEMENT DISCUSSION & ANALYSIS)\n\n{sections['mda']}")

    if "risk_factors" in sections:
        filing_content_parts.append(f"## RISK FACTORS\n\n{sections['risk_factors']}")

    if "guidance" in sections:
        filing_content_parts.append(f"## GUIDANCE / OUTLOOK\n\n{sections['guidance']}")

    if "segments" in sections:
        filing_content_parts.append(f"## SEGMENT INFORMATION\n\n{sections['segments']}")

    filing_content = "\n\n---\n\n".join(filing_content_parts)

    # Use the full filing analysis prompt template
    prompt = FULL_FILING_ANALYSIS_PROMPT.format(
        company_name=company_name,
        fiscal_period=fiscal_period,
        document_type=document_type,
        filing_content=filing_content,
    )

    # Add output instructions
    prompt += """

IMPORTANT: Return ONLY valid JSON. No markdown code blocks, no extra text.
The JSON must be parseable directly.
"""

    return prompt


def parse_opencode_output(stdout: str) -> Optional[dict]:
    """Parse JSON output from OpenCode CLI."""

    ai_response = None
    tokens_info = None

    for line in stdout.split('\n'):
        if line.strip():
            try:
                event = json.loads(line)
                if event.get("type") == "text":
                    ai_response = event.get("part", {}).get("text")
                elif event.get("type") == "step_finish":
                    tokens_info = event.get("part", {}).get("tokens", {})
            except json.JSONDecodeError:
                pass

    if not ai_response:
        return None

    data = extract_json_from_response(ai_response)

    if data and tokens_info:
        data["_token_usage"] = tokens_info

    return data


def validate_analysis(data: dict) -> tuple[bool, str]:
    """Validate analysis against expected schema."""

    # Required top-level fields
    required_fields = ["executive_summary", "key_highlights"]

    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"

    # Validate ceo_letter if present
    if "ceo_letter" in data and data["ceo_letter"]:
        ceo = data["ceo_letter"]
        ceo_required = ["tone", "confidence_level"]
        for field in ceo_required:
            if field not in ceo:
                return False, f"ceo_letter missing field: {field}"

        valid_tones = ["optimistic", "cautiously_optimistic", "neutral", "cautious", "defensive"]
        if ceo.get("tone") not in valid_tones:
            return False, f"ceo_letter invalid tone: {ceo.get('tone')}"

        valid_confidence = ["high", "medium", "low"]
        if ceo.get("confidence_level") not in valid_confidence:
            return False, f"ceo_letter invalid confidence_level: {ceo.get('confidence_level')}"

    # Validate guidance if present
    if "guidance" in data and data["guidance"]:
        guidance = data["guidance"]
        if "overall_direction" in guidance:
            valid_directions = ["raised", "maintained", "lowered"]
            if guidance["overall_direction"] not in valid_directions:
                return False, f"guidance invalid overall_direction: {guidance['overall_direction']}"

    return True, ""


def analyze_filing(
    filing_path: Path,
    max_retries: int = 3,
    timeout: int = 600,  # 10 min for large filings
) -> tuple[Optional[dict], bool, str]:
    """
    Analyze a financial filing with GLM-4.7.

    Returns:
        (analysis_data, success, error_message)
    """

    for attempt in range(1, max_retries + 1):
        try:
            # Read content
            content = filing_path.read_text(encoding="utf-8")
            word_count = len(content.split())

            print(f"  📝 Analyserar: {filing_path.name} ({word_count:,} ord) [forsok {attempt}/{max_retries}]")

            # Extract metadata
            metadata = extract_filing_metadata(filing_path)
            company_name = metadata["company_id"] or "Unknown"

            if metadata["filing_type"] == "quarterly":
                fiscal_period = f"Q{metadata['fiscal_quarter']} {metadata['fiscal_year']}"
            else:
                fiscal_period = f"FY {metadata['fiscal_year']}"

            document_type = f"{metadata['filing_type'].title()} Report" if metadata["filing_type"] else "Financial Report"

            # Extract sections
            print("   Extraherar sektioner...")
            sections = extract_sections(content)

            if not sections:
                return None, False, "No sections found in document"

            # Build prompt
            prompt = build_analysis_prompt(
                sections=sections,
                company_name=company_name.title(),
                fiscal_period=fiscal_period,
                document_type=document_type,
            )

            # Call OpenCode CLI
            cmd = [
                OPENCODE_CLI, "run",
                "--format", "json",
                "-m", GLM_MODEL,
                prompt
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode != 0:
                error = f"CLI error (exit {result.returncode}): {result.stderr[:200]}"
                if attempt < max_retries:
                    print(f"  ⚠️  {error} - forsoker igen...")
                    continue
                return None, False, error

            # Parse response
            data = parse_opencode_output(result.stdout)

            if not data:
                error = "Kunde inte parsa JSON-respons"
                if attempt < max_retries:
                    print(f"  ⚠️  {error} - forsoker igen...")
                    continue
                return None, False, error

            # Validate
            is_valid, validation_error = validate_analysis(data)

            if not is_valid:
                error = f"Validation error: {validation_error}"
                if attempt < max_retries:
                    print(f"  ⚠️  {error} - forsoker igen...")
                    continue
                return None, False, error

            # Add metadata
            tokens = data.pop("_token_usage", {})
            data["filing_id"] = filing_path.stem
            data["company_id"] = metadata["company_id"]
            data["filing_type"] = metadata["filing_type"]
            data["fiscal_year"] = metadata["fiscal_year"]
            data["fiscal_quarter"] = metadata["fiscal_quarter"]
            data["analyzed_at"] = datetime.now().isoformat()
            data["model_used"] = "glm-4.7"

            print(f"  ✅ Analys klar! Tokens: {tokens.get('input', 0):,} in / {tokens.get('output', 0):,} out")

            return data, True, ""

        except subprocess.TimeoutExpired:
            error = f"Timeout efter {timeout} sekunder"
            if attempt < max_retries:
                print(f"  ⚠️  {error} - forsoker igen...")
                continue
            return None, False, error

        except Exception as e:
            error = f"Unexpected error: {str(e)}"
            if attempt < max_retries:
                print(f"  ⚠️  {error} - forsoker igen...")
                continue
            return None, False, error

    return None, False, "Max retries exceeded"


def save_analysis(analysis: dict, output_dir: Path) -> Path:
    """Save analysis to JSON file."""

    output_file = output_dir / f"{analysis['filing_id']}.json"

    output_file.write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return output_file


def get_pending_filings(company: Optional[str] = None) -> list[tuple[str, str]]:
    """Get list of filings that haven't been analyzed yet.

    Checks both raw/ (PDFs) and extracted/ (MDs) to find all potential filings.

    Returns:
        List of (company_id, filing_stem) tuples
    """
    project_root = Path(__file__).parent.parent
    raw_dir = project_root / "data" / "filings" / "raw"
    extracted_dir = project_root / "data" / "filings" / "extracted"
    analysis_dir = project_root / "data" / "filings" / "analysis"

    pending = []

    # Gather all companies from both raw and extracted
    companies = set()
    if raw_dir.exists():
        companies.update(d.name for d in raw_dir.iterdir()
                        if d.is_dir() and d.name != 'presentations')
    if extracted_dir.exists():
        companies.update(d.name for d in extracted_dir.iterdir() if d.is_dir())

    if company:
        companies = {company} if company in companies else set()

    for comp in companies:
        # Get all potential filings (from raw PDFs)
        all_filings = set()
        comp_raw = raw_dir / comp
        if comp_raw.exists():
            all_filings.update(p.stem for p in comp_raw.glob("*.pdf"))

        # Also include any extracted MDs (in case PDF was deleted)
        comp_extracted = extracted_dir / comp
        if comp_extracted.exists():
            all_filings.update(p.stem for p in comp_extracted.glob("*.md"))

        # Get analyzed
        analyzed = set()
        comp_analysis = analysis_dir / comp
        if comp_analysis.exists():
            analyzed = set(p.stem for p in comp_analysis.glob("*.json"))

        # Pending = all filings not yet analyzed
        for filing_stem in all_filings - analyzed:
            pending.append((comp, filing_stem))

    return sorted(pending)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze financial filings with GLM-4.7"
    )
    parser.add_argument(
        "filing",
        nargs="?",
        help="Path to filing (markdown file)"
    )
    parser.add_argument(
        "--batch",
        metavar="COMPANY",
        help="Analyze all pending filings for a company"
    )
    parser.add_argument(
        "--batch-all",
        action="store_true",
        help="Analyze all pending filings for all companies"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List pending filings"
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent

    # List mode
    if args.list:
        pending = get_pending_filings()
        if pending:
            print("PENDING FILINGS:")
            print("=" * 50)
            for company_id, filing_stem in pending:
                # Check if extraction is needed
                extracted_path = project_root / "data" / "filings" / "extracted" / company_id / f"{filing_stem}.md"
                status = "[MD]" if extracted_path.exists() else "[PDF]"
                print(f"  {status} {company_id}/{filing_stem}")
            print("=" * 50)
            print(f"Total: {len(pending)} filings")
        else:
            print("No pending filings")
        return

    # Batch mode
    if args.batch or args.batch_all:
        company = args.batch if args.batch else None
        pending = get_pending_filings(company)

        if not pending:
            print("No pending filings")
            return

        print(f"Analyzing {len(pending)} filings...")
        print("=" * 50)

        success_count = 0
        fail_count = 0

        for i, (company_id, filing_stem) in enumerate(pending, 1):
            print(f"\n[{i}/{len(pending)}] {company_id}/{filing_stem}")

            try:
                # Ensure extracted (auto-extract if needed)
                filing_path = ensure_filing_extracted(company_id, filing_stem)
            except FileNotFoundError as e:
                print(f"  Misslyckades: {e}")
                fail_count += 1
                continue

            analysis, success, error = analyze_filing(filing_path)

            if success and analysis:
                # Determine output directory
                output_dir = project_root / "data" / "filings" / "analysis" / company_id
                output_dir.mkdir(parents=True, exist_ok=True)

                output_file = save_analysis(analysis, output_dir)
                print(f"  Sparade: {output_file.relative_to(project_root)}")
                success_count += 1
            else:
                print(f"  Misslyckades: {error}")
                fail_count += 1

        print("\n" + "=" * 50)
        print(f"Resultat: {success_count} lyckades, {fail_count} misslyckades")
        return

    # Single file mode
    if not args.filing:
        parser.print_help()
        sys.exit(1)

    filing_path = Path(args.filing)

    if not filing_path.exists():
        print(f"Fel: Filen existerar inte: {filing_path}")
        sys.exit(1)

    # If PDF, extract first
    if filing_path.suffix.lower() == '.pdf':
        # Determine company from path
        company_id = filing_path.parent.name
        filing_stem = filing_path.stem
        try:
            filing_path = ensure_filing_extracted(company_id, filing_stem)
        except FileNotFoundError as e:
            print(f"Fel: {e}")
            sys.exit(1)

    analysis, success, error = analyze_filing(filing_path)

    if success and analysis:
        # Determine output directory
        company_id = analysis["company_id"]
        output_dir = project_root / "data" / "filings" / "analysis" / company_id
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = save_analysis(analysis, output_dir)
        print(f"  Sparade: {output_file}")
        sys.exit(0)
    else:
        print(f"  Misslyckades: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
