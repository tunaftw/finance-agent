#!/usr/bin/env python3
"""Import Börsmagasinet 2025 recommendations to the price tracker.

This script reads all Börsmagasinet episode JSON files and imports
buy/sell recommendations to the price tracking system with entry prices.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from podstock.prices.tracker import PriceTracker
from podstock.prices.exceptions import TickerNotFoundError, PriceNotAvailableError


def load_borsmagasinet_episodes(data_dir: Path) -> list[dict]:
    """Load all Börsmagasinet episode JSON files."""
    glm_dir = data_dir / "extracted" / "glm-batch"
    episodes = []

    for f in sorted(glm_dir.glob("borsmagasinet-2025-*.json")):
        with open(f) as fp:
            episode = json.load(fp)
            episodes.append(episode)

    return episodes


def main():
    data_dir = Path(__file__).parent.parent / "data"
    tracker = PriceTracker(data_dir)

    print("=" * 60)
    print("Importing Börsmagasinet 2025 recommendations")
    print("=" * 60)

    episodes = load_borsmagasinet_episodes(data_dir)
    print(f"\nFound {len(episodes)} episodes")

    # Track statistics
    imported = 0
    skipped = 0
    failed = 0
    errors = []

    # Filter for actionable recommendations
    actionable = ["buy", "sell", "avoid"]

    for episode in episodes:
        episode_id = episode.get("episode_id", "unknown")
        episode_date_str = episode.get("date", "")

        try:
            episode_date = datetime.strptime(episode_date_str, "%Y-%m-%d")
        except ValueError:
            print(f"  Skipping {episode_id}: invalid date '{episode_date_str}'")
            continue

        recommendations = episode.get("recommendations", [])

        for rec in recommendations:
            action = rec.get("action", "").lower()

            # Only import actionable recommendations
            if action not in actionable:
                skipped += 1
                continue

            stock_name = rec.get("stock_name", "")
            ticker = rec.get("ticker")
            speaker = rec.get("speaker")
            confidence = rec.get("confidence", "medium")
            reasoning = rec.get("reasoning", "")
            sector = rec.get("sector")
            market = rec.get("market", "sweden")

            if market == "unknown" or market == "other":
                market = "sweden"  # Default to sweden for unknown markets

            # Detect market from ticker suffix if available
            if ticker:
                if ticker.endswith(".ST") or ticker.endswith("-B.ST") or ticker.endswith("-A.ST"):
                    market = "sweden"
                elif ticker.endswith(".OL"):
                    market = "norway"
                elif ticker.endswith(".CO"):
                    market = "denmark"
                elif ticker.endswith(".HE"):
                    market = "finland"
                elif ticker.endswith(".L"):
                    market = "uk"
                elif ticker.endswith(".DE"):
                    market = "germany"
                elif ticker.endswith(".PA"):
                    market = "france"
                elif ticker.endswith(".T"):
                    market = "japan"
                elif ticker.endswith(".HK"):
                    market = "hongkong"
                elif ticker.endswith(".TO") or ticker.endswith(".V"):
                    market = "canada"
                elif not "." in ticker:
                    market = "us"  # US tickers don't have suffix

            # Skip if no stock name
            if not stock_name:
                skipped += 1
                continue

            print(f"\n[{episode_date_str}] {stock_name} ({action.upper()})")
            print(f"  Ticker: {ticker or 'auto-resolve'}")
            print(f"  Confidence: {confidence}")
            print(f"  Reasoning: {reasoning[:80]}..." if len(reasoning) > 80 else f"  Reasoning: {reasoning}")

            try:
                tracked = tracker.track_recommendation(
                    source_type="podcast",
                    source_id=f"{episode_id}_{stock_name}",
                    source_name="Börsmagasinet",
                    asset_name=stock_name,
                    action=action,
                    recommendation_date=episode_date,
                    ticker=ticker,
                    speaker=speaker,
                    market=market,
                )

                entry_price = tracked.entry_price
                if entry_price:
                    print(f"  ✓ Entry price: {entry_price.price:.2f} {entry_price.currency}")
                    print(f"  ✓ Tracking ID: {tracked.tracking_id}")
                imported += 1

            except TickerNotFoundError as e:
                print(f"  ✗ Ticker not found: {e}")
                errors.append(f"{stock_name}: Ticker not found")
                failed += 1

            except PriceNotAvailableError as e:
                print(f"  ✗ Price not available: {e}")
                errors.append(f"{stock_name}: Price not available for {episode_date_str}")
                failed += 1

            except Exception as e:
                print(f"  ✗ Error: {e}")
                errors.append(f"{stock_name}: {str(e)}")
                failed += 1

    # Summary
    print("\n" + "=" * 60)
    print("IMPORT SUMMARY")
    print("=" * 60)
    print(f"Imported: {imported}")
    print(f"Skipped (watch/hold): {skipped}")
    print(f"Failed: {failed}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for err in errors[:20]:  # Show first 20 errors
            print(f"  - {err}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")

    # Now verify at today's prices
    print("\n" + "=" * 60)
    print("VERIFYING AT TODAY'S PRICES")
    print("=" * 60)

    results = tracker.verify_today()

    print(f"\nVerified {len(results)} recommendations:")

    # Sort by return
    results.sort(key=lambda x: x[1].percentage_return, reverse=True)

    for rec, result in results:
        direction = "✓" if result.direction_correct else "✗"
        sign = "+" if result.percentage_return > 0 else ""
        print(f"  {direction} {rec.asset_name}: {sign}{result.percentage_return:.1f}% "
              f"({rec.entry_price.price:.2f} → {result.price_snapshot.price:.2f} {rec.entry_price.currency})")

    # Calculate accuracy stats
    stats = tracker.get_accuracy_stats(source_name="Börsmagasinet")
    print(f"\nAccuracy: {stats.hit_rate}")
    if stats.average_return is not None:
        print(f"Average return: {stats.average_return:+.1f}%")
    if stats.best_return is not None:
        print(f"Best return: {stats.best_return:+.1f}%")
    if stats.worst_return is not None:
        print(f"Worst return: {stats.worst_return:+.1f}%")


if __name__ == "__main__":
    main()
