"""Instagram: REST management API + WebSocket post payload.

Ground truth: https://1322.io/docs ("Instagram" reference).

- REST base: https://1322.io
- WebSocket: wss://1322.io/IG?key={api_key} -- the REST API key doubles as
  the WebSocket key, there is no separate ws_path/ws_key round trip.
- Auth: header Authorization: Bearer <key> or X-API-Key: <key> (REST).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypedDict

from ._base import BaseAdapter

REST_BASE = "https://1322.io"
WS_URL_TEMPLATE = "wss://1322.io/IG?key={api_key}"

PostType = Literal["post", "reel", "story", "carousel"]
MediaKind = Literal["image", "video"]
MediaKindV2 = Literal["image", "video_cover", "video"]


class InstagramLocation(TypedDict, total=False):
    name: str
    lat: float
    lng: float


class InstagramMediaAttachment(TypedDict, total=False):
    kind: MediaKind
    kind_v2: MediaKindV2
    media_role: MediaKindV2
    is_video_cover: bool
    media_index: int
    carousel_index: int
    video_index: int
    cover_media_index: int
    cover_url: str
    covers_video_media_index: int
    covers_video_url: str
    url: str
    width: int
    height: int
    created_at: str


@dataclass(slots=True)
class InstagramPostEvent:
    """An ``InstagramPost`` WebSocket payload (raw frame, no envelope)."""

    platform: str
    username: str
    display_name: str
    user_avatar: str
    user_followers: int
    user_id: str
    key: str
    timestamp: str
    seen_at: str
    text: str
    post_type: PostType
    media_count: int | None
    hashtags: list[str] | None
    mentions: list[str] | None
    media: list[InstagramMediaAttachment]
    is_collab: bool | None
    collab_with: list[str] | None
    is_pinned: bool | None
    is_paid_partnership: bool | None
    location: InstagramLocation | None
    raw: dict[str, Any]


def parse_instagram_event(raw: dict[str, Any]) -> InstagramPostEvent:
    """Parse one decoded Instagram WebSocket frame (a full ``InstagramPost``)."""
    return InstagramPostEvent(
        platform=raw.get("platform", "instagram"),
        username=raw.get("username", ""),
        display_name=raw.get("display_name", ""),
        user_avatar=raw.get("user_avatar", ""),
        user_followers=raw.get("user_followers", 0),
        user_id=raw.get("user_id", ""),
        key=raw.get("key", ""),
        timestamp=raw.get("timestamp", ""),
        seen_at=raw.get("seen_at", ""),
        text=raw.get("text", ""),
        post_type=raw.get("post_type", "post"),
        media_count=raw.get("media_count"),
        hashtags=raw.get("hashtags"),
        mentions=raw.get("mentions"),
        media=raw.get("media") or [],
        is_collab=raw.get("is_collab"),
        collab_with=raw.get("collab_with"),
        is_pinned=raw.get("is_pinned"),
        is_paid_partnership=raw.get("is_paid_partnership"),
        location=raw.get("location"),
        raw=raw,
    )


class InstagramAdapter(BaseAdapter):
    """Instagram connection + REST management API."""

    rest_base = REST_BASE

    def _ws_url(self) -> str:
        return WS_URL_TEMPLATE.format(api_key=self.api_key)

    def _ws_headers(self) -> dict[str, str]:
        return {}

    def _rest_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _parse(self, raw: dict[str, Any]) -> InstagramPostEvent:
        return parse_instagram_event(raw)

    # -- REST: GET /v1/health, GET /v1/limits, GET /v1/list, POST /v1/track,
    # POST /v1/untrack

    async def health(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/health")

    async def limits(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/limits")

    async def list_tracked(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/list")

    async def track(self, username: str) -> dict[str, Any]:
        return await self._request("POST", "/v1/track", json={"username": username})

    async def untrack(self, username: str) -> dict[str, Any]:
        return await self._request("POST", "/v1/untrack", json={"username": username})


__all__ = [
    "InstagramAdapter",
    "InstagramPostEvent",
    "InstagramMediaAttachment",
    "InstagramLocation",
    "parse_instagram_event",
]
