#!/usr/bin/env python3
"""
Pure Python implementation of Apple Podcasts transcript downloader.

Avoids the fork() crash by using requests directly with cached bearer token.
Automatically refreshes expired tokens using GetBearerToken.
"""

from typing import Optional, Dict, List
import base64
import json
import re
import sqlite3
import subprocess
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

import requests

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
APPLE_PODCASTS_CONTAINER = Path.home() / "Library/Group Containers/243LU875E5.groups.com.apple.podcasts"
SQLITE_DB_PATH = APPLE_PODCASTS_CONTAINER / "Documents/MTLibrary.sqlite"
TTML_CACHE_PATH = APPLE_PODCASTS_CONTAINER / "Library/Cache/Assets/TTML"
BEARER_TOKEN_PATH = PROJECT_ROOT / "tools/apple-transcripts/bearer_token.txt"
GET_BEARER_TOKEN_PATH = PROJECT_ROOT / "tools/apple-transcripts/GetBearerToken"
TRANSCRIPTS_DIR = PROJECT_ROOT / "data/transcripts"
PODCAST_MAPPING_PATH = PROJECT_ROOT / "data/podcast_mapping.json"

COCOA_EPOCH = datetime(2001, 1, 1)


def get_token_expiration(token: str) -> Optional[datetime]:
    """Extract expiration datetime from JWT token."""
    try:
        # JWT format: header.payload.signature
        parts = token.split(".")
        if len(parts) != 3:
            return None

        # Decode payload (add padding if needed)
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding

        decoded = base64.urlsafe_b64decode(payload)
        data = json.loads(decoded)

        if "exp" in data:
            return datetime.fromtimestamp(data["exp"])
        return None
    except Exception:
        return None


def is_token_expired(token: str, buffer_hours: int = 1) -> bool:
    """Check if token is expired or will expire within buffer_hours."""
    exp = get_token_expiration(token)
    if not exp:
        return True  # Assume expired if we can't parse

    return datetime.now() > (exp - timedelta(hours=buffer_hours))


def refresh_bearer_token() -> Optional[str]:
    """Refresh bearer token using GetBearerToken tool."""
    if not GET_BEARER_TOKEN_PATH.exists():
        print("  ✗ GetBearerToken not found")
        print(f"    Expected at: {GET_BEARER_TOKEN_PATH}")
        return None

    try:
        print("  Refreshing bearer token...")
        result = subprocess.run(
            [str(GET_BEARER_TOKEN_PATH)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=GET_BEARER_TOKEN_PATH.parent
        )

        token = result.stdout.strip()
        if token.startswith("ey"):
            # Save to file
            BEARER_TOKEN_PATH.write_text(token)
            exp = get_token_expiration(token)
            exp_str = exp.strftime("%Y-%m-%d") if exp else "unknown"
            print(f"  ✓ Token refreshed (expires: {exp_str})")
            return token
        else:
            print(f"  ✗ Failed to get token: {result.stderr[:100] if result.stderr else 'no output'}")
            return None
    except subprocess.TimeoutExpired:
        print("  ✗ Token refresh timed out")
        return None
    except Exception as e:
        print(f"  ✗ Token refresh error: {e}")
        return None


def load_bearer_token(auto_refresh: bool = True) -> Optional[str]:
    """Load cached bearer token, optionally refreshing if expired."""
    if not BEARER_TOKEN_PATH.exists():
        if auto_refresh:
            return refresh_bearer_token()
        return None

    token = BEARER_TOKEN_PATH.read_text().strip()
    if not token.startswith("ey"):  # Invalid JWT prefix
        if auto_refresh:
            return refresh_bearer_token()
        return None

    # Check expiration
    if is_token_expired(token):
        exp = get_token_expiration(token)
        exp_str = exp.strftime("%Y-%m-%d %H:%M") if exp else "unknown"
        print(f"⚠ Token expired ({exp_str})")
        if auto_refresh:
            return refresh_bearer_token()
        return None

    return token


def load_podcast_mapping() -> dict:
    """Load podcast mapping."""
    if not PODCAST_MAPPING_PATH.exists():
        return {"apple_to_id": {}}
    with open(PODCAST_MAPPING_PATH) as f:
        return json.load(f)


class TokenExpiredError(Exception):
    """Raised when the bearer token is expired (401 response)."""
    pass


def fetch_transcript(apple_episode_id: str, bearer_token: str) -> Optional[Dict]:
    """Fetch transcript metadata from Apple API.

    Raises TokenExpiredError on 401 response.
    """
    url = (
        f"https://amp-api.podcasts.apple.com/v1/catalog/us/podcast-episodes/"
        f"{apple_episode_id}/transcripts?fields=ttmlToken,ttmlAssetUrls"
        f"&include%5Bpodcast-episodes%5D=podcast&l=en-US&with=entitlements"
    )

    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "User-Agent": "Podcasts/1.1.0 (macOS 15.5)"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=30)

        # Check for token expiration
        if resp.status_code == 401:
            raise TokenExpiredError("Bearer token expired")

        resp.raise_for_status()
        data = resp.json()

        if "errors" in data:
            print(f"  API error: {data['errors']}")
            return None

        attrs = data.get("data", [{}])[0].get("attributes", {})
        return {
            "ttml_url": attrs.get("ttmlAssetUrls", {}).get("ttml"),
            "ttml_token": attrs.get("ttmlToken"),
        }
    except TokenExpiredError:
        raise  # Re-raise so caller can handle
    except Exception as e:
        print(f"  Fetch error: {e}")
        return None


def download_ttml(ttml_url: str, output_path: Path) -> bool:
    """Download TTML file."""
    try:
        resp = requests.get(ttml_url, timeout=60)
        resp.raise_for_status()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(resp.content)
        return True
    except Exception as e:
        print(f"  Download error: {e}")
        return False


def parse_ttml(ttml_path: Path) -> str:
    """Parse TTML and extract text."""
    raw = ttml_path.read_text(encoding="utf-8")
    words = re.findall(r'podcasts:unit="word"[^>]*>([^<]+)</span>', raw)
    return re.sub(r"\s+", " ", " ".join(w.strip() for w in words if w.strip()))


def get_missing_episodes(year: int = 2026) -> list:
    """Get episodes with transcripts that we don't have locally."""
    mapping = load_podcast_mapping()
    apple_to_id = mapping.get("apple_to_id", {})

    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    # Get cutoff date (start of year)
    cutoff = (datetime(year, 1, 1) - COCOA_EPOCH).total_seconds()

    cursor.execute("""
        SELECT
            e.ZTITLE as episode_title,
            p.ZTITLE as podcast_name,
            e.ZPUBDATE as pub_date,
            e.ZTRANSCRIPTIDENTIFIER as transcript_id
        FROM ZMTEPISODE e
        JOIN ZMTPODCAST p ON e.ZPODCAST = p.Z_PK
        WHERE e.ZTRANSCRIPTIDENTIFIER IS NOT NULL
        AND e.ZPUBDATE > ?
        ORDER BY e.ZPUBDATE DESC
    """, (cutoff,))

    missing = []
    for row in cursor.fetchall():
        episode_title, podcast_name, pub_date_cocoa, transcript_id = row

        # Get our podcast ID
        podcast_id = apple_to_id.get(podcast_name)
        if not podcast_id:
            continue

        pub_date = COCOA_EPOCH + timedelta(seconds=pub_date_cocoa)
        pub_date_str = pub_date.strftime("%Y-%m-%d")

        # Generate episode ID
        episode_id = f"{podcast_id}-{pub_date_str}-{hashlib.md5(episode_title.encode()).hexdigest()[:4]}"

        # Check if transcript exists
        transcript_path = TRANSCRIPTS_DIR / podcast_id / f"{episode_id}.txt"
        if transcript_path.exists():
            continue

        # Extract apple episode ID
        match = re.search(r'transcript_(\d+)\.ttml', transcript_id)
        if not match:
            continue

        missing.append({
            "podcast_id": podcast_id,
            "podcast_name": podcast_name,
            "episode_title": episode_title,
            "episode_id": episode_id,
            "pub_date": pub_date_str,
            "apple_episode_id": match.group(1),
            "transcript_id": transcript_id,
        })

    conn.close()
    return missing


def download_and_save(episode: dict, bearer_token: str, save_to_cache: bool = True) -> bool:
    """Download transcript and save to our format.

    Raises TokenExpiredError if the bearer token is expired.
    """
    apple_id = episode["apple_episode_id"]

    print(f"  Fetching {episode['episode_title'][:50]}...")

    # Fetch metadata (may raise TokenExpiredError)
    meta = fetch_transcript(apple_id, bearer_token)
    if not meta or not meta.get("ttml_url"):
        print(f"  ✗ No TTML URL")
        return False

    # Download TTML
    ttml_path = Path(f"/tmp/transcript_{apple_id}.ttml")
    if not download_ttml(meta["ttml_url"], ttml_path):
        return False

    # Parse text
    text = parse_ttml(ttml_path)
    if len(text.split()) < 100:
        print(f"  ✗ Too short ({len(text.split())} words)")
        return False

    # Save transcript
    transcript_path = TRANSCRIPTS_DIR / episode["podcast_id"] / f"{episode['episode_id']}.txt"
    transcript_path.parent.mkdir(parents=True, exist_ok=True)

    header = (
        f"{'='*60}\n"
        f"Episode: {episode['episode_id']}\n"
        f"Podcast: {episode['podcast_id']}\n"
        f"source: apple\n"
        f"original_title: {episode['episode_title']}\n"
        f"pub_date: {episode['pub_date']}\n"
        f"{'='*60}\n\n"
    )
    transcript_path.write_text(header + text + "\n")

    # Optionally cache TTML in Apple's cache dir
    if save_to_cache:
        cache_path = TTML_CACHE_PATH / episode["transcript_id"]
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            import shutil
            # Apple uses duplicated filename format
            final_name = f"transcript_{apple_id}.ttml-{apple_id}.ttml"
            final_path = cache_path.parent / final_name
            shutil.copy2(ttml_path, final_path)
        except:
            pass

    print(f"  ✓ {episode['episode_id']}")
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Download Apple Podcasts transcripts (pure Python)")
    parser.add_argument("--year", type=int, default=2026, help="Year filter")
    parser.add_argument("--max", type=int, default=0, help="Max downloads (0=unlimited)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded")
    args = parser.parse_args()

    # Load bearer token (auto-refreshes if expired)
    bearer = load_bearer_token(auto_refresh=True)
    if not bearer:
        print("✗ No bearer token available")
        print("  Try running: ./scripts/refresh_apple_token.sh")
        return 1

    exp = get_token_expiration(bearer)
    exp_str = exp.strftime("%Y-%m-%d") if exp else "unknown"
    print(f"✓ Bearer token loaded (expires: {exp_str})")

    # Get missing episodes
    missing = get_missing_episodes(args.year)
    if not missing:
        print("✓ All transcripts synced!")
        return 0

    print(f"\nFound {len(missing)} missing transcripts:")
    for ep in missing[:10]:
        print(f"  - [{ep['podcast_id']}] {ep['episode_title'][:40]}... ({ep['pub_date']})")
    if len(missing) > 10:
        print(f"  ... and {len(missing) - 10} more")

    if args.dry_run:
        return 0

    # Download
    print("\nDownloading...")
    success = 0
    failed = 0
    limit = args.max if args.max > 0 else len(missing)
    token_refreshed = False

    for ep in missing[:limit]:
        try:
            if download_and_save(ep, bearer):
                success += 1
            else:
                failed += 1
        except TokenExpiredError:
            if token_refreshed:
                # Already tried refreshing, give up
                print("  ✗ Token still invalid after refresh")
                failed += 1
                continue

            # Try to refresh token
            print("  ⚠ Token expired mid-download, refreshing...")
            new_token = refresh_bearer_token()
            if new_token:
                bearer = new_token
                token_refreshed = True
                # Retry this episode
                try:
                    if download_and_save(ep, bearer):
                        success += 1
                    else:
                        failed += 1
                except TokenExpiredError:
                    print("  ✗ Token still invalid after refresh")
                    failed += 1
            else:
                print("  ✗ Failed to refresh token")
                failed += 1

    print(f"\n✓ Downloaded: {success}")
    if failed:
        print(f"✗ Failed: {failed}")

    return 0


if __name__ == "__main__":
    exit(main())
