"""Parsing of the YouTube triple event model: upload, upgrade, deletion.

Shapes match UploadMessage / UpgradeMessage / DeletionMessage in
https://1322.io/docs.
"""

from __future__ import annotations

import pytest

from client1322.exceptions import UnknownEventError
from client1322.platforms.youtube import (
    DeletionMessage,
    UploadMessage,
    UpgradeMessage,
    parse_youtube_event,
)


def test_parse_upload_message():
    raw = {
        "type": "upload",
        "subtype": "video",
        "channel": {"id": "UC123", "name": "Example Channel", "url": "https://youtube.com/@example"},
        "video": {
            "id": "vid123",
            "url": "https://youtube.com/watch?v=vid123",
            "title": "My Video",
            "metadata": {"duration_seconds": 600, "category": "Tech"},
        },
        "images": {"seed": "https://i.ytimg.com/vi/vid123/seed.jpg", "chosen": None},
    }
    event = parse_youtube_event(raw)
    assert isinstance(event, UploadMessage)
    assert event.subtype == "video"
    assert event.channel["name"] == "Example Channel"
    assert event.video["id"] == "vid123"
    assert event.video["metadata"]["duration_seconds"] == 600
    assert event.images["chosen"] is None


def test_parse_upload_message_short_subtype():
    raw = {
        "type": "upload",
        "subtype": "short",
        "channel": {"id": None, "name": "Unknown", "url": None},
        "video": {"id": "s1", "url": "https://youtube.com/shorts/s1", "title": None},
        "images": {"seed": None, "chosen": None},
    }
    event = parse_youtube_event(raw)
    assert event.subtype == "short"
    assert event.channel["id"] is None
    assert event.video["title"] is None


def test_parse_upgrade_message():
    raw = {
        "type": "upgrade",
        "upgrade": {"kind": "image", "video_id": "vid123", "url": "https://i.ytimg.com/vi/vid123/hq.jpg"},
    }
    event = parse_youtube_event(raw)
    assert isinstance(event, UpgradeMessage)
    assert event.upgrade["video_id"] == "vid123"
    assert event.upgrade["kind"] == "image"


def test_parse_deletion_message():
    raw = {
        "type": "deletion",
        "video": {"id": "vid123", "url": "https://youtube.com/watch?v=vid123"},
        "channel": {"id": "UC123", "name": "Example Channel", "url": "https://youtube.com/@example"},
    }
    event = parse_youtube_event(raw)
    assert isinstance(event, DeletionMessage)
    assert event.video["id"] == "vid123"
    assert event.channel["name"] == "Example Channel"


def test_unknown_youtube_event_type_raises():
    with pytest.raises(UnknownEventError):
        parse_youtube_event({"type": "renamed"})
