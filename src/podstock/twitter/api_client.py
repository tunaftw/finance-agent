"""Twitter API client using twitterapi.io.

This module provides a client for fetching tweets from Twitter users
via the twitterapi.io service.
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any

import requests

from podstock.twitter.exceptions import TwitterCollectionError, TwitterRateLimitError
from podstock.twitter.models import Tweet


class TwitterAPIClient:
    """Client for twitterapi.io API.

    Fetches tweets from Twitter users using the twitterapi.io service.
    Handles pagination, rate limits, and response mapping.

    Attributes:
        api_key: API key for twitterapi.io.
        base_url: Base URL for the API.
        timeout: Request timeout in seconds.

    Example:
        >>> client = TwitterAPIClient(api_key="your_key")
        >>> tweets = client.collect_user_tweets("vildkatten", max_tweets=100)
        >>> len(tweets)
        100
    """

    DEFAULT_BASE_URL = "https://api.twitterapi.io"
    DEFAULT_TIMEOUT = 30

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the Twitter API client.

        Args:
            api_key: API key for twitterapi.io. If not provided,
                reads from TWITTER_API_KEY environment variable.
            base_url: Base URL for the API.
            timeout: Request timeout in seconds.

        Raises:
            ValueError: If no API key is provided or found in environment.
        """
        self.api_key = api_key or os.getenv("TWITTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Twitter API key required. Set TWITTER_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"X-API-Key": self.api_key})

    def get_user_tweets(
        self,
        username: str,
        cursor: str = "",
        include_replies: bool = False,
    ) -> tuple[list[Tweet], str | None, bool]:
        """Fetch a page of tweets from a user.

        Args:
            username: Twitter username (without @).
            cursor: Pagination cursor (empty for first page).
            include_replies: Whether to include replies.

        Returns:
            Tuple of (tweets, next_cursor, has_more).

        Raises:
            TwitterRateLimitError: If rate limited.
            TwitterCollectionError: If request fails.
        """
        url = f"{self.base_url}/twitter/user/last_tweets"
        params: dict[str, Any] = {
            "userName": username.lstrip("@"),
            "includeReplies": str(include_replies).lower(),
        }
        if cursor:
            params["cursor"] = cursor

        try:
            response = self._session.get(url, params=params, timeout=self.timeout)
        except requests.RequestException as e:
            raise TwitterCollectionError(f"Request failed: {e}") from e

        if response.status_code == 429:
            raise TwitterRateLimitError("Rate limit exceeded")

        if response.status_code != 200:
            raise TwitterCollectionError(
                f"API error: {response.status_code} - {response.text}"
            )

        try:
            data = response.json()
        except ValueError as e:
            raise TwitterCollectionError(f"Invalid JSON response: {e}") from e

        if data.get("status") != "success":
            raise TwitterCollectionError(
                f"API returned error: {data.get('msg', data.get('message', 'Unknown error'))}"
            )

        # Response structure: { status, code, msg, data: { tweets: [...] }, has_next_page, next_cursor }
        response_data = data.get("data", {})
        tweets = [
            self._parse_tweet(tweet_data, username)
            for tweet_data in response_data.get("tweets", [])
        ]

        # Pagination fields are at root level, not inside data
        has_more = data.get("has_next_page", False)
        next_cursor = data.get("next_cursor") if has_more else None

        return tweets, next_cursor, has_more

    def collect_user_tweets(
        self,
        username: str,
        max_tweets: int = 500,
        since_id: str | None = None,
        include_replies: bool = False,
    ) -> list[Tweet]:
        """Collect tweets from a user with pagination.

        Fetches up to max_tweets from the user's timeline.
        Stops early if since_id is reached.

        Args:
            username: Twitter username (without @).
            max_tweets: Maximum number of tweets to collect.
            since_id: Stop collecting when reaching this tweet ID.
            include_replies: Whether to include replies.

        Returns:
            List of tweets (newest first).

        Raises:
            TwitterRateLimitError: If rate limited.
            TwitterCollectionError: If collection fails.

        Example:
            >>> tweets = client.collect_user_tweets("vildkatten", max_tweets=200)
            >>> print(f"Collected {len(tweets)} tweets")
        """
        all_tweets: list[Tweet] = []
        cursor = ""

        while len(all_tweets) < max_tweets:
            tweets, next_cursor, has_more = self.get_user_tweets(
                username, cursor, include_replies
            )

            for tweet in tweets:
                # Stop if we've reached a tweet we already have
                if since_id and tweet.id == since_id:
                    return all_tweets

                all_tweets.append(tweet)

                if len(all_tweets) >= max_tweets:
                    return all_tweets

            if not has_more or not next_cursor:
                break

            cursor = next_cursor
            # Rate limit: wait 5 seconds between pages
            time.sleep(5)

        return all_tweets

    def _parse_tweet(self, data: dict[str, Any], source_id: str) -> Tweet:
        """Parse API response into Tweet model.

        Args:
            data: Raw tweet data from API.
            source_id: Source identifier (username).

        Returns:
            Parsed Tweet object.
        """
        # Parse datetime - Twitter format: "Thu Dec 25 17:04:33 +0000 2025"
        created_at_str = data.get("createdAt", "")
        try:
            # Parse Twitter's date format (includes timezone)
            posted_at = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
        except ValueError:
            from datetime import timezone
            posted_at = datetime.now(timezone.utc)

        # Extract author info
        author = data.get("author", {})

        # Extract media info
        media = data.get("media", []) or []
        media_urls = [m.get("url", "") for m in media if m.get("url")]

        # Extract external URLs
        urls = data.get("urls", []) or []
        external_urls = [u.get("expandedUrl", "") for u in urls if u.get("expandedUrl")]

        tweet = Tweet(
            id=str(data.get("id", "")),
            source_id=source_id.lower(),
            author_handle=author.get("userName", source_id),
            author_display_name=author.get("name"),
            text=data.get("text", ""),
            is_retweet=data.get("isRetweet", False),
            is_reply=data.get("isReply", False),
            is_quote=data.get("isQuote", False),
            quoted_tweet_id=data.get("quotedTweetId"),
            reply_to_tweet_id=data.get("inReplyToTweetId"),
            posted_at=posted_at,
            likes=data.get("likeCount"),
            retweets=data.get("retweetCount"),
            replies=data.get("replyCount"),
            views=data.get("viewCount"),
            bookmarks=data.get("bookmarkCount"),
            has_media=len(media_urls) > 0,
            media_urls=media_urls,
            has_links=len(external_urls) > 0,
            external_urls=external_urls,
        )

        # Extract entities (tickers, mentions, hashtags)
        tweet.extract_entities()

        return tweet


def get_twitter_client(api_key: str | None = None) -> TwitterAPIClient:
    """Create a Twitter API client.

    Convenience function to create a client with default settings.

    Args:
        api_key: API key (optional, uses env var if not provided).

    Returns:
        Configured TwitterAPIClient.

    Example:
        >>> client = get_twitter_client()
        >>> tweets = client.collect_user_tweets("vildkatten")
    """
    return TwitterAPIClient(api_key=api_key)
