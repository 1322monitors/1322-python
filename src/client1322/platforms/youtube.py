"""YouTube: triple event model (upload, upgrade, deletion).

Ground truth: https://1322.io/docs/youtube and https://1322.io/docs
("YouTube" reference, "Event architecture").

- REST base: https://youtube.1322.io (``X-Api-Key`` or
  ``Authorization: Bearer``). ``GET /v1/dashboard`` returns ``ws_url`` and
  ``ws_key``; ``GET /v1/list``, ``POST /v1/track`` and ``POST /v1/untrack``
  manage tracked channels.
- WebSocket: ``wss://youtube.1322.io/{ws_path}?key={ws_key}``, i.e. the
  dashboard ``ws_url`` with ``?key=<ws_key>`` appended.

What this client wraps today: the WebSocket stream and its three event
types (upload / upgrade / deletion). It does not wrap YouTube REST yet:
there are no ``track``/``untrack``/``list_tracked``/``dashboard`` helpers on
:class:`YouTubeAdapter`, and it does not fetch the WebSocket URL for you.
Pass ``ws_url`` with the key already in it; call the documented REST
endpoints with your own HTTP client for now.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypedDict, Union

from ..exceptions import ConfigurationError, UnknownEventError
from ._base import BaseAdapter

#: YouTube REST host (https://1322.io/docs/youtube). This client does not
#: wrap YouTube REST yet, so ws_url is mandatory (see module docstring).
REST_BASE = "https://youtube.1322.io"

VideoSubtype = Literal["video", "short"]


class YouTubeChannelRef(TypedDict):
    # Every channel field is string | null (https://1322.io/docs).
    id: str | None
    name: str | None
    url: str | None
    avatar: str | None


#: ``video.metadata`` is documented as an open object (``Record<string,
#: unknown>``), so it has no fixed keys.
YouTubeVideoMetadata = dict[str, Any]


class _YouTubeVideoRefFields(TypedDict):
    id: str
    url: str
    title: str | None
    description: str | None
    published_at: str | None
    updated_at: str | None


class YouTubeVideoRef(_YouTubeVideoRefFields, total=False):
    view_count: int
    duration_display: str
    metadata: YouTubeVideoMetadata


class YouTubeImages(TypedDict):
    # Every images field is string | null; "chosen" is the best image
    # available at detection time.
    seed: str | None
    chosen: str | None
    thumbnail_small: str | None


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
    """YouTube connection. YouTube REST is not wrapped yet (see module docstring)."""

    rest_base = REST_BASE

    def __init__(self, api_key: str, *, ws_url: str, **kwargs: Any) -> None:
        super().__init__(api_key, **kwargs)
        if not ws_url:
            raise ConfigurationError(
                "YouTube requires an explicit ws_url: take ws_url and ws_key "
                "from GET https://youtube.1322.io/v1/dashboard (or the API "
                "access page in your 1322 dashboard) and pass "
                "ws_url=<ws_url>?key=<ws_key>. See https://1322.io/docs/youtube."
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
