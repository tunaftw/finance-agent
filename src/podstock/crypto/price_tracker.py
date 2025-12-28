"""Price prediction tracking and verification.

This module tracks crypto price predictions made in content and
verifies them against actual price movements over time.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from podstock.crypto.coingecko import CoinGeckoClient
from podstock.crypto.models import (
    CryptoSentimentAnalysis,
    PricePrediction,
)


class PriceTracker:
    """Tracks and verifies crypto price predictions.

    Records predictions from analyzed content and later verifies
    them against actual price movements.

    Example:
        >>> tracker = PriceTracker(data_dir=Path("data"))
        >>> tracker.record_prediction(prediction)
        >>> verified = tracker.verify_due_predictions()
    """

    def __init__(
        self,
        data_dir: Path,
        coingecko: CoinGeckoClient | None = None,
    ) -> None:
        """Initialize price tracker.

        Args:
            data_dir: Base data directory.
            coingecko: CoinGecko client (creates one if not provided).
        """
        self.data_dir = data_dir
        self.crypto_dir = data_dir / "crypto"
        self.predictions_file = self.crypto_dir / "predictions.jsonl"

        self.coingecko = coingecko or CoinGeckoClient()

        # Create directories
        self.crypto_dir.mkdir(parents=True, exist_ok=True)

    def record_prediction(
        self,
        prediction: PricePrediction,
        fetch_current_price: bool = True,
    ) -> PricePrediction:
        """Record a new prediction for tracking.

        Args:
            prediction: Prediction to record.
            fetch_current_price: Whether to fetch current price.

        Returns:
            Updated prediction with current price.
        """
        # Fetch current price if needed
        if fetch_current_price and prediction.price_at_prediction == 0:
            current_price = self.coingecko.get_current_price(prediction.asset_symbol)
            if current_price:
                prediction.price_at_prediction = current_price

        # Append to JSONL file
        with open(self.predictions_file, "a", encoding="utf-8") as f:
            f.write(prediction.model_dump_json() + "\n")

        return prediction

    def record_predictions_from_analysis(
        self,
        analysis: CryptoSentimentAnalysis,
        source_name: str,
    ) -> list[PricePrediction]:
        """Extract and record predictions from an analysis.

        Args:
            analysis: Completed sentiment analysis.
            source_name: Name of the source.

        Returns:
            List of recorded predictions.
        """
        from podstock.crypto.analyzer import CryptoAnalyzer

        # We need to create predictions from the analysis
        predictions = []

        for mention in analysis.mentions:
            # Only create prediction if there's actionable info
            if not mention.price_target and not mention.time_horizon:
                continue

            # Skip neutral mentions
            if mention.sentiment.value == "neutral":
                continue

            # Determine direction
            direction: str
            if mention.sentiment.value in ["bullish", "very_bullish"]:
                direction = "up"
            elif mention.sentiment.value in ["bearish", "very_bearish"]:
                direction = "down"
            else:
                direction = "sideways"

            # Parse deadline
            deadline = self._parse_deadline(mention.time_horizon)

            prediction = PricePrediction(
                prediction_id=f"{analysis.source_id}_{mention.asset_symbol}_{datetime.now().timestamp():.0f}",
                source_id=analysis.source_id,
                source_type=analysis.source_type,
                source_name=source_name,
                asset_symbol=mention.asset_symbol,
                predicted_at=datetime.now(),
                prediction_text=mention.quote,
                target_price=mention.price_target,
                target_currency=mention.price_target_currency,
                direction=direction,
                time_horizon=mention.time_horizon,
                deadline=deadline,
                price_at_prediction=0.0,
                speaker=mention.speaker,
            )

            recorded = self.record_prediction(prediction)
            predictions.append(recorded)

        return predictions

    def _parse_deadline(self, time_horizon: str | None) -> datetime | None:
        """Parse time horizon string into deadline."""
        if not time_horizon:
            return None

        horizon_lower = time_horizon.lower()
        now = datetime.now()

        from datetime import timedelta

        # Handle specific patterns
        if "end of 2025" in horizon_lower or "eoy 2025" in horizon_lower:
            return datetime(2025, 12, 31)
        if "end of 2026" in horizon_lower or "eoy 2026" in horizon_lower:
            return datetime(2026, 12, 31)
        if "q1 2025" in horizon_lower:
            return datetime(2025, 3, 31)
        if "q2 2025" in horizon_lower:
            return datetime(2025, 6, 30)
        if "q3 2025" in horizon_lower:
            return datetime(2025, 9, 30)
        if "q4 2025" in horizon_lower:
            return datetime(2025, 12, 31)
        if "1 week" in horizon_lower or "one week" in horizon_lower:
            return now + timedelta(weeks=1)
        if "1 month" in horizon_lower or "one month" in horizon_lower:
            return now + timedelta(days=30)
        if "3 month" in horizon_lower or "three month" in horizon_lower:
            return now + timedelta(days=90)
        if "6 month" in horizon_lower or "six month" in horizon_lower:
            return now + timedelta(days=180)
        if "1 year" in horizon_lower or "one year" in horizon_lower:
            return now + timedelta(days=365)

        return None

    def load_predictions(self) -> list[PricePrediction]:
        """Load all predictions from disk.

        Returns:
            List of all predictions.
        """
        if not self.predictions_file.exists():
            return []

        predictions = []
        with open(self.predictions_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        predictions.append(PricePrediction.model_validate(data))
                    except (json.JSONDecodeError, ValueError):
                        continue

        return predictions

    def save_predictions(self, predictions: list[PricePrediction]) -> None:
        """Save all predictions to disk (overwrites file).

        Args:
            predictions: List of predictions to save.
        """
        tmp_file = self.predictions_file.with_suffix(".tmp")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                for pred in predictions:
                    f.write(pred.model_dump_json() + "\n")
            tmp_file.rename(self.predictions_file)
        except Exception:
            if tmp_file.exists():
                tmp_file.unlink()
            raise

    def get_pending_predictions(self) -> list[PricePrediction]:
        """Get predictions that haven't been verified yet.

        Returns:
            List of unverified predictions.
        """
        predictions = self.load_predictions()
        return [p for p in predictions if p.verified_at is None]

    def get_due_predictions(self) -> list[PricePrediction]:
        """Get predictions that are due for verification.

        Returns:
            List of predictions past their deadline.
        """
        now = datetime.now()
        pending = self.get_pending_predictions()
        return [
            p for p in pending
            if p.deadline and p.deadline <= now
        ]

    def verify_prediction(
        self,
        prediction: PricePrediction,
    ) -> PricePrediction:
        """Verify a single prediction against current price.

        Args:
            prediction: Prediction to verify.

        Returns:
            Updated prediction with verification data.
        """
        # Get current price
        current_price = self.coingecko.get_current_price(prediction.asset_symbol)

        if current_price is None:
            return prediction

        prediction.verified_at = datetime.now()
        prediction.actual_price = current_price

        # Calculate price change
        if prediction.price_at_prediction > 0:
            change = (current_price - prediction.price_at_prediction) / prediction.price_at_prediction
            prediction.price_change_percent = change * 100

            # Determine if prediction was correct
            if prediction.direction == "up":
                # For specific targets, check if reached
                if prediction.target_price:
                    prediction.prediction_correct = current_price >= prediction.target_price
                else:
                    # Just check direction
                    prediction.prediction_correct = change > 0.05  # 5% threshold
            elif prediction.direction == "down":
                if prediction.target_price:
                    prediction.prediction_correct = current_price <= prediction.target_price
                else:
                    prediction.prediction_correct = change < -0.05
            else:  # sideways
                prediction.prediction_correct = abs(change) < 0.10  # Within 10%

        return prediction

    def verify_due_predictions(self) -> list[PricePrediction]:
        """Verify all predictions that are due.

        Returns:
            List of newly verified predictions.
        """
        all_predictions = self.load_predictions()
        now = datetime.now()

        verified = []
        for i, pred in enumerate(all_predictions):
            if pred.verified_at is None and pred.deadline and pred.deadline <= now:
                all_predictions[i] = self.verify_prediction(pred)
                verified.append(all_predictions[i])

        # Save updated predictions
        if verified:
            self.save_predictions(all_predictions)

        return verified

    def get_accuracy_stats(
        self,
        source_id: str | None = None,
        speaker: str | None = None,
        asset: str | None = None,
    ) -> dict:
        """Calculate prediction accuracy statistics.

        Args:
            source_id: Filter by source ID.
            speaker: Filter by speaker name.
            asset: Filter by asset symbol.

        Returns:
            Dictionary with accuracy statistics.
        """
        predictions = self.load_predictions()

        # Filter verified predictions
        verified = [p for p in predictions if p.verified_at is not None]

        if source_id:
            verified = [p for p in verified if p.source_id == source_id]
        if speaker:
            verified = [p for p in verified if p.speaker == speaker]
        if asset:
            verified = [p for p in verified if p.asset_symbol.upper() == asset.upper()]

        if not verified:
            return {
                "total": 0,
                "verified": 0,
                "accuracy": None,
                "correct": 0,
                "incorrect": 0,
            }

        correct = sum(1 for p in verified if p.prediction_correct)
        incorrect = len(verified) - correct

        return {
            "total": len(predictions),
            "verified": len(verified),
            "correct": correct,
            "incorrect": incorrect,
            "accuracy": correct / len(verified) if verified else None,
            "by_asset": self._accuracy_by_asset(verified),
            "by_direction": self._accuracy_by_direction(verified),
        }

    def _accuracy_by_asset(
        self,
        predictions: list[PricePrediction],
    ) -> dict[str, dict]:
        """Calculate accuracy grouped by asset.

        Args:
            predictions: List of verified predictions.

        Returns:
            Dictionary mapping asset to stats.
        """
        by_asset: dict[str, dict] = {}

        for pred in predictions:
            asset = pred.asset_symbol.upper()
            if asset not in by_asset:
                by_asset[asset] = {"correct": 0, "total": 0}

            by_asset[asset]["total"] += 1
            if pred.prediction_correct:
                by_asset[asset]["correct"] += 1

        # Calculate accuracy
        for asset in by_asset:
            total = by_asset[asset]["total"]
            correct = by_asset[asset]["correct"]
            by_asset[asset]["accuracy"] = correct / total if total > 0 else None

        return by_asset

    def _accuracy_by_direction(
        self,
        predictions: list[PricePrediction],
    ) -> dict[str, dict]:
        """Calculate accuracy grouped by predicted direction.

        Args:
            predictions: List of verified predictions.

        Returns:
            Dictionary mapping direction to stats.
        """
        by_direction: dict[str, dict] = {}

        for pred in predictions:
            direction = pred.direction
            if direction not in by_direction:
                by_direction[direction] = {"correct": 0, "total": 0}

            by_direction[direction]["total"] += 1
            if pred.prediction_correct:
                by_direction[direction]["correct"] += 1

        # Calculate accuracy
        for direction in by_direction:
            total = by_direction[direction]["total"]
            correct = by_direction[direction]["correct"]
            by_direction[direction]["accuracy"] = correct / total if total > 0 else None

        return by_direction

    def get_prediction_summary(self) -> dict:
        """Get summary of all predictions.

        Returns:
            Summary dictionary.
        """
        predictions = self.load_predictions()
        now = datetime.now()

        pending = [p for p in predictions if p.verified_at is None]
        due = [p for p in pending if p.deadline and p.deadline <= now]
        verified = [p for p in predictions if p.verified_at is not None]

        return {
            "total_predictions": len(predictions),
            "pending": len(pending),
            "due_for_verification": len(due),
            "verified": len(verified),
            "accuracy": (
                sum(1 for p in verified if p.prediction_correct) / len(verified)
                if verified else None
            ),
            "assets_tracked": list(set(p.asset_symbol for p in predictions)),
            "sources_tracked": list(set(p.source_name for p in predictions if p.source_name)),
        }
