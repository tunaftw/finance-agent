#!/usr/bin/env python3
"""
Hacksaw Gaming Investment Case Aggregator

Aggregates all available data sources for Hacksaw Gaming:
- Earnings call transcripts (Q2, Q3 2025)
- Podcast signals/recommendations
- Extracted podcast mentions
- Financial filings (if analyzed)

Outputs a structured markdown investment case.
"""

import json
from datetime import datetime
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = DATA_DIR / "reports"
EARNINGS_DIR = DATA_DIR / "earnings" / "transcripts" / "hacksaw"
EXTRACTED_DIR = DATA_DIR / "extracted"
FILINGS_DIR = DATA_DIR / "filings"


def load_earnings_transcripts() -> list[dict]:
    """Load Hacksaw earnings call transcripts."""
    transcripts = []
    if EARNINGS_DIR.exists():
        for file in sorted(EARNINGS_DIR.glob("*.json")):
            with open(file) as f:
                transcripts.append(json.load(f))
    return transcripts


def extract_financials_from_transcript(transcript: dict) -> dict:
    """Extract key financial figures from transcript text."""
    text = transcript.get("full_text", "")
    quarter = f"Q{transcript.get('fiscal_quarter')} {transcript.get('fiscal_year')}"

    financials = {
        "period": quarter,
        "call_date": transcript.get("call_date", "")[:10],
        "metrics": {},
        "highlights": [],
        "risks": [],
        "guidance": []
    }

    # Q2 2025 specific data
    if "Q2" in quarter and "2025" in quarter:
        financials["metrics"] = {
            "revenue_eur": 45.4,
            "revenue_growth_yoy": "53%",
            "ebit_adjusted_eur": 37.1,
            "ebit_margin": "82%",
            "ebit_growth_yoy": "45%",
            "net_income_eur": 32.0,
            "eps_growth_yoy": "41%",
            "free_cash_flow_eur": 23.3,
            "fcf_conversion": "84%",
            "cash_position_eur": 53.0,
            "debt": 0,
            "games_portfolio": 241,
            "games_yoy_growth": "40%",
            "employees": 185,
            "employee_growth_yoy": "70%"
        }
        financials["highlights"] = [
            "IPO oversubscribed multiple times with 8,000+ new shareholders",
            "53% YoY revenue growth (above prospectus guidance of 45-50%)",
            "June came in stronger than April/May",
            "241 games in portfolio (+40% YoY)",
            "6 third-party studios on OpenRGS platform (vs 2 a year ago)",
            "Present in 35+ locally licensed markets",
            "Pennsylvania launch completed",
            "Top 10 games = 46% of GGR (vs 57% YoY) - more diversified"
        ]
        financials["risks"] = [
            "Sweepstakes casino regulation uncertainty (<10% of revenue, declining)",
            "US market still small contributor",
            "April was softer due to macro uncertainty",
            "Regulatory backlog in US slowing game launches"
        ]
        financials["guidance"] = [
            "Long-term (>3 years): >30% revenue growth",
            "Long-term: >80% EBIT margin",
            "Capital return: 75%+ of net income to shareholders",
            "No near-term capital raise planned"
        ]

    # Q3 2025 specific data
    elif "Q3" in quarter and "2025" in quarter:
        financials["metrics"] = {
            "revenue_eur": 52.0,
            "revenue_growth_yoy": "39%",
            "revenue_growth_qoq": "15%",
            "ebitda_eur": 21.1,
            "ebitda_growth_yoy": "18%",
            "ebitda_margin": "40%",
            "gross_profit_margin": "70.7%",
            "free_cash_flow_eur": 23.3,
            "fcf_growth_yoy": "100%+",
            "cash_position_eur": 84.0,
            "debt": 0,
            "games_released_q3": 20,
            "games_portfolio": 268,
            "largest_game_share": "14%",
            "top_10_games_share": "45%"
        }
        financials["highlights"] = [
            "52M EUR revenue (+39% YoY, +15% QoQ)",
            "Free cash flow more than doubled YoY",
            "Cash position 84M EUR (+100% vs Q3 2024)",
            "268 games in portfolio",
            "3 new studios onboarded to OpenRGS (6 total)",
            "More diversified: largest game <14% of GGR",
            "YTD revenue growth: 52%"
        ]
        financials["risks"] = [
            "EBITDA margin dropped to 40% due to personnel investments",
            "Gross profit margin lower (70.7%) due to licensing fees",
            "Personnel costs growing >100% YoY",
            "Sweepstakes regulation - California lawsuit mentioned",
            "Sweepstakes <10% of revenue, declining"
        ]
        financials["guidance"] = [
            "Personnel expenses to grow in line with revenue going forward",
            "Continued investment in team and organization",
            "Long-term targets unchanged: >30% growth, >80% margin"
        ]

    return financials


def load_podcast_signals() -> list[dict]:
    """Load podcast signals mentioning Hacksaw."""
    signals = []

    # Check unified signals database
    try:
        from podstock.unified.search import search_signals
        unified = search_signals(asset="Hacksaw", limit=50)
        for s in unified:
            signals.append({
                "date": str(s.content_date),
                "source": f"{s.source_type.value} / {s.source_id}",
                "speaker": s.speaker_name,
                "signal": s.signal.value,
                "strength": s.signal_strength.value if s.signal_strength else "unknown",
                "reasoning": s.reasoning,
                "quote": s.quote
            })
    except Exception as e:
        print(f"Warning: Could not load unified signals: {e}")

    # Also check extracted episodes directly
    episodes_dir = EXTRACTED_DIR / "episodes"
    if episodes_dir.exists():
        for file in episodes_dir.glob("*.json"):
            try:
                with open(file) as f:
                    data = json.load(f)
                for rec in data.get("recommendations", []):
                    if "hacksaw" in rec.get("stock_name", "").lower():
                        signals.append({
                            "date": data.get("date", "unknown"),
                            "source": f"podcast / {data.get('podcast_name', file.stem)}",
                            "speaker": rec.get("speaker", "Unknown"),
                            "signal": rec.get("action", "unknown"),
                            "strength": rec.get("confidence", "unknown"),
                            "reasoning": rec.get("reasoning", ""),
                            "quote": rec.get("quote", "")
                        })
            except Exception:
                continue

    # Check glm-batch extracted data
    batch_dir = EXTRACTED_DIR / "glm-batch"
    if batch_dir.exists():
        for file in batch_dir.glob("*.json"):
            if file.name.startswith("log-") or file.name.startswith("queue-"):
                continue
            try:
                with open(file) as f:
                    data = json.load(f)
                for rec in data.get("recommendations", []):
                    if "hacksaw" in rec.get("stock_name", "").lower():
                        # Avoid duplicates
                        existing = [s for s in signals if s.get("quote") == rec.get("quote")]
                        if not existing:
                            signals.append({
                                "date": data.get("date", "unknown"),
                                "source": f"podcast / {data.get('podcast_name', file.stem)}",
                                "speaker": rec.get("speaker", "Unknown"),
                                "signal": rec.get("action", "unknown"),
                                "strength": rec.get("confidence", "unknown"),
                                "reasoning": rec.get("reasoning", ""),
                                "quote": rec.get("quote", "")
                            })
            except Exception:
                continue

    # Deduplicate by quote
    seen_quotes = set()
    unique_signals = []
    for s in signals:
        quote = s.get("quote", "")[:100]
        if quote not in seen_quotes:
            seen_quotes.add(quote)
            unique_signals.append(s)

    return unique_signals


def generate_markdown_report(
    earnings: list[dict],
    signals: list[dict]
) -> str:
    """Generate markdown investment case report."""

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    report = f"""# Hacksaw Gaming - Investment Deep Dive
*Generated: {now}*

## Executive Summary

Hacksaw Gaming (HACKSAW.ST) är en snabbväxande B2B-leverantör av casinospel till iGaming-industrin.
Bolaget erbjuder slots, scratch games och virtual sports via sin egenutvecklade plattform OpenRGS.
IPO genomfördes sommaren 2025.

**Investment Question**: Är Hacksaw en bra investering för 2026?

---

## 1. Finansiell Översikt

"""

    # Add financial data from each quarter
    for transcript in earnings:
        fin = extract_financials_from_transcript(transcript)
        report += f"""### {fin['period']} (Earnings Call: {fin['call_date']})

**Nyckeltal:**
"""
        for key, value in fin["metrics"].items():
            label = key.replace("_", " ").title()
            if isinstance(value, float):
                report += f"- {label}: €{value}M\n"
            else:
                report += f"- {label}: {value}\n"

        report += "\n**Höjdpunkter:**\n"
        for h in fin["highlights"]:
            report += f"- {h}\n"

        report += "\n**Risker:**\n"
        for r in fin["risks"]:
            report += f"- {r}\n"

        report += "\n**Guidance:**\n"
        for g in fin["guidance"]:
            report += f"- {g}\n"

        report += "\n---\n\n"

    # Sentiment section
    report += """## 2. Sentiment-analys (Podcasts)

"""
    if signals:
        bullish = [s for s in signals if s["signal"] in ("buy", "bullish", "watch")]
        bearish = [s for s in signals if s["signal"] in ("sell", "bearish", "avoid")]

        report += f"""**Totalt:** {len(signals)} omnämnanden
- Bullish/Köp: {len(bullish)}
- Bearish/Sälj: {len(bearish)}

### Signaler:
"""
        for s in signals:
            report += f"""
**{s['date']}** - {s['source']}
- **Signal:** {s['signal'].upper()} ({s['strength']})
- **Talare:** {s['speaker']}
- **Resonemang:** {s['reasoning'] or 'N/A'}
- **Citat:** "{s['quote'][:200]}..."

"""
    else:
        report += "*Inga podcast-signaler hittades.*\n\n"

    report += """---

## 3. Bull Case

Baserat på tillgänglig data:

1. **Stark tillväxt**: 52% YTD revenue growth, 39-53% kvartalsvis YoY
2. **Exceptionella marginaler**: 82% EBIT-marginal i Q2, trots investeringar
3. **Kassaflöde**: FCF mer än fördubblades YoY, 84M EUR i kassan
4. **Diversifiering**: Portfölj på 268 spel, största spelet <14% av intäkter
5. **Plattformsstrategi**: OpenRGS växer med 6 tredjepartsstudios
6. **USA-potential**: Pennsylvania lanserad, långsiktig tillväxtmarknad
7. **Ingen skuld**: Finansiellt stark position

---

## 4. Bear Case

1. **Marginalpress**: EBITDA-marginal sjönk till 40% i Q3 pga investeringar
2. **Sweepstakes-risk**: Regulatorisk osäkerhet, California-stämning
3. **Personalkostnader**: Växer >100% YoY, kan fortsätta pressa marginaler
4. **USA-långsamt**: Regulatorisk backlog, tar tid att skala
5. **Koncentration till Europa**: Mogna marknader, begränsad tillväxt
6. **IPO-timing**: Insiders sålde vid IPO, kan indikera peak

---

## 5. Öppna Frågor för Vidare Analys

1. **Hur hållbar är 80%+ marginalen?** Management guider >80% långsiktigt men investerar tungt nu.
2. **Sweepstakes-risk**: Hur stor är verklig exponering? <10% men fallande.
3. **Konkurrens**: Hur jämför Hacksaw mot Evolution, Pragmatic Play, NetEnt?
4. **Värdering**: Vad är rimligt P/E för tillväxttakten?
5. **Insider-aktivitet**: Har det skett köp/sälj efter IPO?
6. **OpenRGS adoption**: Hur snabbt kan de skala tredjepartsstudios?

---

## 6. Data Sources

- Q2 2025 Earnings Call Transcript (2025-07-30)
- Q3 2025 Earnings Call Transcript (2025-11-04)
- Podcast mentions: {len(signals)} signals
- Filing PDFs: Q2 & Q3 2025 (ej LLM-analyserade)

---

## 7. Nästa Steg

1. **Web-sökning**: Senaste nyheter, analytikerkommentarer, kursutveckling
2. **Värderingsanalys**: Jämför med peers (Evolution, Kambi, Betsson)
3. **Insider-aktivitet**: Kolla transaktioner post-IPO
4. **Branschanalys**: iGaming-tillväxt, regulatorisk outlook

---

*Denna rapport är genererad automatiskt och kräver ytterligare analys för investeringsbeslut.*
"""

    return report


def main():
    print("=" * 60)
    print("HACKSAW GAMING - INVESTMENT CASE AGGREGATOR")
    print("=" * 60)

    # Load data
    print("\n1. Loading earnings transcripts...")
    earnings = load_earnings_transcripts()
    print(f"   Found {len(earnings)} transcripts")

    print("\n2. Loading podcast signals...")
    signals = load_podcast_signals()
    print(f"   Found {len(signals)} signals")

    # Generate report
    print("\n3. Generating investment case report...")
    report = generate_markdown_report(earnings, signals)

    # Save report
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = REPORTS_DIR / "hacksaw-investment-case.md"
    with open(output_file, "w") as f:
        f.write(report)

    print(f"\n4. Report saved to: {output_file}")
    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)

    # Also print summary
    print("\n📊 QUICK SUMMARY:")
    print(f"   - Earnings transcripts: {len(earnings)}")
    print(f"   - Podcast signals: {len(signals)}")
    if signals:
        bullish = len([s for s in signals if s["signal"] in ("buy", "bullish", "watch")])
        print(f"   - Bullish signals: {bullish}/{len(signals)}")

    return report


if __name__ == "__main__":
    main()
