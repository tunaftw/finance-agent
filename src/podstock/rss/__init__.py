"""RSS module for PodStock.

This module provides:
- RSS feed parsing
- Audio file downloading
- Podcast management (CRUD)
"""

from __future__ import annotations

from podstock.rss.downloader import download_episode, verify_download
from podstock.rss.manager import (
    add_podcast,
    fetch_podcast_info,
    get_active_podcasts,
    get_podcast,
    load_podcasts,
    remove_podcast,
    save_podcasts,
    update_podcast,
)
from podstock.rss.parser import (
    fetch_feed,
    get_all_episodes,
    get_latest_episodes,
    parse_episode,
    validate_rss_url,
)

__all__ = [
    # Parser
    "fetch_feed",
    "get_all_episodes",
    "get_latest_episodes",
    "parse_episode",
    "validate_rss_url",
    # Downloader
    "download_episode",
    "verify_download",
    # Manager
    "add_podcast",
    "fetch_podcast_info",
    "get_active_podcasts",
    "get_podcast",
    "load_podcasts",
    "remove_podcast",
    "save_podcasts",
    "update_podcast",
]
