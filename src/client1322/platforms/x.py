"""X / Twitter: REST management API + WebSocket event types.

Ground truth: https://1322.io/docs ("X / Twitter" reference).

- REST base: https://api.1322.io
- WebSocket: wss://ws.normal.1322.io/ws/normal (Normal tier) or
  wss://ws.ultimate.1322.io/ws/ultimate (Ultimate tier)
- Auth: header X-API-Key, or Authorization: Bearer <key>, or query key=<key>
  (REST); WebSocket: same headers, or query token=<key>.
- Rate limits: reads 1200/min (20/s), writes 600/min (10/s). Bulk add/remove
  accept up to 200 identifiers per request.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypedDict, Union

from ..exceptions import ConfigurationError, UnknownEventError
from ._base import BaseAdapter

NORMAL_WS_URL = "wss://ws.normal.1322.io/ws/normal"
ULTIMATE_WS_URL = "wss://ws.ultimate.1322.io/ws/ultimate"
REST_BASE = "https://api.1322.io"

Tier = Literal["normal", "ultimate"]
TweetType = Literal["TWEET", "RETWEET", "QUOTE", "REPLY"]

# --------------------------------------------------------------------------
# Raw JSON shapes (TypedDicts), mirroring the TS interfaces in the docs.
# --------------------------------------------------------------------------


class TwitterUrlEntity(TypedDict):
    name: str
    url: str
    tco: str


class TwitterMentionEntity(TypedDict):
    id: str
    name: str
    handle: str


class VerificationLabel(TypedDict, total=False):
    description: str
    badge: str | None
    url: str | None


class VerificationBadge(TypedDict):
    type: Literal["none", "blue", "gold"]
    label: VerificationLabel | None


VerifiedField = Union[bool, VerificationBadge]


class TwitterMiniUser(TypedDict, total=False):
    id: str
    handle: str
    name: str
    avatar: str | None
    verified: VerifiedField
    profile: dict[str, Any]
    metrics: dict[str, Any]


class TwitterUserProfileUrl(TypedDict):
    name: str
    url: str
    tco: str


class TwitterUserProfileDescription(TypedDict):
    text: str
    urls: list[TwitterUrlEntity]


class TwitterUserProfile(TypedDict):
    name: str
    location: str | None
    avatar: str | None
    banner: str | None
    pinned: list[str]
    url: TwitterUserProfileUrl | None
    description: TwitterUserProfileDescription


class TwitterUserMetrics(TypedDict):
    likes: int
    media: int
    tweets: int
    friends: int
    followers: int
    following: int


class TwitterUser(TypedDict):
    id: str
    handle: str
    private: bool
    verified: VerifiedField
    sensitive: bool
    restricted: bool
    joined_at: int
    profile: TwitterUserProfile
    metrics: TwitterUserMetrics


class TwitterMiniTweetBody(TypedDict):
    text: str
    urls: list[TwitterUrlEntity]
    mentions: list[TwitterMentionEntity]


class TwitterMiniTweetMediaProxied(TypedDict):
    images: list[str]


class TwitterMiniTweetMedia(TypedDict):
    images: list[str]
    videos: list[str]
    thumbnails: list[str]
    proxied: TwitterMiniTweetMediaProxied | None


class TwitterRef(TypedDict):
    id: str
    handle: str


class TwitterMiniTweet(TypedDict):
    id: str
    type: TweetType
    created_at: int
    author: TwitterMiniUser
    subtweet: "TwitterMiniTweet | None"
    reply: TwitterRef | None
    quoted: TwitterRef | None
    body: TwitterMiniTweetBody
    media: TwitterMiniTweetMedia


class TwitterTextComponent(TypedDict):
    type: Literal["text"]
    text: str
    bold: bool
    italics: bool


class TwitterImageComponent(TypedDict):
    type: Literal["image"]
    url: str


class TwitterVideoComponent(TypedDict):
    type: Literal["video"]
    url: str


TweetBodyComponent = Union[TwitterTextComponent, TwitterImageComponent, TwitterVideoComponent]


class TwitterTweetBody(TypedDict):
    text: str
    urls: list[TwitterUrlEntity]
    mentions: list[TwitterMentionEntity]
    components: list[TweetBodyComponent]


class TwitterTweetMediaProxied(TypedDict):
    images: list[str]
    thumbnails: list[str]


class TwitterTweetMedia(TypedDict):
    images: list[str]
    videos: list[str]
    thumbnails: list[str]
    proxied: TwitterTweetMediaProxied | None


# "from" is a Python keyword, so this TypedDict must use the functional
# (dict-literal) form rather than the class-body form.
TwitterGrokMessage = TypedDict(
    "TwitterGrokMessage",
    {"from": Literal["USER", "AGENT"], "message": str, "images": list[str]},
)


class TwitterGrok(TypedDict):
    id: str
    conversation: list[TwitterGrokMessage]


class TwitterCard(TypedDict):
    url: str
    image: str
    title: str
    description: str


class TwitterPollChoice(TypedDict):
    label: str
    count: int


class TwitterPoll(TypedDict):
    ends_at: int
    updated_at: int
    choices: list[TwitterPollChoice]


TwitterArticleTextStyle = TypedDict(
    "TwitterArticleTextStyle",
    {"from": int, "to": int, "text": Literal["bold", "italics", "strikethrough"]},
)

TwitterArticleTextUrl = TypedDict(
    "TwitterArticleTextUrl", {"from": int, "to": int, "url": str}
)


class TwitterArticleTextLine(TypedDict):
    text: str
    styles: list[TwitterArticleTextStyle]
    urls: list[TwitterArticleTextUrl]


class TwitterArticleDividerComponent(TypedDict):
    type: Literal["divider"]


class TwitterArticleTextComponent(TypedDict):
    type: Literal["text"]
    variant: Literal[
        "header-one",
        "header-two",
        "paragraph",
        "blockquote",
        "ordered-list",
        "unordered-list",
        "latex-box",
        "markdown-box",
    ]
    lines: list[TwitterArticleTextLine]


class TwitterArticleMediaComponent(TypedDict):
    type: Literal["media"]
    variant: Literal["image", "gif", "video"]
    url: str
    thumbnail: str
    caption: str | None


class TwitterArticleEmbeddedTweet(TypedDict):
    id: str
    url: str
    object: "TwitterTweet | None"


class TwitterArticleTweetComponent(TypedDict):
    type: Literal["tweet"]
    tweet: TwitterArticleEmbeddedTweet


ArticleComponent = Union[
    TwitterArticleDividerComponent,
    TwitterArticleTextComponent,
    TwitterArticleMediaComponent,
    TwitterArticleTweetComponent,
]


class TwitterArticleBody(TypedDict):
    text: str
    components: list[ArticleComponent]


class TwitterArticle(TypedDict):
    id: str
    title: str
    thumbnail: str | None
    created_at: int
    updated_at: int
    body: TwitterArticleBody


class TwitterAdvancedMetrics(TypedDict):
    views: int


class TwitterTweetMetrics(TypedDict):
    likes: int
    quotes: int
    replies: int
    retweets: int
    advanced: TwitterAdvancedMetrics | None


class TwitterCommunity(TypedDict):
    id: str
    name: str
    url: str


class TwitterTweet(TypedDict, total=False):
    id: str
    type: TweetType
    created_at: int
    author: TwitterUser
    subtweet: "TwitterTweet | None"
    reply: TwitterRef | None
    quoted: TwitterRef | None
    body: TwitterTweetBody
    media: TwitterTweetMedia
    grok: TwitterGrok | None
    card: TwitterCard | None
    poll: TwitterPoll | None
    article: TwitterArticle | None
    metrics: TwitterTweetMetrics
    community: TwitterCommunity


# --------------------------------------------------------------------------
# Event envelopes
# --------------------------------------------------------------------------


@dataclass(slots=True)
class MiniTweetUpdate:
    type: Literal["tweet.mini.update"]
    tweet: TwitterMiniTweet
    raw: dict[str, Any]


@dataclass(slots=True)
class TweetUpdate:
    type: Literal["tweet.update"]
    tweet: TwitterTweet
    raw: dict[str, Any]


@dataclass(slots=True)
class TweetUpdateExpanded:
    type: Literal["tweet.update.expanded"]
    tweet: TwitterTweet
    raw: dict[str, Any]


@dataclass(slots=True)
class TweetFull:
    type: Literal["tweet.full"]
    tweet: TwitterTweet
    raw: dict[str, Any]


@dataclass(slots=True)
class DeletedTweet:
    type: Literal["tweet.deleted"]
    tweet: TwitterTweet
    deleted_at: int
    raw: dict[str, Any]


@dataclass(slots=True)
class ProfileUpdate:
    type: Literal["profile.update"]
    user: TwitterUser
    before: TwitterUser
    raw: dict[str, Any]


@dataclass(slots=True)
class FollowingUpdate:
    type: Literal["following.update"]
    change: Literal["followed", "unfollowed"]
    following: TwitterUser
    user: TwitterUser
    raw: dict[str, Any]


@dataclass(slots=True)
class ProfilePinnedUpdate:
    type: Literal["profile.pinned.update"]
    user: TwitterUser
    pinned: list[TwitterTweet]
    raw: dict[str, Any]


@dataclass(slots=True)
class ProfileUnpinnedUpdate:
    type: Literal["profile.unpinned.update"]
    user: TwitterUser
    pinned: list[TwitterTweet]
    raw: dict[str, Any]


XEvent = Union[
    MiniTweetUpdate,
    TweetUpdate,
    TweetUpdateExpanded,
    TweetFull,
    DeletedTweet,
    ProfileUpdate,
    FollowingUpdate,
    ProfilePinnedUpdate,
    ProfileUnpinnedUpdate,
]

_EVENT_TYPES = {
    "tweet.mini.update",
    "tweet.update",
    "tweet.update.expanded",
    "tweet.full",
    "tweet.deleted",
    "profile.update",
    "following.update",
    "profile.pinned.update",
    "profile.unpinned.update",
}


def parse_x_event(raw: dict[str, Any]) -> XEvent:
    """Parse one decoded X WebSocket frame into a typed event.

    Every frame has ``{id, type, source: "1322"}`` plus type-specific fields
    (see https://1322.io/docs, "WS Data Types & Events").
    """
    event_type = raw.get("type")
    if event_type == "tweet.mini.update":
        return MiniTweetUpdate(type=event_type, tweet=raw["tweet"], raw=raw)
    if event_type == "tweet.update":
        return TweetUpdate(type=event_type, tweet=raw["tweet"], raw=raw)
    if event_type == "tweet.update.expanded":
        return TweetUpdateExpanded(type=event_type, tweet=raw["tweet"], raw=raw)
    if event_type == "tweet.full":
        return TweetFull(type=event_type, tweet=raw["tweet"], raw=raw)
    if event_type == "tweet.deleted":
        return DeletedTweet(
            type=event_type,
            tweet=raw["tweet"],
            deleted_at=raw.get("deleted_at", 0),
            raw=raw,
        )
    if event_type == "profile.update":
        return ProfileUpdate(type=event_type, user=raw["user"], before=raw["before"], raw=raw)
    if event_type == "following.update":
        return FollowingUpdate(
            type=event_type,
            change=raw["change"],
            following=raw["following"],
            user=raw["user"],
            raw=raw,
        )
    if event_type == "profile.pinned.update":
        return ProfilePinnedUpdate(
            type=event_type, user=raw["user"], pinned=raw.get("pinned", []), raw=raw
        )
    if event_type == "profile.unpinned.update":
        return ProfileUnpinnedUpdate(
            type=event_type, user=raw["user"], pinned=raw.get("pinned", []), raw=raw
        )
    raise UnknownEventError(f"Unrecognized X event type: {event_type!r}")


def tweet_of(event: XEvent) -> TwitterTweet | TwitterMiniTweet | None:
    """Return the tweet payload carried by ``event``, if any."""
    if isinstance(event, (MiniTweetUpdate, TweetUpdate, TweetUpdateExpanded, TweetFull, DeletedTweet)):
        return event.tweet
    return None


# --------------------------------------------------------------------------
# Adapter
# --------------------------------------------------------------------------


class XAdapter(BaseAdapter):
    """X / Twitter connection + REST management API."""

    rest_base = REST_BASE

    def __init__(self, api_key: str, *, tier: Tier = "normal", **kwargs: Any) -> None:
        if tier not in ("normal", "ultimate"):
            raise ConfigurationError(f"tier must be 'normal' or 'ultimate', got {tier!r}")
        super().__init__(api_key, **kwargs)
        self.tier: Tier = tier

    def _ws_url(self) -> str:
        return NORMAL_WS_URL if self.tier == "normal" else ULTIMATE_WS_URL

    def _ws_headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key}

    def _rest_headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key}

    def _parse(self, raw: dict[str, Any]) -> XEvent:
        return parse_x_event(raw)

    # -- REST: GET /v1/tracked, GET /v1/keys, POST/DELETE /v1/tracked,
    # GET /v1/data/tweet/:id, GET /v1/resolve/username/:username, GET /v1/health

    async def list_tracked(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/tracked")

    async def list_keys(self) -> dict[str, Any]:
        """GET /v1/keys -- all keys (normal + ultimate) for hybrid accounts."""
        return await self._request("GET", "/v1/keys")

    @staticmethod
    def _identifiers_param(identifiers: str | list[str]) -> str:
        if isinstance(identifiers, str):
            return identifiers
        return ",".join(identifiers)

    async def add_tracked(
        self,
        identifiers: str | list[str],
        id_type: Literal["username", "id"] = "username",
    ) -> dict[str, Any]:
        """POST /v1/tracked. Accepts up to 200 identifiers per call."""
        body = {"identifiers": self._identifiers_param(identifiers), "type": id_type}
        return await self._request("POST", "/v1/tracked", json=body)

    async def remove_tracked(
        self,
        identifiers: str | list[str],
        id_type: Literal["username", "id"] = "username",
    ) -> dict[str, Any]:
        """DELETE /v1/tracked. Accepts up to 200 identifiers per call."""
        body = {"identifiers": self._identifiers_param(identifiers), "type": id_type}
        return await self._request("DELETE", "/v1/tracked", json=body)

    async def get_tweet(
        self, tweet_id: str, *, full: bool = False, expanded: bool = False
    ) -> dict[str, Any]:
        """GET /v1/data/tweet/:id."""
        params: dict[str, str] = {}
        if full:
            params["full"] = "true"
        if expanded:
            params["expanded"] = "true"
        return await self._request("GET", f"/v1/data/tweet/{tweet_id}", params=params)

    async def resolve_username(self, username: str) -> dict[str, Any]:
        """GET /v1/resolve/username/:username."""
        return await self._request("GET", f"/v1/resolve/username/{username}")

    async def health(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/health")


__all__ = [
    "XAdapter",
    "XEvent",
    "MiniTweetUpdate",
    "TweetUpdate",
    "TweetUpdateExpanded",
    "TweetFull",
    "DeletedTweet",
    "ProfileUpdate",
    "FollowingUpdate",
    "ProfilePinnedUpdate",
    "ProfileUnpinnedUpdate",
    "parse_x_event",
    "tweet_of",
    "TwitterTweet",
    "TwitterMiniTweet",
    "TwitterUser",
    "TwitterMiniUser",
    "VerificationBadge",
]
