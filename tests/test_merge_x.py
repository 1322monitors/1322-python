"""Additive merge across progressive X tweet stages, per docs:

- longest body.text wins
- media arrays are unioned
- deepest subtweet chain wins
- highest metric values win
- a populated field is never overwritten with null
"""

from __future__ import annotations

from client1322 import TweetMerger, merge_tweet


def _mini(tweet_id="1", text="short", **overrides):
    base = {
        "id": tweet_id,
        "type": "TWEET",
        "created_at": 1000,
        "author": {"id": "u1", "handle": "alice"},
        "subtweet": None,
        "reply": None,
        "quoted": None,
        "body": {"text": text, "urls": [], "mentions": []},
        "media": {"images": ["img1.jpg"], "videos": [], "thumbnails": [], "proxied": None},
    }
    base.update(overrides)
    return base


def test_merge_with_no_base_returns_a_copy():
    mini = _mini()
    merged = merge_tweet(None, mini)
    assert merged == mini
    assert merged is not mini  # must not alias the input


def test_longest_text_wins_regardless_of_order():
    mini = _mini(text="short")
    full = _mini(text="a much longer and fully expanded tweet body")
    merged = merge_tweet(mini, full)
    assert merged["body"]["text"] == "a much longer and fully expanded tweet body"

    # And the reverse: merging a shorter later stage must not truncate.
    merged_reverse = merge_tweet(full, mini)
    assert merged_reverse["body"]["text"] == "a much longer and fully expanded tweet body"


def test_media_arrays_are_unioned_not_replaced():
    mini = _mini(media={"images": ["a.jpg"], "videos": [], "thumbnails": [], "proxied": None})
    full = _mini(
        media={"images": ["b.jpg"], "videos": ["c.mp4"], "thumbnails": ["c_thumb.jpg"], "proxied": None}
    )
    merged = merge_tweet(mini, full)
    assert merged["media"]["images"] == ["a.jpg", "b.jpg"]
    assert merged["media"]["videos"] == ["c.mp4"]
    assert merged["media"]["thumbnails"] == ["c_thumb.jpg"]


def test_media_union_deduplicates():
    mini = _mini(media={"images": ["a.jpg", "b.jpg"], "videos": [], "thumbnails": [], "proxied": None})
    full = _mini(media={"images": ["b.jpg", "c.jpg"], "videos": [], "thumbnails": [], "proxied": None})
    merged = merge_tweet(mini, full)
    assert merged["media"]["images"] == ["a.jpg", "b.jpg", "c.jpg"]


def test_proxied_media_is_unioned():
    mini = _mini(
        media={
            "images": [],
            "videos": [],
            "thumbnails": [],
            "proxied": {"images": ["p1.jpg"], "thumbnails": []},
        }
    )
    full = _mini(
        media={
            "images": [],
            "videos": [],
            "thumbnails": [],
            "proxied": {"images": ["p2.jpg"], "thumbnails": ["pt1.jpg"]},
        }
    )
    merged = merge_tweet(mini, full)
    assert merged["media"]["proxied"]["images"] == ["p1.jpg", "p2.jpg"]
    assert merged["media"]["proxied"]["thumbnails"] == ["pt1.jpg"]


def test_highest_metric_values_win():
    early = _mini(metrics={"likes": 10, "quotes": 1, "replies": 2, "retweets": 3, "advanced": None})
    later = _mini(metrics={"likes": 5, "quotes": 9, "replies": 2, "retweets": 30, "advanced": {"views": 500}})
    merged = merge_tweet(early, later)
    assert merged["metrics"] == {
        "likes": 10,  # earlier value was higher, kept
        "quotes": 9,  # later value was higher, taken
        "replies": 2,
        "retweets": 30,
        "advanced": {"views": 500},
    }


def test_advanced_metrics_null_never_overwrites_populated():
    early = _mini(metrics={"likes": 1, "quotes": 1, "replies": 1, "retweets": 1, "advanced": {"views": 42}})
    later = _mini(metrics={"likes": 2, "quotes": 2, "replies": 2, "retweets": 2, "advanced": None})
    merged = merge_tweet(early, later)
    assert merged["metrics"]["advanced"] == {"views": 42}
    assert merged["metrics"]["likes"] == 2


def test_deepest_subtweet_chain_wins():
    shallow = _mini(subtweet={"id": "s1", "subtweet": None})
    deep = _mini(
        subtweet={"id": "s1", "subtweet": {"id": "s2", "subtweet": {"id": "s3", "subtweet": None}}}
    )
    merged = merge_tweet(shallow, deep)
    assert merged["subtweet"]["id"] == "s1"
    assert merged["subtweet"]["subtweet"]["id"] == "s2"
    assert merged["subtweet"]["subtweet"]["subtweet"]["id"] == "s3"

    # Order independence: deep first, then shallow -- deep chain still wins.
    merged_reverse = merge_tweet(deep, shallow)
    assert merged_reverse["subtweet"]["subtweet"]["subtweet"]["id"] == "s3"


def test_null_never_overwrites_a_populated_field():
    early = _mini(card={"url": "https://example.com", "title": "t", "description": "d", "image": "i"})
    later = _mini(card=None)
    merged = merge_tweet(early, later)
    assert merged["card"] == {
        "url": "https://example.com",
        "title": "t",
        "description": "d",
        "image": "i",
    }


def test_later_non_null_field_replaces_earlier_null():
    early = _mini(card=None)
    later = _mini(card={"url": "https://example.com", "title": "t", "description": "d", "image": "i"})
    merged = merge_tweet(early, later)
    assert merged["card"]["url"] == "https://example.com"


def test_merge_does_not_mutate_inputs():
    mini = _mini(text="short")
    full = _mini(text="a longer piece of text here")
    mini_copy = dict(mini)
    full_copy = dict(full)
    merge_tweet(mini, full)
    assert mini == mini_copy
    assert full == full_copy


def test_tweet_merger_caches_by_id_and_evicts_lru():
    merger = TweetMerger(max_entries=2)
    merger.merge(_mini(tweet_id="1"))
    merger.merge(_mini(tweet_id="2"))
    assert len(merger) == 2
    merger.merge(_mini(tweet_id="3"))
    assert len(merger) == 2
    assert merger.get("1") is None  # evicted, oldest
    assert merger.get("2") is not None
    assert merger.get("3") is not None


def test_tweet_merger_progressive_stages_end_to_end():
    merger = TweetMerger()
    mini_stage = _mini(tweet_id="42", text="Breaking:")
    update_stage = _mini(
        tweet_id="42",
        text="Breaking: full",
        media={"images": ["extra.jpg"], "videos": [], "thumbnails": [], "proxied": None},
        metrics={"likes": 3, "quotes": 0, "replies": 0, "retweets": 0, "advanced": None},
    )
    full_stage = _mini(
        tweet_id="42",
        text="Breaking: full story here",
        metrics={"likes": 3, "quotes": 0, "replies": 0, "retweets": 5, "advanced": {"views": 1000}},
    )

    merger.merge(mini_stage)
    merger.merge(update_stage)
    result = merger.merge(full_stage)

    assert result["body"]["text"] == "Breaking: full story here"
    assert result["media"]["images"] == ["img1.jpg", "extra.jpg"]
    assert result["metrics"]["likes"] == 3
    assert result["metrics"]["retweets"] == 5
    assert result["metrics"]["advanced"] == {"views": 1000}
