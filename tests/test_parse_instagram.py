"""Parsing of Instagram WebSocket post payloads.

Shapes match the documented InstagramPost / InstagramMediaAttachment
interfaces at https://1322.io/docs.
"""

from __future__ import annotations

from client1322.platforms.instagram import InstagramPostEvent, parse_instagram_event


def test_parse_basic_post():
    raw = {
        "platform": "instagram",
        "username": "natgeo",
        "display_name": "National Geographic",
        "user_avatar": "https://example.com/a.jpg",
        "user_followers": 200000000,
        "user_id": "1",
        "key": "post123",
        "timestamp": "2026-07-28T12:00:00Z",
        "seen_at": "2026-07-28T12:00:00.200Z",
        "text": "A stunning view",
        "post_type": "post",
        "media_count": 1,
        "hashtags": ["nature"],
        "mentions": [],
        "media": [
            {
                "kind": "image",
                "kind_v2": "image",
                "media_role": "image",
                "media_index": 0,
                "url": "https://example.com/photo.jpg",
                "width": 1080,
                "height": 1080,
                "created_at": "2026-07-28T12:00:00Z",
            }
        ],
    }
    event = parse_instagram_event(raw)
    assert isinstance(event, InstagramPostEvent)
    assert event.post_type == "post"
    assert event.media[0]["media_role"] == "image"
    assert event.hashtags == ["nature"]


def test_parse_collab_reel_with_video_cover_pair():
    raw = {
        "platform": "instagram",
        "username": "brandA",
        "display_name": "Brand A",
        "user_avatar": "",
        "user_followers": 5000,
        "user_id": "2",
        "key": "reel456",
        "timestamp": "2026-07-28T12:00:00Z",
        "seen_at": "2026-07-28T12:00:00Z",
        "text": "collab reel",
        "post_type": "reel",
        "is_collab": True,
        "collab_with": ["brandB"],
        "is_pinned": False,
        "is_paid_partnership": True,
        "mentions": ["brandB"],
        "media": [
            {
                "kind": "video",
                "kind_v2": "video",
                "media_role": "video",
                "media_index": 0,
                "video_index": 0,
                "cover_media_index": 1,
                "cover_url": "https://example.com/cover.jpg",
                "url": "https://example.com/video.mp4",
                "created_at": "2026-07-28T12:00:00Z",
            },
            {
                "kind": "image",
                "kind_v2": "video_cover",
                "media_role": "video_cover",
                "is_video_cover": True,
                "media_index": 1,
                "covers_video_media_index": 0,
                "covers_video_url": "https://example.com/video.mp4",
                "url": "https://example.com/cover.jpg",
                "created_at": "2026-07-28T12:00:00Z",
            },
        ],
    }
    event = parse_instagram_event(raw)
    assert event.is_collab is True
    assert event.collab_with == ["brandB"]
    assert event.is_paid_partnership is True
    assert event.media[0]["media_role"] == "video"
    assert event.media[1]["is_video_cover"] is True
    assert event.media[1]["covers_video_media_index"] == 0


def test_parse_location_tag():
    raw = {
        "platform": "instagram",
        "username": "user",
        "display_name": "User",
        "user_avatar": "",
        "user_followers": 0,
        "user_id": "3",
        "key": "story1",
        "timestamp": "2026-07-28T12:00:00Z",
        "seen_at": "2026-07-28T12:00:00Z",
        "text": "",
        "post_type": "story",
        "location": {"name": "Eiffel Tower", "lat": 48.8584, "lng": 2.2945},
        "media": [],
    }
    event = parse_instagram_event(raw)
    assert event.location == {"name": "Eiffel Tower", "lat": 48.8584, "lng": 2.2945}


def test_parse_defaults_missing_optional_fields():
    raw = {
        "platform": "instagram",
        "username": "user",
        "display_name": "User",
        "user_avatar": "",
        "user_followers": 0,
        "user_id": "3",
        "key": "carousel1",
        "timestamp": "2026-07-28T12:00:00Z",
        "seen_at": "2026-07-28T12:00:00Z",
        "text": "",
        "post_type": "carousel",
    }
    event = parse_instagram_event(raw)
    assert event.media == []
    assert event.is_collab is None
    assert event.location is None
