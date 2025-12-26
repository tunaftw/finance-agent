"""LLM prompts for report generation.

This module contains prompt templates for generating summaries
with Claude Code or other LLMs.
"""

BROAD_SUMMARY_SYSTEM = """Du är en finansanalytiker som sammanfattar svenska aktiepodcasts.
Skriv på svenska. Var koncis men informativ.
Fokusera på konkreta aktierekommendationer och marknadstrender.
"""

BROAD_SUMMARY_USER = """Analysera följande podcast-data från perioden {period}.

PODCASTS SOM INGÅR:
{podcast_list}

AVSNITT ({episode_count} st):
{episodes_summary}

REKOMMENDATIONER ({recommendation_count} st):
{recommendations_json}

---

Generera en sammanfattning med följande sektioner:

## Översikt
Kort sammanfattning av periodens huvudteman (3-5 punkter)

## Aktierekommendationer
Tabell med: Aktie | Podcast | Talare | Typ (Köp/Sälj/Håll) | Kort motivering

## Per Podcast
Kort (2-3 meningar) sammanfattning av varje podcasts huvudfokus

## Marknadssentiment
Övergripande känsla: bullish/bearish/neutral med motivering
"""

DETAILED_SUMMARY_SYSTEM = """Du är en finansanalytiker som gör djupanalyser av svenska aktiepodcasts.
Skriv på svenska. Var detaljerad och inkludera citat.
Fokusera på specifika investeringscase och argumentation.
"""

DETAILED_SUMMARY_USER = """Analysera följande podcast-data från perioden {period} i detalj.

PODCASTS SOM INGÅR:
{podcast_list}

AVSNITT ({episode_count} st):
{episodes_summary}

REKOMMENDATIONER ({recommendation_count} st):
{recommendations_json}

---

Generera en detaljerad rapport med följande sektioner:

## Översikt
Sammanfattning av periodens huvudteman (5-7 punkter)

## Aktierekommendationer
Tabell med: Aktie | Podcast | Talare | Typ | Motivering

## Utförliga Citat
För varje viktig rekommendation, inkludera:
- Det exakta citatet från podcasten
- Kontext kring uttalandet
- Eventuella förbehåll som nämns

## Gäst-insikter
Specifika insikter från gäster (ej värdar):
- Vem: [Gästnamn]
- Tema: [Ämne]
- Nyckeluttalande: [Citat]

## Motsägelser & Debatt
Notera om olika podcasts har olika åsikter om samma aktie:
- Aktie: [Namn]
- Podcast A säger: [Åsikt]
- Podcast B säger: [Åsikt]

## Marknadssentiment
Övergripande känsla med detaljerad motivering baserat på diskussionerna.
"""

OPENCODE_INSTRUCTIONS = """# Instruktioner för sammanfattningsgenerering

Läs igenom datan nedan och generera en {report_type} sammanfattning.

## Format
- Skriv på svenska
- Använd markdown-formatering
- Inkludera tabeller för rekommendationer
- Var {detail_level}

## Data att analysera
Perioden: {period}
Podcasts: {podcast_count} st
Avsnitt: {episode_count} st
Rekommendationer: {recommendation_count} st

Se fältet "data" nedan för fullständig information.

## Förväntad output
Generera rapporten enligt mall i "user_prompt" fältet.
"""


def format_broad_prompt(data: dict) -> str:
    """Format broad summary prompt with data."""
    episodes_summary = "\n".join(
        f"- {ep['published_at'][:10]}: {ep['podcast_name']} - {ep['title']}"
        for ep in data.get("episodes", [])
    )

    recommendations_json = _format_recommendations(data.get("recommendations", []))

    return BROAD_SUMMARY_USER.format(
        period=data.get("period", "okänd period"),
        podcast_list=", ".join(data.get("podcasts", [])),
        episodes_summary=episodes_summary or "Inga avsnitt",
        episode_count=len(data.get("episodes", [])),
        recommendations_json=recommendations_json or "Inga rekommendationer",
        recommendation_count=len(data.get("recommendations", [])),
    )


def format_detailed_prompt(data: dict) -> str:
    """Format detailed summary prompt with data."""
    episodes_summary = "\n".join(
        f"- {ep['published_at'][:10]}: {ep['podcast_name']} - {ep['title']}"
        for ep in data.get("episodes", [])
    )

    recommendations_json = _format_recommendations(data.get("recommendations", []), detailed=True)

    return DETAILED_SUMMARY_USER.format(
        period=data.get("period", "okänd period"),
        podcast_list=", ".join(data.get("podcasts", [])),
        episodes_summary=episodes_summary or "Inga avsnitt",
        episode_count=len(data.get("episodes", [])),
        recommendations_json=recommendations_json or "Inga rekommendationer",
        recommendation_count=len(data.get("recommendations", [])),
    )


def _format_recommendations(recommendations: list[dict], detailed: bool = False) -> str:
    """Format recommendations for prompt."""
    if not recommendations:
        return ""

    lines = []
    for rec in recommendations:
        stock = rec.get("stock", "?")
        action = rec.get("action", "?")
        podcast = rec.get("podcast_name", "?")
        speaker = rec.get("speaker", "?")
        reasoning = rec.get("reasoning", "")
        quote = rec.get("quote", "")

        if detailed and quote:
            lines.append(
                f"- {stock} ({action}): {podcast} / {speaker}\n"
                f"  Motivering: {reasoning}\n"
                f"  Citat: \"{quote[:200]}...\"\n"
            )
        else:
            lines.append(f"- {stock} ({action}): {podcast} / {speaker} - {reasoning[:100]}")

    return "\n".join(lines)
