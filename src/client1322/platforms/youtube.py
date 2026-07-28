"""YouTube: triple event model (upload, upgrade, deletion).

Ground truth: https://1322.io/docs ("YouTube" reference, "Event architecture").

Unlike the other five platforms, 1322's public docs describe the YouTube
*event payload contract* in full (upload / upgrade / deletion messages
below) but, as of this writing, do not publish a fixed WebSocket URL
pattern or a customer-facing REST tracked-account API for YouTube the way
they do for X, Truth Social, Instagram, News, and Binance Square. Rather
than guess at an undocumented endpoint, :class:`YouTubeAdapter` requires you
to supply the full ``ws_url`` from your dashboard configuration, and it only
implements event parsing -- no track/untrack/list REST helpers, because
1322's docs don't define them for this platform. Check
https://1322.io/docs directly if that changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypedDict, Union

from ..exceptions import ConfigurationError, UnknownEventError
from ._base import BaseAdapter

#: Host per 1322's published REST host list (https://1322.io/llms.txt).
#: No documented WebSocket path pattern exists for YouTube; ws_url is
#: mandatory (see module docstring).
REST_BASE = "https://youtube.1322.io"

VideoSubtype = Literal["video", "short"]


class YouTubeChannelRef(TypedDict):
    id: str | None
    name: str
    url: str | None


class YouTubeVideoMetadata(TypedDict, total=False):
    duration_seconds: int
    category: str


class YouTubeVideoRef(TypedDict):
    id: str
    url: str
    title: str | None
    metadata: YouTubeVideoMetadata | None


class YouTubeImages(TypedDict):
    seed: str | None
    chosen: str | None


class YouTubeUpgrade(TypedDict):
    kind: Literal["image"]
    video_id: str
    url: str


class YouTubeDeletedVideoRef(TypedDict):
    id: str
    url: str


@dataclass(slots=True)
class UploadMessage:
    type: Literal["upload"]
    subtype: VideoSubtype
    channel: YouTubeChannelRef
    video: YouTubeVideoRef
    images: YouTubeImages
    raw: dict[str, Any]


@dataclass(slots=True)
class UpgradeMessage:
    type: Literal["upgrade"]
    upgrade: YouTubeUpgrade
    raw: dict[str, Any]


@dataclass(slots=True)
class DeletionMessage:
    type: Literal["deletion"]
    video: YouTubeDeletedVideoRef
    channel: YouTubeChannelRef
    raw: dict[str, Any]


YouTubeEvent = Union[UploadMessage, UpgradeMessage, DeletionMessage]


def parse_youtube_event(raw: dict[str, Any]) -> YouTubeEvent:
    """Parse one decoded YouTube tracker frame (upload/upgrade/deletion)."""
    event_type = raw.get("type")
    if event_type == "upload":
        return UploadMessage(
            type=event_type,
            subtype=raw.get("subtype", "video"),
            channel=raw.get("channel", {}),
            video=raw.get("video", {}),
            images=raw.get("images", {}),
            raw=raw,
        )
    if event_type == "upgrade":
        return UpgradeMessage(type=event_type, upgrade=raw.get("upgrade", {}), raw=raw)
    if event_type == "deletion":
        return DeletionMessage(
            type=event_type,
            video=raw.get("video", {}),
            channel=raw.get("channel", {}),
            raw=raw,
        )
    raise UnknownEventError(f"Unrecognized YouTube event type: {event_type!r}")


class YouTubeAdapter(BaseAdapter):
    """YouTube connection. REST helpers are intentionally not provided (see module docstring)."""

    rest_base = REST_BASE

    def __init__(self, api_key: str, *, ws_url: str, **kwargs: Any) -> None:
        super().__init__(api_key, **kwargs)
        if not ws_url:
            raise ConfigurationError(
                "YouTube requires an explicit ws_url. 1322's public docs do not "
                "publish a fixed YouTube WebSocket path (unlike the other five "
                "platforms) -- copy the connection URL from your 1322 dashboard "
                "and pass it as ws_url=. See https://1322.io/docs."
            )
        self._ws_url_value = ws_url

    def _ws_url(self) -> str:
        return self._ws_url_value

    def _ws_headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key}

    def _rest_headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key}

    def _parse(self, raw: dict[str, Any]) -> YouTubeEvent:
        return parse_youtube_event(raw)


__all__ = [
    "YouTubeAdapter",
    "YouTubeEvent",
    "UploadMessage",
    "UpgradeMessage",
    "DeletionMessage",
    "parse_youtube_event",
]
