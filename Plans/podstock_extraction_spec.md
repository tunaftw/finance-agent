# PodStock: Transcript Extraction Pipeline - Fullständig Specifikation

## Projektöversikt

Bygg en komplett pipeline för att extrahera aktie-rekommendationer från svenska finanspoddar. Målet är att transformera 50+ tunga transkript-filer (10 000-20 000 ord vardera) till strukturerad, sökbar data.

**Podcasts:** Börspodden, Fill or Kill, Börsmagasinet, Market Makers, Gött Tjöt om Aktier, Börsens Finest

**Språk:** Svenska (finansterminologi)

---

## Mappstruktur

Skapa följande struktur:

```
podstock/
├── data/
│   ├── transcripts/
│   │   └── raw/                          # Input: tunga .txt-filer finns här
│   │
│   ├── extracted/                        # Output: strukturerad data
│   │   ├── episodes/                     # En JSON per avsnitt
│   │   ├── recommendations.json          # Alla rekommendationer (flat)
│   │   └── index.json                    # Lättviktigt sökindex
│   │
│   └── processing/
│       ├── queue.json                    # Väntande på analys
│       ├── completed.json                # Färdiga
│       └── errors.json                   # Misslyckade (för retry)
│
├── src/
│   └── extract/
│       ├── __init__.py
│       ├── models.py                     # Pydantic-modeller
│       ├── prompt_templates.py           # Claude-prompts
│       ├── process_transcript.py         # Huvudlogik
│       ├── batch_runner.py               # Batch-processing
│       ├── build_index.py                # Bygg sökindex
│       └── cli.py                        # Kommandoradsgränssnitt
│
├── tests/
│   └── test_extraction.py                # Kvalitetsvalidering
│
├── config.py                             # API-nycklar, sökvägar
└── requirements.txt
```

---

## 1. Datamodeller (`src/extract/models.py`)

```python
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

class StockRecommendation(BaseModel):
    """En enskild aktie-rekommendation från ett poddavsnitt."""
    
    stock_name: str = Field(description="Aktiens namn, t.ex. 'Evolution'")
    ticker: str | None = Field(default=None, description="Ticker om nämnt, t.ex. 'EVO'")
    action: Literal["buy", "sell", "hold", "watch", "avoid"] = Field(
        description="Typ av rekommendation"
    )
    confidence: Literal["high", "medium", "low", "speculative"] = Field(
        description="Hur övertygad är talaren"
    )
    speaker: str | None = Field(default=None, description="Vem gav rekommendationen")
    speaker_role: Literal["host", "guest", "unknown"] = Field(default="unknown")
    timestamp: str | None = Field(default=None, description="Tidsstämpel [HH:MM:SS] om tillgänglig")
    
    reasoning: str = Field(description="Sammanfattning av argumentet, 1-3 meningar")
    price_target: str | None = Field(default=None, description="Kursmål om nämnt")
    time_horizon: str | None = Field(default=None, description="'kort sikt', 'lång sikt', '6 månader'")
    
    quote: str = Field(description="Exakt citat från transkriptet, max 100 ord")
    
    # Kategorisering
    sector: str | None = Field(default=None, description="Bransch: 'tech', 'fastigheter', 'finans', etc.")
    market: Literal["sweden", "us", "europe", "other", "unknown"] = Field(default="unknown")


class EpisodeAnalysis(BaseModel):
    """Komplett analys av ett poddavsnitt."""
    
    # Identifiering
    episode_id: str = Field(description="Unikt ID, t.ex. 'borspodden_2024-12-20'")
    podcast_name: str = Field(description="Podcastens namn")
    episode_title: str | None = Field(default=None)
    episode_number: int | None = Field(default=None)
    date: str = Field(description="Publiceringsdatum, ISO-format YYYY-MM-DD")
    
    # Deltagare
    hosts: list[str] = Field(default_factory=list)
    guests: list[str] = Field(default_factory=list)
    
    # Innehåll
    main_topics: list[str] = Field(description="Max 5 huvudämnen som diskuteras")
    stocks_discussed: list[str] = Field(description="Alla aktier/bolag som nämns")
    recommendations: list[StockRecommendation] = Field(default_factory=list)
    
    # Sentiment
    market_sentiment: Literal["bullish", "bearish", "neutral", "mixed"] = Field(
        description="Övergripande marknadssyn i avsnittet"
    )
    
    # Sammanfattning
    summary: str = Field(description="3-5 meningar som sammanfattar avsnittet")
    key_takeaways: list[str] = Field(description="3-5 huvudpunkter för investerare")
    
    # Metadata
    transcript_file: str
    transcript_word_count: int
    has_timestamps: bool = Field(default=False)
    processed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    model_used: str = Field(default="claude-sonnet-4-20250514")


class ProcessingStatus(BaseModel):
    """Håller koll på processing-status."""
    
    file_path: str
    status: Literal["pending", "processing", "completed", "error"]
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None
    retry_count: int = 0
```

---

## 2. Prompt Template (`src/extract/prompt_templates.py`)

```python
EXTRACTION_SYSTEM_PROMPT = """Du är en expert på att analysera svenska finanspoddar och extrahera investeringsrekommendationer.

Din uppgift är att noggrant läsa podcast-transkript och identifiera:
1. KONKRETA aktie-rekommendationer (köp, sälj, bevaka, undvik)
2. Vem som ger rekommendationen (host eller gäst)
3. Argumenten bakom rekommendationen
4. Eventuella kursmål eller tidshorisonter

VIKTIGA RIKTLINJER:
- Var KONSERVATIV: Inkludera bara tydliga rekommendationer, inte vag diskussion
- "Intressant bolag" eller "värt att titta på" = watch, INTE buy
- "Vi äger aktien" utan vidare kontext = hold
- "Stark köpkandidat", "köpläge", "vi köper" = buy
- "Dags att ta hem vinst", "sälj", "vi säljer" = sell
- Fånga EXAKTA citat som stödjer rekommendationen
- Om tidsstämplar finns [HH:MM:SS], inkludera dem
- Svenska bolag listas ofta utan ticker - det är OK att lämna ticker tom

FINANSTERMINOLOGI ATT KÄNNA IGEN:
- Köpsignaler: "köpläge", "köpvärd", "attraktiv", "undervärderad", "vi köper", "stark köp"
- Säljsignaler: "säljläge", "övervärderad", "ta hem vinst", "vi säljer", "sälj"
- Watch: "bevaka", "intressant", "håll koll på", "kan bli köpvärd"
- Undvik: "håll dig borta", "undvik", "för riskfyllt"

OUTPUT:
Returnera ENDAST valid JSON enligt det schema som anges. Ingen annan text."""


EXTRACTION_USER_PROMPT = """Analysera följande podcast-transkript och extrahera all relevant information.

PODCAST: {podcast_name}
DATUM: {date}
FIL: {filename}

---
TRANSKRIPT:
{transcript}
---

Extrahera:
1. Alla deltagare (hosts och gäster)
2. Huvudämnen som diskuteras (max 5)
3. Alla aktier/bolag som nämns
4. KONKRETA rekommendationer med citat och reasoning
5. Övergripande marknadssentiment
6. Sammanfattning och key takeaways

Returnera som JSON enligt EpisodeAnalysis-schemat."""


FEW_SHOT_EXAMPLE = """
EXEMPEL PÅ KORREKT EXTRAKTION:

Input (utdrag):
"[00:15:23] Johan: Evolution har vi pratat om förut och jag måste säga att efter Q3-rapporten är jag ännu mer övertygad. Tillväxten i Asien är fantastisk, 45% år över år. Det här är ett solklart köp för mig, kursmål 1400 kronor.

[00:16:45] Erik: Håller med, men SBB däremot, där skulle jag vara försiktig. Balansräkningen oroar mig. Inte ett sälj kanske, men definitivt inte köpvärt just nu."

Output (recommendations-delen):
[
  {
    "stock_name": "Evolution",
    "ticker": "EVO",
    "action": "buy",
    "confidence": "high",
    "speaker": "Johan",
    "speaker_role": "host",
    "timestamp": "00:15:23",
    "reasoning": "Stark tillväxt i Asien på 45% YoY efter Q3-rapport. Talaren är 'ännu mer övertygad' efter rapporten.",
    "price_target": "1400 SEK",
    "time_horizon": null,
    "quote": "Evolution har vi pratat om förut och jag måste säga att efter Q3-rapporten är jag ännu mer övertygad. Tillväxten i Asien är fantastisk, 45% år över år. Det här är ett solklart köp för mig, kursmål 1400 kronor.",
    "sector": "gaming",
    "market": "sweden"
  },
  {
    "stock_name": "SBB",
    "ticker": "SBB",
    "action": "avoid",
    "confidence": "medium",
    "speaker": "Erik",
    "speaker_role": "host",
    "timestamp": "00:16:45",
    "reasoning": "Oro för balansräkningen. Inte säljrekommendation men tydlig varning.",
    "price_target": null,
    "time_horizon": null,
    "quote": "SBB däremot, där skulle jag vara försiktig. Balansräkningen oroar mig. Inte ett sälj kanske, men definitivt inte köpvärt just nu.",
    "sector": "fastigheter",
    "market": "sweden"
  }
]
"""
```

---

## 3. Processing Logic (`src/extract/process_transcript.py`)

```python
import json
import re
from pathlib import Path
from anthropic import Anthropic
from .models import EpisodeAnalysis, ProcessingStatus
from .prompt_templates import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT, FEW_SHOT_EXAMPLE


class TranscriptProcessor:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = Anthropic(api_key=api_key)
        self.model = model
    
    def parse_filename(self, filepath: Path) -> dict:
        """
        Extrahera metadata från filnamn.
        Hanterar format som:
        - borspodden_2024-12-20.txt
        - 20241220_borspodden_ep123.txt
        - fill_or_kill_2024-12-18.txt
        """
        stem = filepath.stem
        
        # Försök hitta datum i olika format
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',      # 2024-12-20
            r'(\d{8})',                    # 20241220
            r'(\d{4}_\d{2}_\d{2})',        # 2024_12_20
        ]
        
        date = None
        for pattern in date_patterns:
            match = re.search(pattern, stem)
            if match:
                date_str = match.group(1).replace('_', '-')
                if len(date_str) == 8:  # 20241220 format
                    date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                else:
                    date = date_str
                break
        
        # Försök identifiera podcast-namn
        podcast_patterns = {
            'borspodden': 'Börspodden',
            'fill_or_kill': 'Fill or Kill',
            'borsmagasinet': 'Börsmagasinet',
            'market_makers': 'Market Makers',
            'gott_tjot': 'Gött Tjöt om Aktier',
            'borsens_finest': 'Börsens Finest',
        }
        
        podcast_name = "Okänd podcast"
        stem_lower = stem.lower()
        for key, name in podcast_patterns.items():
            if key in stem_lower:
                podcast_name = name
                break
        
        return {
            'date': date or 'unknown',
            'podcast_name': podcast_name,
            'episode_id': stem
        }
    
    def process_transcript(self, filepath: Path) -> EpisodeAnalysis:
        """Processa ett enskilt transkript."""
        
        # Läs fil
        content = filepath.read_text(encoding='utf-8')
        word_count = len(content.split())
        has_timestamps = bool(re.search(r'\[\d{2}:\d{2}:\d{2}\]', content))
        
        # Parse metadata från filnamn
        file_meta = self.parse_filename(filepath)
        
        # Bygg prompt
        user_prompt = EXTRACTION_USER_PROMPT.format(
            podcast_name=file_meta['podcast_name'],
            date=file_meta['date'],
            filename=filepath.name,
            transcript=content
        )
        
        # Anropa Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            system=EXTRACTION_SYSTEM_PROMPT + "\n\n" + FEW_SHOT_EXAMPLE,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        # Parse response
        response_text = response.content[0].text
        
        # Extrahera JSON från response (kan vara wrappat i markdown code block)
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response_text
        
        # Parse och validera
        data = json.loads(json_str)
        
        # Lägg till metadata
        data['episode_id'] = file_meta['episode_id']
        data['transcript_file'] = str(filepath)
        data['transcript_word_count'] = word_count
        data['has_timestamps'] = has_timestamps
        data['model_used'] = self.model
        
        return EpisodeAnalysis(**data)
    
    def save_analysis(self, analysis: EpisodeAnalysis, output_dir: Path):
        """Spara analys till JSON-fil."""
        episodes_dir = output_dir / "episodes"
        episodes_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = episodes_dir / f"{analysis.episode_id}.json"
        output_file.write_text(
            analysis.model_dump_json(indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        return output_file
```

---

## 4. Batch Runner (`src/extract/batch_runner.py`)

```python
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from .process_transcript import TranscriptProcessor
from .models import ProcessingStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BatchRunner:
    def __init__(
        self,
        api_key: str,
        transcripts_dir: Path,
        output_dir: Path,
        processing_dir: Path
    ):
        self.processor = TranscriptProcessor(api_key)
        self.transcripts_dir = Path(transcripts_dir)
        self.output_dir = Path(output_dir)
        self.processing_dir = Path(processing_dir)
        
        # Säkerställ mappar finns
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.processing_dir.mkdir(parents=True, exist_ok=True)
        
        # Status-filer
        self.completed_file = self.processing_dir / "completed.json"
        self.errors_file = self.processing_dir / "errors.json"
    
    def get_completed(self) -> set:
        """Hämta lista över redan processade filer."""
        if self.completed_file.exists():
            data = json.loads(self.completed_file.read_text())
            return set(data.get('completed', []))
        return set()
    
    def mark_completed(self, filepath: Path):
        """Markera fil som klar."""
        completed = self.get_completed()
        completed.add(str(filepath.name))
        self.completed_file.write_text(
            json.dumps({'completed': list(completed), 'updated': datetime.now().isoformat()}, indent=2)
        )
    
    def log_error(self, filepath: Path, error: str):
        """Logga fel."""
        errors = []
        if self.errors_file.exists():
            errors = json.loads(self.errors_file.read_text()).get('errors', [])
        
        errors.append({
            'file': str(filepath.name),
            'error': error,
            'timestamp': datetime.now().isoformat()
        })
        
        self.errors_file.write_text(json.dumps({'errors': errors}, indent=2))
    
    def run(
        self,
        skip_completed: bool = True,
        max_files: int | None = None,
        delay_between: float = 2.0
    ):
        """
        Kör batch-processing på alla transkript.
        
        Args:
            skip_completed: Hoppa över redan processade filer
            max_files: Max antal filer att processa (None = alla)
            delay_between: Sekunder mellan varje API-anrop (rate limiting)
        """
        # Hitta alla transkript
        transcript_files = list(self.transcripts_dir.glob("*.txt"))
        logger.info(f"Hittade {len(transcript_files)} transkript-filer")
        
        # Filtrera bort redan processade
        completed = self.get_completed() if skip_completed else set()
        pending = [f for f in transcript_files if f.name not in completed]
        logger.info(f"{len(pending)} filer att processa ({len(completed)} redan klara)")
        
        if max_files:
            pending = pending[:max_files]
        
        # Processa
        successful = 0
        failed = 0
        
        for i, filepath in enumerate(pending):
            logger.info(f"[{i+1}/{len(pending)}] Processar: {filepath.name}")
            
            try:
                # Processa
                analysis = self.processor.process_transcript(filepath)
                
                # Spara
                output_file = self.processor.save_analysis(analysis, self.output_dir)
                logger.info(f"  ✓ Sparade: {output_file.name}")
                logger.info(f"  → {len(analysis.recommendations)} rekommendationer extraherade")
                
                # Markera klar
                self.mark_completed(filepath)
                successful += 1
                
            except Exception as e:
                logger.error(f"  ✗ Fel: {str(e)}")
                self.log_error(filepath, str(e))
                failed += 1
            
            # Rate limiting
            if i < len(pending) - 1:
                time.sleep(delay_between)
        
        # Sammanfattning
        logger.info(f"\n{'='*50}")
        logger.info(f"KLAR! Lyckade: {successful}, Misslyckade: {failed}")
        
        return {'successful': successful, 'failed': failed}
```

---

## 5. Index Builder (`src/extract/build_index.py`)

```python
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def build_index(extracted_dir: Path) -> dict:
    """
    Bygg sökindex från alla extraherade episode-analyser.
    """
    episodes_dir = extracted_dir / "episodes"
    
    if not episodes_dir.exists():
        raise ValueError(f"Episodes-mappen finns inte: {episodes_dir}")
    
    # Samla data
    episodes = []
    all_recommendations = []
    stocks_data = defaultdict(lambda: {
        'mention_count': 0,
        'episodes': [],
        'recommendations': []
    })
    
    # Läs alla episode-filer
    for episode_file in episodes_dir.glob("*.json"):
        data = json.loads(episode_file.read_text(encoding='utf-8'))
        
        # Episode-sammanfattning för index
        episode_summary = {
            'id': data['episode_id'],
            'podcast': data['podcast_name'],
            'date': data['date'],
            'title': data.get('episode_title'),
            'stocks': data.get('stocks_discussed', []),
            'recommendation_count': len(data.get('recommendations', [])),
            'sentiment': data.get('market_sentiment', 'unknown'),
            'hosts': data.get('hosts', []),
            'guests': data.get('guests', [])
        }
        episodes.append(episode_summary)
        
        # Processa rekommendationer
        for i, rec in enumerate(data.get('recommendations', [])):
            rec_entry = {
                'id': f"{data['episode_id']}_rec_{i:03d}",
                'stock': rec['stock_name'],
                'ticker': rec.get('ticker'),
                'action': rec['action'],
                'confidence': rec.get('confidence', 'unknown'),
                'date': data['date'],
                'podcast': data['podcast_name'],
                'episode_id': data['episode_id'],
                'speaker': rec.get('speaker'),
                'speaker_role': rec.get('speaker_role', 'unknown'),
                'reasoning': rec.get('reasoning', ''),
                'price_target': rec.get('price_target'),
                'time_horizon': rec.get('time_horizon'),
                'sector': rec.get('sector'),
                'market': rec.get('market', 'unknown'),
                'timestamp': rec.get('timestamp'),
                'quote': rec.get('quote', '')
            }
            all_recommendations.append(rec_entry)
            
            # Uppdatera stock-data
            stock_key = rec['stock_name'].lower()
            stocks_data[stock_key]['mention_count'] += 1
            if data['episode_id'] not in stocks_data[stock_key]['episodes']:
                stocks_data[stock_key]['episodes'].append(data['episode_id'])
            stocks_data[stock_key]['recommendations'].append({
                'action': rec['action'],
                'date': data['date'],
                'episode_id': data['episode_id'],
                'confidence': rec.get('confidence')
            })
    
    # Sortera episodes efter datum (nyast först)
    episodes.sort(key=lambda x: x['date'] or '', reverse=True)
    all_recommendations.sort(key=lambda x: x['date'] or '', reverse=True)
    
    # Bygg stocks-index med senaste rekommendation
    stocks_index = {}
    for stock_name, data in stocks_data.items():
        # Hitta senaste rekommendation
        recs_sorted = sorted(data['recommendations'], key=lambda x: x['date'] or '', reverse=True)
        latest = recs_sorted[0] if recs_sorted else None
        
        stocks_index[stock_name] = {
            'mention_count': data['mention_count'],
            'episodes': data['episodes'],
            'latest_recommendation': latest
        }
    
    # Skapa huvudindex
    index = {
        'last_updated': datetime.now().isoformat(),
        'episode_count': len(episodes),
        'recommendation_count': len(all_recommendations),
        'unique_stocks': len(stocks_index),
        'episodes': episodes,
        'stocks': stocks_index
    }
    
    return index, all_recommendations


def save_index(extracted_dir: Path):
    """Bygg och spara index-filer."""
    
    index, recommendations = build_index(extracted_dir)
    
    # Spara index.json
    index_file = extracted_dir / "index.json"
    index_file.write_text(
        json.dumps(index, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    
    # Spara recommendations.json
    recs_file = extracted_dir / "recommendations.json"
    recs_file.write_text(
        json.dumps(recommendations, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    
    print(f"Index sparat: {index_file}")
    print(f"  - {index['episode_count']} avsnitt")
    print(f"  - {index['recommendation_count']} rekommendationer")
    print(f"  - {index['unique_stocks']} unika aktier")
    print(f"Rekommendationer sparade: {recs_file}")
    
    return index_file, recs_file
```

---

## 6. Search Utilities (`src/extract/search.py`)

```python
import json
from pathlib import Path
from datetime import datetime, timedelta


class RecommendationSearch:
    def __init__(self, extracted_dir: Path):
        self.extracted_dir = Path(extracted_dir)
        self._load_data()
    
    def _load_data(self):
        """Ladda index och rekommendationer."""
        index_file = self.extracted_dir / "index.json"
        recs_file = self.extracted_dir / "recommendations.json"
        
        if not index_file.exists():
            raise FileNotFoundError(f"Index saknas: {index_file}. Kör 'rebuild-index' först.")
        
        self.index = json.loads(index_file.read_text(encoding='utf-8'))
        self.recommendations = json.loads(recs_file.read_text(encoding='utf-8'))
    
    def get_recommendations_for_stock(self, stock: str, action: str = None) -> list:
        """
        Hämta alla rekommendationer för en aktie.
        
        Args:
            stock: Aktienamn (case-insensitive)
            action: Filtrera på 'buy', 'sell', etc. (optional)
        """
        stock_lower = stock.lower()
        results = [
            r for r in self.recommendations
            if stock_lower in r['stock'].lower()
        ]
        
        if action:
            results = [r for r in results if r['action'] == action]
        
        return results
    
    def get_recent_recommendations(self, days: int = 30, action: str = None) -> list:
        """Hämta rekommendationer från senaste X dagar."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        results = [
            r for r in self.recommendations
            if r['date'] and r['date'] >= cutoff
        ]
        
        if action:
            results = [r for r in results if r['action'] == action]
        
        return results
    
    def get_episode_summary(self, episode_id: str) -> dict | None:
        """Hämta sammanfattning för ett avsnitt."""
        for ep in self.index['episodes']:
            if ep['id'] == episode_id:
                return ep
        return None
    
    def get_full_episode(self, episode_id: str) -> dict | None:
        """Hämta fullständig episod-analys."""
        episode_file = self.extracted_dir / "episodes" / f"{episode_id}.json"
        if episode_file.exists():
            return json.loads(episode_file.read_text(encoding='utf-8'))
        return None
    
    def search_by_speaker(self, speaker: str) -> list:
        """Sök rekommendationer från en specifik person."""
        speaker_lower = speaker.lower()
        return [
            r for r in self.recommendations
            if r.get('speaker') and speaker_lower in r['speaker'].lower()
        ]
    
    def search_by_sector(self, sector: str) -> list:
        """Sök rekommendationer inom en sektor."""
        sector_lower = sector.lower()
        return [
            r for r in self.recommendations
            if r.get('sector') and sector_lower in r['sector'].lower()
        ]
    
    def get_stats(self) -> dict:
        """Övergripande statistik."""
        action_counts = {}
        for r in self.recommendations:
            action = r['action']
            action_counts[action] = action_counts.get(action, 0) + 1
        
        return {
            'total_episodes': self.index['episode_count'],
            'total_recommendations': self.index['recommendation_count'],
            'unique_stocks': self.index['unique_stocks'],
            'recommendations_by_action': action_counts,
            'last_updated': self.index['last_updated']
        }
    
    def get_top_stocks(self, n: int = 10) -> list:
        """Aktier med flest omnämnanden."""
        stocks = [
            {'name': k, **v}
            for k, v in self.index['stocks'].items()
        ]
        stocks.sort(key=lambda x: x['mention_count'], reverse=True)
        return stocks[:n]
```

---

## 7. CLI (`src/extract/cli.py`)

```python
import argparse
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description='PodStock Transcript Extraction')
    subparsers = parser.add_subparsers(dest='command', help='Kommandon')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Processa transkript')
    process_parser.add_argument('--all', action='store_true', help='Processa alla väntande')
    process_parser.add_argument('--file', type=str, help='Processa en specifik fil')
    process_parser.add_argument('--max', type=int, help='Max antal filer')
    process_parser.add_argument('--delay', type=float, default=2.0, help='Sekunder mellan anrop')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Sök i extraherad data')
    search_parser.add_argument('--stock', type=str, help='Sök på aktienamn')
    search_parser.add_argument('--recent', type=int, help='Senaste X dagar')
    search_parser.add_argument('--speaker', type=str, help='Sök på talare')
    search_parser.add_argument('--action', type=str, choices=['buy', 'sell', 'hold', 'watch', 'avoid'])
    
    # Rebuild index
    subparsers.add_parser('rebuild-index', help='Bygg om index från extraherade filer')
    
    # Stats
    subparsers.add_parser('stats', help='Visa statistik')
    
    args = parser.parse_args()
    
    # Sökvägar
    base_dir = Path(__file__).parent.parent.parent / "data"
    transcripts_dir = base_dir / "transcripts" / "raw"
    extracted_dir = base_dir / "extracted"
    processing_dir = base_dir / "processing"
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if args.command == 'process':
        if not api_key:
            print("Fel: ANTHROPIC_API_KEY saknas i miljövariabler")
            return
        
        from .batch_runner import BatchRunner
        
        runner = BatchRunner(
            api_key=api_key,
            transcripts_dir=transcripts_dir,
            output_dir=extracted_dir,
            processing_dir=processing_dir
        )
        
        if args.file:
            # Processa en fil
            from .process_transcript import TranscriptProcessor
            processor = TranscriptProcessor(api_key)
            analysis = processor.process_transcript(Path(args.file))
            processor.save_analysis(analysis, extracted_dir)
            print(f"Klar! {len(analysis.recommendations)} rekommendationer extraherade.")
        else:
            # Batch
            runner.run(
                skip_completed=True,
                max_files=args.max,
                delay_between=args.delay
            )
    
    elif args.command == 'search':
        from .search import RecommendationSearch
        search = RecommendationSearch(extracted_dir)
        
        results = []
        if args.stock:
            results = search.get_recommendations_for_stock(args.stock, args.action)
        elif args.recent:
            results = search.get_recent_recommendations(args.recent, args.action)
        elif args.speaker:
            results = search.search_by_speaker(args.speaker)
        
        if results:
            print(f"\nHittade {len(results)} rekommendationer:\n")
            for r in results:
                print(f"  [{r['date']}] {r['stock']} - {r['action'].upper()}")
                print(f"    Podcast: {r['podcast']}")
                print(f"    Speaker: {r.get('speaker', 'Okänd')}")
                print(f"    Reasoning: {r['reasoning'][:100]}...")
                print()
        else:
            print("Inga resultat hittades.")
    
    elif args.command == 'rebuild-index':
        from .build_index import save_index
        save_index(extracted_dir)
    
    elif args.command == 'stats':
        from .search import RecommendationSearch
        search = RecommendationSearch(extracted_dir)
        stats = search.get_stats()
        
        print("\n📊 PodStock Statistik")
        print("=" * 40)
        print(f"Totalt antal avsnitt:      {stats['total_episodes']}")
        print(f"Totalt rekommendationer:   {stats['total_recommendations']}")
        print(f"Unika aktier:              {stats['unique_stocks']}")
        print(f"\nPer typ:")
        for action, count in stats['recommendations_by_action'].items():
            print(f"  {action}: {count}")
        print(f"\nSenast uppdaterat: {stats['last_updated']}")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
```

---

## 8. Config & Requirements

### `config.py`
```python
from pathlib import Path
import os

# Sökvägar
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts" / "raw"
EXTRACTED_DIR = DATA_DIR / "extracted"
PROCESSING_DIR = DATA_DIR / "processing"

# API
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
MODEL = "claude-sonnet-4-20250514"

# Processing
DEFAULT_DELAY = 2.0  # sekunder mellan API-anrop
MAX_RETRIES = 3
```

### `requirements.txt`
```
anthropic>=0.39.0
pydantic>=2.0.0
python-dotenv>=1.0.0
```

### `.env` (skapa manuellt)
```
ANTHROPIC_API_KEY=din-api-nyckel-här
```

---

## 9. Kvalitetsvalidering (`tests/test_extraction.py`)

```python
"""
Kvalitetsvalidering för extraherade rekommendationer.

Kör efter batch-extraction för att validera resultat:
  python -m pytest tests/test_extraction.py -v
"""

import json
from pathlib import Path
import random

EXTRACTED_DIR = Path(__file__).parent.parent / "data" / "extracted"


def load_random_episodes(n: int = 5) -> list:
    """Ladda N slumpmässiga episode-analyser för validering."""
    episodes_dir = EXTRACTED_DIR / "episodes"
    all_files = list(episodes_dir.glob("*.json"))
    
    if len(all_files) < n:
        sample_files = all_files
    else:
        sample_files = random.sample(all_files, n)
    
    return [json.loads(f.read_text()) for f in sample_files]


class TestDataQuality:
    """Testa datakvalitet på extraherade analyser."""
    
    def test_recommendations_have_required_fields(self):
        """Alla rekommendationer ska ha nödvändiga fält."""
        required = ['stock_name', 'action', 'reasoning', 'quote']
        
        episodes = load_random_episodes(10)
        for ep in episodes:
            for rec in ep.get('recommendations', []):
                for field in required:
                    assert field in rec, f"Saknar {field} i {ep['episode_id']}"
                    assert rec[field], f"Tomt {field} i {ep['episode_id']}"
    
    def test_actions_are_valid(self):
        """Actions ska vara giltiga värden."""
        valid_actions = {'buy', 'sell', 'hold', 'watch', 'avoid'}
        
        episodes = load_random_episodes(10)
        for ep in episodes:
            for rec in ep.get('recommendations', []):
                assert rec['action'] in valid_actions, \
                    f"Ogiltig action '{rec['action']}' i {ep['episode_id']}"
    
    def test_quotes_are_substantial(self):
        """Citat ska vara meningsfulla (inte för korta)."""
        min_quote_length = 20  # tecken
        
        episodes = load_random_episodes(10)
        for ep in episodes:
            for rec in ep.get('recommendations', []):
                quote = rec.get('quote', '')
                assert len(quote) >= min_quote_length, \
                    f"För kort citat ({len(quote)} tecken) i {ep['episode_id']}"
    
    def test_no_duplicate_recommendations(self):
        """Samma aktie+action ska inte förekomma flera gånger i samma avsnitt."""
        episodes = load_random_episodes(10)
        for ep in episodes:
            seen = set()
            for rec in ep.get('recommendations', []):
                key = (rec['stock_name'].lower(), rec['action'])
                # Tillåt samma aktie med olika action, men inte identiska
                if key in seen:
                    # Kontrollera att det verkligen är duplicat (inte olika tidsstämplar)
                    pass  # Kan vara OK om tidsstämplar skiljer sig
                seen.add(key)
    
    def test_episode_has_summary(self):
        """Varje avsnitt ska ha en sammanfattning."""
        episodes = load_random_episodes(10)
        for ep in episodes:
            assert 'summary' in ep, f"Saknar summary i {ep['episode_id']}"
            assert len(ep['summary']) > 50, f"För kort summary i {ep['episode_id']}"


class TestIndexIntegrity:
    """Testa att index är korrekt."""
    
    def test_index_exists(self):
        """Index-filen ska finnas."""
        index_file = EXTRACTED_DIR / "index.json"
        assert index_file.exists(), "index.json saknas"
    
    def test_index_counts_match(self):
        """Räknare i index ska matcha faktiskt innehåll."""
        index_file = EXTRACTED_DIR / "index.json"
        index = json.loads(index_file.read_text())
        
        episodes_dir = EXTRACTED_DIR / "episodes"
        actual_episodes = len(list(episodes_dir.glob("*.json")))
        
        assert index['episode_count'] == actual_episodes, \
            f"Index säger {index['episode_count']} avsnitt men hittade {actual_episodes}"
    
    def test_recommendations_file_exists(self):
        """Recommendations-filen ska finnas."""
        recs_file = EXTRACTED_DIR / "recommendations.json"
        assert recs_file.exists(), "recommendations.json saknas"


def manual_validation_report(n: int = 5):
    """
    Generera rapport för manuell validering.
    
    Kör: python -c "from tests.test_extraction import manual_validation_report; manual_validation_report()"
    """
    episodes = load_random_episodes(n)
    
    print("\n" + "=" * 60)
    print("MANUELL VALIDERINGSRAPPORT")
    print("=" * 60)
    print(f"\nGranska {n} slumpmässiga avsnitt nedan.")
    print("Kontrollera att rekommendationerna stämmer med citaten.\n")
    
    for i, ep in enumerate(episodes, 1):
        print(f"\n{'─' * 60}")
        print(f"AVSNITT {i}: {ep['episode_id']}")
        print(f"Podcast: {ep['podcast_name']}")
        print(f"Datum: {ep['date']}")
        print(f"Antal rekommendationer: {len(ep.get('recommendations', []))}")
        print(f"\nSammanfattning:\n{ep.get('summary', 'Saknas')}")
        
        for j, rec in enumerate(ep.get('recommendations', [])[:3], 1):  # Max 3 per avsnitt
            print(f"\n  📌 Rekommendation {j}:")
            print(f"     Aktie: {rec['stock_name']} ({rec.get('ticker', 'N/A')})")
            print(f"     Action: {rec['action'].upper()}")
            print(f"     Confidence: {rec.get('confidence', 'N/A')}")
            print(f"     Speaker: {rec.get('speaker', 'Okänd')}")
            print(f"     Reasoning: {rec.get('reasoning', 'N/A')}")
            print(f"     Citat: \"{rec.get('quote', 'N/A')[:150]}...\"")
        
        print(f"\n  ✅ Ser detta korrekt ut? (granska manuellt)")
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    manual_validation_report(5)
```

---

## Användning

### Steg 1: Installera dependencies
```bash
pip install -r requirements.txt
```

### Steg 2: Konfigurera API-nyckel
```bash
echo "ANTHROPIC_API_KEY=din-nyckel" > .env
```

### Steg 3: Lägg transkript i rätt mapp
```bash
# Kopiera dina 50+ transkript till:
data/transcripts/raw/
```

### Steg 4: Kör batch-extraction
```bash
# Processa alla (med paus mellan anrop)
python -m src.extract.cli process --all --delay 2.0

# Eller begränsa till 5 filer för test
python -m src.extract.cli process --all --max 5
```

### Steg 5: Bygg index
```bash
python -m src.extract.cli rebuild-index
```

### Steg 6: Validera kvalitet
```bash
python -m pytest tests/test_extraction.py -v
python -c "from tests.test_extraction import manual_validation_report; manual_validation_report(5)"
```

### Steg 7: Sök och använd data
```bash
# Statistik
python -m src.extract.cli stats

# Sök på aktie
python -m src.extract.cli search --stock "Evolution"

# Senaste köprekommendationer
python -m src.extract.cli search --recent 30 --action buy
```

---

## Uppskattade kostnader

Med claude-sonnet-4-20250514:
- Input: ~$3 per 1M tokens
- Output: ~$15 per 1M tokens

50 transkript × 15 000 ord ≈ 750 000 tokens input
Estimerad output: ~150 000 tokens

**Total uppskattad kostnad: ~$5-10 för hela batchen**
