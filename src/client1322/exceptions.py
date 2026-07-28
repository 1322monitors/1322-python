"""Exceptions raised by client1322."""

from __future__ import annotations

from typing import Any


class Client1322Error(Exception):
    """Base class for all errors raised by this library."""


class ConfigurationError(Client1322Error):
    """Raised when a :class:`~client1322.client.Client` is misconfigured.

    Examples: an unknown ``platform`` name, or a platform (Truth Social,
    News, Binance Square, YouTube) that needs WebSocket connection details
    the caller did not supply and that 1322 does not expose a way to infer.
    """


class UnknownEventError(Client1322Error):
    """Raised when a WebSocket frame does not match any documented event shape."""


class APIError(Client1322Error):
    """Raised when a 1322 REST call returns an HTTP error status."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        payload: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.payload = payload

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"APIError({str(self)!r}, status={self.status!r}, payload={self.payload!r})"
