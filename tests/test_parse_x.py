"""Parsing of X/Twitter WebSocket event frames into typed dataclasses.

Fixture payloads are hand-built to match the documented TwitterMiniTweet /
TwitterTweet / TwitterUser shapes from https://1322.io/docs -- they are
illustrative test data, not measured/live results.
"""

from __future__ import annotations

import pytest

from client1322.exceptions import UnknownEventError
from client1322.platforms.x import (
    DeletedTweet,
    FollowingUpdate,
    MiniTweetUpdate,
    ProfilePinnedUpdate,
    ProfileUnpinnedUpdate,
    ProfileUpdate,
    TweetFull,
    TweetUpdate,
    TweetUpdateExpanded,
    parse_x_event,
    tweet_of,
)

MINI_USER = {"id": "44196397", "handle": "elonmusk", "name": "Elon Musk", "avatar": None}

MINI_TWEET = {
    "id": "1234567890123456789",
    "type": "TWEET",
    "created_at": 1700000000000,
    "author": MINI_USER,
    "subtweet": None,
    "reply": None,
    "quoted": None,
    "body": {"text": "hello world", "urls": [], "mentions": []},
    "media": {"images": [], "videos": [], "thumbnails": [], "proxied": None},
}

FULL_USER = {
    "id": "44196397",
    "handle": "elonmusk",
    "private": False,
    "verified": True,
    "sensitive": False,
    "restricted": False,
    "joined_at": 1234567890000,
    "profile": {
        "name": "Elon Musk",
        "location": None,
        "avatar": None,
        "banner": None,
        "pinned": [],
        "url": None,
        "description": {"text": "", "urls": []},
    },
    "metrics": {"likes": 1, "media": 2, "tweets": 3, "friends": 4, "followers": 5, "following": 6},
}

FULL_TWEET = {
    "id": "1234567890123456789",
    "type": "TWEET",
    "created_at": 1700000000000,
    "author": FULL_USER,
    "subtweet": None,
    "reply": None,
    "quoted": None,
    "body": {"text": "hello world, expanded", "urls": [], "mentions": [], "components": []},
    "media": {"images": [], "videos": [], "thumbnails": [], "proxied": None},
    "grok": None,
    "card": None,
    "poll": None,
    "article": None,
    "metrics": {"likes": 10, "quotes": 1, "replies": 2, "retweets": 3, "advanced": None},
}


def test_parse_mini_tweet_update():
    raw = {"id": "evt1", "type": "tweet.mini.update", "source": "1322", "tweet": MINI_TWEET}
    event = parse_x_event(raw)
    assert isinstance(event, MiniTweetUpdate)
    assert event.type == "tweet.mini.update"
    assert event.tweet["id"] == "1234567890123456789"
    assert event.tweet["author"]["handle"] == "elonmusk"
    assert event.raw is raw
    assert tweet_of(event) is event.tweet


def test_parse_tweet_update():
    raw = {"id": "evt2", "type": "tweet.update", "source": "1322", "tweet": FULL_TWEET}
    event = parse_x_event(raw)
    assert isinstance(event, TweetUpdate)
    assert event.tweet["metrics"]["likes"] == 10


def test_parse_tweet_update_expanded():
    raw = {"id": "evt3", "type": "tweet.update.expanded", "source": "1322", "tweet": FULL_TWEET}
    event = parse_x_event(raw)
    assert isinstance(event, TweetUpdateExpanded)


def test_parse_tweet_full():
    raw = {"id": "evt4", "type": "tweet.full", "source": "1322", "tweet": FULL_TWEET}
    event = parse_x_event(raw)
    assert isinstance(event, TweetFull)


def test_parse_deleted_tweet():
    raw = {
        "id": "evt5",
        "type": "tweet.deleted",
        "source": "1322",
        "tweet": FULL_TWEET,
        "deleted_at": 1700000005000,
    }
    event = parse_x_event(raw)
    assert isinstance(event, DeletedTweet)
    assert event.deleted_at == 1700000005000
    assert tweet_of(event) is event.tweet


def test_parse_profile_update():
    before = dict(FULL_USER, verified=False)
    raw = {"id": "evt6", "type": "profile.update", "source": "1322", "user": FULL_USER, "before": before}
    event = parse_x_event(raw)
    assert isinstance(event, ProfileUpdate)
    assert event.user["verified"] is True
    assert event.before["verified"] is False


def test_parse_following_update():
    raw = {
        "id": "evt7",
        "type": "following.update",
        "source": "1322",
        "change": "followed",
        "following": FULL_USER,
        "user": FULL_USER,
    }
    event = parse_x_event(raw)
    assert isinstance(event, FollowingUpdate)
    assert event.change == "followed"


def test_parse_profile_pinned_update():
    raw = {
        "id": "evt8",
        "type": "profile.pinned.update",
        "source": "1322",
        "user": FULL_USER,
        "pinned": [FULL_TWEET],
    }
    event = parse_x_event(raw)
    assert isinstance(event, ProfilePinnedUpdate)
    assert len(event.pinned) == 1


def test_parse_profile_unpinned_update():
    raw = {
        "id": "evt9",
        "type": "profile.unpinned.update",
        "source": "1322",
        "user": FULL_USER,
        "pinned": [],
    }
    event = parse_x_event(raw)
    assert isinstance(event, ProfileUnpinnedUpdate)
    assert event.pinned == []


def test_unknown_event_type_raises():
    with pytest.raises(UnknownEventError):
        parse_x_event({"id": "evt10", "type": "tweet.something.new", "source": "1322"})


def test_tweet_of_returns_none_for_non_tweet_events():
    raw = {
        "id": "evt11",
        "type": "profile.update",
        "source": "1322",
        "user": FULL_USER,
        "before": FULL_USER,
    }
    event = parse_x_event(raw)
    assert tweet_of(event) is None
