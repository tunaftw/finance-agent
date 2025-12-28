"""Tweet collection via browser automation.

This module provides collection plans and utilities for gathering tweets
using browser-based scraping with date-range searches.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from dateutil.relativedelta import relativedelta
from pathlib import Path
from typing import Iterator


@dataclass
class CollectionChunk:
    """A date range chunk for collection."""

    start_date: str
    end_date: str
    source_id: str
    status: str = "pending"  # pending, in_progress, completed, error
    tweets_collected: int = 0

    @property
    def search_url(self) -> str:
        """Generate Twitter advanced search URL."""
        query = f"from:{self.source_id} since:{self.start_date} until:{self.end_date}"
        encoded = query.replace(":", "%3A").replace(" ", "%20")
        return f"https://x.com/search?q={encoded}&src=typed_query&f=live"

    def to_dict(self) -> dict:
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "source_id": self.source_id,
            "status": self.status,
            "tweets_collected": self.tweets_collected,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CollectionChunk":
        return cls(**data)


@dataclass
class CollectionPlan:
    """A collection plan for a Twitter source."""

    source_id: str
    handle: str
    chunks: list[CollectionChunk] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create_quarterly(
        cls,
        source_id: str,
        handle: str,
        start_date: datetime,
        end_date: datetime | None = None,
    ) -> "CollectionPlan":
        """Create a quarterly collection plan.

        Args:
            source_id: Internal source identifier.
            handle: Twitter handle.
            start_date: When the account was created/earliest date.
            end_date: Latest date (defaults to today).

        Returns:
            CollectionPlan with quarterly chunks.
        """
        if end_date is None:
            end_date = datetime.now()

        chunks = []
        current = end_date

        while current > start_date:
            chunk_start = current - relativedelta(months=3)
            if chunk_start < start_date:
                chunk_start = start_date

            chunks.append(CollectionChunk(
                start_date=chunk_start.strftime("%Y-%m-%d"),
                end_date=current.strftime("%Y-%m-%d"),
                source_id=source_id,
            ))
            current = chunk_start

        return cls(source_id=source_id, handle=handle, chunks=chunks)

    @classmethod
    def create_monthly(
        cls,
        source_id: str,
        handle: str,
        start_date: datetime,
        end_date: datetime | None = None,
    ) -> "CollectionPlan":
        """Create a monthly collection plan for high-volume accounts."""
        if end_date is None:
            end_date = datetime.now()

        chunks = []
        current = end_date

        while current > start_date:
            chunk_start = current - relativedelta(months=1)
            if chunk_start < start_date:
                chunk_start = start_date

            chunks.append(CollectionChunk(
                start_date=chunk_start.strftime("%Y-%m-%d"),
                end_date=current.strftime("%Y-%m-%d"),
                source_id=source_id,
            ))
            current = chunk_start

        return cls(source_id=source_id, handle=handle, chunks=chunks)

    def get_pending_chunks(self) -> list[CollectionChunk]:
        """Get chunks that haven't been collected yet."""
        return [c for c in self.chunks if c.status == "pending"]

    def get_next_chunk(self) -> CollectionChunk | None:
        """Get the next chunk to collect."""
        pending = self.get_pending_chunks()
        return pending[0] if pending else None

    def mark_chunk_complete(self, chunk: CollectionChunk, tweets_collected: int) -> None:
        """Mark a chunk as completed."""
        chunk.status = "completed"
        chunk.tweets_collected = tweets_collected

    def mark_chunk_error(self, chunk: CollectionChunk) -> None:
        """Mark a chunk as having an error."""
        chunk.status = "error"

    @property
    def progress(self) -> dict:
        """Get collection progress."""
        total = len(self.chunks)
        completed = len([c for c in self.chunks if c.status == "completed"])
        tweets = sum(c.tweets_collected for c in self.chunks)

        return {
            "total_chunks": total,
            "completed_chunks": completed,
            "pending_chunks": total - completed,
            "progress_pct": round(completed / total * 100, 1) if total > 0 else 0,
            "tweets_collected": tweets,
        }

    def save(self, path: Path) -> None:
        """Save plan to JSON file."""
        data = {
            "source_id": self.source_id,
            "handle": self.handle,
            "created_at": self.created_at.isoformat(),
            "chunks": [c.to_dict() for c in self.chunks],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "CollectionPlan":
        """Load plan from JSON file."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        plan = cls(
            source_id=data["source_id"],
            handle=data["handle"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )
        plan.chunks = [CollectionChunk.from_dict(c) for c in data["chunks"]]
        return plan

    def print_status(self) -> None:
        """Print collection status."""
        prog = self.progress
        print(f"\nCollection Plan: @{self.handle}")
        print("=" * 50)
        print(f"Progress: {prog['completed_chunks']}/{prog['total_chunks']} chunks ({prog['progress_pct']}%)")
        print(f"Tweets collected: {prog['tweets_collected']}")

        next_chunk = self.get_next_chunk()
        if next_chunk:
            print(f"\nNext chunk: {next_chunk.start_date} to {next_chunk.end_date}")
            print(f"URL: {next_chunk.search_url}")
        else:
            print("\nAll chunks completed!")


def create_collection_plan(
    source_id: str,
    handle: str,
    joined_date: datetime,
    interval: str = "quarterly",
) -> CollectionPlan:
    """Create a collection plan for a source.

    Args:
        source_id: Internal identifier.
        handle: Twitter handle.
        joined_date: When the account joined Twitter.
        interval: "quarterly" or "monthly".

    Returns:
        CollectionPlan ready for execution.
    """
    if interval == "monthly":
        return CollectionPlan.create_monthly(source_id, handle, joined_date)
    else:
        return CollectionPlan.create_quarterly(source_id, handle, joined_date)
