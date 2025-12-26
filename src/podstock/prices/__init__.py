"""Price tracking and verification for stock and crypto recommendations.

This module provides unified price tracking for both stocks (via Yahoo Finance)
and crypto (via Yahoo Finance with -USD suffix), enabling verification of
recommendations against actual price movements.

Main Components
---------------
PriceTracker
    Main service class for tracking and verifying recommendations.
    Coordinates between price clients, ticker mapping, and storage.

TickerMapper
    Maps company names to ticker symbols with fuzzy matching support.
    Maintains a JSON file with mappings and aliases.

RecommendationStorage
    JSONL-based storage for tracked recommendations.

Models
------
TrackedRecommendation
    A recommendation linked to price tracking data.
VerificationResult
    Price verification at a specific time interval.
PriceSnapshot
    A point-in-time price observation.
AccuracyStats
    Aggregated accuracy statistics for recommendations.
ImportResult
    Result of importing recommendations from extractions.
AssetType
    Enum: STOCK or CRYPTO.

Quick Start
-----------
Track a recommendation manually::

    from pathlib import Path
    from datetime import datetime
    from podstock.prices import PriceTracker

    tracker = PriceTracker(Path("data"))
    rec = tracker.track_recommendation(
        source_type="podcast",
        source_id="fillorkill-2024-06-15",
        source_name="Fill or Kill",
        asset_name="Evolution",
        action="buy",
        recommendation_date=datetime(2024, 6, 15),
    )

Import from extracted recommendations::

    result = tracker.import_from_extractions(
        podcast="fill or kill",
        since_date=datetime(2024, 6, 1),
        actions=["buy"],
    )
    print(f"Imported {result.imported} recommendations")

Verify recommendations::

    # Verify at current prices
    results = tracker.verify_today()

    # Verify all due intervals
    results = tracker.verify_all_due()

Get accuracy statistics::

    stats = tracker.get_accuracy_stats(source_name="Fill or Kill")
    print(f"Hit rate: {stats.hit_rate}")

CLI Commands
------------
The following CLI commands are available via ``podstock prices``:

``podstock prices track <stock> <action>``
    Track a new recommendation manually.

``podstock prices import [options]``
    Import recommendations from extracted episode data.
    Options: --podcast, --stock, --episode, --since, --action, --dry-run, --force

``podstock prices verify [options]``
    Verify recommendations against current prices.
    Options: --all, --today, --id

``podstock prices list``
    List all tracked recommendations.

``podstock prices accuracy [options]``
    Show accuracy statistics.
    Options: --podcast, --speaker, --action

``podstock prices mapping <subcommand>``
    Manage ticker mappings: add, list, search, stats
"""

from podstock.prices.exceptions import (
    PriceError,
    PriceNotAvailableError,
    TickerNotFoundError,
)
from podstock.prices.models import (
    AccuracyStats,
    AssetType,
    ImportResult,
    PriceSnapshot,
    TrackedRecommendation,
    VerificationResult,
)
from podstock.prices.storage import RecommendationStorage
from podstock.prices.ticker_mapping import TickerMapper
from podstock.prices.tracker import PriceTracker

__all__ = [
    # Models
    "AccuracyStats",
    "AssetType",
    "ImportResult",
    "PriceSnapshot",
    "TrackedRecommendation",
    "VerificationResult",
    # Services
    "PriceTracker",
    "RecommendationStorage",
    "TickerMapper",
    # Exceptions
    "PriceError",
    "PriceNotAvailableError",
    "TickerNotFoundError",
]
