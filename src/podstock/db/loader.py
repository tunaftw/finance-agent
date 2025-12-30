"""Data loaders for importing JSON analyses into database."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING


def tweet_id_to_date(tweet_id: str) -> str:
    """Extract date from Twitter Snowflake ID.

    Twitter IDs encode timestamp: (id >> 22) + 1288834974657 = timestamp_ms
    Returns ISO date string (YYYY-MM-DD).
    """
    try:
        timestamp_ms = (int(tweet_id) >> 22) + 1288834974657
        return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d")
    except (ValueError, OSError):
        return datetime.now().strftime("%Y-%m-%d")

from podstock.db.models import (
    Analysis,
    Content,
    KeyTakeaway,
    LoadLog,
    Mention,
    PendingSecurity,
    Recommendation,
    Source,
)
from podstock.db.ticker_lookup import resolve_security

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass
class LoadResult:
    """Result of a load operation."""

    status: str  # 'success', 'skipped', 'failed'
    content_id: str | None = None
    analysis_id: int | None = None
    recommendations_count: int = 0
    error: str | None = None


class BaseLoader:
    """Base class for data loaders."""

    def compute_content_hash(self, data: dict) -> str:
        """Compute SHA256 hash of content for idempotency."""
        # Use recommendations + summary as the "content" that matters
        relevant = {
            "recommendations": data.get("recommendations", []),
            "summary": data.get("summary", ""),
            "key_takeaways": data.get("key_takeaways", []),
        }
        content = json.dumps(relevant, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()

    def compute_file_hash(self, path: Path) -> str:
        """Compute hash of file for load tracking."""
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def should_load(self, session: "Session", file_path: Path, file_hash: str) -> bool:
        """Check if file should be loaded (not already loaded with same hash)."""
        # Always use absolute paths for consistent matching
        normalized_path = str(file_path.absolute())
        existing = (
            session.query(LoadLog)
            .filter_by(file_path=normalized_path, file_hash=file_hash, status="success")
            .first()
        )
        return existing is None

    def get_or_create_source(
        self,
        session: "Session",
        source_id: str,
        source_type: str,
        name: str,
    ) -> Source:
        """Get existing source or create new one."""
        source = session.query(Source).filter_by(id=source_id).first()
        if source:
            return source

        source = Source(id=source_id, type=source_type, name=name)
        session.add(source)
        session.flush()
        return source

    def create_or_update_pending(
        self,
        session: "Session",
        raw_name: str,
        raw_ticker: str | None,
        source: str,
        context: str | None = None,
    ) -> None:
        """Create or update pending security entry."""
        existing = (
            session.query(PendingSecurity)
            .filter_by(raw_name=raw_name, raw_ticker=raw_ticker)
            .first()
        )

        if existing:
            existing.occurrence_count += 1
        else:
            pending = PendingSecurity(
                raw_name=raw_name,
                raw_ticker=raw_ticker,
                source=source,
                context=context,
            )
            session.add(pending)


class PodcastLoader(BaseLoader):
    """Loader for podcast episode analyses."""

    def load(self, json_path: Path, session: "Session") -> LoadResult:
        """Load a podcast episode JSON file.

        Args:
            json_path: Path to JSON file
            session: Database session

        Returns:
            LoadResult with status and details
        """
        try:
            data = json.loads(json_path.read_text())
        except json.JSONDecodeError as e:
            return LoadResult(status="failed", error=f"Invalid JSON: {e}")

        # Validate data is a dict
        if not isinstance(data, dict):
            return LoadResult(status="failed", error="JSON root must be an object")

        # Validate required fields
        episode_id = data.get("episode_id")
        if not episode_id:
            return LoadResult(status="failed", error="Missing episode_id")

        # Check file hash
        file_hash = self.compute_file_hash(json_path)
        if not self.should_load(session, json_path, file_hash):
            return LoadResult(status="skipped", content_id=episode_id)

        # Compute content hash for versioning
        content_hash = self.compute_content_hash(data)

        # Check if this exact version already exists
        existing_analysis = (
            session.query(Analysis)
            .join(Content)
            .filter(Content.id == episode_id, Analysis.content_hash == content_hash)
            .first()
        )

        if existing_analysis:
            # Log as skipped but mark file as loaded
            self._log_load(session, json_path, file_hash, "podcast", "skipped", existing_analysis.id)
            return LoadResult(status="skipped", content_id=episode_id)

        # Get or create source
        podcast_name = data.get("podcast_name", "Unknown")
        source_id = self._normalize_source_id(podcast_name)
        source = self.get_or_create_source(session, source_id, "podcast", podcast_name)

        # Get or create content
        content = session.query(Content).filter_by(id=episode_id).first()
        if not content:
            content = Content(
                id=episode_id,
                source_id=source.id,
                type="episode",
                title=data.get("episode_title"),
                published_at=data.get("date", datetime.now().date().isoformat()),
                raw_text=None,  # Don't store full transcript
                word_count=data.get("transcript_word_count"),
                extra_data=json.dumps(
                    {
                        "episode_number": data.get("episode_number"),
                        "hosts": data.get("hosts", []),
                        "guests": data.get("guests", []),
                        "has_timestamps": data.get("has_timestamps"),
                    }
                ),
            )
            session.add(content)
            session.flush()

        # Determine next version number
        latest_version = (
            session.query(Analysis.version)
            .filter_by(content_id=episode_id)
            .order_by(Analysis.version.desc())
            .first()
        )
        new_version = (latest_version[0] + 1) if latest_version else 1

        # Create analysis
        analysis = Analysis(
            content_id=episode_id,
            version=new_version,
            content_hash=content_hash,
            model_used=data.get("model_used"),
            analyzed_at=data.get("processed_at", datetime.now().isoformat()),
            summary=data.get("summary"),
            sentiment=data.get("market_sentiment"),
            raw_json=json.dumps(data),
        )
        session.add(analysis)
        session.flush()

        # Create recommendations
        rec_count = 0
        for rec_data in data.get("recommendations", []):
            rec = self._create_recommendation(session, analysis.id, rec_data, source_id)
            if rec:
                rec_count += 1

        # Create key takeaways
        for i, takeaway in enumerate(data.get("key_takeaways", [])):
            kt = KeyTakeaway(
                analysis_id=analysis.id,
                takeaway=takeaway,
                sort_order=i,
            )
            session.add(kt)

        # Log successful load
        self._log_load(session, json_path, file_hash, "podcast", "success", analysis.id)

        return LoadResult(
            status="success",
            content_id=episode_id,
            analysis_id=analysis.id,
            recommendations_count=rec_count,
        )

    def _normalize_source_id(self, name: str) -> str:
        """Convert podcast name to source ID."""
        return (
            name.lower()
            .replace(" ", "")
            .replace("ä", "a")
            .replace("ö", "o")
            .replace("å", "a")
        )

    def _create_recommendation(
        self,
        session: "Session",
        analysis_id: int,
        data: dict,
        source_id: str,
    ) -> Recommendation | None:
        """Create a recommendation from JSON data."""
        stock_name = data.get("stock_name")
        if not stock_name:
            return None

        action = data.get("action")
        if not action:
            return None

        # Normalize action
        action = action.lower()
        if action not in ("buy", "sell", "hold", "watch", "avoid"):
            action = "watch"  # Default for unclear signals

        # Try to resolve security
        raw_ticker = data.get("ticker")
        security = resolve_security(session, stock_name, raw_ticker)

        # Create pending entry if not resolved
        if not security:
            reasoning = data.get("reasoning") or ""
            self.create_or_update_pending(
                session,
                raw_name=stock_name,
                raw_ticker=raw_ticker,
                source=source_id,
                context=reasoning[:200] if reasoning else None,
            )

        # Handle sector which can be string or list
        sector = data.get("sector")
        if isinstance(sector, list):
            sector = ", ".join(str(s) for s in sector)

        # Handle market which can be string or list
        market = data.get("market")
        if isinstance(market, list):
            market = ", ".join(str(m) for m in market)

        rec = Recommendation(
            analysis_id=analysis_id,
            security_id=security.id if security else None,
            raw_stock_name=stock_name,
            raw_ticker=raw_ticker,
            action=action,
            confidence=data.get("confidence"),
            speaker=data.get("speaker"),
            speaker_role=data.get("speaker_role"),
            reasoning=data.get("reasoning"),
            quote=data.get("quote"),
            timestamp=str(data.get("timestamp")) if data.get("timestamp") else None,
            price_target=str(data.get("price_target")) if data.get("price_target") else None,
            time_horizon=data.get("time_horizon"),
            sector=sector,
            market=market,
        )
        session.add(rec)
        return rec

    def _log_load(
        self,
        session: "Session",
        file_path: Path,
        file_hash: str,
        file_type: str,
        status: str,
        analysis_id: int | None,
        error: str | None = None,
    ) -> None:
        """Log a load operation."""
        # Always use absolute paths for consistent matching
        log = LoadLog(
            file_path=str(file_path.absolute()),
            file_hash=file_hash,
            file_type=file_type,
            status=status,
            analysis_id=analysis_id,
            error_message=error,
        )
        session.add(log)


class TwitterLoader(BaseLoader):
    """Loader for Twitter analyses.

    Loads tweet-analyses JSON files which contain individual tweet analyses
    with stock mentions and recommendations.
    """

    def load(self, json_path: Path, session: "Session") -> LoadResult:
        """Load a Twitter analysis JSON file.

        Expected format: *-tweet-analyses.json with structure:
        {
            "source_id": "username",
            "analyzed_at": "2025-12-25T...",
            "analyses": [
                {
                    "tweet_id": "123",
                    "stock_mentions": [
                        {"stock_name": "...", "ticker": "...", "action": "buy", ...}
                    ],
                    ...
                }
            ]
        }

        Args:
            json_path: Path to JSON file
            session: Database session

        Returns:
            LoadResult with status and details
        """
        try:
            data = json.loads(json_path.read_text())
        except json.JSONDecodeError as e:
            return LoadResult(status="failed", error=f"Invalid JSON: {e}")

        if not isinstance(data, dict):
            return LoadResult(status="failed", error="JSON root must be an object")

        # Check for tweet-analyses format
        source_id = data.get("source_id")
        analyses = data.get("analyses", [])

        if not source_id:
            return LoadResult(status="failed", error="Missing source_id")

        if not analyses:
            return LoadResult(status="failed", error="No analyses found")

        # Check file hash
        file_hash = self.compute_file_hash(json_path)
        if not self.should_load(session, json_path, file_hash):
            return LoadResult(status="skipped", content_id=source_id)

        # Compute content hash
        content_hash = self.compute_content_hash({"analyses": analyses})

        # Get or create source
        source = self.get_or_create_source(
            session, source_id, "twitter", f"@{source_id}"
        )

        total_recs = 0
        analyzed_at = data.get("analyzed_at", datetime.now().isoformat())

        for tweet_analysis in analyses:
            tweet_id = tweet_analysis.get("tweet_id")
            if not tweet_id:
                continue

            stock_mentions = tweet_analysis.get("stock_mentions", [])
            if not stock_mentions:
                continue

            # Create content entry for this tweet
            content_id = f"{source_id}-tweet-{tweet_id}"
            content = session.query(Content).filter_by(id=content_id).first()

            if not content:
                content = Content(
                    id=content_id,
                    source_id=source.id,
                    type="tweet",
                    external_id=tweet_id,
                    title=None,
                    published_at=tweet_id_to_date(tweet_id),
                    raw_text=None,
                    extra_data=json.dumps({
                        "market_sentiment": tweet_analysis.get("market_sentiment"),
                        "is_actionable": tweet_analysis.get("is_actionable"),
                    }),
                )
                session.add(content)
                session.flush()

            # Check if analysis already exists with same hash
            existing = (
                session.query(Analysis)
                .filter_by(content_id=content_id, content_hash=content_hash)
                .first()
            )
            if existing:
                continue

            # Get next version
            latest = (
                session.query(Analysis.version)
                .filter_by(content_id=content_id)
                .order_by(Analysis.version.desc())
                .first()
            )
            new_version = (latest[0] + 1) if latest else 1

            # Create analysis
            analysis = Analysis(
                content_id=content_id,
                version=new_version,
                content_hash=content_hash,
                model_used=tweet_analysis.get("model_used") or data.get("model_used"),
                analyzed_at=analyzed_at,
                summary=None,
                sentiment=tweet_analysis.get("market_sentiment"),
                raw_json=json.dumps(tweet_analysis),
            )
            session.add(analysis)
            session.flush()

            # Create recommendations from stock mentions
            for mention in stock_mentions:
                rec = self._create_recommendation(session, analysis.id, mention, source_id)
                if rec:
                    total_recs += 1

        # Log load
        self._log_load(session, json_path, file_hash, "twitter", "success", None)

        return LoadResult(
            status="success",
            content_id=source_id,
            recommendations_count=total_recs,
        )

    def _create_recommendation(
        self,
        session: "Session",
        analysis_id: int,
        data: dict,
        source_id: str,
    ) -> Recommendation | None:
        """Create a recommendation from stock mention data."""
        stock_name = data.get("stock_name")
        if not stock_name:
            return None

        action = data.get("action", "").lower()
        if action not in ("buy", "sell", "hold", "watch", "avoid"):
            action = "watch"

        # Try to resolve security
        raw_ticker = data.get("ticker")
        security = resolve_security(session, stock_name, raw_ticker)

        if not security:
            reasoning = data.get("reasoning") or ""
            self.create_or_update_pending(
                session,
                raw_name=stock_name,
                raw_ticker=raw_ticker,
                source=source_id,
                context=reasoning[:200] if reasoning else None,
            )

        rec = Recommendation(
            analysis_id=analysis_id,
            security_id=security.id if security else None,
            raw_stock_name=stock_name,
            raw_ticker=raw_ticker,
            action=action,
            confidence=data.get("confidence"),
            speaker=None,  # Twitter doesn't have speakers
            speaker_role=None,
            reasoning=data.get("reasoning"),
            quote=data.get("quote"),
            timestamp=None,
            price_target=str(data.get("price_target")) if data.get("price_target") else None,
            time_horizon=data.get("time_horizon"),
            sector=data.get("sector"),
            market=data.get("market"),
        )
        session.add(rec)
        return rec

    def _log_load(
        self,
        session: "Session",
        file_path: Path,
        file_hash: str,
        file_type: str,
        status: str,
        analysis_id: int | None,
        error: str | None = None,
    ) -> None:
        """Log a load operation."""
        # Always use absolute paths for consistent matching
        log = LoadLog(
            file_path=str(file_path.absolute()),
            file_hash=file_hash,
            file_type=file_type,
            status=status,
            analysis_id=analysis_id,
            error_message=error,
        )
        session.add(log)


class YouTubeLoader(BaseLoader):
    """Loader for YouTube crypto analysis files.

    Loads crypto analysis files from data/crypto/{channel}-analysis/*.json
    which contain crypto asset mentions with sentiment analysis.
    """

    def compute_content_hash(self, data: dict) -> str:
        """Compute hash using mentions and summary."""
        relevant = {
            "mentions": data.get("mentions", []),
            "summary": data.get("summary", ""),
            "key_insights": data.get("key_insights", []),
        }
        content = json.dumps(relevant, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()

    def load(self, json_path: Path, session: "Session") -> LoadResult:
        """Load a YouTube crypto analysis JSON file.

        Expected format: {video_id}.json with structure:
        {
            "source_id": "video_id",
            "source_type": "youtube",
            "channel": "TechnicalRoundup",
            "date": "2021-07-23",
            "hosts": ["Cred", "Duck"],
            "mentions": [
                {
                    "asset_symbol": "BTC",
                    "asset_name": "Bitcoin",
                    "sentiment": "bullish",
                    "speaker": "...",
                    "context": "...",
                    "quote": "...",
                    "confidence": "high"
                }
            ],
            "overall_market_sentiment": "neutral",
            "summary": "..."
        }

        Args:
            json_path: Path to JSON file
            session: Database session

        Returns:
            LoadResult with status and details
        """
        # Skip -analysis.json variant files (duplicates)
        if json_path.stem.endswith("-analysis"):
            return LoadResult(status="skipped", error="Skipping -analysis variant")

        try:
            data = json.loads(json_path.read_text())
        except json.JSONDecodeError as e:
            return LoadResult(status="failed", error=f"Invalid JSON: {e}")

        if not isinstance(data, dict):
            return LoadResult(status="failed", error="JSON root must be an object")

        # Validate required fields
        video_id = data.get("source_id")
        if not video_id:
            return LoadResult(status="failed", error="Missing source_id")

        channel = data.get("channel")
        if not channel:
            return LoadResult(status="failed", error="Missing channel")

        mentions = data.get("mentions", [])
        if not mentions:
            return LoadResult(
                status="skipped", content_id=video_id, error="No mentions in file"
            )

        # Check file hash
        file_hash = self.compute_file_hash(json_path)
        if not self.should_load(session, json_path, file_hash):
            return LoadResult(status="skipped", content_id=video_id)

        content_hash = self.compute_content_hash(data)

        # Normalize channel name for source_id
        source_id = self._normalize_source_id(channel)

        # Get or create source
        source = self.get_or_create_source(session, source_id, "youtube", channel)

        # Create unique content ID
        content_id = f"{source_id}-{video_id}"

        # Get or create content
        content = session.query(Content).filter_by(id=content_id).first()
        if not content:
            content = Content(
                id=content_id,
                source_id=source.id,
                type="video",
                external_id=video_id,
                title=None,  # Could extract from transcript if available
                published_at=data.get("date", datetime.now().date().isoformat()),
                raw_text=None,
                word_count=data.get("transcript_word_count"),
                extra_data=json.dumps(
                    {
                        "hosts": data.get("hosts", []),
                        "overall_market_sentiment": data.get("overall_market_sentiment"),
                        "market_analysis": data.get("market_analysis"),
                    }
                ),
            )
            session.add(content)
            session.flush()

        # Check for existing analysis with same hash
        existing = (
            session.query(Analysis)
            .filter_by(content_id=content_id, content_hash=content_hash)
            .first()
        )
        if existing:
            self._log_load(
                session, json_path, file_hash, "youtube", "skipped", existing.id
            )
            return LoadResult(status="skipped", content_id=content_id)

        # Get next version
        latest = (
            session.query(Analysis.version)
            .filter_by(content_id=content_id)
            .order_by(Analysis.version.desc())
            .first()
        )
        new_version = (latest[0] + 1) if latest else 1

        # Create analysis
        analysis = Analysis(
            content_id=content_id,
            version=new_version,
            content_hash=content_hash,
            model_used=data.get("model_used"),
            analyzed_at=data.get("analyzed_at", datetime.now().isoformat()),
            summary=data.get("summary"),
            sentiment=data.get("overall_market_sentiment"),
            raw_json=json.dumps(data),
        )
        session.add(analysis)
        session.flush()

        # Create mentions
        mention_count = 0
        for mention_data in mentions:
            mention = self._create_mention(session, analysis.id, mention_data, source_id)
            if mention:
                mention_count += 1

        # Create key takeaways from key_insights
        for i, insight in enumerate(data.get("key_insights", [])):
            kt = KeyTakeaway(
                analysis_id=analysis.id,
                takeaway=insight,
                sort_order=i,
            )
            session.add(kt)

        self._log_load(session, json_path, file_hash, "youtube", "success", analysis.id)

        return LoadResult(
            status="success",
            content_id=content_id,
            analysis_id=analysis.id,
            recommendations_count=mention_count,  # Reusing field for mentions
        )

    def _normalize_source_id(self, name: str) -> str:
        """Convert channel name to source ID."""
        return name.lower().replace(" ", "").replace("-", "")

    def _create_mention(
        self,
        session: "Session",
        analysis_id: int,
        data: dict,
        source_id: str,
    ) -> Mention | None:
        """Create a mention from crypto mention data."""
        asset_name = data.get("asset_name")
        asset_symbol = data.get("asset_symbol")

        if not asset_name and not asset_symbol:
            return None

        # Build context string from multiple fields
        context_parts = []
        if data.get("context"):
            context_parts.append(data["context"])
        if data.get("quote"):
            context_parts.append(f'Quote: "{data["quote"]}"')
        if data.get("speaker"):
            context_parts.append(f"Speaker: {data['speaker']}")
        if data.get("timeframe"):
            context_parts.append(f"Timeframe: {data['timeframe']}")
        price_levels = data.get("price_levels")
        if price_levels:
            context_parts.append(f"Price levels: {', '.join(str(p) for p in price_levels)}")

        # Try to resolve security (likely won't find crypto in stock mapping)
        security = resolve_security(session, asset_name or asset_symbol, asset_symbol)

        if not security:
            self.create_or_update_pending(
                session,
                raw_name=asset_name or asset_symbol,
                raw_ticker=asset_symbol,
                source=source_id,
                context=(data.get("context", "") or "")[:200],
            )

        mention = Mention(
            analysis_id=analysis_id,
            security_id=security.id if security else None,
            raw_stock_name=asset_name or asset_symbol,
            raw_ticker=asset_symbol,
            sentiment=data.get("sentiment"),  # bullish, bearish, neutral
            context="\n".join(context_parts) if context_parts else None,
        )
        session.add(mention)
        return mention

    def _log_load(
        self,
        session: "Session",
        file_path: Path,
        file_hash: str,
        file_type: str,
        status: str,
        analysis_id: int | None,
        error: str | None = None,
    ) -> None:
        """Log a load operation."""
        # Always use absolute paths for consistent matching
        log = LoadLog(
            file_path=str(file_path.absolute()),
            file_hash=file_hash,
            file_type=file_type,
            status=status,
            analysis_id=analysis_id,
            error_message=error,
        )
        session.add(log)
