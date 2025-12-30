"""Pydantic data models for insider transaction tracking.

This module defines the core data structures used for insider
transaction data from SEC EDGAR and Finansinspektionen.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class InsiderRole(str, Enum):
    """Role of the insider making the transaction."""

    CEO = "ceo"
    CFO = "cfo"
    DIRECTOR = "director"
    OFFICER = "officer"
    MAJOR_SHAREHOLDER = "major_shareholder"
    OTHER = "other"


class TransactionType(str, Enum):
    """Type of insider transaction."""

    BUY = "buy"
    SELL = "sell"
    GIFT = "gift"
    EXERCISE = "exercise"
    OTHER = "other"


class InsiderTransaction(BaseModel):
    """A single insider transaction.

    Attributes:
        insider_name: Full name of the insider.
        role: Role of the insider (CEO, CFO, etc.).
        transaction_type: Type of transaction (buy, sell, etc.).
        shares: Number of shares transacted.
        price: Price per share if available.
        total_value: Total transaction value in local currency.
        currency: Currency code (USD, SEK, etc.).
        transaction_date: Date the transaction occurred.
        filing_date: Date the transaction was publicly disclosed.
        shares_after: Insider's holdings after transaction.
        source: Data source identifier (sec_edgar, finansinspektionen).
        source_url: Link to original filing.
    """

    insider_name: str
    role: InsiderRole
    transaction_type: TransactionType
    shares: int
    price: float | None = None
    total_value: float
    currency: str
    transaction_date: date
    filing_date: date
    shares_after: int | None = None
    source: str
    source_url: str | None = None


class InsiderReport(BaseModel):
    """Response for a single stock insider lookup.

    Attributes:
        ticker: Stock ticker symbol.
        company_name: Full company name.
        market: Market code (US, SE, NO, etc.).
        transactions: List of insider transactions.
        period_days: Number of days of data included.
        fetched_at: When this data was fetched.
    """

    ticker: str
    company_name: str
    market: str
    transactions: list[InsiderTransaction] = Field(default_factory=list)
    period_days: int
    fetched_at: datetime
