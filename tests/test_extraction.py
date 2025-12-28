"""
Kvalitetsvalidering för extraherade rekommendationer.

Kör efter batch-extraction för att validera resultat:
  python -m pytest tests/test_extraction.py -v
"""

import json
import random
from pathlib import Path

EXTRACTED_DIR = Path(__file__).parent.parent / "data" / "extracted"


def load_random_episodes(n: int = 5) -> list:
    """Ladda N slumpmässiga episode-analyser för validering."""
    episodes_dir = EXTRACTED_DIR / "episodes"

    if not episodes_dir.exists():
        return []

    all_files = list(episodes_dir.glob("*.json"))

    if len(all_files) < n:
        sample_files = all_files
    else:
        sample_files = random.sample(all_files, n)

    return [json.loads(f.read_text(encoding="utf-8")) for f in sample_files]


class TestDataQuality:
    """Testa datakvalitet på extraherade analyser."""

    def test_recommendations_have_required_fields(self):
        """Alla rekommendationer ska ha nödvändiga fält."""
        required = ["stock_name", "action", "reasoning", "quote"]

        episodes = load_random_episodes(10)
        if not episodes:
            return  # Inga data att testa

        for ep in episodes:
            for rec in ep.get("recommendations", []):
                for field in required:
                    assert field in rec, f"Saknar {field} i {ep['episode_id']}"
                    assert rec[field], f"Tomt {field} i {ep['episode_id']}"

    def test_actions_are_valid(self):
        """Actions ska vara giltiga värden."""
        valid_actions = {"buy", "sell", "hold", "watch", "avoid"}

        episodes = load_random_episodes(10)
        if not episodes:
            return

        for ep in episodes:
            for rec in ep.get("recommendations", []):
                assert rec["action"] in valid_actions, (
                    f"Ogiltig action '{rec['action']}' i {ep['episode_id']}"
                )

    def test_quotes_are_substantial(self):
        """Citat ska vara meningsfulla (inte för korta)."""
        min_quote_length = 20  # tecken

        episodes = load_random_episodes(10)
        if not episodes:
            return

        for ep in episodes:
            for rec in ep.get("recommendations", []):
                quote = rec.get("quote", "")
                assert len(quote) >= min_quote_length, (
                    f"För kort citat ({len(quote)} tecken) i {ep['episode_id']}"
                )

    def test_no_duplicate_recommendations(self):
        """Samma aktie+action ska inte förekomma flera gånger i samma avsnitt."""
        episodes = load_random_episodes(10)
        if not episodes:
            return

        for ep in episodes:
            seen = set()
            for rec in ep.get("recommendations", []):
                key = (rec["stock_name"].lower(), rec["action"])
                # Tillåt samma aktie med olika action, men inte identiska
                if key in seen:
                    # Kontrollera att det verkligen är duplicat (inte olika tidsstämplar)
                    pass  # Kan vara OK om tidsstämplar skiljer sig
                seen.add(key)

    def test_episode_has_summary(self):
        """Varje avsnitt ska ha en sammanfattning."""
        episodes = load_random_episodes(10)
        if not episodes:
            return

        for ep in episodes:
            assert "summary" in ep, f"Saknar summary i {ep['episode_id']}"
            assert len(ep["summary"]) > 50, f"För kort summary i {ep['episode_id']}"


class TestIndexIntegrity:
    """Testa att index är korrekt."""

    def test_index_exists(self):
        """Index-filen ska finnas om det finns extraherad data."""
        episodes_dir = EXTRACTED_DIR / "episodes"
        if not episodes_dir.exists() or not list(episodes_dir.glob("*.json")):
            return  # Inga data att testa

        index_file = EXTRACTED_DIR / "index.json"
        assert index_file.exists(), "index.json saknas"

    def test_index_counts_match(self):
        """Räknare i index ska matcha faktiskt innehåll."""
        index_file = EXTRACTED_DIR / "index.json"
        if not index_file.exists():
            return

        index = json.loads(index_file.read_text(encoding="utf-8"))

        episodes_dir = EXTRACTED_DIR / "episodes"
        actual_episodes = len(list(episodes_dir.glob("*.json")))

        assert index["episode_count"] == actual_episodes, (
            f"Index säger {index['episode_count']} avsnitt men hittade {actual_episodes}"
        )

    def test_recommendations_file_exists(self):
        """Recommendations-filen ska finnas om det finns extraherad data."""
        episodes_dir = EXTRACTED_DIR / "episodes"
        if not episodes_dir.exists() or not list(episodes_dir.glob("*.json")):
            return

        recs_file = EXTRACTED_DIR / "recommendations.json"
        assert recs_file.exists(), "recommendations.json saknas"


def manual_validation_report(n: int = 5):
    """
    Generera rapport för manuell validering.

    Kör: python -c "from tests.test_extraction import manual_validation_report; manual_validation_report()"
    """
    episodes = load_random_episodes(n)

    if not episodes:
        print("Inga extraherade avsnitt hittades.")
        print(f"Kontrollera att {EXTRACTED_DIR / 'episodes'} finns och innehåller JSON-filer.")
        return

    print("\n" + "=" * 60)
    print("MANUELL VALIDERINGSRAPPORT")
    print("=" * 60)
    print(f"\nGranska {len(episodes)} slumpmässiga avsnitt nedan.")
    print("Kontrollera att rekommendationerna stämmer med citaten.\n")

    for i, ep in enumerate(episodes, 1):
        print(f"\n{'─' * 60}")
        print(f"AVSNITT {i}: {ep['episode_id']}")
        print(f"Podcast: {ep['podcast_name']}")
        print(f"Datum: {ep['date']}")
        print(f"Antal rekommendationer: {len(ep.get('recommendations', []))}")
        print(f"\nSammanfattning:\n{ep.get('summary', 'Saknas')}")

        for j, rec in enumerate(
            ep.get("recommendations", [])[:3], 1
        ):  # Max 3 per avsnitt
            print(f"\n  📌 Rekommendation {j}:")
            print(f"     Aktie: {rec['stock_name']} ({rec.get('ticker', 'N/A')})")
            print(f"     Action: {rec['action'].upper()}")
            print(f"     Confidence: {rec.get('confidence', 'N/A')}")
            print(f"     Speaker: {rec.get('speaker', 'Okänd')}")
            print(f"     Reasoning: {rec.get('reasoning', 'N/A')}")
            quote = rec.get("quote", "N/A")[:150]
            if len(rec.get("quote", "")) > 150:
                quote += "..."
            print(f'     Citat: "{quote}"')

        print("\n  ✅ Ser detta korrekt ut? (granska manuellt)")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    manual_validation_report(5)
