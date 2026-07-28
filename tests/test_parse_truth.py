"""Parsing of Truth Social WebSocket post payloads.

Shapes match the documented TruthSocialPost / TruthSocialMediaAttachment
interfaces at https://1322.io/docs.
"""

from __future__ import annotations

from client1322.platforms.truth import TruthPostEvent, parse_truth_event


def test_parse_simple_post():
    raw = {
        "platform": "truth",
        "username": "realDonaldTrump",
        "display_name": "Donald J. Trump",
        "user_avatar": "https://example.com/avatar.jpg",
        "user_following": 100,
        "user_followers": 9000000,
        "user_id": "107780257626128497",
        "key": "113000000000000001",
        "timestamp": "2026-07-28T12:00:00Z",
        "seen_at": "2026-07-28T12:00:00.150Z",
        "text": "Hello Truth Social",
        "media": [],
    }
    event = parse_truth_event(raw)
    assert isinstance(event, TruthPostEvent)
    assert event.username == "realDonaldTrump"
    assert event.key == "113000000000000001"
    assert event.is_quote is None
    assert event.media == []
    assert event.raw is raw


def test_parse_quote_with_nested_quote_and_authors():
    raw = {
        "platform": "truth",
        "username": "DanScavino",
        "display_name": "Dan Scavino",
        "user_avatar": "https://example.com/a.jpg",
        "user_following": 10,
        "user_followers": 500000,
        "user_id": "1",
        "key": "2",
        "timestamp": "2026-07-28T12:00:00Z",
        "seen_at": "2026-07-28T12:00:00.100Z",
        "text": "See this",
        "is_quote": True,
        "quoted": {
            "key": "3",
            "text": "original post",
            "url": "https://truthsocial.com/@x/posts/3",
            "author": {"id": "9", "username": "someone", "display_name": "Someone"},
            "quoted": {
                "key": "4",
                "text": "nested original",
                "url": "https://truthsocial.com/@y/posts/4",
                "author": {"id": "10", "username": "another", "display_name": "Another"},
            },
        },
        "media": [],
    }
    event = parse_truth_event(raw)
    assert event.is_quote is True
    assert event.quoted["key"] == "3"
    assert event.quoted["author"]["username"] == "someone"
    assert event.quoted["quoted"]["key"] == "4"
    assert event.quoted["quoted"]["author"]["username"] == "another"


def test_parse_retruth_with_original_author():
    raw = {
        "platform": "truth",
        "username": "someRetruther",
        "display_name": "Some Retruther",
        "user_avatar": "https://example.com/a.jpg",
        "user_following": 1,
        "user_followers": 1,
        "user_id": "5",
        "key": "6",
        "timestamp": "2026-07-28T12:00:00Z",
        "seen_at": "2026-07-28T12:00:00.050Z",
        "text": "original text",
        "is_retruth": True,
        "retruth_of_id": "7",
        "retruth_of": {"id": "7", "username": "originalAuthor", "display_name": "Original Author"},
        "media": [],
    }
    event = parse_truth_event(raw)
    assert event.is_retruth is True
    assert event.retruth_of_id == "7"
    assert event.retruth_of["username"] == "originalAuthor"


def test_parse_media_with_source_discriminator():
    raw = {
        "platform": "truth",
        "username": "user",
        "display_name": "User",
        "user_avatar": "",
        "user_following": 0,
        "user_followers": 0,
        "user_id": "1",
        "key": "1",
        "timestamp": "2026-07-28T12:00:00Z",
        "seen_at": "2026-07-28T12:00:00Z",
        "text": "",
        "media": [
            {
                "kind": "image",
                "url": "https://example.com/own.jpg",
                "poster_url": "",
                "created_at": "2026-07-28T12:00:00Z",
                "source": "own",
            },
            {
                "kind": "video",
                "url": "https://example.com/quoted.mp4",
                "poster_url": "https://example.com/poster.jpg",
                "created_at": "2026-07-28T12:00:00Z",
                "source": "quoted",
            },
        ],
    }
    event = parse_truth_event(raw)
    assert len(event.media) == 2
    assert event.media[0]["source"] == "own"
    assert event.media[1]["source"] == "quoted"


def test_parse_defaults_missing_optional_fields():
    raw = {
        "platform": "truth",
        "username": "user",
        "display_name": "User",
        "user_avatar": "",
        "user_following": 0,
        "user_followers": 0,
        "user_id": "1",
        "key": "1",
        "timestamp": "2026-07-28T12:00:00Z",
        "seen_at": "2026-07-28T12:00:00Z",
        "text": "no media key at all",
    }
    event = parse_truth_event(raw)
    assert event.media == []
    assert event.card is None
    assert event.quoted is None
