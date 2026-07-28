"""News: REST management API + WebSocket article payload.

Ground truth: https://1322.io/docs ("News Feed" reference).

- REST base: https://newsfeed.1322.io
- WebSocket: wss://newsfeed.1322.io/{ws_path}?key={ws_key} -- path and key
  come from GET /v1/dashboard. If you don't pass them explicitly, the
  adapter fetches /v1/dashboard once before connecting.
- Auth: header X-Api-Key (REST). WebSocket: key= query parameter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypedDict

from ._base import BaseAdapter

REST_BASE = "https://newsfeed.1322.io"
WS_HOST = "newsfeed.1322.io"


class NewsMediaAttachment(TypedDict, total=False):
    url: str
    type: Literal["image", "video"]
    caption: str


@dataclass(slots=True)
class NewsArticleEvent:
    """A ``WebSocketNewsFeedPayload`` frame (raw, no envelope)."""

    feed: str
    guid: str
    url: str
    title: str
    publish_time: str
    modified_time: str | None
    primary_category: str
    categories: list[str]
    author: str
    keywords: list[str]
    description: str
    summary: str
    media: list[NewsMediaAttachment]
    full_text: str
    language: str | None
    copyright: str | None
    event_type: Literal["LIVE_POST"]
    sent_time: str
    raw: dict[str, Any]


def parse_news_event(raw: dict[str, Any]) -> NewsArticleEvent:
    """Parse one decoded News WebSocket frame (a full article payload)."""
    return NewsArticleEvent(
        feed=raw.get("feed", ""),
        guid=raw.get("guid", ""),
        url=raw.get("url", ""),
        title=raw.get("title", ""),
        publish_time=raw.get("publish_time", ""),
        modified_time=raw.get("modified_time"),
        primary_category=raw.get("primary_category", ""),
        categories=raw.get("categories") or [],
        author=raw.get("author", ""),
        keywords=raw.get("keywords") or [],
        description=raw.get("description", ""),
        summary=raw.get("summary", ""),
        media=raw.get("media") or [],
        full_text=raw.get("full_text", ""),
        language=raw.get("language"),
        copyright=raw.get("copyright"),
        event_type=raw.get("_event_type", "LIVE_POST"),
        sent_time=raw.get("_sent_time", ""),
        raw=raw,
    )


class NewsAdapter(BaseAdapter):
    """News connection + REST management API."""

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

    def _parse(self, raw: dict[str, Any]) -> NewsArticleEvent:
        return parse_news_event(raw)

    async def stream(self):  # type: ignore[override]
        await self._resolve_ws()
        async for event in super().stream():
            yield event

    # -- REST: GET /v1/dashboard, POST /v1/subscribe, POST /v1/unsubscribe

    async def dashboard(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/dashboard")

    async def subscribe(self, feed: str) -> dict[str, Any]:
        return await self._request("POST", "/v1/subscribe", json={"feed": feed})

    async def unsubscribe(self, feed: str) -> dict[str, Any]:
        return await self._request("POST", "/v1/unsubscribe", json={"feed": feed})


__all__ = [
    "NewsAdapter",
    "NewsArticleEvent",
    "NewsMediaAttachment",
    "parse_news_event",
]
