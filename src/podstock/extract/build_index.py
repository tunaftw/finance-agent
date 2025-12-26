"""Bygg sökindex från extraherade episode-analyser."""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def build_index(extracted_dir: Path) -> tuple[dict, list]:
    """
    Bygg sökindex från alla extraherade episode-analyser.

    Returns:
        tuple: (index, all_recommendations)
    """
    episodes_dir = extracted_dir / "episodes"

    if not episodes_dir.exists():
        raise ValueError(f"Episodes-mappen finns inte: {episodes_dir}")

    # Samla data
    episodes = []
    all_recommendations = []
    stocks_data = defaultdict(
        lambda: {"mention_count": 0, "episodes": [], "recommendations": []}
    )

    # Läs alla episode-filer
    for episode_file in episodes_dir.glob("*.json"):
        data = json.loads(episode_file.read_text(encoding="utf-8"))

        # Episode-sammanfattning för index
        episode_summary = {
            "id": data["episode_id"],
            "podcast": data["podcast_name"],
            "date": data["date"],
            "title": data.get("episode_title"),
            "stocks": data.get("stocks_discussed", []),
            "recommendation_count": len(data.get("recommendations", [])),
            "sentiment": data.get("market_sentiment", "unknown"),
            "hosts": data.get("hosts", []),
            "guests": data.get("guests", []),
        }
        episodes.append(episode_summary)

        # Processa rekommendationer
        for i, rec in enumerate(data.get("recommendations", [])):
            rec_entry = {
                "id": f"{data['episode_id']}_rec_{i:03d}",
                "stock": rec["stock_name"],
                "ticker": rec.get("ticker"),
                "action": rec["action"],
                "confidence": rec.get("confidence", "unknown"),
                "date": data["date"],
                "podcast": data["podcast_name"],
                "episode_id": data["episode_id"],
                "speaker": rec.get("speaker"),
                "speaker_role": rec.get("speaker_role", "unknown"),
                "reasoning": rec.get("reasoning", ""),
                "price_target": rec.get("price_target"),
                "time_horizon": rec.get("time_horizon"),
                "sector": rec.get("sector"),
                "market": rec.get("market", "unknown"),
                "timestamp": rec.get("timestamp"),
                "quote": rec.get("quote", ""),
            }
            all_recommendations.append(rec_entry)

            # Uppdatera stock-data
            stock_key = rec["stock_name"].lower()
            stocks_data[stock_key]["mention_count"] += 1
            if data["episode_id"] not in stocks_data[stock_key]["episodes"]:
                stocks_data[stock_key]["episodes"].append(data["episode_id"])
            stocks_data[stock_key]["recommendations"].append(
                {
                    "action": rec["action"],
                    "date": data["date"],
                    "episode_id": data["episode_id"],
                    "confidence": rec.get("confidence"),
                }
            )

    # Sortera episodes efter datum (nyast först)
    episodes.sort(key=lambda x: x["date"] or "", reverse=True)
    all_recommendations.sort(key=lambda x: x["date"] or "", reverse=True)

    # Bygg stocks-index med senaste rekommendation
    stocks_index = {}
    for stock_name, data in stocks_data.items():
        # Hitta senaste rekommendation
        recs_sorted = sorted(
            data["recommendations"], key=lambda x: x["date"] or "", reverse=True
        )
        latest = recs_sorted[0] if recs_sorted else None

        stocks_index[stock_name] = {
            "mention_count": data["mention_count"],
            "episodes": data["episodes"],
            "latest_recommendation": latest,
        }

    # Skapa huvudindex
    index = {
        "last_updated": datetime.now().isoformat(),
        "episode_count": len(episodes),
        "recommendation_count": len(all_recommendations),
        "unique_stocks": len(stocks_index),
        "episodes": episodes,
        "stocks": stocks_index,
    }

    return index, all_recommendations


def save_index(extracted_dir: Path) -> tuple[Path, Path]:
    """Bygg och spara index-filer."""

    index, recommendations = build_index(extracted_dir)

    # Spara index.json
    index_file = extracted_dir / "index.json"
    index_file.write_text(
        json.dumps(index, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Spara recommendations.json
    recs_file = extracted_dir / "recommendations.json"
    recs_file.write_text(
        json.dumps(recommendations, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Index sparat: {index_file}")
    print(f"  - {index['episode_count']} avsnitt")
    print(f"  - {index['recommendation_count']} rekommendationer")
    print(f"  - {index['unique_stocks']} unika aktier")
    print(f"Rekommendationer sparade: {recs_file}")

    return index_file, recs_file
