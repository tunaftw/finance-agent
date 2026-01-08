#!/usr/bin/env python
"""Test script for section extraction (no LLM calls)."""

from pathlib import Path

from podstock.filings.analysis.ceo_letter import find_ceo_letter_section
from podstock.filings.analysis.deep_analysis import (
    find_guidance_section,
    find_mda_section,
    find_risk_factors_section,
    find_segment_section,
)


def main():
    """Test section extraction on Getinge annual report."""
    # Setup paths
    project_root = Path(__file__).parent.parent
    filing_path = (
        project_root
        / "data/filings/extracted/getinge/getinge_annual_report_2024.md"
    )

    # Read content
    print(f"Reading: {filing_path}")
    content = filing_path.read_text()
    print(f"Content length: {len(content):,} characters\n")

    # Test CEO letter extraction
    print("=" * 60)
    print("CEO LETTER SECTION EXTRACTION")
    print("=" * 60)
    ceo_section = find_ceo_letter_section(content)

    if ceo_section:
        print(f"Found CEO letter section: {len(ceo_section):,} characters")
        print(f"Word count: ~{len(ceo_section.split()):,} words")
        print("\nFirst 500 characters:")
        print("-" * 40)
        print(ceo_section[:500])
        print("-" * 40)
        print("\nLast 500 characters:")
        print("-" * 40)
        print(ceo_section[-500:])
    else:
        print("CEO letter section NOT FOUND")

    # Test other section finders
    print("\n" + "=" * 60)
    print("OTHER SECTION EXTRACTION")
    print("=" * 60)

    # Test MD&A section
    mda_section = find_mda_section(content)
    if mda_section:
        print(f"\nMD&A section: {len(mda_section):,} characters (~{len(mda_section.split()):,} words)")
        print(f"Preview: {mda_section[:200]}...")
    else:
        print("\nMD&A section: NOT FOUND")

    # Test Risk Factors section
    risk_section = find_risk_factors_section(content)
    if risk_section:
        print(f"\nRisk Factors section: {len(risk_section):,} characters (~{len(risk_section.split()):,} words)")
        print(f"Preview: {risk_section[:200]}...")
    else:
        print("\nRisk Factors section: NOT FOUND")

    # Test Guidance section
    guidance_section = find_guidance_section(content)
    if guidance_section:
        print(f"\nGuidance section: {len(guidance_section):,} characters (~{len(guidance_section.split()):,} words)")
        print(f"Preview: {guidance_section[:200]}...")
    else:
        print("\nGuidance section: NOT FOUND")

    # Test Segment section
    segment_section = find_segment_section(content)
    if segment_section:
        print(f"\nSegment section: {len(segment_section):,} characters (~{len(segment_section.split()):,} words)")
        print(f"Preview: {segment_section[:200]}...")
    else:
        print("\nSegment section: NOT FOUND")

    print("\n" + "=" * 60)
    print("SECTION EXTRACTION COMPLETE")
    print("=" * 60)
    print("\nTo run analysis:")
    print("  Claude Code: /analyze-filings (choose Claude Code method)")
    print("  OpenCode: python scripts/filings_glm_driver.py <filing_path>")


if __name__ == "__main__":
    main()
