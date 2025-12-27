"""LLM-klient re-export.

Denna modul re-exporterar LLM-klienten från extract/ för enklare import.
Den ursprungliga implementationen finns i extract/llm_client.py.

Exempel:
    >>> from podstock.analysis import create_llm_client
    >>>
    >>> # Claude
    >>> client = create_llm_client("claude-sonnet-4-20250514")
    >>>
    >>> # Ollama (lokal)
    >>> client = create_llm_client("ollama:llama3.3")
    >>>
    >>> # Generera
    >>> response = client.generate(
    ...     system_prompt="Du är en finansanalytiker.",
    ...     user_prompt="Analysera följande...",
    ...     max_tokens=4000,
    ... )
"""

# Re-export från extract/llm_client.py
from podstock.extract.llm_client import (
    LLMClient,
    ClaudeClient,
    OllamaClient,
    create_llm_client,
)

__all__ = [
    "LLMClient",
    "ClaudeClient",
    "OllamaClient",
    "create_llm_client",
]
