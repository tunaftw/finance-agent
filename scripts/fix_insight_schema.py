#!/usr/bin/env python3
"""Fix insight schema in existing analysis files.

Transforms wrong format (topic/insight) to correct v2.1 (quote/summary/category/tags).
Creates .bak backups before modifying files.

Usage:
    python3 scripts/fix_insight_schema.py --dry-run  # Preview changes
    python3 scripts/fix_insight_schema.py            # Apply changes
"""

import json
import shutil
from pathlib import Path


def normalize_insight(ins: dict) -> dict:
    """Transform wrong insight schema to correct v2.1 format."""
    if "summary" in ins and "quote" in ins:
        return ins  # Already correct

    if "insight" in ins or "topic" in ins:
        insight_text = ins.get("insight", ins.get("topic", ""))
        return {
            "quote": insight_text,
            "summary": insight_text,
            "category": ins.get("category", "wisdom"),
            "speaker": ins.get("speaker", ""),
            "speaker_role": ins.get("speaker_role", "unknown"),
            "timestamp": ins.get("timestamp"),
            "confidence": ins.get("confidence", "medium"),
            "tags": ins.get("tags", []),
        }

    return ins


def fix_file(filepath: Path, dry_run: bool = False) -> tuple[bool, int]:
    """Fix insights in a single file.

    Returns: (was_modified, num_insights_fixed)
    """
    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  [!] Could not read {filepath.name}: {e}")
        return False, 0

    insights = data.get("insights", [])
    if not insights:
        return False, 0

    fixed_count = 0
    new_insights = []

    for ins in insights:
        # Check if needs fixing
        needs_fix = "summary" not in ins and ("insight" in ins or "topic" in ins)
        if needs_fix:
            new_insights.append(normalize_insight(ins))
            fixed_count += 1
        else:
            new_insights.append(ins)

    if fixed_count == 0:
        return False, 0

    if dry_run:
        print(f"  [*] Would fix {fixed_count} insights in {filepath.name}")
        return True, fixed_count

    # Create backup
    backup_path = filepath.with_suffix(".json.bak")
    shutil.copy2(filepath, backup_path)

    # Write fixed data
    data["insights"] = new_insights
    filepath.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"  [+] Fixed {fixed_count} insights in {filepath.name}")
    return True, fixed_count


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fix insight schema in analysis files")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be fixed without modifying"
    )
    parser.add_argument(
        "--path",
        default="data/podcasts/analyses-v2",
        help="Path to analyses directory",
    )
    args = parser.parse_args()

    analyses_dir = Path(args.path)
    if not analyses_dir.exists():
        print(f"[!] Directory not found: {analyses_dir}")
        return 1

    print(f"{'DRY RUN - ' if args.dry_run else ''}Scanning {analyses_dir}...")
    print()

    files_fixed = 0
    insights_fixed = 0

    for filepath in sorted(analyses_dir.glob("*-20??-??-??-????.json")):
        was_modified, count = fix_file(filepath, dry_run=args.dry_run)
        if was_modified:
            files_fixed += 1
            insights_fixed += count

    print()
    print("=" * 50)
    if args.dry_run:
        print(f"Would fix {insights_fixed} insights in {files_fixed} files")
    else:
        print(f"[+] Fixed {insights_fixed} insights in {files_fixed} files")
        if files_fixed > 0:
            print("    Backups created with .bak extension")

    return 0


if __name__ == "__main__":
    exit(main())
