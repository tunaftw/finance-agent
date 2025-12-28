"""Custom exceptions for the filings module.

Exceptions
----------
FilingsError
    Base exception for all filings-related errors.

FilingNotFoundError(FilingsError)
    Raised when a filing cannot be found.

CompanyNotFoundError(FilingsError)
    Raised when a company cannot be found in EDGAR or local storage.

PDFParseError(FilingsError)
    Raised when PDF parsing fails.

XBRLParseError(FilingsError)
    Raised when XBRL data cannot be parsed.

ChunkingError(FilingsError)
    Raised when document chunking fails.

Example::

    from podstock.filings import FilingsError, PDFParseError

    try:
        chunks = chunker.chunk_filing(pdf_path)
    except PDFParseError as e:
        print(f"Failed to parse PDF: {e.path}")
"""


class FilingsError(Exception):
    """Base exception for filings-related errors."""

    pass


class FilingNotFoundError(FilingsError):
    """Raised when a filing cannot be found."""

    def __init__(self, filing_id: str, message: str | None = None):
        self.filing_id = filing_id
        super().__init__(message or f"Filing not found: '{filing_id}'")


class CompanyNotFoundError(FilingsError):
    """Raised when a company cannot be found."""

    def __init__(self, identifier: str, market: str = "us", message: str | None = None):
        self.identifier = identifier
        self.market = market
        super().__init__(
            message
            or f"Company not found: '{identifier}' in market '{market}'. "
            f"Check the ticker/CIK and try again."
        )


class PDFParseError(FilingsError):
    """Raised when PDF parsing fails."""

    def __init__(self, path: str, reason: str | None = None):
        self.path = path
        self.reason = reason
        msg = f"Failed to parse PDF: '{path}'"
        if reason:
            msg += f" - {reason}"
        super().__init__(msg)


class XBRLParseError(FilingsError):
    """Raised when XBRL data cannot be parsed."""

    def __init__(self, filing_id: str, reason: str | None = None):
        self.filing_id = filing_id
        self.reason = reason
        msg = f"Failed to parse XBRL for filing: '{filing_id}'"
        if reason:
            msg += f" - {reason}"
        super().__init__(msg)


class ChunkingError(FilingsError):
    """Raised when document chunking fails."""

    def __init__(self, filing_id: str, reason: str | None = None):
        self.filing_id = filing_id
        self.reason = reason
        msg = f"Failed to chunk document: '{filing_id}'"
        if reason:
            msg += f" - {reason}"
        super().__init__(msg)


class AnalysisError(FilingsError):
    """Raised when LLM analysis fails."""

    def __init__(self, filing_id: str, reason: str | None = None):
        self.filing_id = filing_id
        self.reason = reason
        msg = f"Failed to analyze filing: '{filing_id}'"
        if reason:
            msg += f" - {reason}"
        super().__init__(msg)
