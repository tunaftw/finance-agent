"""Tests for podstock.twitter module."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from podstock.twitter.models import (
    Tweet,
    TwitterSource,
    TwitterCollectionState,
    TweetAnalysis,
    TweetActionType,
    StockMention,
    extract_tickers,
    extract_mentions,
    extract_hashtags,
)
from podstock.twitter.exceptions import (
    TwitterError,
    TwitterStateError,
    TwitterStorageError,
    TwitterSourceNotFoundError,
)
from podstock.twitter.state import TwitterState
from podstock.twitter.manager import (
    add_twitter_source,
    remove_twitter_source,
    get_twitter_source,
    list_twitter_sources,
    load_twitter_sources,
    save_twitter_sources,
)
from podstock.twitter.storage import TweetStorage
from podstock.twitter.index import TwitterIndexBuilder, build_twitter_indexes
from podstock.twitter.search import TweetSearch


# =============================================================================
# Model Tests
# =============================================================================


class TestTwitterSource:
    """Tests for TwitterSource model."""

    def test_create_source_basic(self) -> None:
        """Should create source with minimal fields."""
        source = TwitterSource(
            id="vildkatten",
            handle="vildkatten",
        )
        assert source.id == "vildkatten"
        assert source.handle == "vildkatten"
        assert source.active is True

    def test_create_source_with_all_fields(self) -> None:
        """Should create source with all fields."""
        source = TwitterSource(
            id="vildkatten",
            handle="vildkatten",
            display_name="Per Ekström",
            category="analyst",
            description="Börsdata analyst",
            language="sv",
            active=True,
        )
        assert source.display_name == "Per Ekström"
        assert source.category == "analyst"

    def test_handle_normalization(self) -> None:
        """Should normalize handle with @ prefix."""
        source = TwitterSource(id="test", handle="@vildkatten")
        assert source.handle == "vildkatten"

    def test_handle_normalized_to_lowercase(self) -> None:
        """Should normalize handle to lowercase."""
        source = TwitterSource(id="test", handle="VildKatten")
        assert source.handle == "vildkatten"


class TestTweet:
    """Tests for Tweet model."""

    def test_create_tweet_basic(self) -> None:
        """Should create tweet with required fields."""
        tweet = Tweet(
            id="123456789",
            source_id="vildkatten",
            author_handle="vildkatten",
            text="Hello world",
            posted_at=datetime.now(),
        )
        assert tweet.id == "123456789"
        assert tweet.source_id == "vildkatten"

    def test_tweet_with_engagement(self) -> None:
        """Should store engagement metrics."""
        tweet = Tweet(
            id="123",
            source_id="test",
            author_handle="test",
            text="Test",
            posted_at=datetime.now(),
            likes=100,
            retweets=50,
            views=1000,
        )
        assert tweet.likes == 100
        assert tweet.retweets == 50
        assert tweet.views == 1000

    def test_extract_entities(self) -> None:
        """Should extract tickers, mentions, and hashtags."""
        tweet = Tweet(
            id="123",
            source_id="test",
            author_handle="test",
            text="Köper $TSLA och $EVO. @vildkatten har rätt! #aktier",
            posted_at=datetime.now(),
        )
        tweet.extract_entities()

        assert "TSLA" in tweet.mentioned_tickers
        assert "EVO" in tweet.mentioned_tickers
        assert "vildkatten" in tweet.mentioned_users
        assert "aktier" in tweet.hashtags


class TestExtractTickers:
    """Tests for extract_tickers function."""

    def test_extract_single_ticker(self) -> None:
        """Should extract single ticker."""
        tickers = extract_tickers("Köper $TSLA idag")
        assert tickers == ["TSLA"]

    def test_extract_multiple_tickers(self) -> None:
        """Should extract multiple tickers."""
        tickers = extract_tickers("$TSLA och $EVO ser bra ut")
        assert set(tickers) == {"TSLA", "EVO"}

    def test_extract_lowercase_normalized(self) -> None:
        """Should normalize to uppercase."""
        tickers = extract_tickers("$tsla is up")
        assert tickers == ["TSLA"]

    def test_extract_no_tickers(self) -> None:
        """Should return empty for no tickers."""
        tickers = extract_tickers("No stock mentions here")
        assert tickers == []

    def test_ignore_currency(self) -> None:
        """Should ignore common currency-like patterns."""
        tickers = extract_tickers("I have $100 in my account")
        assert tickers == []


class TestExtractMentions:
    """Tests for extract_mentions function."""

    def test_extract_single_mention(self) -> None:
        """Should extract single @mention."""
        mentions = extract_mentions("Thanks @vildkatten!")
        assert mentions == ["vildkatten"]

    def test_extract_multiple_mentions(self) -> None:
        """Should extract multiple mentions."""
        mentions = extract_mentions("@user1 and @user2 are cool")
        assert set(mentions) == {"user1", "user2"}


class TestExtractHashtags:
    """Tests for extract_hashtags function."""

    def test_extract_single_hashtag(self) -> None:
        """Should extract single hashtag."""
        hashtags = extract_hashtags("Check this #aktier")
        assert hashtags == ["aktier"]

    def test_extract_multiple_hashtags(self) -> None:
        """Should extract multiple hashtags."""
        hashtags = extract_hashtags("#stocks #trading #aktier")
        assert set(hashtags) == {"stocks", "trading", "aktier"}


class TestTwitterCollectionState:
    """Tests for TwitterCollectionState model."""

    def test_create_default_state(self) -> None:
        """Should create state with defaults."""
        state = TwitterCollectionState(source_id="vildkatten")
        assert state.source_id == "vildkatten"
        assert state.tweet_count == 0
        assert state.collection_complete is False

    def test_state_with_progress(self) -> None:
        """Should track collection progress."""
        state = TwitterCollectionState(
            source_id="vildkatten",
            tweet_count=500,
            last_tweet_id="12345",
            oldest_tweet_id="00001",
            collection_complete=False,
        )
        assert state.tweet_count == 500
        assert state.last_tweet_id == "12345"


# =============================================================================
# State Tests
# =============================================================================


class TestTwitterState:
    """Tests for TwitterState class."""

    def test_empty_state(self, tmp_path: Path) -> None:
        """Should start with empty state."""
        state_file = tmp_path / "twitter_state.json"
        state = TwitterState(state_file)

        assert state.get_all_states() == {}

    def test_get_state_unknown_returns_none(self, tmp_path: Path) -> None:
        """Should return None for unknown source."""
        state_file = tmp_path / "twitter_state.json"
        state = TwitterState(state_file)

        s = state.get_state("unknown")
        assert s is None

    def test_mark_collected(self, tmp_path: Path) -> None:
        """Should mark collection progress."""
        state_file = tmp_path / "twitter_state.json"
        state = TwitterState(state_file)

        state.mark_collected("vildkatten", last_tweet_id="12345", tweet_count=100)

        s = state.get_state("vildkatten")
        assert s.tweet_count == 100
        assert s.last_tweet_id == "12345"
        assert s.last_collected_at is not None

    def test_mark_collected_persists(self, tmp_path: Path) -> None:
        """Should persist state to file."""
        state_file = tmp_path / "twitter_state.json"
        state = TwitterState(state_file)

        state.mark_collected("vildkatten", last_tweet_id="99999", tweet_count=50)

        # Load fresh state
        new_state = TwitterState(state_file)
        s = new_state.get_state("vildkatten")
        assert s.tweet_count == 50

    def test_get_pending_collection(self, tmp_path: Path) -> None:
        """Should return sources that have never been collected."""
        state_file = tmp_path / "twitter_state.json"
        state = TwitterState(state_file)

        # Source 1: never collected (no last_collected_at)
        state._data.sources["src1"] = TwitterCollectionState(source_id="src1")
        # Source 2: collected (has last_collected_at)
        state._data.sources["src2"] = TwitterCollectionState(
            source_id="src2",
            last_collected_at=datetime.now(),
        )

        pending = state.get_pending_collection()
        # Both should be in pending - get_pending_collection returns all sources
        assert "src1" in pending

    def test_load_invalid_json_raises_error(self, tmp_path: Path) -> None:
        """Should raise TwitterStateError for invalid JSON."""
        state_file = tmp_path / "twitter_state.json"
        state_file.write_text("not valid json")

        with pytest.raises(TwitterStateError, match="Invalid JSON"):
            TwitterState(state_file)


# =============================================================================
# Manager Tests
# =============================================================================


class TestTwitterManager:
    """Tests for twitter manager functions."""

    def test_add_source(self, tmp_path: Path) -> None:
        """Should add new source."""
        sources_file = tmp_path / "twitter_sources.json"

        source = add_twitter_source(
            "vildkatten",
            sources_file,
            category="analyst",
        )

        assert source.id == "vildkatten"
        assert source.handle == "vildkatten"

    def test_add_source_duplicate_raises(self, tmp_path: Path) -> None:
        """Should raise for duplicate source."""
        sources_file = tmp_path / "twitter_sources.json"

        add_twitter_source("vildkatten", sources_file)

        with pytest.raises(TwitterError, match="already exists"):
            add_twitter_source("vildkatten", sources_file)

    def test_list_sources(self, tmp_path: Path) -> None:
        """Should list all sources."""
        sources_file = tmp_path / "twitter_sources.json"

        add_twitter_source("user1", sources_file)
        add_twitter_source("user2", sources_file)

        sources = list_twitter_sources(sources_file)
        assert len(sources) == 2

    def test_get_source(self, tmp_path: Path) -> None:
        """Should get specific source."""
        sources_file = tmp_path / "twitter_sources.json"

        add_twitter_source("vildkatten", sources_file, category="analyst")

        source = get_twitter_source("vildkatten", sources_file)
        assert source is not None
        assert source.category == "analyst"

    def test_get_source_not_found_raises(self, tmp_path: Path) -> None:
        """Should raise for unknown source."""
        sources_file = tmp_path / "twitter_sources.json"

        with pytest.raises(TwitterSourceNotFoundError):
            get_twitter_source("unknown", sources_file)

    def test_remove_source(self, tmp_path: Path) -> None:
        """Should remove existing source."""
        sources_file = tmp_path / "twitter_sources.json"

        add_twitter_source("vildkatten", sources_file)
        remove_twitter_source("vildkatten", sources_file)

        sources = list_twitter_sources(sources_file)
        assert len(sources) == 0

    def test_remove_source_not_found_raises(self, tmp_path: Path) -> None:
        """Should raise for unknown source."""
        sources_file = tmp_path / "twitter_sources.json"

        with pytest.raises(TwitterSourceNotFoundError):
            remove_twitter_source("unknown", sources_file)


# =============================================================================
# Storage Tests
# =============================================================================


class TestTweetStorage:
    """Tests for TweetStorage class."""

    def _make_tweet(self, tweet_id: str, source_id: str = "test") -> Tweet:
        """Create a test tweet."""
        return Tweet(
            id=tweet_id,
            source_id=source_id,
            author_handle=source_id,
            text=f"Tweet {tweet_id}",
            posted_at=datetime.now(),
        )

    def test_save_and_load_tweet(self, tmp_path: Path) -> None:
        """Should save and load tweet."""
        storage = TweetStorage(tmp_path)
        tweet = self._make_tweet("123", "vildkatten")

        storage.save_tweet(tweet)
        loaded = list(storage.load_tweets("vildkatten"))

        assert len(loaded) == 1
        assert loaded[0].id == "123"

    def test_save_multiple_tweets(self, tmp_path: Path) -> None:
        """Should save multiple tweets."""
        storage = TweetStorage(tmp_path)
        tweets = [self._make_tweet(str(i), "test") for i in range(5)]

        saved = storage.save_tweets(tweets)
        loaded = list(storage.load_tweets("test"))

        assert saved == 5
        assert len(loaded) == 5

    def test_load_with_deduplication(self, tmp_path: Path) -> None:
        """Should deduplicate tweets on load."""
        storage = TweetStorage(tmp_path)
        tweet = self._make_tweet("123", "test")

        # Save same tweet twice
        storage.save_tweet(tweet)
        storage.save_tweet(tweet)

        loaded = list(storage.load_tweets("test", deduplicate=True))
        assert len(loaded) == 1

    def test_load_without_deduplication(self, tmp_path: Path) -> None:
        """Should return duplicates when dedup disabled."""
        storage = TweetStorage(tmp_path)
        tweet = self._make_tweet("123", "test")

        storage.save_tweet(tweet)
        storage.save_tweet(tweet)

        loaded = list(storage.load_tweets("test", deduplicate=False))
        assert len(loaded) == 2

    def test_get_tweet_count(self, tmp_path: Path) -> None:
        """Should count unique tweets."""
        storage = TweetStorage(tmp_path)

        for i in range(10):
            storage.save_tweet(self._make_tweet(str(i), "test"))

        assert storage.get_tweet_count("test") == 10

    def test_get_tweet_ids(self, tmp_path: Path) -> None:
        """Should return all tweet IDs."""
        storage = TweetStorage(tmp_path)

        for i in range(5):
            storage.save_tweet(self._make_tweet(str(i), "test"))

        ids = storage.get_tweet_ids("test")
        assert ids == {"0", "1", "2", "3", "4"}

    def test_load_all_tweets(self, tmp_path: Path) -> None:
        """Should load from all sources."""
        storage = TweetStorage(tmp_path)

        storage.save_tweet(self._make_tweet("1", "user1"))
        storage.save_tweet(self._make_tweet("2", "user2"))

        all_tweets = list(storage.load_all_tweets())
        assert len(all_tweets) == 2

    def test_compact_storage(self, tmp_path: Path) -> None:
        """Should remove duplicates in storage."""
        storage = TweetStorage(tmp_path)
        tweet = self._make_tweet("123", "test")

        # Create duplicates
        storage.save_tweet(tweet)
        storage.save_tweet(tweet)
        storage.save_tweet(tweet)

        removed = storage.compact_storage("test")
        assert removed == 2

        # Verify only one remains
        loaded = list(storage.load_tweets("test", deduplicate=False))
        assert len(loaded) == 1

    def test_get_sources_with_tweets(self, tmp_path: Path) -> None:
        """Should list sources that have tweets."""
        storage = TweetStorage(tmp_path)

        storage.save_tweet(self._make_tweet("1", "user1"))
        storage.save_tweet(self._make_tweet("2", "user2"))

        sources = storage.get_sources_with_tweets()
        assert set(sources) == {"user1", "user2"}


# =============================================================================
# Index Tests
# =============================================================================


class TestTwitterIndexBuilder:
    """Tests for TwitterIndexBuilder class."""

    def _create_test_tweets(self, storage: TweetStorage) -> None:
        """Create test tweets for indexing."""
        tweets = [
            Tweet(
                id="1",
                source_id="user1",
                author_handle="user1",
                text="Buying $TSLA today",
                posted_at=datetime(2024, 1, 15, 10, 0),
                mentioned_tickers=["TSLA"],
            ),
            Tweet(
                id="2",
                source_id="user1",
                author_handle="user1",
                text="$EVO looks good",
                posted_at=datetime(2024, 1, 16, 10, 0),
                mentioned_tickers=["EVO"],
            ),
            Tweet(
                id="3",
                source_id="user2",
                author_handle="user2",
                text="$TSLA is overvalued",
                posted_at=datetime(2024, 1, 17, 10, 0),
                mentioned_tickers=["TSLA"],
            ),
        ]
        storage.save_tweets(tweets)

    def test_build_ticker_index(self, tmp_path: Path) -> None:
        """Should index tweets by ticker."""
        storage = TweetStorage(tmp_path)
        self._create_test_tweets(storage)

        builder = TwitterIndexBuilder(tmp_path)
        index = builder.build_ticker_index()

        assert "TSLA" in index
        assert len(index["TSLA"]) == 2
        assert "EVO" in index
        assert len(index["EVO"]) == 1

    def test_build_user_index(self, tmp_path: Path) -> None:
        """Should index tweets by user."""
        storage = TweetStorage(tmp_path)
        self._create_test_tweets(storage)

        builder = TwitterIndexBuilder(tmp_path)
        index = builder.build_user_index()

        assert "user1" in index
        assert index["user1"]["tweet_count"] == 2
        assert "user2" in index
        assert index["user2"]["tweet_count"] == 1

    def test_build_date_index(self, tmp_path: Path) -> None:
        """Should index tweets by date."""
        storage = TweetStorage(tmp_path)
        self._create_test_tweets(storage)

        builder = TwitterIndexBuilder(tmp_path)
        index = builder.build_date_index()

        assert "2024-01-15" in index
        assert "2024-01-16" in index
        assert "2024-01-17" in index

    def test_build_all_indexes(self, tmp_path: Path) -> None:
        """Should build and save all indexes."""
        storage = TweetStorage(tmp_path)
        self._create_test_tweets(storage)

        builder = TwitterIndexBuilder(tmp_path)
        stats = builder.build_all()

        assert stats["tweet_count"] == 3
        assert stats["source_count"] == 2
        assert stats["unique_tickers"] == 2

        # Verify files created
        index_dir = tmp_path / "twitter" / "index"
        assert (index_dir / "by_ticker.json").exists()
        assert (index_dir / "by_user.json").exists()
        assert (index_dir / "by_date.json").exists()
        assert (index_dir / "index.json").exists()


# =============================================================================
# Search Tests
# =============================================================================


class TestTweetSearch:
    """Tests for TweetSearch class."""

    @pytest.fixture
    def search_with_data(self, tmp_path: Path) -> TweetSearch:
        """Create search instance with test data."""
        storage = TweetStorage(tmp_path)

        # Create test tweets
        tweets = [
            Tweet(
                id="1",
                source_id="analyst1",
                author_handle="analyst1",
                text="Köper $TSLA",
                posted_at=datetime.now() - timedelta(days=5),
                mentioned_tickers=["TSLA"],
            ),
            Tweet(
                id="2",
                source_id="analyst1",
                author_handle="analyst1",
                text="$EVO ser bra ut",
                posted_at=datetime.now() - timedelta(days=3),
                mentioned_tickers=["EVO"],
            ),
            Tweet(
                id="3",
                source_id="analyst2",
                author_handle="analyst2",
                text="$TSLA är övervärderad",
                posted_at=datetime.now() - timedelta(days=1),
                mentioned_tickers=["TSLA"],
            ),
        ]
        storage.save_tweets(tweets)

        # Build indexes
        builder = TwitterIndexBuilder(tmp_path)
        builder.build_all()

        return TweetSearch(tmp_path)

    def test_search_ticker(self, search_with_data: TweetSearch) -> None:
        """Should find tweets by ticker."""
        results = search_with_data.search_ticker("TSLA")
        assert len(results) == 2

    def test_search_ticker_with_dollar(self, search_with_data: TweetSearch) -> None:
        """Should handle $ prefix."""
        results = search_with_data.search_ticker("$TSLA")
        assert len(results) == 2

    def test_search_ticker_with_limit(self, search_with_data: TweetSearch) -> None:
        """Should respect limit."""
        results = search_with_data.search_ticker("TSLA", limit=1)
        assert len(results) == 1

    def test_search_user(self, search_with_data: TweetSearch) -> None:
        """Should find tweets by user."""
        results = search_with_data.search_user("analyst1")
        assert len(results) == 2

    def test_get_top_tickers(self, search_with_data: TweetSearch) -> None:
        """Should rank tickers by frequency."""
        top = search_with_data.get_top_tickers(10)
        assert len(top) == 2
        assert top[0]["ticker"] == "TSLA"
        assert top[0]["mention_count"] == 2

    def test_get_top_sources(self, search_with_data: TweetSearch) -> None:
        """Should rank sources by tweet count."""
        top = search_with_data.get_top_sources(10)
        assert len(top) == 2
        assert top[0]["source_id"] == "analyst1"
        assert top[0]["tweet_count"] == 2

    def test_get_stats(self, search_with_data: TweetSearch) -> None:
        """Should return overall statistics."""
        stats = search_with_data.get_stats()
        assert stats["tweet_count"] == 3
        assert stats["source_count"] == 2

    def test_has_data(self, search_with_data: TweetSearch) -> None:
        """Should detect when data exists."""
        assert search_with_data.has_data() is True

    def test_empty_search(self, tmp_path: Path) -> None:
        """Should handle empty indexes gracefully."""
        search = TweetSearch(tmp_path)
        assert search.has_data() is False
        assert search.search_ticker("TSLA") == []
