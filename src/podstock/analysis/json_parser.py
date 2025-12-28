"""Gemensam JSON-parsing för LLM-responser.

Denna modul hanterar extraktion av JSON från LLM-responser som kan vara
wrappade i markdown code blocks eller innehålla extra text.

Exempel:
    >>> from podstock.analysis import extract_json_from_response, parse_llm_json
    >>>
    >>> # Extrahera JSON-sträng
    >>> response = '```json\\n{"key": "value"}\\n```'
    >>> json_str = extract_json_from_response(response)
    >>> print(json_str)
    {"key": "value"}
    >>>
    >>> # Parsa direkt till dict
    >>> data = parse_llm_json(response)
    >>> print(data["key"])
    value
"""

import json
import re
from typing import Any


def extract_json_from_response(response: str) -> str:
    """Extrahera JSON från LLM-respons.

    Hanterar följande format:
    - Markdown code blocks: ```json ... ``` eller ``` ... ```
    - Raw JSON-objekt: { ... }
    - JSON med omgivande text

    Args:
        response: Rå respons från LLM.

    Returns:
        Extraherad JSON-sträng.

    Raises:
        ValueError: Om ingen giltig JSON hittas i responsen.

    Exempel:
        >>> extract_json_from_response('```json\\n{"a": 1}\\n```')
        '{"a": 1}'
        >>> extract_json_from_response('Here is the result: {"a": 1}')
        '{"a": 1}'
    """
    if not response or not response.strip():
        raise ValueError("Empty response")

    # Försök 1: JSON i markdown code block med språkspecifikation
    json_match = re.search(
        r"```(?:json)?\s*\n?(\{.*?\})\s*\n?```",
        response,
        re.DOTALL,
    )
    if json_match:
        return json_match.group(1).strip()

    # Försök 2: JSON i markdown code block (array)
    json_match = re.search(
        r"```(?:json)?\s*\n?(\[.*?\])\s*\n?```",
        response,
        re.DOTALL,
    )
    if json_match:
        return json_match.group(1).strip()

    # Försök 3: Raw JSON-objekt
    json_match = re.search(r"\{.*\}", response, re.DOTALL)
    if json_match:
        return json_match.group(0)

    # Försök 4: Raw JSON-array
    json_match = re.search(r"\[.*\]", response, re.DOTALL)
    if json_match:
        return json_match.group(0)

    raise ValueError(f"No JSON found in response: {response[:200]}...")


def parse_llm_json(response: str) -> dict[str, Any]:
    """Extrahera och parsa JSON från LLM-respons.

    Kombinerar extract_json_from_response() med json.loads() för
    en enklare API.

    Args:
        response: Rå respons från LLM.

    Returns:
        Parsad JSON som dict (eller list för JSON-arrays).

    Raises:
        ValueError: Om ingen giltig JSON hittas.
        json.JSONDecodeError: Om JSON är malformerad.

    Exempel:
        >>> data = parse_llm_json('```json\\n{"name": "test"}\\n```')
        >>> data["name"]
        'test'
    """
    json_str = extract_json_from_response(response)
    return json.loads(json_str)


def safe_parse_llm_json(response: str, default: Any = None) -> Any:
    """Parsa JSON från LLM-respons utan att kasta exception.

    Args:
        response: Rå respons från LLM.
        default: Värde att returnera om parsing misslyckas.

    Returns:
        Parsad JSON eller default-värde.

    Exempel:
        >>> safe_parse_llm_json('invalid', default={})
        {}
        >>> safe_parse_llm_json('{"a": 1}')
        {'a': 1}
    """
    try:
        return parse_llm_json(response)
    except (ValueError, json.JSONDecodeError):
        return default
