#!/usr/bin/env python3
"""
Check which podcasts have transcript support in their RSS feeds.

Uses Podcasting 2.0 namespace: <podcast:transcript>
"""

from typing import Optional, Tuple
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote

PODCASTS = {
    "aktiepodden": "Aktiepodden",
    "analyspodden": "Analyspodden DNB Carnegie",
    "avanzapodden": "Avanzapodden",
    "bullochbjorn": "Bull Björn podcast",
    "borsensfinest": "Börsens Finest",
    "borsmagasinet": "Börsmagasinet",
    "borsmaklarna": "Börsmäklarna",
    "borspodden": "Börspodden",
    "ettrikareliv": "Ett rikare liv podcast",
    "fillorkill": "Fill or Kill podcast",
    "globalgains": "Global Gains podcast",
    "gotttjot": "Gött Tjöt om Aktier",
    "igborssnack": "IG Börssnack",
    "kortochlang": "Kort Lång Di podcast",
    "kvalitetforpengarna": "Kvalitet För Pengarna",
    "kvalitetsaktiepodden": "Kvalitetsaktiepodden",
    "marketmakers": "Market Makers Sverige",
    "marknaden": "Marknaden podcast Sverige",
    "montrosepodden": "Montrosepodden",
    "smaspararpodden": "Småspararpodden",
    "sparpodden": "Sparpodden",
    "veckanstrade": "Veckans Trade podcast",
}

def get_rss_url(search_term: str) -> Tuple[Optional[str], Optional[str]]:
    """Look up podcast RSS URL via iTunes Search API."""
    url = f"https://itunes.apple.com/search?term={quote(search_term)}&media=podcast&limit=3&country=se"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data.get("resultCount", 0) > 0:
            result = data["results"][0]
            return result.get("feedUrl"), result.get("collectionName")
    except Exception as e:
        print(f"  Error searching: {e}")
    return None, None


def check_rss_for_transcripts(rss_url: str) -> dict:
    """Check RSS feed for podcast:transcript tags."""
    result = {
        "has_transcript_tag": False,
        "transcript_count": 0,
        "transcript_types": set(),
        "sample_url": None,
        "has_podcast_namespace": False,
    }

    try:
        resp = requests.get(rss_url, timeout=15, headers={"User-Agent": "PodcastChecker/1.0"})
        resp.raise_for_status()

        # Check for podcast namespace declaration
        content = resp.text
        if "xmlns:podcast" in content or "podcast:transcript" in content:
            result["has_podcast_namespace"] = True

        # Parse XML
        root = ET.fromstring(resp.content)

        # Define namespaces
        namespaces = {
            "podcast": "https://podcastindex.org/namespace/1.0",
            "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
        }

        # Find all transcript tags
        for item in root.findall(".//item"):
            transcripts = item.findall("podcast:transcript", namespaces)
            if transcripts:
                result["has_transcript_tag"] = True
                result["transcript_count"] += len(transcripts)
                for t in transcripts:
                    t_type = t.get("type", "unknown")
                    result["transcript_types"].add(t_type)
                    if not result["sample_url"]:
                        result["sample_url"] = t.get("url")

        # Also check without namespace (some feeds use it differently)
        for item in root.iter():
            if "transcript" in item.tag.lower():
                result["has_transcript_tag"] = True

    except ET.ParseError as e:
        result["error"] = f"XML parse error: {e}"
    except Exception as e:
        result["error"] = str(e)

    result["transcript_types"] = list(result["transcript_types"])
    return result


def main():
    print("=" * 70)
    print("RSS Transcript Support Check")
    print("=" * 70)

    results = []

    for podcast_id, search_term in PODCASTS.items():
        print(f"\n{podcast_id}:")

        # Get RSS URL
        rss_url, found_name = get_rss_url(search_term)
        if not rss_url:
            print(f"  ✗ Could not find RSS feed")
            results.append({"id": podcast_id, "status": "no_rss"})
            continue

        print(f"  Found: {found_name}")
        print(f"  RSS: {rss_url[:60]}...")

        # Check for transcripts
        check = check_rss_for_transcripts(rss_url)

        if check.get("error"):
            print(f"  ✗ Error: {check['error']}")
            results.append({"id": podcast_id, "status": "error", "error": check["error"]})
            continue

        if check["has_transcript_tag"]:
            print(f"  ✓ HAS TRANSCRIPTS! ({check['transcript_count']} episodes)")
            print(f"    Types: {', '.join(check['transcript_types'])}")
            if check["sample_url"]:
                print(f"    Sample: {check['sample_url'][:70]}...")
            results.append({
                "id": podcast_id,
                "status": "has_transcripts",
                "count": check["transcript_count"],
                "types": check["transcript_types"],
                "rss_url": rss_url,
            })
        elif check["has_podcast_namespace"]:
            print(f"  ~ Has podcast namespace but no transcripts")
            results.append({"id": podcast_id, "status": "no_transcripts", "rss_url": rss_url})
        else:
            print(f"  ✗ No transcript support")
            results.append({"id": podcast_id, "status": "no_transcripts", "rss_url": rss_url})

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    with_transcripts = [r for r in results if r.get("status") == "has_transcripts"]
    without = [r for r in results if r.get("status") == "no_transcripts"]
    errors = [r for r in results if r.get("status") in ("error", "no_rss")]

    print(f"\n✓ With RSS transcripts: {len(with_transcripts)}")
    for r in with_transcripts:
        print(f"  - {r['id']} ({r['count']} episodes, types: {r['types']})")

    print(f"\n✗ Without RSS transcripts: {len(without)}")
    for r in without:
        print(f"  - {r['id']}")

    if errors:
        print(f"\n? Errors: {len(errors)}")
        for r in errors:
            print(f"  - {r['id']}: {r.get('error', 'no RSS found')}")


if __name__ == "__main__":
    main()
