# Analysis Module

Central modul för gemensamma analysutilities i PodStock.

## Syfte

Denna modul tillhandahåller gemensam infrastruktur för alla analystyper:

- **JSON-parsing** - Extrahera JSON från LLM-responser (markdown-wrapped eller raw)
- **LLM-klient** - Unified interface för Claude och Ollama

## Användning

### JSON-parsing

```python
from podstock.analysis import parse_llm_json, extract_json_from_response

# LLM-respons kan vara wrappade i markdown
response = '''
Here is the analysis:
```json
{"sentiment": "bullish", "confidence": "high"}
```
'''

# Extrahera och parsa
data = parse_llm_json(response)
print(data["sentiment"])  # "bullish"

# Eller extrahera bara JSON-strängen
json_str = extract_json_from_response(response)
```

### LLM-klient

```python
from podstock.analysis import create_llm_client

# Claude (kräver ANTHROPIC_API_KEY)
client = create_llm_client("claude-sonnet-4-20250514")

# Ollama (lokal, gratis)
client = create_llm_client("ollama:llama3.3")

# Generera
response = client.generate(
    system_prompt="Du är en finansanalytiker.",
    user_prompt="Analysera följande transkript: ...",
    max_tokens=4000,
)
```

## Filer

| Fil | Beskrivning |
|-----|-------------|
| `__init__.py` | Re-export av publika API:er |
| `json_parser.py` | JSON-extraktion från LLM-responser |
| `llm.py` | LLM-klient (re-export från extract/) |

## Se även

- `docs/ANALYSIS-GUIDE.md` - Fullständig arkitekturdokumentation
- `extract/llm_client.py` - Ursprunglig LLM-implementation
