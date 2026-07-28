"""The unified ``Client`` facade covering all six 1322 platforms.

.. code-block:: python

    from client1322 import Client

    async with Client(platform="x", api_key="...") as client:
        async for event in client.stream():
            print(event)

Every platform is reached through the same shape: construct a
:class:`Client`, use it as an async context manager, and iterate
:meth:`Client.stream`. What differs -- necessarily, since 1322 documents a
different REST/WebSocket contract per platform -- is the constructor
keyword arguments (see each adapter's docstring under
:mod:`client1322.platforms`) and the type of event object ``stream()``
yields. REST helpers (``track``, ``untrack``, ``list_tracked``, ``health``,
...) are looked up on the underlying adapter, so only the methods that
platform's documented API actually has are available.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Literal

from .exceptions import ConfigurationError
from .platforms._base import BaseAdapter
from .platforms.binance import BinanceAdapter
from .platforms.instagram import InstagramAdapter
from .platforms.news import NewsAdapter
from .platforms.truth import TruthAdapter
from .platforms.x import XAdapter
from .platforms.youtube import YouTubeAdapter

Platform = Literal["x", "twitter", "truth", "instagram", "news", "youtube", "binance"]

_ADAPTERS: dict[str, type[BaseAdapter]] = {
    "x": XAdapter,
    "twitter": XAdapter,
    "truth": TruthAdapter,
    "instagram": InstagramAdapter,
    "news": NewsAdapter,
    "youtube": YouTubeAdapter,
    "binance": BinanceAdapter,
}


class Client:
    """Unified async client for the 1322 real-time monitoring API.

    :param platform: one of ``"x"`` (alias ``"twitter"``), ``"truth"``,
        ``"instagram"``, ``"news"``, ``"youtube"``, ``"binance"``.
    :param api_key: the API key for that platform (from your 1322 dashboard).
    :param kwargs: forwarded to the platform's adapter constructor. Common
        ones: ``session`` (an existing ``aiohttp.ClientSession`` to reuse),
        ``auto_reconnect`` (default ``True``), ``backoff_base``/``backoff_cap``
        (default 1s / 30s, matching 1322's documented reconnect policy).
        X also takes ``tier`` (``"normal"`` or ``"ultimate"``). Truth Social
        takes ``ws_path``/``ws_key`` (or ``ws_url``). News and Binance Square
        take optional ``ws_path``/``ws_key``/``ws_url`` -- if omitted, they
        are fetched automatically from that platform's ``/v1/dashboard``.
        YouTube requires ``ws_url`` explicitly (see
        :mod:`client1322.platforms.youtube`).
    """

    def __init__(self, platform: Platform | str, api_key: str, **kwargs: Any) -> None:
        key = platform.lower()
        adapter_cls = _ADAPTERS.get(key)
        if adapter_cls is None:
            raise ConfigurationError(
                f"Unknown platform {platform!r}. Choose one of: "
                "x (or twitter), truth, instagram, news, youtube, binance."
            )
        self.platform: str = "x" if key == "twitter" else key
        self._adapter: BaseAdapter = adapter_cls(api_key, **kwargs)

    @property
    def adapter(self) -> BaseAdapter:
        """The underlying platform adapter, for advanced/typed access."""
        return self._adapter

    async def __aenter__(self) -> "Client":
        await self._adapter.__aenter__()
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self._adapter.__aexit__(*exc_info)

    async def close(self) -> None:
        await self._adapter.close()

    def stream(self) -> AsyncIterator[Any]:
        """Connect (with auto-reconnect) and yield typed events forever."""
        return self._adapter.stream()

    def __getattr__(self, name: str) -> Any:
        # Delegates platform-specific REST helpers (track/untrack/list_tracked/
        # health/dashboard/...) to the adapter, so each platform exposes
        # exactly the methods its documented REST API actually has.
        if name == "_adapter":
            # Guards against recursion if __init__ raised before this was set.
            raise AttributeError(name)
        try:
            return getattr(self._adapter, name)
        except AttributeError as exc:
            raise AttributeError(
                f"{self.platform!r} client has no attribute {name!r}"
            ) from exc

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"Client(platform={self.platform!r})"


__all__ = ["Client", "Platform"]
