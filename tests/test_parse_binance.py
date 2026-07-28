"""Parsing of Binance Square WebSocket frames: {type, data} envelope.

Shapes match the documented BinancePost / WsEnvelope / PinUpdate interfaces
at https://1322.io/docs.
"""

from __future__ import annotations

import pytest

from client1322.exceptions import UnknownEventError
from client1322.platforms.binance import (
    BinancePinUpdateEvent,
    BinancePostEvent,
    parse_binance_event,
)


def test_parse_binance_post_event():
    raw = {
        "type": "binance.post",
        "data": {
            "id": "p1",
            "username": "CZ_Binance",
            "display_name": "CZ",
            "avatar_url": "https://example.com/a.jpg",
            "square_uid": "123456789",
            "content_type": "post",
            "text": "BTC looking strong",
            "is_reply": False,
            "tendency": "bullish",
            "coin_pairs": ["BTCUSDT", "ETHUSDT"],
            "like_count": 100,
            "published_at": "2026-07-28T12:00:00Z",
            "detected_at": "2026-07-28T12:00:00.180Z",
        },
    }
    event = parse_binance_event(raw)
    assert isinstance(event, BinancePostEvent)
    assert event.type == "binance.post"
    assert event.post["username"] == "CZ_Binance"
    assert event.post["tendency"] == "bullish"
    assert event.post["coin_pairs"] == ["BTCUSDT", "ETHUSDT"]
    assert event.raw is raw


def test_parse_binance_pin_update_event():
    raw = {
        "type": "binance.pin.update",
        "data": {
            "username": "CZ_Binance",
            "display_name": "CZ",
            "added": [{"id": "p2", "username": "CZ_Binance", "is_reply": False}],
            "removed": [],
            "removed_ids": [],
            "detected_at": "2026-07-28T12:00:01Z",
        },
    }
    event = parse_binance_event(raw)
    assert isinstance(event, BinancePinUpdateEvent)
    assert event.type == "binance.pin.update"
    assert event.pin["added"][0]["id"] == "p2"


def test_parse_reply_with_quote_and_poll():
    raw = {
        "type": "binance.post",
        "data": {
            "id": "p3",
            "username": "trader1",
            "is_reply": True,
            "parent_id": "p2",
            "quote": {"id": "p0", "username": "other", "text": "original"},
            "poll": {"options": [{"label": "yes", "votes": 5}, {"label": "no", "votes": 2}]},
        },
    }
    event = parse_binance_event(raw)
    assert event.post["is_reply"] is True
    assert event.post["quote"]["username"] == "other"
    assert event.post["poll"]["options"][0]["votes"] == 5


def test_unknown_binance_event_type_raises():
    with pytest.raises(UnknownEventError):
        parse_binance_event({"type": "binance.something.else", "data": {}})
