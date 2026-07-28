"""End-to-end Client.stream()/REST behavior against a fake aiohttp session.

No real socket is opened. This exercises the exact code path a real
connection would use (BaseAdapter.stream()'s reconnect loop, JSON decoding,
and per-platform parsing dispatch), just with a scripted transport -- the
same approach used for the post-install smoke test in scripts/smoke_test.py.
"""

from __future__ import annotations

import asyncio
import json

import aiohttp
import pytest

from client1322 import Client
from client1322.exceptions import APIError
from client1322.platforms.x import MiniTweetUpdate

from _fakes import FakeSession, FakeWebSocket, FakeWSMessage

MINI_TWEET_FRAME = {
    "id": "evt1",
    "type": "tweet.mini.update",
    "source": "1322",
    "tweet": {
        "id": "1",
        "type": "TWEET",
        "created_at": 1700000000000,
        "author": {"id": "1", "handle": "someone"},
        "subtweet": None,
        "reply": None,
        "quoted": None,
        "body": {"text": "hi", "urls": [], "mentions": []},
        "media": {"images": [], "videos": [], "thumbnails": [], "proxied": None},
    },
}


def _text_message(payload: dict) -> FakeWSMessage:
    return FakeWSMessage(type=aiohttp.WSMsgType.TEXT, data=json.dumps(payload))


def test_stream_yields_parsed_events_then_stops_without_auto_reconnect():
    async def run() -> list:
        ws = FakeWebSocket([_text_message(MINI_TWEET_FRAME), _text_message(MINI_TWEET_FRAME)])
        session = FakeSession(ws_script=[ws])
        client = Client(
            platform="x",
            api_key="test-key",
            session=session,
            auto_reconnect=False,
        )
        events = []
        async with client:
            async for event in client.stream():
                events.append(event)
        return events

    events = asyncio.run(run())
    assert len(events) == 2
    assert all(isinstance(e, MiniTweetUpdate) for e in events)
    assert events[0].tweet["id"] == "1"


def test_stream_reconnects_after_a_dropped_connection():
    async def run() -> tuple[list, FakeSession]:
        first_ws = FakeWebSocket([])  # connects, then immediately ends (drop)
        second_ws = FakeWebSocket([_text_message(MINI_TWEET_FRAME)])
        session = FakeSession(ws_script=[first_ws, second_ws])
        client = Client(
            platform="x",
            api_key="test-key",
            session=session,
            auto_reconnect=True,
            backoff_base=0.0,
            backoff_cap=0.0,
        )
        events = []
        agen = client.stream()
        async with client:
            async for event in agen:
                events.append(event)
                break
            await agen.aclose()
        return events, session

    events, session = asyncio.run(run())
    assert len(events) == 1
    assert len(session.ws_connect_calls) == 2  # first drop, then a real reconnect


def test_stream_reconnects_after_a_connection_error():
    async def run() -> tuple[list, FakeSession]:
        second_ws = FakeWebSocket([_text_message(MINI_TWEET_FRAME)])
        session = FakeSession(
            ws_script=[aiohttp.ClientConnectionError("refused"), second_ws]
        )
        client = Client(
            platform="x",
            api_key="test-key",
            session=session,
            backoff_base=0.0,
            backoff_cap=0.0,
        )
        events = []
        agen = client.stream()
        async with client:
            async for event in agen:
                events.append(event)
                break
            await agen.aclose()
        return events, session

    events, session = asyncio.run(run())
    assert len(events) == 1
    assert len(session.ws_connect_calls) == 2


def test_stream_uses_platform_specific_ws_headers_and_url():
    async def run() -> FakeSession:
        session = FakeSession(ws_script=[FakeWebSocket([])])
        client = Client(
            platform="x",
            api_key="secret-key",
            tier="ultimate",
            session=session,
            auto_reconnect=False,
        )
        async with client:
            async for _event in client.stream():
                pass
        return session

    session = asyncio.run(run())
    call = session.ws_connect_calls[0]
    assert call["url"] == "wss://ws.ultimate.1322.io/ws/ultimate"
    assert call["headers"] == {"X-API-Key": "secret-key"}


def test_list_tracked_rest_helper_builds_correct_request():
    async def run() -> tuple[dict, FakeSession]:
        session = FakeSession(
            rest_script=[(200, {"success": True, "tier": "normal", "trackedAccounts": []})]
        )
        client = Client(platform="x", api_key="secret-key", session=session)
        async with client:
            result = await client.list_tracked()
        return result, session

    result, session = asyncio.run(run())
    assert result == {"success": True, "tier": "normal", "trackedAccounts": []}
    call = session.request_calls[0]
    assert call["method"] == "GET"
    assert call["url"] == "https://api.1322.io/v1/tracked"
    assert call["headers"]["X-API-Key"] == "secret-key"


def test_rest_helper_raises_api_error_on_http_error_status():
    async def run() -> None:
        session = FakeSession(rest_script=[(429, {"error": "rate limited"})])
        client = Client(platform="x", api_key="secret-key", session=session)
        async with client:
            await client.list_tracked()

    with pytest.raises(APIError) as excinfo:
        asyncio.run(run())
    assert excinfo.value.status == 429
    assert excinfo.value.payload == {"error": "rate limited"}


def test_unknown_platform_raises_configuration_error():
    from client1322.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError):
        Client(platform="myspace", api_key="k")


def test_twitter_alias_resolves_to_x_platform():
    client = Client(platform="twitter", api_key="k")
    assert client.platform == "x"
