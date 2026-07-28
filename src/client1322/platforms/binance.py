"""Binance Square: REST management API + WebSocket event envelope.

Ground truth: https://1322.io/docs ("Binance Square" reference).

- REST base: https://binance.1322.io
- WebSocket: wss://binance.1322.io/{ws_path}?key={ws_key} -- path and key
  come from GET /v1/dashboard. If you don't pass them explicitly, the
  adapter fetches /v1/dashboard once before connecting.
- Auth: header X-Api-Key (REST). WebSocket: key= query parameter.
- Every WS frame is ``{type, data}``; ``type`` is ``"binance.post"`` or
  ``"binance.pin.update"``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypedDict, Union

from ..exceptions import UnknownEventError
from ._base import BaseAdapter

REST_BASE = "https://binance.1322.io"
WS_HOST = "binance.1322.io"

ContentType = Literal["post", "video", "space", "article"]
Tendency = Literal["bullish", "bearish", ""]


class MediaItem(TypedDict, total=False):
    url: str
    type: str
    width: int
    height: int


class PostPollOption(TypedDict, total=False):
    label: str
    votes: int


class PostPoll(TypedDict, total=False):
    options: list[PostPollOption]
    ends_at: str


class PostQuote(TypedDict, total=False):
    id: str
    username: str
    text: str
    url: str


class PostTranslation(TypedDict, total=False):
    language: str
    text: str


class SpaceLiveReplay(TypedDict, total=False):
    url: str
    duration_seconds: int


class PostResolvedLink(TypedDict, total=False):
    url: str
    title: str
    description: str
    image: str


class BinancePost(TypedDict, total=False):
    id: str
    username: str
    display_name: str
    avatar_url: str
    square_uid: str
    content_type: ContentType
    title: str
    text: str
    web_link: str
    share_link: str
    is_reply: bool
    parent_id: str
    reply_count: int
    like_count: int
    comment_count: int
    share_count: int
    view_count: int
    tendency: Tendency
    bullish_ratio: float
    bearish_ratio: float
    coin_pairs: list[str]
    hashtags: list[str]
    mentions: list[str]
    media: list[MediaItem]
    poll: PostPoll
    quote: PostQuote
    reply_to: PostQuote
    translation: PostTranslation
    live_replay: SpaceLiveReplay
    resolved_links: list[PostResolvedLink]
    published_at: str
    detected_at: str


class PinUpdate(TypedDict, total=False):
    username: str
    display_name: str
    avatar_url: str
    square_uid: str
    added: list[BinancePost]
    removed: list[BinancePost]
    removed_ids: list[str]
    note: str
    detected_at: str


@dataclass(slots=True)
class BinancePostEvent:
    type: Literal["binance.post"]
    post: BinancePost
    raw: dict[str, Any]


@dataclass(slots=True)
class BinancePinUpdateEvent:
    type: Literal["binance.pin.update"]
    pin: PinUpdate
    raw: dict[str, Any]


BinanceEvent = Union[BinancePostEvent, BinancePinUpdateEvent]


def parse_binance_event(raw: dict[str, Any]) -> BinanceEvent:
    """Parse one decoded Binance Square WebSocket frame: ``{type, data}``."""
    event_type = raw.get("type")
    data = raw.get("data", {})
    if event_type == "binance.post":
        return BinancePostEvent(type=event_type, post=data, raw=raw)
    if event_type == "binance.pin.update":
        return BinancePinUpdateEvent(type=event_type, pin=data, raw=raw)
    raise UnknownEventError(f"Unrecognized Binance Square event type: {event_type!r}")


class BinanceAdapter(BaseAdapter):
    """Binance Square connection + REST management API."""

    rest_base = REST_BASE

    def __init__(
        self,
        api_key: str,
        *,
        ws_path: str | None = None,
        ws_key: str | None = None,
        ws_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key, **kwargs)
        self.ws_path = ws_path
        self.ws_key = ws_key
        self._ws_url_override = ws_url

    async def _resolve_ws(self) -> None:
        if self._ws_url_override:
            return
        if self.ws_path and self.ws_key:
            return
        data = await self.dashboard()
        self.ws_path = self.ws_path or data.get("ws_path")
        self.ws_key = self.ws_key or data.get("ws_key")

    def _ws_url(self) -> str:
        if self._ws_url_override:
            return self._ws_url_override
        if not (self.ws_path and self.ws_key):
            raise RuntimeError(
                "ws_path/ws_key not resolved yet; call 'await adapter._resolve_ws()' "
                "(done automatically by stream()), or pass ws_path/ws_key/ws_url "
                "explicitly."
            )
        path = self.ws_path if self.ws_path.startswith("/") else f"/{self.ws_path}"
        return f"wss://{WS_HOST}{path}?key={self.ws_key}"

    def _ws_headers(self) -> dict[str, str]:
        return {}

    def _rest_headers(self) -> dict[str, str]:
        return {"X-Api-Key": self.api_key}

    def _parse(self, raw: dict[str, Any]) -> BinanceEvent:
        return parse_binance_event(raw)

    async def stream(self):  # type: ignore[override]
        await self._resolve_ws()
        async for event in super().stream():
            yield event

    # -- REST: GET /v1/dashboard, POST /v1/track, POST /v1/untrack

    async def dashboard(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/dashboard")

    async def track(self, username: str) -> dict[str, Any]:
        return await self._request("POST", "/v1/track", json={"username": username})

    async def untrack(self, username: str) -> dict[str, Any]:
        return await self._request("POST", "/v1/untrack", json={"username": username})


__all__ = [
    "BinanceAdapter",
    "BinanceEvent",
    "BinancePostEvent",
    "BinancePinUpdateEvent",
    "BinancePost",
    "PinUpdate",
    "parse_binance_event",
]
