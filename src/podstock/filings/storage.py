"""Storage management for filings data.

This module handles persisting companies, filings state, and analysis results.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from podstock.filings.models import (
    CompaniesFile,
    Company,
    Filing,
    FilingAnalysis,
    FilingsStateFile,
    FinancialMetrics,
)

if TYPE_CHECKING:
    from podstock.core.config import Config


class FilingsStorage:
    """Storage manager for filings data.

    Handles:
    - Companies tracking (companies.json)
    - Filings state (filings_state.json)
    - Analysis results (analysis/*.json)
    - Metrics extraction (extracted/*.json)

    Example:
        >>> storage = FilingsStorage(config)
        >>> storage.add_company(company)
        >>> companies = storage.list_companies()
    """

    def __init__(self, config: Config):
        """Initialize storage with configuration.

        Args:
            config: Application configuration with filings paths.
        """
        self.config = config
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create required directories."""
        self.config.filings_dir.mkdir(parents=True, exist_ok=True)
        self.config.filings_raw_dir.mkdir(parents=True, exist_ok=True)
        self.config.filings_analysis_dir.mkdir(parents=True, exist_ok=True)
        (self.config.filings_dir / "extracted").mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # Companies Management
    # =========================================================================

    def _load_companies_file(self) -> CompaniesFile:
        """Load companies file or create empty."""
        path = self.config.filings_companies_file
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return CompaniesFile.model_validate(data)
        return CompaniesFile()

    def _save_companies_file(self, file: CompaniesFile) -> None:
        """Save companies file atomically."""
        file.updated_at = datetime.now()
        path = self.config.filings_companies_file
        temp_path = path.with_suffix(".tmp")

        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(file.model_dump_json(indent=2))

        temp_path.replace(path)

    def list_companies(self) -> list[Company]:
        """Get all tracked companies."""
        return self._load_companies_file().companies

    def get_company(self, company_id: str) -> Company | None:
        """Get a company by ID."""
        companies = self.list_companies()
        for company in companies:
            if company.id == company_id:
                return company
        return None

    def add_company(self, company: Company) -> None:
        """Add a new company.

        Args:
            company: Company to add.

        Raises:
            ValueError: If company ID already exists.
        """
        file = self._load_companies_file()

        # Check for duplicates
        for existing in file.companies:
            if existing.id == company.id:
                raise ValueError(f"Company '{company.id}' already exists")

        file.companies.append(company)
        self._save_companies_file(file)

    def update_company(self, company: Company) -> None:
        """Update an existing company."""
        file = self._load_companies_file()

        for i, existing in enumerate(file.companies):
            if existing.id == company.id:
                file.companies[i] = company
                self._save_companies_file(file)
                return

        raise ValueError(f"Company '{company.id}' not found")

    def remove_company(self, company_id: str) -> None:
        """Remove a company."""
        file = self._load_companies_file()
        file.companies = [c for c in file.companies if c.id != company_id]
        self._save_companies_file(file)

    # =========================================================================
    # Filings State Management
    # =========================================================================

    def _load_state_file(self) -> FilingsStateFile:
        """Load state file or create empty."""
        path = self.config.filings_state_file
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return FilingsStateFile.model_validate(data)
        return FilingsStateFile()

    def _save_state_file(self, file: FilingsStateFile) -> None:
        """Save state file atomically."""
        file.last_updated = datetime.now()
        path = self.config.filings_state_file
        temp_path = path.with_suffix(".tmp")

        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(file.model_dump_json(indent=2))

        temp_path.replace(path)

    def list_filings(self, company_id: str | None = None) -> list[Filing]:
        """Get all filings, optionally filtered by company."""
        state = self._load_state_file()
        filings = list(state.filings.values())

        if company_id:
            filings = [f for f in filings if f.company_id == company_id]

        # Sort by date descending
        filings.sort(key=lambda f: (f.fiscal_year, f.fiscal_quarter or 0), reverse=True)
        return filings

    def get_filing(self, filing_id: str) -> Filing | None:
        """Get a filing by ID."""
        state = self._load_state_file()
        return state.filings.get(filing_id)

    def add_filing(self, filing: Filing) -> None:
        """Add a new filing."""
        state = self._load_state_file()
        state.filings[filing.id] = filing
        self._save_state_file(state)

    def update_filing(self, filing: Filing) -> None:
        """Update an existing filing."""
        state = self._load_state_file()
        state.filings[filing.id] = filing
        self._save_state_file(state)

    def mark_analyzed(self, filing_id: str) -> None:
        """Mark a filing as analyzed."""
        state = self._load_state_file()

        if filing_id in state.filings:
            state.filings[filing_id].analyzed = True

        if filing_id not in state.analyzed_filings:
            state.analyzed_filings.append(filing_id)

        self._save_state_file(state)

    def is_analyzed(self, filing_id: str) -> bool:
        """Check if a filing has been analyzed."""
        state = self._load_state_file()
        return filing_id in state.analyzed_filings

    # =========================================================================
    # Analysis Results
    # =========================================================================

    def save_analysis(self, analysis: FilingAnalysis) -> Path:
        """Save analysis results.

        Args:
            analysis: Analysis to save.

        Returns:
            Path to saved file.
        """
        path = self.config.filings_analysis_dir / f"{analysis.filing_id}.json"

        with open(path, "w", encoding="utf-8") as f:
            f.write(analysis.model_dump_json(indent=2))

        # Mark as analyzed in state
        self.mark_analyzed(analysis.filing_id)

        return path

    def load_analysis(self, filing_id: str) -> FilingAnalysis | None:
        """Load analysis results for a filing."""
        path = self.config.filings_analysis_dir / f"{filing_id}.json"

        if not path.exists():
            return None

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        return FilingAnalysis.model_validate(data)

    # =========================================================================
    # Metrics Results
    # =========================================================================

    def save_metrics(self, metrics: FinancialMetrics) -> Path:
        """Save extracted metrics.

        Args:
            metrics: Metrics to save.

        Returns:
            Path to saved file.
        """
        extracted_dir = self.config.filings_dir / "extracted"
        extracted_dir.mkdir(exist_ok=True)
        path = extracted_dir / f"{metrics.filing_id}.json"

        with open(path, "w", encoding="utf-8") as f:
            f.write(metrics.model_dump_json(indent=2))

        return path

    def load_metrics(self, filing_id: str) -> FinancialMetrics | None:
        """Load extracted metrics for a filing."""
        path = self.config.filings_dir / "extracted" / f"{filing_id}.json"

        if not path.exists():
            return None

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        return FinancialMetrics.model_validate(data)

    def list_metrics(self, company_id: str | None = None) -> list[FinancialMetrics]:
        """List all extracted metrics, optionally filtered by company."""
        extracted_dir = self.config.filings_dir / "extracted"
        if not extracted_dir.exists():
            return []

        metrics_list = []
        for path in extracted_dir.glob("*.json"):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            metrics = FinancialMetrics.model_validate(data)

            if company_id:
                # Check if filing belongs to company
                filing = self.get_filing(metrics.filing_id)
                if filing and filing.company_id == company_id:
                    metrics_list.append(metrics)
            else:
                metrics_list.append(metrics)

        return metrics_list
