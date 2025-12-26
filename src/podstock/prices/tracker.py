"""Main price tracking and verification service.

This module provides the PriceTracker class which coordinates
price fetching, recommendation tracking, and verification.

The PriceTracker is the main entry point for:
- Tracking new recommendations (manual or from extractions)
- Verifying recommendations at specified intervals
- Calculating accuracy statistics
- Managing the recommendation storage

Example usage::

    from pathlib import Path
    from datetime import datetime
    from podstock.prices import PriceTracker

    # Initialize tracker
    tracker = PriceTracker(Path("data"))

    # Track a manual recommendation
    rec = tracker.track_recommendation(
        source_type="podcast",
        source_id="fillorkill-2024-06-15",
        source_name="Fill or Kill",
        asset_name="Evolution",
        action="buy",
        recommendation_date=datetime(2024, 6, 15),
    )

    # Import from extracted recommendations
    result = tracker.import_from_extractions(
        podcast="fill or kill",
        actions=["buy"],
    )

    # Verify at current prices
    tracker.verify_today()

    # Get accuracy stats
    stats = tracker.get_accuracy_stats(source_name="Fill or Kill")
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import TYPE_CHECKING, Callable

from dateutil.relativedelta import relativedelta

from podstock.prices.clients.base import PriceClient
from podstock.prices.clients.coingecko import CoinGeckoAdapter
from podstock.prices.clients.yahoo import YahooFinanceClient
from podstock.prices.exceptions import PriceNotAvailableError, TickerNotFoundError
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


class PriceTracker:
    """Main service for tracking and verifying recommendations.

    Coordinates between price clients, ticker mapping, and storage
    to track recommendations and verify them against actual prices.

    Attributes:
        data_dir: Base data directory.
        prices_dir: Directory for price data storage.
        storage: RecommendationStorage instance.
        yahoo: YahooFinanceClient instance.
        mapper: TickerMapper instance.

    Class Attributes:
        DEFAULT_INTERVALS: Default verification intervals [1, 3, 6, 12] months.

    Methods
    -------
    track_recommendation(...)
        Track a new recommendation with entry price.
    import_from_extractions(...)
        Import recommendations from extracted episode data.
    verify_recommendation(tracking_id, interval_months)
        Verify a single recommendation.
    verify_all_due()
        Verify all recommendations due for verification.
    verify_today(tracking_id)
        Verify recommendations at current prices.
    get_accuracy_stats(...)
        Calculate accuracy statistics with filters.
    get_all_recommendations()
        Get all tracked recommendations.
    get_recommendation(tracking_id)
        Get a specific recommendation.
    delete_recommendation(tracking_id)
        Delete a tracked recommendation.
    get_ticker_mapper()
        Get the TickerMapper instance.

    Example:
        >>> tracker = PriceTracker(Path("data"))
        >>> rec = tracker.track_recommendation(
        ...     source_type="podcast",
        ...     source_id="episode-123",
        ...     source_name="Fill or Kill",
        ...     asset_name="Evolution",
        ...     action="buy",
        ...     recommendation_date=datetime(2024, 1, 15),
        ... )
        >>> result = tracker.verify_recommendation(rec.tracking_id)
    """

    DEFAULT_INTERVALS = [1, 3, 6, 12]

    def __init__(
        self,
        data_dir: Path,
        yahoo_client: YahooFinanceClient | None = None,
        coingecko_client: CoinGeckoAdapter | None = None,
        ticker_mapper: TickerMapper | None = None,
    ):
        """Initialize the tracker.

        Args:
            data_dir: Base data directory.
            yahoo_client: Optional custom Yahoo client.
            coingecko_client: Optional custom CoinGecko adapter.
            ticker_mapper: Optional custom ticker mapper.
        """
        self.data_dir = data_dir
        self.prices_dir = data_dir / "prices"
        self.prices_dir.mkdir(parents=True, exist_ok=True)

        self.storage = RecommendationStorage(
            self.prices_dir / "verified_recommendations.jsonl"
        )
        self.yahoo = yahoo_client or YahooFinanceClient()
        self.coingecko = coingecko_client or CoinGeckoAdapter()
        self.mapper = ticker_mapper or TickerMapper(
            self.prices_dir / "ticker_mapping.json"
        )

    def _get_client(self, asset_type: AssetType) -> PriceClient:
        """Get appropriate client for asset type.

        Now uses Yahoo Finance for both stocks and crypto since
        CoinGecko free API has limitations on historical data.

        Args:
            asset_type: Stock or crypto.

        Returns:
            Yahoo Finance client (for both types).
        """
        # Use Yahoo for everything - crypto tickers end with -USD (e.g., BTC-USD)
        return self.yahoo

    def _detect_asset_type(
        self,
        asset_name: str,
        ticker: str | None = None,
    ) -> AssetType:
        """Detect if an asset is stock or crypto.

        Args:
            asset_name: Name of the asset.
            ticker: Optional ticker symbol.

        Returns:
            AssetType.STOCK or AssetType.CRYPTO.
        """
        # Check if ticker is known crypto
        if ticker and self.mapper.is_crypto(ticker):
            return AssetType.CRYPTO

        # Check common crypto names
        crypto_names = {
            "bitcoin", "ethereum", "solana", "cardano", "ripple",
            "dogecoin", "polkadot", "chainlink", "polygon", "avalanche",
        }
        if asset_name.lower() in crypto_names:
            return AssetType.CRYPTO

        return AssetType.STOCK

    def _generate_tracking_id(
        self,
        source_id: str,
        asset_name: str,
    ) -> str:
        """Generate a unique tracking ID.

        Args:
            source_id: Source identifier.
            asset_name: Asset name.

        Returns:
            Unique tracking ID.
        """
        content = f"{source_id}:{asset_name}:{datetime.now().isoformat()}"
        hash_part = hashlib.md5(content.encode()).hexdigest()[:8]
        safe_name = asset_name.lower().replace(" ", "-")[:20]
        return f"{safe_name}-{hash_part}"

    def track_recommendation(
        self,
        source_type: str,
        source_id: str,
        source_name: str,
        asset_name: str,
        action: str,
        recommendation_date: datetime,
        ticker: str | None = None,
        speaker: str | None = None,
        market: str = "sweden",
        price_target: float | None = None,
        price_target_currency: str = "SEK",
        intervals: list[int] | None = None,
    ) -> TrackedRecommendation:
        """Create a new tracked recommendation with entry price.

        Args:
            source_type: Type of source (podcast, twitter, youtube).
            source_id: Source identifier.
            source_name: Human-readable source name.
            asset_name: Name of the asset.
            action: Recommendation action (buy, sell, hold, watch, avoid).
            recommendation_date: When the recommendation was made.
            ticker: Optional ticker symbol (resolved if not provided).
            speaker: Who made the recommendation.
            market: Market classification.
            price_target: Optional price target.
            price_target_currency: Currency for price target.
            intervals: Verification intervals in months.

        Returns:
            The created TrackedRecommendation.

        Raises:
            TickerNotFoundError: If ticker cannot be resolved.
            PriceNotAvailableError: If entry price cannot be fetched.
        """
        # Detect asset type
        asset_type = self._detect_asset_type(asset_name, ticker)

        # Resolve ticker if not provided
        if not ticker:
            ticker = self.mapper.lookup(asset_name)
            if not ticker:
                raise TickerNotFoundError(asset_name)

        # Normalize ticker for stocks
        if asset_type == AssetType.STOCK:
            ticker = self.yahoo.normalize_ticker(ticker, market)

        # Fetch entry price
        client = self._get_client(asset_type)
        entry_price = client.get_historical_price(ticker, recommendation_date)

        # Generate tracking ID
        tracking_id = self._generate_tracking_id(source_id, asset_name)

        # Create recommendation
        rec = TrackedRecommendation(
            tracking_id=tracking_id,
            source_type=source_type,  # type: ignore
            source_id=source_id,
            source_name=source_name,
            asset_type=asset_type,
            asset_name=asset_name,
            symbol=ticker,
            market=market,
            action=action,  # type: ignore
            speaker=speaker,
            recommendation_date=recommendation_date,
            price_target=price_target,
            price_target_currency=price_target_currency,
            entry_price=entry_price,
            verification_intervals=intervals or self.DEFAULT_INTERVALS,
        )

        self.storage.save(rec)
        return rec

    def verify_recommendation(
        self,
        tracking_id: str,
        interval_months: int = 0,
    ) -> VerificationResult | None:
        """Verify a recommendation at current prices or specific interval.

        Args:
            tracking_id: The tracking ID to verify.
            interval_months: Interval to verify (0 = today).

        Returns:
            VerificationResult or None if verification failed.
        """
        rec = self.storage.get(tracking_id)
        if not rec or not rec.entry_price:
            return None

        client = self._get_client(rec.asset_type)
        current_snapshot = client.get_current_price(rec.symbol)

        if not current_snapshot:
            return None

        # Calculate returns
        entry = rec.entry_price.price
        current = current_snapshot.price
        abs_return = current - entry
        pct_return = (abs_return / entry) * 100

        # Determine if direction was correct
        direction_correct: bool | None = None
        if rec.action in ["buy", "watch"]:
            direction_correct = pct_return > 0
        elif rec.action in ["sell", "avoid"]:
            direction_correct = pct_return < 0

        # Check if target reached
        target_reached: bool | None = None
        if rec.price_target is not None:
            if rec.action == "buy":
                target_reached = current >= rec.price_target
            elif rec.action == "sell":
                target_reached = current <= rec.price_target

        result = VerificationResult(
            interval_months=interval_months,
            verified_at=datetime.now(),
            price_snapshot=current_snapshot,
            absolute_return=abs_return,
            percentage_return=pct_return,
            direction_correct=direction_correct,
            target_reached=target_reached,
        )

        # Update recommendation
        rec.verifications.append(result)
        rec.updated_at = datetime.now()
        self.storage.update(rec)

        return result

    def verify_all_due(
        self,
    ) -> list[tuple[TrackedRecommendation, VerificationResult]]:
        """Verify all recommendations that are due for verification.

        Returns:
            List of (recommendation, result) tuples.
        """
        results: list[tuple[TrackedRecommendation, VerificationResult]] = []
        now = datetime.now()

        for rec in self.storage.get_all():
            # Skip if no entry price
            if not rec.entry_price:
                continue

            # Check which intervals are due
            for interval in rec.verification_intervals:
                due_date = rec.recommendation_date + relativedelta(months=interval)

                # Already verified?
                if rec.is_verified_at(interval):
                    continue

                # Due?
                if now >= due_date:
                    result = self.verify_recommendation(rec.tracking_id, interval)
                    if result:
                        # Reload rec since it was updated
                        updated_rec = self.storage.get(rec.tracking_id)
                        if updated_rec:
                            results.append((updated_rec, result))

        return results

    def verify_today(
        self,
        tracking_id: str | None = None,
    ) -> list[tuple[TrackedRecommendation, VerificationResult]]:
        """Verify recommendations at current prices (interval=0).

        Args:
            tracking_id: Optional specific ID to verify. If None, verify all.

        Returns:
            List of (recommendation, result) tuples.
        """
        results: list[tuple[TrackedRecommendation, VerificationResult]] = []

        if tracking_id:
            recs = [self.storage.get(tracking_id)]
            recs = [r for r in recs if r is not None]
        else:
            recs = self.storage.get_all()

        for rec in recs:
            if not rec.entry_price:
                continue

            result = self.verify_recommendation(rec.tracking_id, 0)
            if result:
                updated_rec = self.storage.get(rec.tracking_id)
                if updated_rec:
                    results.append((updated_rec, result))

        return results

    def get_accuracy_stats(
        self,
        source_name: str | None = None,
        speaker: str | None = None,
        action: str | None = None,
        asset_type: AssetType | None = None,
    ) -> AccuracyStats:
        """Calculate accuracy statistics with optional filters.

        Args:
            source_name: Filter by source.
            speaker: Filter by speaker.
            action: Filter by action type.
            asset_type: Filter by asset type.

        Returns:
            AccuracyStats with calculated statistics.
        """
        recs = self.storage.get_all()

        # Apply filters
        if source_name:
            recs = [r for r in recs if r.source_name == source_name]
        if speaker:
            recs = [r for r in recs if r.speaker and r.speaker.lower() == speaker.lower()]
        if action:
            recs = [r for r in recs if r.action == action]
        if asset_type:
            recs = [r for r in recs if r.asset_type == asset_type]

        # Calculate stats
        total = len(recs)
        verified = [r for r in recs if r.verifications]
        correct = 0
        incorrect = 0
        returns: list[float] = []

        for rec in verified:
            latest = rec.get_latest_verification()
            if latest:
                returns.append(latest.percentage_return)
                if latest.direction_correct is True:
                    correct += 1
                elif latest.direction_correct is False:
                    incorrect += 1

        stats = AccuracyStats(
            total_recommendations=total,
            verified_recommendations=len(verified),
            correct_direction=correct,
            incorrect_direction=incorrect,
        )

        if verified:
            if correct + incorrect > 0:
                stats.direction_accuracy = correct / (correct + incorrect)
            if returns:
                stats.average_return = sum(returns) / len(returns)
                stats.median_return = median(returns)
                stats.best_return = max(returns)
                stats.worst_return = min(returns)

        return stats

    def get_all_recommendations(self) -> list[TrackedRecommendation]:
        """Get all tracked recommendations.

        Returns:
            List of all recommendations.
        """
        return self.storage.get_all()

    def get_recommendation(self, tracking_id: str) -> TrackedRecommendation | None:
        """Get a specific recommendation.

        Args:
            tracking_id: The tracking ID.

        Returns:
            The recommendation or None.
        """
        return self.storage.get(tracking_id)

    def delete_recommendation(self, tracking_id: str) -> bool:
        """Delete a tracked recommendation.

        Args:
            tracking_id: The tracking ID to delete.

        Returns:
            True if deleted.
        """
        return self.storage.delete(tracking_id)

    def get_ticker_mapper(self) -> TickerMapper:
        """Get the ticker mapper instance.

        Returns:
            The TickerMapper.
        """
        return self.mapper

    def import_from_extractions(
        self,
        episode_ids: list[str] | None = None,
        stock_name: str | None = None,
        podcast: str | None = None,
        since_date: datetime | None = None,
        actions: list[str] | None = None,
        force: bool = False,
        dry_run: bool = False,
        on_missing_ticker: Callable[[str, dict], str | None] | None = None,
    ) -> ImportResult:
        """Import recommendations from extracted episode data.

        Reads recommendations from data/extracted/recommendations.json
        and creates TrackedRecommendation entries with entry prices.

        Args:
            episode_ids: Filter to specific episode IDs.
            stock_name: Filter by stock name (case-insensitive).
            podcast: Filter by podcast name (case-insensitive).
            since_date: Only import recommendations after this date.
            actions: Filter by action types (buy, sell, etc.).
            force: Re-import even if already tracked.
            dry_run: Only preview, don't actually import.
            on_missing_ticker: Callback when ticker is missing.
                Receives (stock_name, rec_info) and returns ticker or None.

        Returns:
            ImportResult with counts of imported/skipped/failed.

        Example:
            >>> tracker = PriceTracker(Path("data"))
            >>> result = tracker.import_from_extractions(
            ...     podcast="fill or kill",
            ...     since_date=datetime(2024, 6, 1),
            ...     actions=["buy"],
            ... )
            >>> print(f"Imported {result.imported} recommendations")
        """
        result = ImportResult()

        # Load recommendations file
        recs_file = self.data_dir / "extracted" / "recommendations.json"
        if not recs_file.exists():
            result.errors.append(f"Recommendations file not found: {recs_file}")
            return result

        with open(recs_file) as f:
            all_recs = json.load(f)

        # Get existing tracking IDs to check for duplicates
        existing_ids = {r.source_id for r in self.storage.get_all()}

        for rec in all_recs:
            # Apply filters
            if episode_ids and rec.get("episode_id") not in episode_ids:
                result.skipped += 1
                continue

            if stock_name and stock_name.lower() not in rec.get("stock", "").lower():
                result.skipped += 1
                continue

            if podcast and podcast.lower() not in rec.get("podcast", "").lower():
                result.skipped += 1
                continue

            if since_date:
                rec_date_str = rec.get("date")
                if rec_date_str:
                    try:
                        rec_date = datetime.strptime(rec_date_str, "%Y-%m-%d")
                        if rec_date < since_date:
                            result.skipped += 1
                            continue
                    except ValueError:
                        pass

            if actions and rec.get("action") not in actions:
                result.skipped += 1
                continue

            # Check for existing
            rec_id = rec.get("id", rec.get("episode_id", ""))
            if rec_id in existing_ids and not force:
                result.skipped += 1
                continue

            # Dry run - don't actually import
            if dry_run:
                result.imported += 1
                result.imported_ids.append(rec_id)
                continue

            # Try to resolve ticker
            stock = rec.get("stock", "")
            ticker = rec.get("ticker")

            if not ticker:
                ticker = self.mapper.lookup(stock)

            if not ticker and on_missing_ticker:
                rec_info = {
                    "podcast": rec.get("podcast", "Unknown"),
                    "date": rec.get("date", "Unknown"),
                    "speaker": rec.get("speaker"),
                    "action": rec.get("action"),
                }
                ticker = on_missing_ticker(stock, rec_info)

            if not ticker:
                result.failed += 1
                result.errors.append(f"No ticker for '{stock}' in {rec.get('episode_id')}")
                continue

            # Parse recommendation date
            try:
                rec_date_str = rec.get("date", "")
                rec_date = datetime.strptime(rec_date_str, "%Y-%m-%d")
            except ValueError:
                result.failed += 1
                result.errors.append(f"Invalid date '{rec_date_str}' for {stock}")
                continue

            # Track the recommendation
            try:
                market = rec.get("market", "sweden")
                if market == "unknown":
                    market = "sweden"

                tracked = self.track_recommendation(
                    source_type="podcast",
                    source_id=rec_id,
                    source_name=rec.get("podcast", "Unknown"),
                    asset_name=stock,
                    action=rec.get("action", "watch"),
                    recommendation_date=rec_date,
                    ticker=ticker,
                    speaker=rec.get("speaker"),
                    market=market,
                )
                result.imported += 1
                result.imported_ids.append(tracked.tracking_id)
                existing_ids.add(rec_id)  # Prevent re-importing in same batch

            except TickerNotFoundError as e:
                result.failed += 1
                result.errors.append(f"Ticker not found for '{stock}': {e}")
            except Exception as e:
                result.failed += 1
                result.errors.append(f"Failed to import '{stock}': {e}")

        return result
