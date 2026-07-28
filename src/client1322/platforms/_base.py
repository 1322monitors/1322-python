"""Shared WebSocket reconnect loop + REST plumbing for one 1322 platform.

Each concrete adapter (:mod:`client1322.platforms.x`,
:mod:`client1322.platforms.truth`, etc.) implements the small set of
abstract hooks below; everything else -- connecting, auto-reconnect with
backoff, JSON decoding, dispatching to the per-platform parser, and REST
request plumbing -- lives here once.
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any, AsyncIterator

import aiohttp

from .._backoff import BackoffPolicy
from ..exceptions import APIError

logger = logging.getLogger("client1322")

#: aiohttp message types that mean "this connection is over, reconnect."
_TERMINAL_WS_TYPES = (
    aiohttp.WSMsgType.CLOSED,
    aiohttp.WSMsgType.CLOSE,
    aiohttp.WSMsgType.CLOSING,
    aiohttp.WSMsgType.ERROR,
)


class BaseAdapter(ABC):
    """Base class for a single platform's connection + REST logic."""

    #: REST base URL for this platform, e.g. "https://api.1322.io".
    rest_base: str

    def __init__(
        self,
        api_key: str,
        *,
        session: aiohttp.ClientSession | None = None,
        auto_reconnect: bool = True,
        backoff_base: float = 1.0,
        backoff_cap: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self._session = session
        self._owns_session = session is None
        self.auto_reconnect = auto_reconnect
        self._backoff = BackoffPolicy(base=backoff_base, cap=backoff_cap)
        self._closed = False
        self._ws: aiohttp.ClientWebSocketResponse | None = None

    # -- lifecycle ---------------------------------------------------------

    async def __aenter__(self) -> "BaseAdapter":
        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        self._closed = False
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        self._closed = True
        if self._ws is not None and not self._ws.closed:
            await self._ws.close()
        self._ws = None
        if self._owns_session and self._session is not None:
            await self._session.close()

    def _require_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            raise RuntimeError(
                "No open session. Use 'async with Client(...) as client:' "
                "(or await adapter.__aenter__()) before streaming or making "
                "REST calls."
            )
        return self._session

    # -- hooks implemented by each platform ---------------------------------

    @abstractmethod
    def _ws_url(self) -> str:
        """Return the WebSocket URL to connect to."""

    @abstractmethod
    def _ws_headers(self) -> dict[str, str]:
        """Return extra headers to send on the WebSocket handshake."""

    @abstractmethod
    def _rest_headers(self) -> dict[str, str]:
        """Return auth headers to send on REST requests."""

    @abstractmethod
    def _parse(self, raw: dict[str, Any]) -> Any:
        """Turn one decoded JSON frame into a typed event object."""

    # -- streaming -----------------------------------------------------------

    async def stream(self) -> AsyncIterator[Any]:
        """Connect (with auto-reconnect) and yield parsed events forever.

        Reconnection follows 1322's documented policy: exponential backoff
        starting at 1s, doubling, capped at 30s (see
        :mod:`client1322._backoff`). No events are queued while
        disconnected -- this matches the documented server behavior, so a
        client that is offline will simply miss whatever happened during
        that window, the same as any other 1322 WebSocket client.

        aiohttp answers server-sent WebSocket pings with pongs at the
        protocol layer automatically; callers do not need to handle this.
        """
        self._closed = False
        while not self._closed:
            session = self._require_session()
            url = self._ws_url()
            try:
                async with session.ws_connect(
                    url, headers=self._ws_headers(), heartbeat=30
                ) as ws:
                    self._ws = ws
                    self._backoff.reset()
                    logger.debug("client1322: connected to %s", url)
                    async for message in ws:
                        if message.type == aiohttp.WSMsgType.TEXT:
                            try:
                                payload = json.loads(message.data)
                            except json.JSONDecodeError:
                                logger.warning(
                                    "client1322: dropped non-JSON frame: %.200s",
                                    message.data,
                                )
                                continue
                            try:
                                yield self._parse(payload)
                            except Exception:
                                logger.exception(
                                    "client1322: failed to parse event: %.200s",
                                    message.data,
                                )
                        elif message.type in _TERMINAL_WS_TYPES:
                            break
                        # BINARY/PING/PONG frames: nothing to surface to callers.
            except (aiohttp.ClientError, OSError) as exc:
                logger.warning("client1322: websocket connection lost: %s", exc)
            finally:
                self._ws = None

            if self._closed or not self.auto_reconnect:
                return

            delay = self._backoff.next()
            logger.info("client1322: reconnecting in %.1fs", delay)
            await asyncio.sleep(delay)

    # -- REST ------------------------------------------------------------

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        session = self._require_session()
        url = f"{self.rest_base}{path}"
        extra_headers = kwargs.pop("headers", None) or {}
        headers = {**self._rest_headers(), **extra_headers}
        async with session.request(method, url, headers=headers, **kwargs) as resp:
            text = await resp.text()
            data: Any = None
            if text:
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    data = text
            if resp.status >= 400:
                raise APIError(
                    f"{method} {path} failed with HTTP {resp.status}",
                    status=resp.status,
                    payload=data,
                )
            return data
