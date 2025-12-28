"""Prompt-mallar för Claude API-anrop."""

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
