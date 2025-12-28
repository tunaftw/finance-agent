"""Central analysmodul för PodStock.

Denna modul tillhandahåller gemensamma utilities för alla analystyper:
- JSON-parsing från LLM-responser
- LLM-klient (re-exporterad från extract/)

Se docs/ANALYSIS-GUIDE.md för fullständig dokumentation.

Exempel:
    >>> from podstock.analysis import parse_llm_json, create_llm_client
    >>>
    >>> client = create_llm_client("claude-sonnet-4-20250514")
    >>> response = client.generate(system_prompt="...", user_prompt="...")
    >>> data = parse_llm_json(response)
"""

from .json_parser import extract_json_from_response, parse_llm_json
from .llm import LLMClient, ClaudeClient, OllamaClient, create_llm_client

__all__ = [
    # JSON-parsing
    "extract_json_from_response",
    "parse_llm_json",
    # LLM-klienter
    "LLMClient",
    "ClaudeClient",
    "OllamaClient",
    "create_llm_client",
]
