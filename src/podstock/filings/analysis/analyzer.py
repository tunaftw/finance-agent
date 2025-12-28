"""Multi-pass LLM analyzer for financial filings.

This module implements the core analysis pipeline:
1. Chunk the document
2. Analyze each chunk individually
3. Synthesize chunk analyses into a complete report
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from podstock.filings.analysis.prompt_templates import (
    CHUNK_ANALYSIS_PROMPT,
    METRICS_EXTRACTION_PROMPT,
    SYNTHESIS_PROMPT,
    get_analysis_prompt,
    get_metrics_prompt,
)
from podstock.filings.exceptions import AnalysisError
from podstock.filings.models import (
    ChunkAnalysis,
    DocumentChunk,
    Filing,
    FilingAnalysis,
    FinancialMetrics,
    ManagementTone,
)
from podstock.filings.pdf.chunker import ChunkConfig, FilingChunker

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class FilingAnalyzer:
    """Multi-pass analyzer for financial filings.

    Implements a three-pass analysis strategy:
    1. Chunk the document to fit context windows
    2. Analyze each chunk independently
    3. Synthesize all chunk analyses into a unified report

    Example:
        >>> from podstock.filings.analysis import FilingAnalyzer
        >>> analyzer = FilingAnalyzer(api_key="...")
        >>> analysis = analyzer.analyze(filing, pdf_path)
        >>> print(analysis.executive_summary)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        chunk_config: ChunkConfig | None = None,
    ):
        """Initialize the analyzer.

        Args:
            api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
            model: Model to use for analysis.
            chunk_config: Configuration for document chunking.
        """
        import os

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.model = model
        self.chunk_config = chunk_config or ChunkConfig()
        self.chunker = FilingChunker(self.chunk_config)
        self._client = None
        self._total_tokens = 0

    def _get_client(self):
        """Get or create Anthropic client."""
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError as e:
                raise ImportError(
                    "anthropic package required. Install with: pip install anthropic"
                ) from e
        return self._client

    def analyze(
        self,
        filing: Filing,
        pdf_path: str | Path,
        extract_metrics: bool = True,
    ) -> FilingAnalysis:
        """Perform complete analysis of a filing.

        Args:
            filing: The Filing object with metadata.
            pdf_path: Path to the PDF file.
            extract_metrics: Whether to also extract financial metrics.

        Returns:
            FilingAnalysis with complete analysis.

        Raises:
            AnalysisError: If analysis fails.
        """
        self._total_tokens = 0

        try:
            # Step 1: Chunk the document
            logger.info(f"Chunking document {filing.id}...")
            chunks = self.chunker.chunk_filing(filing, pdf_path)
            logger.info(f"Created {len(chunks)} chunks")

            # Step 2: Analyze each chunk
            logger.info("Analyzing chunks...")
            chunk_analyses = []
            for i, chunk in enumerate(chunks):
                logger.debug(f"Analyzing chunk {i + 1}/{len(chunks)}")
                chunk_analysis = self._analyze_chunk(chunk, filing)
                chunk_analyses.append(chunk_analysis)

            # Step 3: Synthesize
            logger.info("Synthesizing analysis...")
            final_analysis = self._synthesize(chunk_analyses, filing)
            final_analysis.chunks_processed = len(chunks)
            final_analysis.total_tokens_used = self._total_tokens

            return final_analysis

        except Exception as e:
            if isinstance(e, AnalysisError):
                raise
            raise AnalysisError(filing.id, str(e)) from e

    def extract_metrics(
        self,
        filing: Filing,
        pdf_path: str | Path,
    ) -> FinancialMetrics:
        """Extract financial metrics from a filing.

        This focuses specifically on extracting structured financial data
        from the financial statements section.

        Args:
            filing: The Filing object.
            pdf_path: Path to the PDF file.

        Returns:
            FinancialMetrics with extracted data.
        """
        # For metrics, we want to focus on the financial statements section
        # Use a more targeted chunking approach
        from podstock.filings.pdf.table_extractor import TableExtractor

        try:
            # First, try to extract tables which often contain the key metrics
            extractor = TableExtractor()
            categorized = extractor.find_financial_tables(pdf_path)

            # Build context from financial tables
            tables_markdown = ""
            for category in ["income_statement", "balance_sheet", "cash_flow"]:
                tables = categorized.get(category, [])
                if tables:
                    tables_markdown += f"\n## {category.replace('_', ' ').title()}\n"
                    tables_markdown += extractor.tables_to_markdown(tables)

            # If we found tables, use them as primary source
            if tables_markdown:
                content = tables_markdown
            else:
                # Fall back to first few pages (usually contain key figures)
                from podstock.filings.pdf.parser import PDFParser

                parser = PDFParser()
                pages = parser.to_markdown_pages(pdf_path)
                # Take first 30 pages or so where financials usually are
                content = "\n\n---\n\n".join(pages[:30])

            # Determine currency based on market
            from podstock.filings.models import Market

            currency = "SEK" if filing.language == "sv" else "USD"

            prompt = get_metrics_prompt(
                language=filing.language,
                filing_type=filing.filing_type.value,
                company_name=filing.company_id,
                currency=currency,
                fiscal_year=filing.fiscal_year,
            )

            # Call LLM
            response = self._call_llm(
                system_prompt="You are a financial analyst extracting metrics from financial reports. Return only valid JSON.",
                user_prompt=f"{prompt}\n\nDOCUMENT CONTENT:\n{content[:50000]}",  # Limit content
            )

            # Parse response
            metrics_data = self._parse_json_response(response)
            if not metrics_data:
                return FinancialMetrics(filing_id=filing.id, currency=currency)

            # Build FinancialMetrics object
            metrics = FinancialMetrics(
                filing_id=filing.id,
                currency=metrics_data.get("currency", currency),
                extraction_method="llm",
                revenue=metrics_data.get("revenue") or metrics_data.get("nettoomsattning"),
                gross_profit=metrics_data.get("gross_profit") or metrics_data.get("bruttovinst"),
                operating_income=metrics_data.get("operating_income") or metrics_data.get("rorelseresultat"),
                net_income=metrics_data.get("net_income") or metrics_data.get("arets_resultat"),
                eps=metrics_data.get("eps"),
                eps_diluted=metrics_data.get("eps_diluted"),
                total_assets=metrics_data.get("total_assets") or metrics_data.get("balansomslutning"),
                total_equity=metrics_data.get("total_equity") or metrics_data.get("eget_kapital"),
                total_debt=metrics_data.get("total_debt"),
                cash_and_equivalents=metrics_data.get("cash_and_equivalents") or metrics_data.get("likvida_medel"),
                operating_cash_flow=metrics_data.get("operating_cash_flow") or metrics_data.get("kassaflode_lopande"),
                capex=metrics_data.get("capex") or metrics_data.get("investeringar"),
                free_cash_flow=metrics_data.get("free_cash_flow"),
            )

            # Compute ratios if we have the data
            metrics.compute_ratios()

            return metrics

        except Exception as e:
            logger.warning(f"Failed to extract metrics: {e}")
            return FinancialMetrics(filing_id=filing.id)

    def _analyze_chunk(
        self,
        chunk: DocumentChunk,
        filing: Filing,
    ) -> ChunkAnalysis:
        """Analyze a single document chunk."""
        prompt = get_analysis_prompt(
            language=filing.language,
            document_metadata=self._format_metadata(filing, chunk),
            section_content=chunk.content,
            company_name=filing.company_id,
            section_type=chunk.section_type or "general",
        )

        response = self._call_llm(
            system_prompt="You are a financial analyst. Analyze the document section and return structured JSON.",
            user_prompt=prompt,
        )

        # Parse response
        data = self._parse_json_response(response) or {}

        # Map sentiment string to enum
        sentiment_str = data.get("sentiment", data.get("ton", "neutral")).lower()
        if "positiv" in sentiment_str:
            sentiment = ManagementTone.POSITIVE
        elif "negativ" in sentiment_str:
            sentiment = ManagementTone.NEGATIVE
        elif "cautious" in sentiment_str or "försiktig" in sentiment_str:
            sentiment = ManagementTone.CAUTIOUS
        else:
            sentiment = ManagementTone.NEUTRAL

        return ChunkAnalysis(
            chunk_id=chunk.chunk_id,
            filing_id=filing.id,
            key_points=data.get("key_points", data.get("huvudpunkter", [])),
            risks=data.get("risks", data.get("risker", [])),
            metrics_mentioned=data.get("metrics_mentioned", {}),
            sentiment=sentiment,
            notable_quotes=data.get("notable_quotes", []),
        )

    def _synthesize(
        self,
        chunk_analyses: list[ChunkAnalysis],
        filing: Filing,
    ) -> FilingAnalysis:
        """Synthesize chunk analyses into final analysis."""
        # Format chunk analyses for the prompt
        analyses_text = ""
        for i, ca in enumerate(chunk_analyses):
            analyses_text += f"\n--- Chunk {i + 1} Analysis ---\n"
            analyses_text += f"Key Points: {json.dumps(ca.key_points)}\n"
            analyses_text += f"Risks: {json.dumps(ca.risks)}\n"
            analyses_text += f"Metrics: {json.dumps(ca.metrics_mentioned)}\n"
            analyses_text += f"Sentiment: {ca.sentiment.value}\n"

        fiscal_period = f"FY{filing.fiscal_year}"
        if filing.fiscal_quarter:
            fiscal_period += f" Q{filing.fiscal_quarter}"

        prompt = SYNTHESIS_PROMPT.format(
            company_name=filing.company_id,
            filing_type=filing.filing_type.value,
            fiscal_period=fiscal_period,
            chunk_count=len(chunk_analyses),
            chunk_analyses=analyses_text,
        )

        response = self._call_llm(
            system_prompt="You are a senior financial analyst creating a comprehensive report. Return structured JSON.",
            user_prompt=prompt,
        )

        data = self._parse_json_response(response) or {}

        # Map tone
        tone_str = data.get("management_tone", "neutral").lower()
        if "positive" in tone_str or "positiv" in tone_str:
            tone = ManagementTone.POSITIVE
        elif "negative" in tone_str or "negativ" in tone_str:
            tone = ManagementTone.NEGATIVE
        elif "cautious" in tone_str or "försiktig" in tone_str:
            tone = ManagementTone.CAUTIOUS
        else:
            tone = ManagementTone.NEUTRAL

        return FilingAnalysis(
            filing_id=filing.id,
            executive_summary=data.get("executive_summary", ""),
            key_highlights=data.get("key_highlights", []),
            risks_mentioned=data.get("risks_mentioned", []),
            opportunities_mentioned=data.get("opportunities_mentioned", []),
            yoy_changes=data.get("yoy_changes", {}),
            guidance=data.get("guidance"),
            management_tone=tone,
            model_used=self.model,
        )

    def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
    ) -> str:
        """Make an LLM API call."""
        client = self._get_client()

        try:
            message = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            # Track token usage
            if hasattr(message, "usage"):
                self._total_tokens += message.usage.input_tokens + message.usage.output_tokens

            return message.content[0].text if message.content else ""

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _parse_json_response(self, response: str) -> dict | None:
        """Parse JSON from LLM response."""
        import re

        # Try to extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
        if json_match:
            response = json_match.group(1)

        # Clean up common issues
        response = response.strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON object in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(response[start:end])
                except json.JSONDecodeError:
                    pass
            logger.warning(f"Failed to parse JSON response: {response[:200]}...")
            return None

    def _format_metadata(self, filing: Filing, chunk: DocumentChunk) -> str:
        """Format filing metadata for prompt context."""
        return f"""Company: {filing.company_id}
Filing Type: {filing.filing_type.value}
Fiscal Year: {filing.fiscal_year}
Quarter: {filing.fiscal_quarter or 'N/A'}
Period End: {filing.period_end_date.strftime('%Y-%m-%d') if filing.period_end_date else 'N/A'}
Language: {filing.language}
Current Section: {chunk.section_type or 'general'}
Pages: {chunk.page_start}-{chunk.page_end}"""
