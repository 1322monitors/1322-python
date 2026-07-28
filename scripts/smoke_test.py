#!/usr/bin/env python
"""Standalone post-install smoke test -- no pytest, no API key required.

Proves that an *installed* `client1322` (e.g. from the built wheel) actually
imports and functions as documented: connects (against a mocked WebSocket
transport, since no live 1322 key exists in this environment), receives
frames, reconnects after a drop, parses them into the documented typed
events, and exercises a REST helper.

Run:

    python scripts/smoke_test.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from client1322 import Client
from client1322.platforms.x import MiniTweetUpdate


# -- minimal fake aiohttp session/websocket, self-contained ------------------


@dataclass
class _FakeWSMessage:
    type: Any
    data: Any


class _FakeWebSocket:
    def __init__(self, messages: list[_FakeWSMessage]) -> None:
        self._messages = list(messages)
        self.closed = False

    def __aiter__(self) -> "_FakeWebSocket":
        return self

    async def __anext__(self) -> _FakeWSMessage:
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)

    async def close(self) -> None:
        self.closed = True


class _WSConnectCM:
    def __init__(self, outcome: Any) -> None:
        self._outcome = outcome

    async def __aenter__(self) -> _FakeWebSocket:
        if isinstance(self._outcome, BaseException):
            raise self._outcome
        return self._outcome

    async def __aexit__(self, *exc_info: Any) -> bool:
        return False


class _FakeResponse:
    def __init__(self, status: int, body: Any) -> None:
        self.status = status
        self._body = body

    async def text(self) -> str:
        return json.dumps(self._body)


class _RequestCM:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response

    async def __aenter__(self) -> _FakeResponse:
        return self._response

    async def __aexit__(self, *exc_info: Any) -> bool:
        return False


@dataclass
class _FakeSession:
    ws_script: list[Any] = field(default_factory=list)
    rest_script: list[tuple[int, Any]] = field(default_factory=list)
    ws_connect_calls: int = 0

    def ws_connect(self, url: str, headers: dict | None = None, **kwargs: Any) -> _WSConnectCM:
        self.ws_connect_calls += 1
        return _WSConnectCM(self.ws_script.pop(0))

    def request(self, method: str, url: str, headers: dict | None = None, **kwargs: Any) -> _RequestCM:
        status, body = self.rest_script.pop(0)
        return _RequestCM(_FakeResponse(status, body))

    async def close(self) -> None:
        pass


def _mini_tweet_frame(tweet_id: str, text: str) -> dict:
    return {
        "id": f"evt-{tweet_id}",
        "type": "tweet.mini.update",
        "source": "1322",
        "tweet": {
            "id": tweet_id,
            "type": "TWEET",
            "created_at": 1700000000000,
            "author": {"id": "1", "handle": "smoke_test"},
            "subtweet": None,
            "reply": None,
            "quoted": None,
            "body": {"text": text, "urls": [], "mentions": []},
            "media": {"images": [], "videos": [], "thumbnails": [], "proxied": None},
        },
    }


def _text_msg(payload: dict) -> _FakeWSMessage:
    return _FakeWSMessage(type=aiohttp.WSMsgType.TEXT, data=json.dumps(payload))


async def main() -> int:
    print("client1322 smoke test (mocked WebSocket transport, no live key)")

    session = _FakeSession(
        ws_script=[
            aiohttp.ClientConnectionError("simulated connection refused"),
            _FakeWebSocket([_text_msg(_mini_tweet_frame("1", "hello from the smoke test"))]),
        ],
        rest_script=[(200, {"success": True, "tier": "normal", "trackedAccounts": []})],
    )

    events = []
    client = Client(
        platform="x",
        api_key="smoke-test-key",
        session=session,
        backoff_base=0.0,
        backoff_cap=0.0,
    )

    async with client:
        tracked = await client.list_tracked()
        assert tracked["success"] is True, "REST helper did not return the scripted response"
        print(f"REST OK: list_tracked() -> {tracked}")

        agen = client.stream()
        async for event in agen:
            events.append(event)
            break
        await agen.aclose()

    assert session.ws_connect_calls == 2, (
        f"expected 1 failed + 1 successful connect attempt (auto-reconnect), got {session.ws_connect_calls}"
    )
    assert len(events) == 1, f"expected exactly 1 parsed event, got {len(events)}"
    assert isinstance(events[0], MiniTweetUpdate), f"unexpected event type: {type(events[0])}"
    assert events[0].tweet["body"]["text"] == "hello from the smoke test"
    print(f"WebSocket OK: reconnected after a simulated drop, parsed {events[0]!r}")

    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
