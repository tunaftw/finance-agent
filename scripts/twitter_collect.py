#!/usr/bin/env python3
"""Smart Twitter collection utilities.

This script provides tools for efficient tweet collection:
- Coverage analysis (which periods are complete/incomplete/missing)
- Gap detection (identify periods needing collection)
- URL generation (search URLs for specific date ranges)
- Browser deduplication (export existing IDs for JS)
- Tweet saving (save browser-collected tweets to JSONL)

Usage:
    # Show coverage analysis
    python scripts/twitter_collect.py coverage vildkatten

    # Generate URLs for gaps only
    python scripts/twitter_collect.py urls vildkatten --gaps-only

    # Export existing IDs for browser dedup
    python scripts/twitter_collect.py ids vildkatten

    # Save tweets from browser JSON
    python scripts/twitter_collect.py save vildkatten --data '[{"id":"123",...}]'
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from podstock.twitter.models import Tweet
from podstock.twitter.storage import TweetStorage


# Constants
DATA_DIR = Path(__file__).parent.parent / "data"
MIN_TWEETS_FOR_COMPLETE = 20  # Period needs 20+ tweets to be "complete"


def analyze_coverage(source_id: str) -> dict[str, Any]:
    """Analyze tweet coverage for a source.

    Returns information about:
    - Total tweets collected
    - Date range covered
    - Complete months (20+ tweets and fully scrolled)
    - Incomplete months (<20 tweets)
    - Missing months (no tweets at all)

    Args:
        source_id: Twitter handle/source identifier.

    Returns:
        Coverage analysis dictionary.
    """
    storage = TweetStorage(DATA_DIR)
    tweets = list(storage.load_tweets(source_id))

    if not tweets:
        return {
            "source_id": source_id,
            "total_tweets": 0,
            "oldest_date": None,
            "newest_date": None,
            "by_month": {},
            "complete_months": [],
            "incomplete_months": [],
            "missing_months": [],
        }

    # Group by month
    by_month: dict[str, list[Tweet]] = defaultdict(list)
    for tweet in tweets:
        month_key = tweet.posted_at.strftime("%Y-%m")
        by_month[month_key].append(tweet)

    # Find date range
    dates = [t.posted_at for t in tweets]
    oldest = min(dates)
    newest = max(dates)

    # Generate all months in range
    all_months = []
    current = oldest.replace(day=1)
    end = newest.replace(day=1)
    while current <= end:
        all_months.append(current.strftime("%Y-%m"))
        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    # Categorize months
    complete_months = []
    incomplete_months = []
    missing_months = []

    for month in all_months:
        count = len(by_month.get(month, []))
        if count == 0:
            missing_months.append(month)
        elif count < MIN_TWEETS_FOR_COMPLETE:
            incomplete_months.append((month, count))
        else:
            complete_months.append((month, count))

    return {
        "source_id": source_id,
        "total_tweets": len(tweets),
        "oldest_date": oldest.isoformat(),
        "newest_date": newest.isoformat(),
        "by_month": {k: len(v) for k, v in sorted(by_month.items())},
        "complete_months": complete_months,
        "incomplete_months": incomplete_months,
        "missing_months": missing_months,
    }


def print_coverage(coverage: dict[str, Any]) -> None:
    """Print coverage analysis in human-readable format."""
    print(f"\n{'='*60}")
    print(f"Coverage Analysis: @{coverage['source_id']}")
    print(f"{'='*60}")

    if coverage["total_tweets"] == 0:
        print("No tweets collected yet.")
        return

    print(f"\nTotal tweets: {coverage['total_tweets']}")
    print(f"Date range: {coverage['oldest_date'][:10]} -> {coverage['newest_date'][:10]}")

    # Complete months
    if coverage["complete_months"]:
        print(f"\nComplete months ({len(coverage['complete_months'])}):")
        for month, count in coverage["complete_months"]:
            print(f"  {month}: {count} tweets")

    # Incomplete months
    if coverage["incomplete_months"]:
        print(f"\nIncomplete months ({len(coverage['incomplete_months'])}):")
        for month, count in coverage["incomplete_months"]:
            print(f"  {month}: {count} tweets (< {MIN_TWEETS_FOR_COMPLETE})")

    # Missing months
    if coverage["missing_months"]:
        print(f"\nMissing months ({len(coverage['missing_months'])}):")
        for month in coverage["missing_months"]:
            print(f"  {month}")

    # Recommendations
    print(f"\n{'='*60}")
    print("Recommendations:")
    if coverage["missing_months"]:
        print(f"  - Collect missing periods: {', '.join(coverage['missing_months'][:5])}" +
              (f" (+{len(coverage['missing_months'])-5} more)" if len(coverage['missing_months']) > 5 else ""))
    if coverage["incomplete_months"]:
        months = [m for m, _ in coverage["incomplete_months"]]
        print(f"  - Re-scan incomplete periods: {', '.join(months[:5])}" +
              (f" (+{len(months)-5} more)" if len(months) > 5 else ""))
    if not coverage["missing_months"] and not coverage["incomplete_months"]:
        print("  - All periods appear complete!")


def generate_search_url(handle: str, start_date: str, end_date: str) -> str:
    """Generate Twitter advanced search URL for date range.

    Args:
        handle: Twitter handle (without @).
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD).

    Returns:
        Twitter search URL.
    """
    query = f"from:{handle} since:{start_date} until:{end_date}"
    encoded = query.replace(":", "%3A").replace(" ", "%20")
    return f"https://x.com/search?q={encoded}&src=typed_query&f=live"


def generate_gap_urls(
    source_id: str,
    mode: str = "all",
    year: int | None = None,
) -> list[dict[str, str]]:
    """Generate search URLs for missing/incomplete periods.

    Args:
        source_id: Twitter handle.
        mode: "all" | "gaps-only" | "incomplete"
        year: Optional year filter.

    Returns:
        List of {start_date, end_date, url, reason} dicts.
    """
    coverage = analyze_coverage(source_id)
    urls = []

    # Collect target months based on mode
    target_months = []

    if mode in ("all", "gaps-only"):
        for month in coverage["missing_months"]:
            if year is None or month.startswith(str(year)):
                target_months.append((month, "missing"))

    if mode in ("all", "incomplete"):
        for month, count in coverage["incomplete_months"]:
            if year is None or month.startswith(str(year)):
                target_months.append((month, f"incomplete ({count} tweets)"))

    # Generate URLs for each month
    for month, reason in sorted(target_months):
        year_m, month_m = int(month[:4]), int(month[5:7])

        # Start of month
        start_date = f"{year_m}-{month_m:02d}-01"

        # End of month (first day of next month)
        if month_m == 12:
            end_date = f"{year_m + 1}-01-01"
        else:
            end_date = f"{year_m}-{month_m + 1:02d}-01"

        urls.append({
            "start_date": start_date,
            "end_date": end_date,
            "month": month,
            "reason": reason,
            "url": generate_search_url(source_id, start_date, end_date),
        })

    return urls


def get_existing_ids(source_id: str) -> set[str]:
    """Get all existing tweet IDs for a source.

    Args:
        source_id: Twitter handle.

    Returns:
        Set of tweet IDs.
    """
    storage = TweetStorage(DATA_DIR)
    return storage.get_tweet_ids(source_id)


def get_existing_ids_json(source_id: str) -> str:
    """Get existing IDs as JSON array for browser.

    Args:
        source_id: Twitter handle.

    Returns:
        JSON array string.
    """
    ids = get_existing_ids(source_id)
    return json.dumps(list(ids))


def save_tweets_from_json(
    source_id: str,
    json_data: str | list[dict],
) -> dict[str, int]:
    """Save tweets from browser-collected JSON.

    Args:
        source_id: Twitter handle.
        json_data: JSON string or list of tweet dicts.

    Returns:
        Dict with saved/skipped counts.
    """
    storage = TweetStorage(DATA_DIR)
    existing_ids = storage.get_tweet_ids(source_id)

    # Parse JSON if string
    if isinstance(json_data, str):
        # Handle special quotes from browser
        json_data = json_data.replace("\u201c", '"').replace("\u201d", '"')
        json_data = json_data.replace("\u2018", "'").replace("\u2019", "'")
        tweets_data = json.loads(json_data)
    else:
        tweets_data = json_data

    now = datetime.now(timezone.utc)
    saved = 0
    skipped = 0

    for t in tweets_data:
        tweet_id = t.get("id")
        if not tweet_id:
            continue

        if tweet_id in existing_ids:
            skipped += 1
            continue

        # Parse posted date
        posted = t.get("posted")
        if posted:
            if posted.endswith("Z"):
                posted_at = datetime.fromisoformat(posted.replace("Z", "+00:00"))
            else:
                posted_at = datetime.fromisoformat(posted)
        else:
            posted_at = now

        tweet = Tweet(
            id=tweet_id,
            source_id=source_id,
            author_handle=source_id,
            text=t.get("text", ""),
            posted_at=posted_at,
            collected_at=now,
        )

        # Extract entities
        tweet.extract_entities()

        storage.save_tweet(tweet)
        existing_ids.add(tweet_id)
        saved += 1

    return {
        "saved": saved,
        "skipped": skipped,
        "total": storage.get_tweet_count(source_id),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Smart Twitter collection utilities"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # coverage command
    coverage_parser = subparsers.add_parser(
        "coverage",
        help="Analyze tweet coverage for a source"
    )
    coverage_parser.add_argument("source_id", help="Twitter handle")
    coverage_parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON"
    )

    # urls command
    urls_parser = subparsers.add_parser(
        "urls",
        help="Generate search URLs for collection"
    )
    urls_parser.add_argument("source_id", help="Twitter handle")
    urls_parser.add_argument(
        "--mode",
        choices=["all", "gaps-only", "incomplete"],
        default="all",
        help="Which periods to include"
    )
    urls_parser.add_argument(
        "--year", type=int,
        help="Filter to specific year"
    )
    urls_parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON"
    )

    # ids command
    ids_parser = subparsers.add_parser(
        "ids",
        help="Export existing tweet IDs"
    )
    ids_parser.add_argument("source_id", help="Twitter handle")
    ids_parser.add_argument(
        "--format",
        choices=["json", "count"],
        default="json",
        help="Output format"
    )

    # save command
    save_parser = subparsers.add_parser(
        "save",
        help="Save tweets from browser JSON"
    )
    save_parser.add_argument("source_id", help="Twitter handle")
    save_parser.add_argument(
        "--data",
        help="JSON array of tweets (or pass via stdin)"
    )
    save_parser.add_argument(
        "--file",
        help="Read JSON from file"
    )

    # url command (single URL)
    url_parser = subparsers.add_parser(
        "url",
        help="Generate single search URL"
    )
    url_parser.add_argument("source_id", help="Twitter handle")
    url_parser.add_argument("--since", required=True, help="Start date (YYYY-MM-DD)")
    url_parser.add_argument("--until", required=True, help="End date (YYYY-MM-DD)")

    args = parser.parse_args()

    if args.command == "coverage":
        coverage = analyze_coverage(args.source_id)
        if args.json:
            print(json.dumps(coverage, indent=2))
        else:
            print_coverage(coverage)

    elif args.command == "urls":
        urls = generate_gap_urls(
            args.source_id,
            mode=args.mode,
            year=args.year,
        )
        if args.json:
            print(json.dumps(urls, indent=2))
        else:
            if not urls:
                print("No URLs to generate - all periods complete!")
            else:
                print(f"\nSearch URLs for @{args.source_id}:")
                print("-" * 60)
                for item in urls:
                    print(f"\n{item['month']} ({item['reason']}):")
                    print(f"  {item['url']}")

    elif args.command == "ids":
        if args.format == "count":
            ids = get_existing_ids(args.source_id)
            print(len(ids))
        else:
            print(get_existing_ids_json(args.source_id))

    elif args.command == "save":
        if args.file:
            with open(args.file) as f:
                data = f.read()
        elif args.data:
            data = args.data
        else:
            # Read from stdin
            data = sys.stdin.read()

        result = save_tweets_from_json(args.source_id, data)
        print(f"Saved: {result['saved']}, Skipped: {result['skipped']}")
        print(f"Total tweets now: {result['total']}")

    elif args.command == "url":
        url = generate_search_url(args.source_id, args.since, args.until)
        print(url)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
