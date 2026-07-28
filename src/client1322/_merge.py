"""Additive merge + dedup for progressive X/Twitter tweet events.

Per https://1322.io/docs ("Additive Merge (Recommended)"), X tweets arrive
across up to four progressive stages (``tweet.mini.update`` ->
``tweet.update`` -> ``tweet.update.expanded`` -> ``tweet.full``), each one
enriching the previous. The documented merge rules, by ``tweet.id``:

- use the **longest** ``body.text``
- **union** all media arrays
- keep the **deepest** ``subtweet`` chain
- take the **highest** metric values
- **never overwrite** a populated field with null/empty; a later stage may
  lack data an earlier stage had

Everything below operates on plain ``dict`` payloads (the raw
``TwitterMiniTweet`` / ``TwitterTweet`` JSON shape) so it has no dependency
on the dataclass wrappers in :mod:`client1322.platforms.x` and is trivial to
unit test.
"""

from __future__ import annotations

import copy
from collections import OrderedDict
from typing import Any

_MEDIA_ARRAY_KEYS = ("images", "videos", "thumbnails")
_PROXIED_ARRAY_KEYS = ("images", "thumbnails")
_METRIC_KEYS = ("likes", "quotes", "replies", "retweets")


def _union_preserve_order(a: list[Any], b: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    out: list[Any] = []
    for item in (*a, *b):
        key = item if isinstance(item, (str, int, float, bool, type(None))) else repr(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _merge_body(dst: dict[str, Any], src: dict[str, Any]) -> None:
    src_text = src.get("text")
    dst_text = dst.get("text")
    if isinstance(src_text, str) and (
        not isinstance(dst_text, str) or len(src_text) > len(dst_text)
    ):
        dst["text"] = src_text
    # Other body fields (urls, mentions, components) are not called out with
    # a specific merge rule in the docs; apply the general "later stage
    # enriches, never overwrite with null" rule.
    for key, val in src.items():
        if key == "text" or val is None:
            continue
        dst[key] = val


def _merge_media(dst: dict[str, Any], src: dict[str, Any]) -> None:
    for key in _MEDIA_ARRAY_KEYS:
        if key in dst or key in src:
            dst[key] = _union_preserve_order(dst.get(key) or [], src.get(key) or [])

    src_proxied = src.get("proxied")
    if src_proxied is None:
        return
    dst_proxied = dst.get("proxied")
    if dst_proxied is None:
        dst["proxied"] = copy.deepcopy(src_proxied)
        return
    for key in _PROXIED_ARRAY_KEYS:
        if key in dst_proxied or key in src_proxied:
            dst_proxied[key] = _union_preserve_order(
                dst_proxied.get(key) or [], src_proxied.get(key) or []
            )


def _merge_metrics(dst: dict[str, Any], src: dict[str, Any]) -> None:
    for key in _METRIC_KEYS:
        src_val = src.get(key)
        if src_val is None:
            continue
        dst_val = dst.get(key)
        if dst_val is None or src_val > dst_val:
            dst[key] = src_val

    src_adv = src.get("advanced")
    if src_adv is None:
        return  # never overwrite a populated 'advanced' block with null
    dst_adv = dst.get("advanced")
    if dst_adv is None:
        dst["advanced"] = copy.deepcopy(src_adv)
        return
    src_views = src_adv.get("views")
    if src_views is not None and (
        dst_adv.get("views") is None or src_views > dst_adv["views"]
    ):
        dst_adv["views"] = src_views


def _chain_depth(node: dict[str, Any] | None) -> int:
    depth = 0
    while node is not None:
        depth += 1
        node = node.get("subtweet")
    return depth


def _merge_subtweet(
    dst_val: dict[str, Any] | None, src_val: dict[str, Any] | None
) -> dict[str, Any] | None:
    if src_val is None:
        return dst_val
    if dst_val is None:
        return copy.deepcopy(src_val)
    if dst_val.get("id") == src_val.get("id"):
        merged = copy.deepcopy(dst_val)
        _merge_tweet_dicts(merged, src_val)
        return merged
    # Different referenced tweets (shouldn't normally happen across stages of
    # the same root tweet) -- keep whichever chain resolves deeper.
    return dst_val if _chain_depth(dst_val) >= _chain_depth(src_val) else copy.deepcopy(src_val)


def _merge_tweet_dicts(dst: dict[str, Any], src: dict[str, Any]) -> None:
    """Merge ``src`` (a later/enriching stage) into ``dst`` in place."""
    for key, src_val in src.items():
        if key == "body" and isinstance(src_val, dict):
            dst["body"] = dst.get("body") or {}
            _merge_body(dst["body"], src_val)
        elif key == "media" and isinstance(src_val, dict):
            dst["media"] = dst.get("media") or {}
            _merge_media(dst["media"], src_val)
        elif key == "metrics" and isinstance(src_val, dict):
            dst["metrics"] = dst.get("metrics") or {}
            _merge_metrics(dst["metrics"], src_val)
        elif key == "subtweet":
            dst["subtweet"] = _merge_subtweet(dst.get("subtweet"), src_val)
        elif src_val is not None:
            dst[key] = src_val
        # src_val is None and key already absent/None in dst: nothing to do.
        # src_val is None and dst has a populated value: never overwrite.


def merge_tweet(base: dict[str, Any] | None, incoming: dict[str, Any]) -> dict[str, Any]:
    """Merge ``incoming`` (a raw tweet dict) on top of ``base``.

    ``base`` may be ``None`` (first time this tweet id is seen). Returns a
    new merged dict; neither input is mutated.
    """
    if base is None:
        return copy.deepcopy(incoming)
    merged = copy.deepcopy(base)
    _merge_tweet_dicts(merged, incoming)
    return merged


class TweetMerger:
    """Bounded, in-memory cache that applies :func:`merge_tweet` by tweet id.

    This is purely a client-side convenience for consumers who want a single
    up-to-date view of each tweet across its progressive stages, matching
    the docs' recommended merge behavior. It has no bearing on 1322's own
    infrastructure -- it just deduplicates and enriches events on your side.

    ``max_entries`` bounds memory use: once exceeded, the least-recently-
    merged tweet is evicted (simple LRU), independent of stream volume.
    """

    def __init__(self, max_entries: int = 500) -> None:
        if max_entries <= 0:
            raise ValueError("max_entries must be > 0")
        self.max_entries = max_entries
        self._cache: "OrderedDict[str, dict[str, Any]]" = OrderedDict()

    def __len__(self) -> int:
        return len(self._cache)

    def get(self, tweet_id: str) -> dict[str, Any] | None:
        return self._cache.get(tweet_id)

    def merge(self, tweet: dict[str, Any]) -> dict[str, Any]:
        """Merge ``tweet`` into the cache and return the merged result."""
        tweet_id = tweet.get("id")
        if not tweet_id:
            raise ValueError("tweet dict has no 'id' field")
        merged = merge_tweet(self._cache.get(tweet_id), tweet)
        self._cache[tweet_id] = merged
        self._cache.move_to_end(tweet_id)
        while len(self._cache) > self.max_entries:
            self._cache.popitem(last=False)
        return merged

    def clear(self) -> None:
        self._cache.clear()


__all__ = ["merge_tweet", "TweetMerger"]
