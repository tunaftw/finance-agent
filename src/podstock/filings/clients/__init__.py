"""Filings API clients.

This package provides clients for fetching financial filings from various sources.

Clients:
- EdgarClient: SEC EDGAR filings via EdgarTools
- PDFClient: Local PDF parsing and extraction
- SwedishIRClient: Swedish company IR page scraping
"""

from podstock.filings.clients.base import FilingsClient
from podstock.filings.clients.swedish_ir import SwedishIRClient

__all__ = ["FilingsClient", "SwedishIRClient"]
