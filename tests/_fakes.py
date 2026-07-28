"""Fake aiohttp session/websocket/response for network-free adapter tests.

Not a test module itself (no ``test_`` prefix) -- imported by tests that
need to drive :class:`client1322.client.Client` end to end without opening
a real socket. Duck-types just the surface ``BaseAdapter`` touches:
``session.ws_connect(...)`` and ``session.request(...)``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeWSMessage:
    type: Any
    data: Any


class FakeWebSocket:
    """A scripted sequence of incoming WS messages, then a clean end."""

    def __init__(self, messages: list[FakeWSMessage]) -> None:
        self._messages = list(messages)
        self.closed = False

    def __aiter__(self) -> "FakeWebSocket":
        return self

    async def __anext__(self) -> FakeWSMessage:
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)

    async def close(self) -> None:
        self.closed = True


class _WSConnectCM:
    """What ``session.ws_connect(...)`` returns: an async context manager."""

    def __init__(self, outcome: BaseException | FakeWebSocket) -> None:
        self._outcome = outcome

    async def __aenter__(self) -> FakeWebSocket:
        if isinstance(self._outcome, BaseException):
            raise self._outcome
        return self._outcome

    async def __aexit__(self, *exc_info: Any) -> bool:
        return False


class FakeResponse:
    def __init__(self, status: int, body: Any) -> None:
        self.status = status
        self._body = body

    async def text(self) -> str:
        if self._body is None:
            return ""
        if isinstance(self._body, str):
            return self._body
        return json.dumps(self._body)


class _RequestCM:
    def __init__(self, response: FakeResponse) -> None:
        self._response = response

    async def __aenter__(self) -> FakeResponse:
        return self._response

    async def __aexit__(self, *exc_info: Any) -> bool:
        return False


@dataclass
class FakeSession:
    """Records calls and plays back a scripted sequence of outcomes.

    ``ws_script``: list of ``FakeWebSocket`` instances or exceptions,
    consumed one per ``ws_connect`` call.
    ``rest_script``: list of ``(status, body)`` tuples, consumed one per
    ``request`` call.
    """

    ws_script: list[Any] = field(default_factory=list)
    rest_script: list[tuple[int, Any]] = field(default_factory=list)
    ws_connect_calls: list[dict[str, Any]] = field(default_factory=list)
    request_calls: list[dict[str, Any]] = field(default_factory=list)
    closed: bool = False

    def ws_connect(self, url: str, headers: dict[str, str] | None = None, **kwargs: Any) -> _WSConnectCM:
        self.ws_connect_calls.append({"url": url, "headers": headers})
        if not self.ws_script:
            raise AssertionError("FakeSession.ws_connect called more times than scripted")
        return _WSConnectCM(self.ws_script.pop(0))

    def request(
        self, method: str, url: str, headers: dict[str, str] | None = None, **kwargs: Any
    ) -> _RequestCM:
        self.request_calls.append({"method": method, "url": url, "headers": headers, "kwargs": kwargs})
        if not self.rest_script:
            raise AssertionError("FakeSession.request called more times than scripted")
        status, body = self.rest_script.pop(0)
        return _RequestCM(FakeResponse(status, body))

    async def close(self) -> None:
        self.closed = True
