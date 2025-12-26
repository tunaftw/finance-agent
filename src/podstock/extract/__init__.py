"""PodStock Transcript Extraction Pipeline.

Extraherar aktie-rekommendationer från svenska finanspoddar.
"""

from .batch_runner import BatchRunner
from .build_index import build_index, save_index
from .llm_client import ClaudeClient, LLMClient, OllamaClient, create_llm_client
from .models import EpisodeAnalysis, ProcessingStatus, StockRecommendation
from .process_transcript import TranscriptProcessor
from .search import RecommendationSearch

__all__ = [
    "StockRecommendation",
    "EpisodeAnalysis",
    "ProcessingStatus",
    "TranscriptProcessor",
    "BatchRunner",
    "RecommendationSearch",
    "build_index",
    "save_index",
    "LLMClient",
    "ClaudeClient",
    "OllamaClient",
    "create_llm_client",
]
