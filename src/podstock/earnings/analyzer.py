"""LLM-powered analysis of earnings call transcripts.

This module provides the TranscriptAnalyzer class for:
- Structured analysis of earnings call transcripts
- Interactive Q&A on transcript content
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING

import anthropic

from podstock.earnings.models import (
    AnalystQuestion,
    EarningsTranscript,
    FollowUpItem,
    GuidanceChange,
    GuidanceItem,
    ManagementTone,
    NotableQuote,
    Signal,
    SignalType,
    TranscriptAnalysis,
)
from podstock.earnings.prompts import (
    INTERACTIVE_QA_SYSTEM,
    INTERACTIVE_QA_USER,
    TRANSCRIPT_ANALYSIS_SYSTEM,
    TRANSCRIPT_ANALYSIS_SYSTEM_CONDENSED,
    TRANSCRIPT_ANALYSIS_USER,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Maximum tokens for transcript in a single request
MAX_TRANSCRIPT_TOKENS = 150000  # Leave room for system prompt and response


class TranscriptAnalyzer:
    """Analyzer for earnings call transcripts using LLM.

    Provides structured analysis extraction and interactive Q&A capabilities.

    Example:
        >>> analyzer = TranscriptAnalyzer()
        >>> analysis = analyzer.analyze(transcript)
        >>> print(analysis.executive_summary)

        >>> answer = analyzer.ask(transcript, "What did they say about margins?")
        >>> print(answer)
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        """Initialize the analyzer.

        Args:
            model: LLM model to use for analysis.
        """
        self.model = model
        self.client = anthropic.Anthropic()

    def analyze(
        self,
        transcript: EarningsTranscript,
        previous_transcript: EarningsTranscript | None = None,
    ) -> TranscriptAnalysis:
        """Analyze a transcript and extract structured insights.

        Args:
            transcript: Transcript to analyze.
            previous_transcript: Optional previous quarter for comparison.

        Returns:
            Structured analysis results.
        """
        # Prepare transcript text
        transcript_text = transcript.full_text

        # Check if we need condensed prompt for very long transcripts
        word_count = len(transcript_text.split())
        use_condensed = word_count > 25000

        system_prompt = (
            TRANSCRIPT_ANALYSIS_SYSTEM_CONDENSED
            if use_condensed
            else TRANSCRIPT_ANALYSIS_SYSTEM
        )

        user_message = TRANSCRIPT_ANALYSIS_USER.format(
            company_name=transcript.company_name,
            quarter=transcript.fiscal_quarter,
            year=transcript.fiscal_year,
            call_date=transcript.call_date.strftime("%Y-%m-%d"),
            transcript_text=transcript_text,
        )

        logger.info(
            f"Analyzing transcript {transcript.id} "
            f"({word_count} words, {'condensed' if use_condensed else 'full'} prompt)"
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                messages=[
                    {"role": "user", "content": user_message},
                ],
                system=system_prompt,
            )

            # Extract text content
            response_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    response_text += block.text

            # Parse JSON response
            analysis = self._parse_analysis_response(response_text, transcript.id)

            logger.info(f"Analysis complete for {transcript.id}")
            return analysis

        except anthropic.APIError as e:
            logger.error(f"API error during analysis: {e}")
            raise

    def _parse_analysis_response(
        self,
        response_text: str,
        transcript_id: str,
    ) -> TranscriptAnalysis:
        """Parse LLM response into TranscriptAnalysis.

        Args:
            response_text: Raw LLM response text.
            transcript_id: ID of the analyzed transcript.

        Returns:
            Parsed TranscriptAnalysis.
        """
        # Try to extract JSON from response
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1

        if json_start == -1 or json_end == 0:
            logger.warning("Could not find JSON in response, creating minimal analysis")
            return TranscriptAnalysis(
                transcript_id=transcript_id,
                executive_summary=response_text[:500] if response_text else "",
                model_used=self.model,
            )

        json_text = response_text[json_start:json_end]

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return TranscriptAnalysis(
                transcript_id=transcript_id,
                executive_summary=response_text[:500] if response_text else "",
                model_used=self.model,
            )

        # Build analysis from parsed data
        analysis = TranscriptAnalysis(
            transcript_id=transcript_id,
            executive_summary=data.get("executive_summary", ""),
            key_takeaways_bullish=data.get("key_takeaways_bullish", []),
            key_takeaways_bearish=data.get("key_takeaways_bearish", []),
            model_used=self.model,
        )

        # Parse management tone
        tone_str = data.get("management_tone", "neutral").lower()
        try:
            analysis.management_tone = ManagementTone(tone_str)
        except ValueError:
            analysis.management_tone = ManagementTone.NEUTRAL

        # Parse guidance items
        for item in data.get("guidance_items", []):
            try:
                change = GuidanceChange(item.get("change", "reaffirmed"))
            except ValueError:
                change = GuidanceChange.REAFFIRMED

            analysis.guidance_items.append(
                GuidanceItem(
                    metric=item.get("metric", ""),
                    value=item.get("value", ""),
                    period=item.get("period"),
                    change=change,
                    notes=item.get("notes"),
                )
            )

        # Parse overall guidance direction
        direction_str = data.get("guidance_overall_direction")
        if direction_str:
            try:
                analysis.guidance_overall_direction = GuidanceChange(direction_str)
            except ValueError:
                pass

        # Parse warning flags
        for signal in data.get("warning_flags", []):
            analysis.warning_flags.append(
                Signal(
                    signal_type=SignalType.BEARISH,
                    category=signal.get("category", "risk"),
                    description=signal.get("description", ""),
                    quote=signal.get("quote"),
                    confidence=signal.get("confidence", "medium"),
                )
            )

        # Parse bullish signals
        for signal in data.get("bullish_signals", []):
            analysis.bullish_signals.append(
                Signal(
                    signal_type=SignalType.BULLISH,
                    category=signal.get("category", "growth"),
                    description=signal.get("description", ""),
                    quote=signal.get("quote"),
                    confidence=signal.get("confidence", "medium"),
                )
            )

        # Parse analyst questions
        for q in data.get("analyst_questions", []):
            analysis.analyst_questions.append(
                AnalystQuestion(
                    analyst_name=q.get("analyst_name"),
                    analyst_firm=q.get("analyst_firm"),
                    question=q.get("question", ""),
                    answer_summary=q.get("answer_summary"),
                    was_deflected=q.get("was_deflected", False),
                )
            )

        # Parse unanswered questions
        analysis.unanswered_questions = data.get("unanswered_questions", [])

        # Parse follow-up items
        for item in data.get("follow_up_items", []):
            analysis.follow_up_items.append(
                FollowUpItem(
                    topic=item.get("topic", ""),
                    context=item.get("context", ""),
                    expected_update=item.get("expected_update"),
                )
            )

        # Parse notable quotes
        for quote in data.get("notable_quotes", []):
            analysis.notable_quotes.append(
                NotableQuote(
                    speaker=quote.get("speaker", "Unknown"),
                    quote=quote.get("quote", ""),
                    context=quote.get("context"),
                )
            )

        return analysis

    def ask(
        self,
        transcript: EarningsTranscript,
        question: str,
    ) -> str:
        """Ask a question about a transcript.

        Args:
            transcript: Transcript to query.
            question: Question to ask.

        Returns:
            Answer string.
        """
        system_prompt = INTERACTIVE_QA_SYSTEM.format(
            company_name=transcript.company_name,
            quarter=transcript.fiscal_quarter,
            year=transcript.fiscal_year,
            call_date=transcript.call_date.strftime("%Y-%m-%d"),
            transcript_text=transcript.full_text,
        )

        user_message = INTERACTIVE_QA_USER.format(question=question)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[
                    {"role": "user", "content": user_message},
                ],
                system=system_prompt,
            )

            # Extract text content
            answer = ""
            for block in response.content:
                if hasattr(block, "text"):
                    answer += block.text

            return answer.strip()

        except anthropic.APIError as e:
            logger.error(f"API error during Q&A: {e}")
            return f"Error: {e}"

    def summarize(
        self,
        transcript: EarningsTranscript,
        max_sentences: int = 5,
    ) -> str:
        """Generate a brief summary of the transcript.

        Args:
            transcript: Transcript to summarize.
            max_sentences: Maximum sentences in summary.

        Returns:
            Summary string.
        """
        prompt = f"""Summarize this earnings call in {max_sentences} sentences or less.
Focus on the most important financial results and forward-looking statements.

Company: {transcript.company_name}
Period: Q{transcript.fiscal_quarter} {transcript.fiscal_year}

{transcript.full_text[:30000]}
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[
                    {"role": "user", "content": prompt},
                ],
            )

            summary = ""
            for block in response.content:
                if hasattr(block, "text"):
                    summary += block.text

            return summary.strip()

        except anthropic.APIError as e:
            logger.error(f"API error during summarization: {e}")
            return f"Error: {e}"
