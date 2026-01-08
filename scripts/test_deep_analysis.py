#!/usr/bin/env python
"""Test script for deep filing analysis."""

import json
from datetime import datetime
from pathlib import Path

from podstock.filings import DeepFilingAnalyzer, Filing, FilingType, FilingSource


def main():
    """Run deep analysis on Getinge annual report."""
    # Setup paths
    project_root = Path(__file__).parent.parent
    filing_path = (
        project_root
        / "data/filings/extracted/getinge/getinge_annual_report_2024.md"
    )
    output_path = project_root / "data/filings/analysis/getinge/annual-2024.json"

    # Check file exists
    if not filing_path.exists():
        raise FileNotFoundError(f"Filing not found: {filing_path}")

    print(f"Reading filing: {filing_path}")
    content = filing_path.read_text()
    print(f"Content length: {len(content):,} characters")

    # Create Filing object
    filing = Filing(
        id="getinge-annual-2024",
        company_id="getinge",
        filing_type=FilingType.ANNUAL_REPORT,
        fiscal_year=2024,
        fiscal_quarter=None,
        filing_date=datetime(2025, 3, 15),  # Approximate publication date
        period_end_date=datetime(2024, 12, 31),
        source=FilingSource.MANUAL_PDF,
        source_url=None,
        local_path=str(filing_path),
        language="en",
        analyzed=False,
    )

    # Initialize analyzer
    print("\nInitializing DeepFilingAnalyzer...")
    analyzer = DeepFilingAnalyzer()

    # Run analysis
    print("Running deep analysis (this will call the LLM)...")
    print("This may take a few minutes as it analyzes multiple sections...\n")
    analysis = analyzer.analyze_filing(
        filing=filing,
        document_path=filing_path,
        previous_analysis=None,
    )

    # Save result
    print(f"\nSaving analysis to: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(analysis.model_dump(mode="json"), f, indent=2, default=str)

    # Print summary
    print("\n" + "=" * 60)
    print("ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Filing ID: {analysis.filing_id}")
    print(f"Company: {analysis.company_id}")
    print(f"Type: {analysis.filing_type}")

    if analysis.ceo_letter:
        ceo = analysis.ceo_letter
        print(f"\nCEO Letter:")
        print(f"  Author: {ceo.author} ({ceo.title})")
        print(f"  Word count: {ceo.word_count}")
        print(f"  Tone: {ceo.tone}")
        print(f"  Confidence: {ceo.confidence_level}")
        print(f"  Promises: {len(ceo.promises)}")
        for p in ceo.promises[:3]:
            print(f"    - {p.metric}: {p.target} ({p.timeframe})")
        print(f"  Themes: {len(ceo.themes)}")
        for t in ceo.themes[:3]:
            print(f"    - {t.topic}: {t.emphasis} emphasis, {t.sentiment}")
        print(f"  Challenges: {len(ceo.challenges)}")
        for c in ceo.challenges[:3]:
            print(f"    - {c.challenge} ({c.attribution})")

    if analysis.mda_analysis:
        mda = analysis.mda_analysis
        print(f"\nMD&A Analysis:")
        print(f"  Key narratives: {len(mda.key_narratives)}")
        for n in mda.key_narratives[:3]:
            print(f"    - {n[:80]}...")
        print(f"  Segments: {len(mda.segment_commentary)}")

    if analysis.guidance:
        g = analysis.guidance
        print(f"\nGuidance:")
        print(f"  Targets: {len(g.targets)}")
        for t in g.targets[:3]:
            print(f"    - {t.metric}: {t.value} ({t.period})")
        print(f"  Direction: {g.overall_direction}")

    if analysis.segment_reporting:
        print(f"\nSegments analyzed: {len(analysis.segment_reporting)}")
        for s in analysis.segment_reporting[:3]:
            print(f"  - {s.name}: {s.performance}")

    if analysis.risk_factors:
        rf = analysis.risk_factors
        print(f"\nRisk Factors:")
        print(f"  Total risks: {len(rf.risks)}")
        print(f"  New risks: {rf.new_risks_count}")
        print(f"  Boilerplate ratio: {rf.boilerplate_ratio:.0%}")

    print("\n" + "=" * 60)
    print(f"Full analysis saved to: {output_path}")


if __name__ == "__main__":
    main()
