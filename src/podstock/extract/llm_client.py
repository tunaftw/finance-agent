"""LLM-klient abstraktion för Claude och Ollama."""

import json
from abc import ABC, abstractmethod

import requests
from anthropic import Anthropic


class LLMClient(ABC):
    """Abstrakt basklass för LLM-klienter."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 8000) -> str:
        """Generera text från LLM.

        Args:
            system_prompt: Systemprompt med instruktioner
            user_prompt: Användarprompt med transkript
            max_tokens: Max antal tokens i svaret

        Returns:
            Genererad text (förväntas vara JSON)
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Returnera modellnamnet för metadata."""
        pass


class ClaudeClient(LLMClient):
    """Anthropic Claude API-klient."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 8000) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text

    @property
    def model_name(self) -> str:
        return self.model


class OllamaClient(LLMClient):
    """Ollama lokal LLM-klient."""

    def __init__(self, model: str = "llama3.3", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 8000) -> str:
        """Generera text via Ollama API."""
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.1,  # Låg temperatur för konsekvent JSON
            },
        }

        try:
            response = requests.post(url, json=payload, timeout=300)  # 5 min timeout
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"Kunde inte ansluta till Ollama på {self.base_url}. "
                "Kör 'ollama serve' för att starta servern."
            )
        except requests.exceptions.Timeout:
            raise RuntimeError(
                "Ollama timeout efter 5 minuter. Transkriptet kan vara för långt."
            )

    @property
    def model_name(self) -> str:
        return f"ollama:{self.model}"


def create_llm_client(model_spec: str, api_key: str | None = None) -> LLMClient:
    """Factory-funktion för att skapa rätt LLM-klient.

    Args:
        model_spec: Modellspecifikation, t.ex.:
            - "claude-sonnet-4-20250514" (Claude)
            - "ollama:llama3.3" (Ollama)
            - "ollama:qwen2.5:72b" (Ollama med specifik tag)
        api_key: Anthropic API-nyckel (krävs för Claude)

    Returns:
        Konfigurerad LLMClient
    """
    if model_spec.startswith("ollama:"):
        # Format: ollama:model_name eller ollama:model_name:tag
        model_name = model_spec[7:]  # Ta bort "ollama:" prefix
        return OllamaClient(model=model_name)
    else:
        # Anta Claude-modell
        if not api_key:
            raise ValueError("API-nyckel krävs för Claude-modeller")
        return ClaudeClient(api_key=api_key, model=model_spec)
