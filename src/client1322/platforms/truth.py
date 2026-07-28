"""Truth Social: REST management API + WebSocket post payload.

Ground truth: https://1322.io/docs ("Truth Social" reference).

- REST base: https://truth.1322.io
- WebSocket: wss://truth.1322.io/{path}?key={ws_key} -- path and WS key are
  provided in your dashboard configuration. Unlike News and Binance Square,
  1322's docs do not expose a REST endpoint that returns these for Truth
  Social, so callers must supply them (or a full ``ws_url``).
- Auth: header X-Api-Key (REST). WebSocket: key= query parameter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

from ..exceptions import ConfigurationError
from ._base import BaseAdapter

REST_BASE = "https://truth.1322.io"
WS_HOST = "truth.1322.io"


class TruthSocialMediaAttachment(TypedDict, total=False):
    kind: str  # 'image' | 'video' | 'gifv' | 'audio' | other
    url: str
    poster_url: str
    created_at: str
    source: str  # 'own' | 'quoted' | 'nested_quoted'


class TruthSocialAuthor(TypedDict, total=False):
    id: str
    username: str
    display_name: str
    avatar: str


class TruthSocialCard(TypedDict, total=False):
    url: str
    title: str
    description: str
    image: str


class TruthSocialQuotedInner(TypedDict, total=False):
    key: str
    text: str
    url: str
    author: TruthSocialAuthor


class TruthSocialQuoted(TypedDict, total=False):
    key: str
    text: str
    url: str
    author: TruthSocialAuthor
    quoted: TruthSocialQuotedInner


@dataclass(slots=True)
class TruthPostEvent:
    """A ``TruthSocialPost`` WebSocket payload (raw frame, no envelope/type field)."""

    platform: str
    username: str
    display_name: str
    user_avatar: str
    user_following: int
    user_followers: int
    user_id: str
    key: str
    timestamp: str
    seen_at: str
    text: str
    is_quote: bool | None
    quoted: TruthSocialQuoted | None
    is_retruth: bool | None
    retruth_of_id: str | None
    retruth_of: TruthSocialAuthor | None
    card: TruthSocialCard | None
    media: list[TruthSocialMediaAttachment]
    raw: dict[str, Any]


def parse_truth_event(raw: dict[str, Any]) -> TruthPostEvent:
    """Parse one decoded Truth Social WebSocket frame.

    Every frame is a full ``TruthSocialPost`` object; there is no envelope
    or ``type`` discriminator (unlike X or Binance Square).
    """
    return TruthPostEvent(
        platform=raw.get("platform", "truth"),
        username=raw.get("username", ""),
        display_name=raw.get("display_name", ""),
        user_avatar=raw.get("user_avatar", ""),
        user_following=raw.get("user_following", 0),
        user_followers=raw.get("user_followers", 0),
        user_id=raw.get("user_id", ""),
        key=raw.get("key", ""),
        timestamp=raw.get("timestamp", ""),
        seen_at=raw.get("seen_at", ""),
        text=raw.get("text", ""),
        is_quote=raw.get("is_quote"),
        quoted=raw.get("quoted"),
        is_retruth=raw.get("is_retruth"),
        retruth_of_id=raw.get("retruth_of_id"),
        retruth_of=raw.get("retruth_of"),
        card=raw.get("card"),
        media=raw.get("media") or [],
        raw=raw,
    )


class TruthAdapter(BaseAdapter):
    """Truth Social connection + REST management API."""

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
        if ws_url is None and (ws_path is None or ws_key is None):
            raise ConfigurationError(
                "Truth Social needs ws_path and ws_key from your 1322 dashboard "
                "configuration (1322's docs do not publish a fixed WebSocket "
                "path or a REST endpoint that returns these for Truth Social, "
                "unlike News/Binance Square). Pass ws_path+ws_key, or pass a "
                "full ws_url directly. See https://1322.io/docs."
            )

    def _ws_url(self) -> str:
        if self._ws_url_override:
            return self._ws_url_override
        assert self.ws_path is not None and self.ws_key is not None
        path = self.ws_path if self.ws_path.startswith("/") else f"/{self.ws_path}"
        return f"wss://{WS_HOST}{path}?key={self.ws_key}"

    def _ws_headers(self) -> dict[str, str]:
        return {}

    def _rest_headers(self) -> dict[str, str]:
        return {"X-Api-Key": self.api_key}

    def _parse(self, raw: dict[str, Any]) -> TruthPostEvent:
        return parse_truth_event(raw)

    # -- REST: GET /health, GET /v1/status, GET /v1/list, GET /v1/limits,
    # POST /v1/track, POST /v1/untrack

    async def health(self) -> dict[str, Any]:
        return await self._request("GET", "/health")

    async def status(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/status")

    async def list_tracked(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/v1/list")

    async def limits(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/limits")

    async def track(self, handle: str) -> dict[str, Any]:
        return await self._request("POST", "/v1/track", json={"handle": handle})

    async def untrack(self, handle: str) -> dict[str, Any]:
        return await self._request("POST", "/v1/untrack", json={"handle": handle})


__all__ = [
    "TruthAdapter",
    "TruthPostEvent",
    "TruthSocialMediaAttachment",
    "TruthSocialAuthor",
    "TruthSocialCard",
    "TruthSocialQuoted",
    "parse_truth_event",
]
