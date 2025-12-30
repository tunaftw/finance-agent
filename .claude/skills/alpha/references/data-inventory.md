# Data Inventory

Module for scanning all available local data sources for a company.

## Inventory Function

```python
import os
import json
import glob
import sqlite3
from pathlib import Path
from typing import Optional

def inventory_company_data(company_query: str) -> dict:
    """
    Scan all local data sources for a company and return availability summary.

    Args:
        company_query: Company name or ticker (e.g., "Betsson", "BETS-B", "EVO")

    Returns:
        dict with sources found and analysis mode recommendation
    """
    # Use relative path from project root (works from any machine)
    # When running from Claude Code, the CWD is typically the project root
    base_path = Path("data")
    if not base_path.exists():
        # Fallback: try to find data directory relative to this file
        base_path = Path(__file__).parent.parent.parent.parent / "data"

    # Create query variants for flexible matching
    query_lower = company_query.lower()
    query_variants = {
        query_lower,
        query_lower.replace(".st", ""),
        query_lower.replace("-", ""),
        query_lower.replace("-b", ""),
        query_lower.replace("-a", ""),
        query_lower.replace(" ", "-"),
        query_lower.replace(" ", ""),
    }

    # Also add the original query as-is
    query_variants.add(company_query)

    results = {
        "query": company_query,
        "query_variants": list(query_variants),
        "sources": {},
        "summary": {
            "total_sources": 0,
            "total_items": 0,
            "mode": "discovery"  # Will be updated based on findings
        }
    }

    # 1. Scan filings (subdirectory-based)
    filings_path = base_path / "filings" / "analysis"
    filings_found = []
    if filings_path.exists():
        for company_dir in filings_path.iterdir():
            if company_dir.is_dir():
                dir_name = company_dir.name.lower()
                if any(v in dir_name or dir_name in v for v in query_variants):
                    files = list(company_dir.glob("*.json"))
                    filings_found.extend([str(f) for f in files])

    if filings_found:
        results["sources"]["filings"] = {
            "count": len(filings_found),
            "files": filings_found,
            "description": "Financial reports (annual/quarterly)"
        }

    # 2. Scan podcasts (analyses-v2 with fallback to analyses)
    podcast_files = []
    podcasts_v2_path = base_path / "podcasts" / "analyses-v2"
    podcasts_v1_path = base_path / "podcasts" / "analyses"

    podcast_path = podcasts_v2_path if podcasts_v2_path.exists() else podcasts_v1_path

    if podcast_path.exists():
        for json_file in podcast_path.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)

                # Check stocks_discussed and recommendations
                stocks = data.get("stocks_discussed", [])
                recs = data.get("recommendations", [])

                # Normalize for comparison
                stocks_lower = [s.lower() for s in stocks]
                rec_stocks = [r.get("stock_name", "").lower() for r in recs]
                rec_tickers = [r.get("ticker", "").lower() for r in recs]

                all_mentions = set(stocks_lower + rec_stocks + rec_tickers)

                if any(v in mention or mention in v for v in query_variants for mention in all_mentions if mention):
                    podcast_files.append({
                        "file": str(json_file),
                        "episode_id": data.get("episode_id"),
                        "date": data.get("date"),
                        "podcast": data.get("podcast_name")
                    })
            except (json.JSONDecodeError, KeyError):
                continue

    if podcast_files:
        results["sources"]["podcasts"] = {
            "count": len(podcast_files),
            "episodes": podcast_files,
            "description": "Podcast episode mentions"
        }

    # 3. Scan Twitter analyses
    twitter_files = []
    twitter_path = base_path / "twitter" / "analyses"

    if twitter_path.exists():
        for json_file in twitter_path.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)

                # Check top_tickers in Twitter analyses
                top_tickers = data.get("top_tickers", [])
                ticker_names = [t.get("ticker", "").lower() for t in top_tickers]

                if any(v in ticker or ticker in v for v in query_variants for ticker in ticker_names if ticker):
                    twitter_files.append({
                        "file": str(json_file),
                        "source": data.get("source_id"),
                        "display_name": data.get("display_name"),
                        "matching_tickers": [t for t in top_tickers if any(v in t.get("ticker", "").lower() for v in query_variants)]
                    })
            except (json.JSONDecodeError, KeyError):
                continue

    if twitter_files:
        results["sources"]["twitter"] = {
            "count": len(twitter_files),
            "analyses": twitter_files,
            "description": "Twitter/X mentions from tracked accounts"
        }

    # 4. Scan YouTube analyses
    youtube_files = []
    youtube_path = base_path / "youtube" / "analyses"

    if youtube_path.exists():
        for json_file in youtube_path.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)

                # YouTube uses mentions[] structure with asset_symbol and asset_name
                mentions = data.get("mentions", [])

                mention_symbols = [m.get("asset_symbol", "").lower() for m in mentions]
                mention_names = [m.get("asset_name", "").lower() for m in mentions]

                all_mentions = set(mention_symbols + mention_names)

                if any(v in mention or mention in v for v in query_variants for mention in all_mentions if mention):
                    youtube_files.append({
                        "file": str(json_file),
                        "video_id": json_file.stem,
                        "title": data.get("episode_title", data.get("title"))
                    })
            except (json.JSONDecodeError, KeyError):
                continue

    if youtube_files:
        results["sources"]["youtube"] = {
            "count": len(youtube_files),
            "videos": youtube_files,
            "description": "YouTube video mentions"
        }

    # 5. Scan insider transactions
    insider_files = []
    insider_path = base_path / "insider"

    # Check raw subfolder and reports
    for subdir in ["raw", "reports", "cache"]:
        insider_subpath = insider_path / subdir
        if insider_subpath.exists():
            for json_file in insider_subpath.rglob("*.json"):
                filename_lower = json_file.name.lower()
                if any(v in filename_lower for v in query_variants):
                    insider_files.append(str(json_file))

    if insider_files:
        results["sources"]["insider"] = {
            "count": len(insider_files),
            "files": insider_files,
            "description": "Insider transaction data"
        }

    # 6. Scan news (raw press releases and analyses)
    news_files = []
    news_path = base_path / "news"

    if news_path.exists():
        # Check raw subdirectories (company-specific folders)
        raw_path = news_path / "raw"
        if raw_path.exists():
            for company_dir in raw_path.iterdir():
                if company_dir.is_dir():
                    dir_name = company_dir.name.lower()
                    if any(v in dir_name or dir_name in v for v in query_variants):
                        pr_files = list(company_dir.rglob("*.json"))
                        news_files.extend([str(f) for f in pr_files])

        # Check analyses folder
        analyses_path = news_path / "analyses"
        if analyses_path.exists():
            for json_file in analyses_path.glob("*.json"):
                if any(v in json_file.name.lower() for v in query_variants):
                    news_files.append(str(json_file))

    if news_files:
        results["sources"]["news"] = {
            "count": len(news_files),
            "files": news_files,
            "description": "News articles and press releases"
        }

    # 7. Check price data availability
    prices_path = base_path / "prices"
    price_data = {}

    if prices_path.exists():
        # Check ticker mapping
        mapping_file = prices_path / "ticker_mapping.json"
        if mapping_file.exists():
            try:
                with open(mapping_file, 'r') as f:
                    mappings = json.load(f)
                    for key, value in mappings.items():
                        if any(v in key.lower() or v in str(value).lower() for v in query_variants):
                            price_data["ticker_mapping"] = {key: value}
                            break
            except json.JSONDecodeError:
                pass

    if price_data:
        results["sources"]["prices"] = {
            "available": True,
            "data": price_data,
            "description": "Historical price data"
        }

    # 8. Check database availability
    db_path = base_path / "podstock.db"
    db_info = {}

    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Check for company mentions in recommendations table
            # Schema uses raw_stock_name and raw_ticker columns
            cursor.execute("""
                SELECT COUNT(*) FROM recommendations
                WHERE LOWER(raw_stock_name) LIKE ? OR LOWER(raw_ticker) LIKE ?
            """, (f"%{query_lower}%", f"%{query_lower}%"))
            rec_count = cursor.fetchone()[0]

            conn.close()

            if rec_count > 0:
                db_info = {
                    "recommendations_count": rec_count
                }
        except sqlite3.Error:
            pass

    if db_info:
        results["sources"]["database"] = {
            "available": True,
            "data": db_info,
            "description": "SQLite database (podstock.db)"
        }

    # Calculate summary
    total_sources = len(results["sources"])
    total_items = sum(
        src.get("count", 1) if isinstance(src.get("count"), int)
        else (1 if src.get("available") else 0)
        for src in results["sources"].values()
    )

    # Determine mode based on data availability
    if total_items >= 10 and total_sources >= 3:
        mode = "full"
    elif total_items >= 3 or total_sources >= 2:
        mode = "partial"
    else:
        mode = "discovery"

    results["summary"] = {
        "total_sources": total_sources,
        "total_items": total_items,
        "mode": mode,
        "mode_explanation": {
            "full": "Rich local data available - comprehensive analysis possible",
            "partial": "Some local data found - supplement with external research",
            "discovery": "Limited local data - focus on discovery and thesis development"
        }[mode]
    }

    return results
```

## Display Results

Format the inventory results for display:

```python
def display_inventory(inventory: dict) -> str:
    """Format inventory results for readable output."""
    lines = []

    query = inventory["query"]
    summary = inventory["summary"]
    sources = inventory["sources"]

    lines.append(f"## Data Inventory: {query}")
    lines.append("")
    lines.append(f"**Mode:** {summary['mode'].upper()} - {summary['mode_explanation']}")
    lines.append(f"**Sources found:** {summary['total_sources']} | **Total items:** {summary['total_items']}")
    lines.append("")

    if not sources:
        lines.append("No local data found for this company.")
        lines.append("")
        lines.append("Consider:")
        lines.append("- Checking ticker/name spelling")
        lines.append("- Running /analyze on relevant podcasts first")
        lines.append("- Downloading filings with /download-reports")
        return "\n".join(lines)

    lines.append("### Available Sources")
    lines.append("")

    # Filings
    if "filings" in sources:
        src = sources["filings"]
        lines.append(f"**Filings** ({src['count']} reports)")
        for f in src["files"][:5]:
            lines.append(f"  - {Path(f).name}")
        if src["count"] > 5:
            lines.append(f"  - ... and {src['count'] - 5} more")
        lines.append("")

    # Podcasts
    if "podcasts" in sources:
        src = sources["podcasts"]
        lines.append(f"**Podcasts** ({src['count']} episodes)")
        for ep in src["episodes"][:5]:
            lines.append(f"  - {ep['podcast']} ({ep['date']})")
        if src["count"] > 5:
            lines.append(f"  - ... and {src['count'] - 5} more")
        lines.append("")

    # Twitter
    if "twitter" in sources:
        src = sources["twitter"]
        lines.append(f"**Twitter** ({src['count']} accounts)")
        for tw in src["analyses"]:
            lines.append(f"  - @{tw['source']} ({tw['display_name']})")
        lines.append("")

    # YouTube
    if "youtube" in sources:
        src = sources["youtube"]
        lines.append(f"**YouTube** ({src['count']} videos)")
        for vid in src["videos"][:3]:
            title = vid.get("title", vid["video_id"])
            lines.append(f"  - {title[:50]}...")
        lines.append("")

    # Insider
    if "insider" in sources:
        src = sources["insider"]
        lines.append(f"**Insider** ({src['count']} files)")
        lines.append("")

    # News
    if "news" in sources:
        src = sources["news"]
        lines.append(f"**News** ({src['count']} items)")
        lines.append("")

    # Database
    if "database" in sources:
        src = sources["database"]
        data = src["data"]
        lines.append(f"**Database** (podstock.db)")
        lines.append(f"  - {data.get('recommendations_count', 0)} recommendations")
        lines.append("")

    # Prices
    if "prices" in sources:
        lines.append("**Price data** available")
        lines.append("")

    return "\n".join(lines)
```

## Usage Example

```python
# Run inventory for a company
inventory = inventory_company_data("Betsson")
print(display_inventory(inventory))

# Check mode to determine analysis approach
if inventory["summary"]["mode"] == "full":
    # Spawn comprehensive analysis agents
    pass
elif inventory["summary"]["mode"] == "partial":
    # Supplement with external research
    pass
else:
    # Discovery mode - focus on thesis development
    pass
```

## Mode Definitions

| Mode | Criteria | Approach |
|------|----------|----------|
| **full** | 10+ items across 3+ sources | Comprehensive analysis using all local data |
| **partial** | 3+ items or 2+ sources | Mixed approach - local data + external research |
| **discovery** | <3 items, <2 sources | Thesis development mode - gather data first |
