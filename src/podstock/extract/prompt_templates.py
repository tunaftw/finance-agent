"""Prompt-mallar för Claude API-anrop - Schema 2.1 med stock_segments, insights och alfa-fält."""

EXTRACTION_SYSTEM_PROMPT = """Du är en expert på att analysera svenska finanspoddar och extrahera investeringsrekommendationer.

Din uppgift är att noggrant läsa podcast-transkript och identifiera:
1. KONKRETA aktie-rekommendationer (köp, sälj, bevaka, undvik)
2. DETALJERADE DISKUSSIONSSEGMENT för varje aktie som diskuteras >2 minuter
3. Vem som ger rekommendationen (host eller gäst)
4. Argumenten bakom rekommendationen (bull case, bear case, catalysts, risks)
5. Eventuella kursmål, tidshorisonter och finansiella nyckeltal
6. Om talaren äger aktien (position disclosure)
7. INVESTERINGSVISDOM och insikter (insights)

VIKTIGA RIKTLINJER:
- Var KONSERVATIV för rekommendationer: Inkludera bara tydliga köp/sälj/watch
- Var GENERÖS för stock_segments: Fånga ALL diskussion om aktier som nämns betydligt
- "Intressant bolag" eller "värt att titta på" = watch, INTE buy
- "Vi äger aktien" utan vidare kontext = hold, position_disclosure: "owns"
- "Stark köpkandidat", "köpläge", "vi köper" = buy
- "Dags att ta hem vinst", "sälj", "vi säljer" = sell
- Fånga FLERA citat per aktie med olika context (thesis, bull_case, bear_case, metric, conclusion)
- Extrahera finansiella nyckeltal som nämns (P/E, EV/EBITDA, marginaler, skuldsättning)

TIMESTAMPS - KRITISKT:
- Transkript har timestamps i format [MM:SS] eller [HH:MM:SS]
- VARJE citat och rekommendation MÅSTE inkludera närmaste timestamp
- timestamp_start och timestamp_end för stock_segments
- Om timestamp saknas i transkriptet, skriv null - gissa ALDRIG
- Timestamps möjliggör direkt navigering till diskussionen

FINANSTERMINOLOGI ATT KÄNNA IGEN:
- Köpsignaler: "köpläge", "köpvärd", "attraktiv", "undervärderad", "vi köper", "stark köp"
- Säljsignaler: "säljläge", "övervärderad", "ta hem vinst", "vi säljer", "sälj"
- Watch: "bevaka", "intressant", "håll koll på", "kan bli köpvärd"
- Undvik: "håll dig borta", "undvik", "för riskfyllt"

STOCK_SEGMENTS - DETALJERAD DISKUSSION:
För varje aktie som diskuteras mer än ~2 minuter, skapa ett stock_segment med:
- discussion_summary: 3-5 meningar som sammanfattar hela diskussionen om aktien
- thesis: { bull_case: [...], bear_case: [...], catalysts: [...], risks: [...] }
- quotes: array med flera citat, varje med speaker, text, timestamp, context
- financial_metrics: P/E, marginaler, skuldsättning etc. om de nämns
- position_disclosure: "owns" om talaren äger aktien, "none" om inte, "unknown" annars

INSIGHTS - FÅNGA INVESTERINGSVISDOM:
Extrahera tidlösa insikter och lärdomar som INTE är specifika aktie-tips:

Kategorier:
- "philosophy": Investeringsfilosofi och grundprinciper
  Exempel: "Jag köper aldrig bolag jag inte förstår", "Tid i marknaden slår timing"
- "lesson": Lärdomar från misstag eller erfarenheter
  Exempel: "Det största misstaget jag gjort var...", "Jag lärde mig att aldrig..."
- "wisdom": Marknadsvisdom, psykologi, timing
  Exempel: "Rädsla skapar möjligheter", "Girigheten tar över när..."

INKLUDERA:
- Tidlösa principer som håller över tid
- Konkreta lärdomar från erfarenhet
- Psykologiska insikter om investerande
- Riskhanterings-filosofi

TAGS (använd relevanta för varje insight):
psychology, timing, diversification, risk_management, position_sizing,
valuation, quality, growth, contrarian, momentum, long_term, patience,
mistakes, success_factors, market_cycles

EXKLUDERA från insights (fångas i recommendations):
- Specifika aktie-tips ("köp Evolution")
- Tidsbunden marknadskommentar ("marknaden är övervärderad just nu")

EXTRA ALFA (fyll bara i om EXPLICIT nämnt - annars null):

POSITION CONTEXT (position_context i recommendations):
- "50% av portföljen" → "50% av portföljen"
- "Största positionen" → "Största positionen"
- "Liten position" → "Liten position"
- "Vi byggde på" → "Ökade positionen"

DOWNSIDE/RISK (downside_note i recommendations):
- "30% nedsida härifrån" → "30% downside"
- "Värsta fall 50 SEK" → "Downside 50 SEK"
- "3:1 risk/reward" → "Risk/reward 3:1"

CATALYST TIMING (catalyst_timing i recommendations):
- "Rapport 15 feb" → "Rapport 2025-02-15"
- "Produktlansering Q2" → "Produktlansering Q2 2025"
- "Efter nästa Fed-möte" → "Efter Fed-möte"

SPEAKER-IDENTIFIERING:
Om kända hosts anges i prompten:
1. Matcha namn mot kända hosts (fullständigt namn ELLER smeknamn)
2. Gäster introduceras ofta i introt: "Välkommen till X, vd för Y"
3. speaker_role: "host" för kända hosts, "guest" för identifierade gäster
4. Fånga gästens titel/roll om det nämns
5. Om osäker: använd förnamn + speaker_role: "unknown"

OUTPUT:
Returnera ENDAST valid JSON enligt schemat. Ingen annan text."""


EXTRACTION_USER_PROMPT = """Analysera följande podcast-transkript och extrahera all relevant information enligt Schema 2.1.

PODCAST: {podcast_name}
DATUM: {date}
FIL: {filename}
KÄNDA HOSTS: {hosts}

---
TRANSKRIPT:
{transcript}
---

Extrahera (KOMPLETT SCHEMA 2.1):

1. **Metadata**
   - hosts, guests (med titel/roll om nämnt), main_topics (max 5), stocks_discussed (alla som nämns)

2. **Recommendations** (för tydliga köp/sälj/watch)
   - stock_name, ticker, action, confidence, speaker, speaker_role
   - timestamp (KRITISKT - måste inkluderas om tillgänglig!)
   - reasoning, price_target, time_horizon
   - quote (exakt citat, max 100 ord), sector, market
   - position_context (om nämnt: "50% av portföljen", etc.)
   - downside_note (om nämnt: "30% downside", "Risk/reward 3:1")
   - catalyst_timing (om nämnt: "Rapport 2025-02-15", "Q2-lansering")

3. **Stock Segments** (VIKTIGT - för varje aktie med >2 min diskussion)
   - stock_name, ticker
   - timestamp_start, timestamp_end (KRITISKT om tidsstämplar finns!)
   - discussion_summary (3-5 meningar sammanfattning)
   - quotes: [ {{ speaker, text, timestamp, context: "thesis"|"bull_case"|"bear_case"|"metric"|"conclusion"|"other" }} ]
   - thesis: {{ bull_case: [...], bear_case: [...], catalysts: [...], risks: [...] }}
   - financial_metrics: {{ pe_ratio, margin, debt_level, revenue_growth, custom: [...] }}
   - position_disclosure: "owns"|"none"|"unknown"

4. **Insights** (VIKTIGT - fånga investeringsvisdom)
   - quote: Exakt citat
   - summary: Kort sammanfattning av insikten
   - category: "philosophy"|"lesson"|"wisdom"
   - speaker, speaker_role
   - confidence: "high"|"medium"|"low"
   - tags: Relevanta taggar (psychology, timing, risk_management, etc.)

5. **Övergripande**
   - market_sentiment: bullish|bearish|neutral|mixed
   - summary (3-5 meningar)
   - key_takeaways (3-5 punkter för investerare)

Returnera som JSON med schema_version: "2.1"."""


FEW_SHOT_EXAMPLE = """
EXEMPEL PÅ KORREKT EXTRAKTION (Schema 2.1):

Input (utdrag):
"[00:15:23] Johan: Evolution har vi pratat om förut och jag måste säga att efter Q3-rapporten är jag ännu mer övertygad. Tillväxten i Asien är fantastisk, 45% år över år. Det här är ett solklart köp för mig, kursmål 1400 kronor. Det är ungefär 40% av min portfölj nu.

[00:17:10] Johan: De har ju P/E runt 25 nu men växer 30% per år. Och marginalerna är fantastiska, över 60% EBIT. Enda risken är väl reglering i Asien, men det ser stabilt ut just nu. Nedsidan är kanske 15-20% om det går dåligt.

[00:18:45] Erik: Håller med om Evolution. Men SBB däremot, där skulle jag vara försiktig. Balansräkningen oroar mig med 6x skuldsättning. Vi äger inte SBB och kommer inte köpa.

[00:22:30] Johan: En sak jag lärt mig genom åren är att aldrig jaga aktier. Om du missar ett köpläge, vänta på nästa. Det kommer alltid fler möjligheter."

Output (komplett med stock_segments, insights och alfa-fält):
{
  "schema_version": "2.1",
  "recommendations": [
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
      "sector": "gaming",
      "market": "sweden",
      "position_context": "40% av portföljen",
      "downside_note": "15-20% downside",
      "catalyst_timing": null
    },
    {
      "stock_name": "SBB",
      "ticker": "SBB",
      "action": "avoid",
      "confidence": "medium",
      "speaker": "Erik",
      "speaker_role": "host",
      "timestamp": "00:18:45",
      "reasoning": "Oro för balansräkningen med 6x skuldsättning.",
      "sector": "fastigheter",
      "market": "sweden",
      "position_context": null,
      "downside_note": null,
      "catalyst_timing": null
    }
  ],
  "stock_segments": [
    {
      "stock_name": "Evolution",
      "ticker": "EVO",
      "timestamp_start": "00:15:23",
      "timestamp_end": "00:17:10",
      "discussion_summary": "Johan diskuterar Evolution som ett starkt köp efter Q3-rapporten. Tillväxten i Asien på 45% YoY imponerar. Värderingen på P/E 25 motiveras av 30% tillväxt och starka marginaler över 60% EBIT. Reglering i Asien lyfts som enda risken.",
      "quotes": [
        {
          "speaker": "Johan",
          "text": "Evolution har vi pratat om förut och jag måste säga att efter Q3-rapporten är jag ännu mer övertygad. Tillväxten i Asien är fantastisk, 45% år över år.",
          "timestamp": "00:15:23",
          "context": "thesis"
        },
        {
          "speaker": "Johan",
          "text": "De har ju P/E runt 25 nu men växer 30% per år. Och marginalerna är fantastiska, över 60% EBIT.",
          "timestamp": "00:17:10",
          "context": "metric"
        },
        {
          "speaker": "Johan",
          "text": "Enda risken är väl reglering i Asien, men det ser stabilt ut just nu.",
          "timestamp": "00:17:10",
          "context": "bear_case"
        }
      ],
      "thesis": {
        "bull_case": ["Stark tillväxt på 45% i Asien", "Höga marginaler över 60% EBIT", "Växer 30% per år"],
        "bear_case": ["Reglering i Asien kan påverka"],
        "catalysts": ["Q3-rapport visade stark tillväxt"],
        "risks": ["Regulatorisk osäkerhet i Asien"]
      },
      "financial_metrics": {
        "pe_ratio": "25",
        "margin": "60% EBIT",
        "revenue_growth": "30% per år"
      },
      "position_disclosure": "owns"
    },
    {
      "stock_name": "SBB",
      "ticker": "SBB",
      "timestamp_start": "00:18:45",
      "discussion_summary": "Erik varnar för SBB på grund av hög skuldsättning på 6x. De äger inte aktien och planerar inte köpa.",
      "quotes": [
        {
          "speaker": "Erik",
          "text": "SBB däremot, där skulle jag vara försiktig. Balansräkningen oroar mig med 6x skuldsättning.",
          "timestamp": "00:18:45",
          "context": "bear_case"
        }
      ],
      "thesis": {
        "bull_case": [],
        "bear_case": ["Hög skuldsättning på 6x"],
        "catalysts": [],
        "risks": ["Balansräkningsrisk"]
      },
      "financial_metrics": {
        "debt_level": "6x"
      },
      "position_disclosure": "none"
    }
  ],
  "insights": [
    {
      "quote": "En sak jag lärt mig genom åren är att aldrig jaga aktier. Om du missar ett köpläge, vänta på nästa. Det kommer alltid fler möjligheter.",
      "summary": "Jaga aldrig aktier - vänta på nästa köpläge istället för att FOMO-köpa",
      "category": "lesson",
      "speaker": "Johan",
      "speaker_role": "host",
      "confidence": "high",
      "tags": ["patience", "psychology", "timing"]
    }
  ]
}
"""


# === HELPER FUNCTIONS ===

import json
from pathlib import Path


def get_podcast_hosts(podcast_id: str) -> list[str]:
    """Hämta hosts för en podcast från podcasts.json."""
    podcasts_file = Path(__file__).parent.parent.parent.parent / "data" / "podcasts.json"
    if podcasts_file.exists():
        data = json.loads(podcasts_file.read_text(encoding="utf-8"))
        for p in data.get("podcasts", []):
            if p.get("id") == podcast_id:
                return p.get("hosts", [])
    return []


def build_analysis_prompt(
    transcript: str,
    podcast_name: str,
    date: str,
    filename: str,
    podcast_id: str | None = None,
) -> tuple[str, str]:
    """Bygg system och user prompt för analys.

    Args:
        transcript: Transkript-innehållet
        podcast_name: Namn på podcasten
        date: Datum för avsnittet (YYYY-MM-DD)
        filename: Filnamn
        podcast_id: Podcast ID för att hämta hosts (optional)

    Returns:
        Tuple av (system_prompt, user_prompt)
    """
    # Hämta hosts om podcast_id anges
    hosts = []
    if podcast_id:
        hosts = get_podcast_hosts(podcast_id)

    hosts_str = ", ".join(hosts) if hosts else "Okända (extrahera från introt)"

    user_prompt = EXTRACTION_USER_PROMPT.format(
        podcast_name=podcast_name,
        date=date,
        filename=filename,
        hosts=hosts_str,
        transcript=transcript,
    )

    return EXTRACTION_SYSTEM_PROMPT, user_prompt


def build_comprehensive_prompt(
    transcript_content: str,
    episode_id: str,
    extract_types: list[str] | None = None,
) -> tuple[str, str]:
    """Bygg prompt för comprehensive analys (bakåtkompatibel).

    Args:
        transcript_content: Transkript-innehållet
        episode_id: Episode ID (t.ex. "borspodden-2025-01-15-abc1")
        extract_types: Lista med extract types (ignoreras, extraherar alltid allt)

    Returns:
        Tuple av (system_prompt, user_prompt)
    """
    # Extrahera podcast_id från episode_id (första delen innan datum)
    parts = episode_id.split("-")
    podcast_id = parts[0] if parts else None

    # Extrahera datum om det finns i episode_id
    date = "Okänt"
    if len(parts) >= 4:
        # Format: podcast-YYYY-MM-DD-hash
        try:
            date = f"{parts[1]}-{parts[2]}-{parts[3]}"
        except IndexError:
            pass

    # Hämta podcast-namn från podcasts.json
    podcast_name = podcast_id or "Okänd podcast"
    podcasts_file = Path(__file__).parent.parent.parent.parent / "data" / "podcasts.json"
    if podcasts_file.exists() and podcast_id:
        data = json.loads(podcasts_file.read_text(encoding="utf-8"))
        for p in data.get("podcasts", []):
            if p.get("id") == podcast_id:
                podcast_name = p.get("name", podcast_id)
                break

    return build_analysis_prompt(
        transcript=transcript_content,
        podcast_name=podcast_name,
        date=date,
        filename=f"{episode_id}.txt",
        podcast_id=podcast_id,
    )
